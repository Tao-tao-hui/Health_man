"""子代理架构直接数据抓取方案

核心组件：
- ScrapeAgent: 单个子代理，负责 HTTP 抓取和内容解析
- AgentManager: 代理池管理器，负责生命周期管理和任务分发
- LoadBalancer: 加权轮询负载均衡器
- HealthMonitor: 后台健康监控协程
- ResultAggregator: 结果聚合器（去重/质量评分/路由存储）
- config: 配置加载模块

使用方式：
    from scripts.scraping import AgentManager, ScrapeTask

    manager = AgentManager(config_path=Path("config/scrape_sources.yaml"))
    await manager.initialize()
    await manager.health_monitor.start()

    task = ScrapeTask(task_id="t1", source_type="api", url="https://example.com", parse_rules={})
    result = await manager.submit_task(task)
"""

from .scrape_agent import AgentHealth, ScrapeAgent, ScrapeResult, ScrapeTask
from .agent_manager import AgentManager
from .load_balancer import LoadBalancer
from .health_monitor import HealthMonitor
from .result_aggregator import ResultAggregator
from .config import SourceConfig, PoolConfig, load_config

__all__ = [
    "AgentHealth",
    "ScrapeAgent",
    "ScrapeResult",
    "ScrapeTask",
    "AgentManager",
    "LoadBalancer",
    "HealthMonitor",
    "ResultAggregator",
    "SourceConfig",
    "PoolConfig",
    "load_config",
]
