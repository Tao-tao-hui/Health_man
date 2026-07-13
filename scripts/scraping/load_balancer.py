# scripts/scraping/load_balancer.py - 负载均衡器
"""负载均衡器

加权轮询选择最优代理执行任务。

LoadBalancer 接收一个 dict[str, ScrapeAgent] 代理集合，根据以下规则
为 ScrapeTask 选出最合适的代理：
  1. 过滤不可用代理（熔断器开启 / 健康状态为 unhealthy / source_type 不匹配）
  2. 基于 health_score 做加权随机选择，分高的代理被选中概率更大
  3. 无可用代理时返回 None 并记录告警日志
"""
import logging
import random
from typing import Optional

from scripts.scraping.scrape_agent import ScrapeAgent, ScrapeTask

logger = logging.getLogger(__name__)


class LoadBalancer:
    """加权轮询负载均衡器

    通过 health_score 作为权重进行加权随机，让健康分高的代理承担更多
    任务，同时保证降级代理仍有机会恢复（只要非 unhealthy 即可参与）。
    """

    def __init__(self, agents: dict[str, ScrapeAgent]):
        """初始化负载均衡器

        Args:
            agents: 代理字典，key 为 agent_id，value 为 ScrapeAgent 实例。
                    外部字典被直接引用，后续 add/remove_agent 会同步影响。
        """
        self.agents = agents

    def select_agent(self, task: ScrapeTask) -> Optional[ScrapeAgent]:
        """选择最优代理

        过滤规则：
          - circuit_breaker.can_call() 为 False（熔断开启）→ 跳过
          - health.state == "unhealthy" → 跳过
          - source_config["type"] != task.source_type → 跳过

        选择规则：
          - 按 health_score 加权随机
          - 所有权重为 0 时退化为等概率随机

        Args:
            task: 待执行的抓取任务

        Returns:
            被选中的 ScrapeAgent，无可用代理时返回 None
        """
        # 过滤可用代理：非熔断 + 非 unhealthy + source_type 匹配
        available: list[ScrapeAgent] = []
        for agent in self.agents.values():
            # 熔断器开启时跳过
            if not agent.circuit_breaker.can_call():
                continue
            # 健康状态为 unhealthy 时跳过
            if agent.health.state == "unhealthy":
                continue
            # 按 source_type 筛选（空字符串视为不限制）
            if task.source_type and agent.source_config.get("type") != task.source_type:
                continue
            available.append(agent)

        if not available:
            logger.warning("无可用代理执行任务: %s", task.task_id)
            return None

        # 按 health_score 加权随机选择
        weights = [agent.health.health_score for agent in available]
        total_weight = sum(weights)

        if total_weight == 0:
            # 所有代理权重为 0，等概率随机选择
            return random.choice(available)

        # 加权随机：在 [0, total_weight) 区间取随机数，按累积权重命中
        random_val = random.uniform(0, total_weight)
        current = 0.0
        for agent, weight in zip(available, weights):
            current += weight
            if current >= random_val:
                logger.debug(
                    "选择代理 %s (健康分=%.2f)", agent.agent_id, weight
                )
                return agent

        # 浮点数边界兜底（理论上不会到达）
        return available[-1]

    def update_weights(self) -> None:
        """重新计算权重

        健康分由 ScrapeAgent 在每次请求后实时更新，select_agent 直接读取
        最新值即可。此方法保留为扩展接口，预留给未来需要批量刷新或
        缓存权重场景使用。
        """
        pass

    def add_agent(self, agent_id: str, agent: ScrapeAgent) -> None:
        """添加新代理

        Args:
            agent_id: 代理唯一标识
            agent: ScrapeAgent 实例
        """
        self.agents[agent_id] = agent
        logger.info("添加代理: %s", agent_id)

    def remove_agent(self, agent_id: str) -> None:
        """移除代理

        Args:
            agent_id: 要移除的代理唯一标识
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info("移除代理: %s", agent_id)

    def get_available_count(self) -> int:
        """获取可用代理数

        可用定义：熔断器允许调用且健康状态非 unhealthy。
        注意：此处不考虑 source_type 匹配，因 source_type 与具体任务相关。

        Returns:
            可用代理数量
        """
        count = 0
        for agent in self.agents.values():
            if agent.circuit_breaker.can_call() and agent.health.state != "unhealthy":
                count += 1
        return count
