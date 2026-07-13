# scripts/scraping/health_monitor.py - 健康监控器
"""健康监控器

后台协程，周期性检测代理健康，触发自动替换。

替换触发条件：
1. 连续不健康次数 >= unhealthy_threshold
2. 超过 stale_timeout 无响应（last_active 距今过久）
"""
import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    # 仅用于类型提示；运行时不需要导入（AgentManager 在 Task 6 实现）
    from scripts.scraping.agent_manager import AgentManager

from scripts.scraping.scrape_agent import AgentHealth

logger = logging.getLogger(__name__)


class HealthMonitor:
    """后台健康监控协程

    周期性遍历 agent_manager.agents，依据代理健康状态触发自动替换：
    - 条件1：连续不健康次数 >= unhealthy_threshold
    - 条件2：超过 stale_timeout 无响应

    Attributes:
        agent_manager: 持有 agents 字典与 replace_agent 异步方法的管理器
        check_interval: 检测周期（秒）
        unhealthy_threshold: 连续不健康次数阈值
        stale_timeout: 僵死判定超时（秒）
    """

    def __init__(
        self,
        agent_manager: "AgentManager",
        check_interval: float = 30.0,
        unhealthy_threshold: int = 3,
        stale_timeout: float = 300.0,
    ):
        """初始化健康监控器

        Args:
            agent_manager: 代理管理器（含 agents dict 与 replace_agent 异步方法）
            check_interval: 检测周期，默认 30s
            unhealthy_threshold: 触发替换的连续不健康次数，默认 3
            stale_timeout: 僵死超时阈值，默认 300s
        """
        self.agent_manager = agent_manager
        self.check_interval = check_interval
        self.unhealthy_threshold = unhealthy_threshold
        self.stale_timeout = stale_timeout
        # 每个代理的连续不健康计数
        self._unhealthy_counts: dict[str, int] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动后台监控协程"""
        self._running = True
        self._task = asyncio.create_task(self._run_periodic_check())
        logger.info("健康监控器已启动，检查间隔: %.1fs", self.check_interval)

    async def stop(self) -> None:
        """停止监控

        取消后台任务并等待其退出。即使任务被取消异常也会被吞掉，
        保证 stop() 总是平稳返回。
        """
        self._running = False
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        logger.info("健康监控器已停止")

    async def _run_periodic_check(self) -> None:
        """周期性检测循环

        循环执行：检测所有代理 → 睡眠 check_interval 秒。
        被 stop() 通过 task.cancel() 终止。
        """
        while self._running:
            await self._check_all_agents()
            await asyncio.sleep(self.check_interval)

    async def _check_all_agents(self) -> None:
        """检测所有代理

        遍历 agent_manager.agents 的快照（避免迭代中替换导致字典变更），
        对每个代理：获取健康 → 更新不健康计数 → 判断是否替换。
        单个代理检测异常不影响其他代理。
        """
        for agent_id, agent in list(self.agent_manager.agents.items()):
            try:
                health = agent.get_health()
                self._update_unhealthy_count(agent_id, health)
                await self._maybe_replace(agent_id)
            except Exception as e:
                logger.warning("健康检测异常 %s: %s", agent_id, e)

    def _update_unhealthy_count(self, agent_id: str, health: AgentHealth) -> None:
        """更新连续不健康计数

        health.state 为 "unhealthy" 时累加，否则清零。

        Args:
            agent_id: 代理 ID
            health: 代理健康状态对象
        """
        if health.state == "unhealthy":
            self._unhealthy_counts[agent_id] = (
                self._unhealthy_counts.get(agent_id, 0) + 1
            )
        else:
            self._unhealthy_counts[agent_id] = 0

    async def _maybe_replace(self, agent_id: str) -> None:
        """判断是否需要替换代理

        两个触发条件（任一满足即替换）：
        1. 连续不健康次数 >= unhealthy_threshold
        2. agent.health.last_active 距今超过 stale_timeout

        替换后清理旧 ID 的计数，并为新 ID 初始化计数。

        Args:
            agent_id: 待判定的代理 ID
        """
        count = self._unhealthy_counts.get(agent_id, 0)
        agent = self.agent_manager.agents.get(agent_id)
        if not agent:
            return

        # 条件1：连续不健康次数超阈值
        if count >= self.unhealthy_threshold:
            logger.warning(
                "代理 %s 连续 %d 次不健康，触发替换", agent_id, count
            )
            new_id = await self.agent_manager.replace_agent(agent_id)
            self._unhealthy_counts.pop(agent_id, None)
            self._unhealthy_counts[new_id] = 0
            return

        # 条件2：超过 stale_timeout 无响应
        if time.monotonic() - agent.health.last_active > self.stale_timeout:
            logger.warning(
                "代理 %s 超过 %.0fs 无响应，立即替换",
                agent_id,
                self.stale_timeout,
            )
            new_id = await self.agent_manager.replace_agent(agent_id)
            self._unhealthy_counts.pop(agent_id, None)
            self._unhealthy_counts[new_id] = 0
