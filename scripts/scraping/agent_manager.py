# scripts/scraping/agent_manager.py - 代理池管理器
"""代理池管理器

管理所有 ScrapeAgent 的生命周期，提供任务提交入口。

核心职责：
1. 创建 / 销毁 / 替换子代理（ScrapeAgent）
2. 与 LoadBalancer 协作完成任务分发
3. 与 HealthMonitor 协作完成自动健康检测与替换
4. 与 ResultAggregator 协作完成结果聚合与存储

依赖关系（构造时注入）：
- LoadBalancer 接收 self.agents 字典引用，后续 add/remove 会同步生效
- HealthMonitor 接收 self（AgentManager），用于触发 replace_agent
- ResultAggregator 接收 dest_dir 与可选 audit_logger
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional

from scripts.scraping.config import PoolConfig, SourceConfig, load_config
from scripts.scraping.health_monitor import HealthMonitor
from scripts.scraping.load_balancer import LoadBalancer
from scripts.scraping.result_aggregator import ResultAggregator
from scripts.scraping.scrape_agent import ScrapeAgent, ScrapeResult, ScrapeTask
from scripts.utils.audit_logger import AuditLogger
from scripts.utils.circuit_breaker import CircuitBreaker
from scripts.utils.rate_limiter import TokenBucketLimiter

logger = logging.getLogger(__name__)


class AgentManager:
    """代理池管理器

    通过 create_agent 动态创建 ScrapeAgent（含真实 CircuitBreaker 与
    TokenBucketLimiter），由 LoadBalancer 负责任务分发，HealthMonitor
    负责周期性健康检测，ResultAggregator 负责结果持久化。

    Attributes:
        max_agents: 代理池容量上限
        agents: 当前活跃代理字典（key=agent_id, value=ScrapeAgent）
        load_balancer: 负载均衡器（持有 self.agents 引用）
        health_monitor: 健康监控器（持有 self 引用）
        result_aggregator: 结果聚合器
        audit_logger: 可选审计日志器
    """

    def __init__(
        self,
        max_agents: int = 20,
        health_check_interval: float = 30.0,
        config_path: Optional[Path] = None,
        audit_logger: Optional[AuditLogger] = None,
        dest_dir: Optional[Path] = None,
    ):
        """初始化代理池管理器

        Args:
            max_agents: 代理池容量上限，默认 20
            health_check_interval: 健康检测周期（秒），默认 30.0
            config_path: 可选的 YAML 配置文件路径，传入后可调用 initialize() 加载
            audit_logger: 可选审计日志器，会透传给 ScrapeAgent 与 ResultAggregator
            dest_dir: 结果存储根目录，默认 data/scraping
        """
        self.max_agents = max_agents
        # agents 字典被 LoadBalancer 引用，故 add/remove_agent 必须同步操作此字典
        self.agents: dict[str, ScrapeAgent] = {}
        self.load_balancer = LoadBalancer(self.agents)
        # HealthMonitor 持有 self 引用，用于触发 replace_agent
        self.health_monitor = HealthMonitor(self, health_check_interval)
        self.result_aggregator = ResultAggregator(
            dest_dir or Path("data/scraping"), audit_logger
        )
        self.audit_logger = audit_logger
        # 代理计数器：生成 agent_id 后缀，保证全局唯一
        self._agent_counter = 0
        self._config_path = config_path

    async def initialize(self) -> None:
        """从配置文件加载所有启用的数据源

        读取 self._config_path 指定的 YAML 文件，加载 PoolConfig（含
        max_agents / 健康检测参数）与 SourceConfig 列表，依次为每个
        enabled=True 的数据源创建代理。
        """
        if not self._config_path:
            logger.warning("未指定配置文件路径，跳过初始化")
            return

        sources, pool = load_config(self._config_path)
        self.max_agents = pool.max_agents
        # 同步健康检测参数，避免运行期不一致
        self.health_monitor.check_interval = pool.health_check_interval
        self.health_monitor.unhealthy_threshold = pool.unhealthy_threshold
        self.health_monitor.stale_timeout = pool.stale_timeout

        for source in sources:
            if not source.enabled:
                continue

            source_config = {
                "name": source.name,
                "type": source.source_type,
                "base_url": source.base_url,
                "parser": source.parser,
                "headers": source.headers,
                "rate_limit_capacity": source.rate_limit_capacity,
                "rate_limit_refill": source.rate_limit_refill,
                "circuit_failure_threshold": source.circuit_failure_threshold,
                "circuit_recovery_timeout": source.circuit_recovery_timeout,
            }

            await self.create_agent(source_config)

        logger.info("代理池初始化完成，共 %d 个代理", len(self.agents))

    async def create_agent(self, source_config: dict) -> str:
        """动态创建代理

        每个代理分配独立的 CircuitBreaker 与 TokenBucketLimiter，agent_id
        格式为 "<name>_<counter>"，保证全局唯一。

        Args:
            source_config: 数据源配置字典，必须含 name 字段

        Returns:
            新代理的 agent_id

        Raises:
            ValueError: 代理池已满
        """
        if len(self.agents) >= self.max_agents:
            raise ValueError(f"代理池已满，最大代理数: {self.max_agents}")

        self._agent_counter += 1
        agent_id = f"{source_config['name']}_{self._agent_counter}"

        # 熔断器：独立实例，失败阈值与冷却时间由配置驱动
        circuit_breaker = CircuitBreaker(
            failure_threshold=source_config.get("circuit_failure_threshold", 5),
            recovery_timeout=source_config.get("circuit_recovery_timeout", 30.0),
        )
        # 限流器：独立令牌桶，按数据源配置的容量与填充速率工作
        rate_limiter = TokenBucketLimiter(
            capacity=source_config.get("rate_limit_capacity", 5),
            refill_rate=source_config.get("rate_limit_refill", 5.0),
        )

        # 创建子代理
        agent = ScrapeAgent(
            agent_id=agent_id,
            source_config=source_config,
            circuit_breaker=circuit_breaker,
            rate_limiter=rate_limiter,
            audit_logger=self.audit_logger,
        )

        # 写入 agents 字典后，LoadBalancer 立即可见
        self.agents[agent_id] = agent
        self.load_balancer.add_agent(agent_id, agent)

        logger.info("创建代理: %s", agent_id)
        return agent_id

    async def destroy_agent(self, agent_id: str) -> None:
        """销毁代理

        关闭 HTTP 会话并从 agents 字典与 LoadBalancer 中移除。
        重复销毁同一 agent_id 是幂等的。

        Args:
            agent_id: 待销毁代理的唯一标识
        """
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        await agent.close()
        del self.agents[agent_id]
        self.load_balancer.remove_agent(agent_id)

        logger.info("销毁代理: %s", agent_id)

    async def replace_agent(self, agent_id: str) -> str:
        """替换不健康代理

        从旧代理读取 source_config，销毁后用相同配置重建一个新代理。
        调用方为 HealthMonitor（依据连续不健康次数或僵死超时触发）。

        Args:
            agent_id: 待替换代理的唯一标识

        Returns:
            新代理的 agent_id

        Raises:
            ValueError: 代理不存在
        """
        if agent_id not in self.agents:
            raise ValueError(f"代理不存在: {agent_id}")

        source_config = self.agents[agent_id].source_config

        await self.destroy_agent(agent_id)
        new_id = await self.create_agent(source_config)

        if self.audit_logger:
            self.audit_logger.log(
                operation="agent_replace",
                target=agent_id,
                success=True,
                new_agent_id=new_id,
            )

        logger.info("代理替换完成: %s -> %s", agent_id, new_id)
        return new_id

    async def submit_task(self, task: ScrapeTask) -> ScrapeResult:
        """提交任务到代理池

        流程：
        1. LoadBalancer.select_agent(task) 选出可用代理
        2. 调用 agent.execute(task) 执行抓取
        3. 成功结果提交给 ResultAggregator 进行去重 / 评分 / 存储

        无可用代理时返回 success=False 的占位结果，不抛异常。

        Args:
            task: 抓取任务

        Returns:
            ScrapeResult（含成功标志与数据或错误信息）
        """
        # 选择代理
        agent = self.load_balancer.select_agent(task)
        if not agent:
            return ScrapeResult(
                task_id=task.task_id,
                success=False,
                url=task.url,
                error="无可用代理",
            )

        # 代理执行任务
        result = await agent.execute(task)

        # 处理结果：成功结果进入聚合器进行去重 / 评分 / 存储
        # submit() 为同步文件 I/O，通过 asyncio.to_thread 在线程池执行，
        # 避免在批量提交等场景下阻塞事件循环
        if result.success:
            await asyncio.to_thread(self.result_aggregator.submit, result)

        return result

    async def submit_batch(self, tasks: list[ScrapeTask]) -> list[ScrapeResult]:
        """批量提交任务（并行执行）

        使用 asyncio.gather(return_exceptions=True) 并行调度所有任务，
        单任务抛出的异常被捕获并转为 success=False 的 ScrapeResult，
        不影响其他任务的结果。返回结果顺序与输入任务顺序一致。

        Args:
            tasks: 待执行任务列表

        Returns:
            ScrapeResult 列表，与输入一一对应
        """
        tasks_coroutines = [self.submit_task(task) for task in tasks]
        raw_results = await asyncio.gather(*tasks_coroutines, return_exceptions=True)

        results: list[ScrapeResult] = []
        for task, raw in zip(tasks, raw_results):
            if isinstance(raw, Exception):
                # 异常任务转为失败结果，保留 task_id / url 便于追溯
                results.append(ScrapeResult(
                    task_id=task.task_id,
                    success=False,
                    url=task.url,
                    error=f"批量任务异常: {raw}",
                ))
            else:
                results.append(raw)
        return results

    def get_pool_status(self) -> dict:
        """代理池状态概览

        Returns:
            包含 total_agents / healthy / degraded / unhealthy 计数与
            agents 明细列表的字典
        """
        status = {
            "total_agents": len(self.agents),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "agents": [],
        }

        for agent_id, agent in self.agents.items():
            health = agent.get_health()
            status["agents"].append({
                "agent_id": agent_id,
                "source": agent.source_config.get("name", "unknown"),
                "health_score": health.health_score,
                "state": health.state,
            })

            if health.state == "healthy":
                status["healthy"] += 1
            elif health.state == "degraded":
                status["degraded"] += 1
            else:
                status["unhealthy"] += 1

        return status

    async def shutdown(self) -> None:
        """关闭代理池

        顺序：
        1. 停止 HealthMonitor 后台协程
        2. 遍历销毁所有代理（关闭 HTTP 会话 + 移除字典引用）
        """
        await self.health_monitor.stop()

        for agent_id in list(self.agents.keys()):
            await self.destroy_agent(agent_id)

        logger.info("代理池已关闭")
