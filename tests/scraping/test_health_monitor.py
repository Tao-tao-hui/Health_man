# tests/scraping/test_health_monitor.py - HealthMonitor 健康监控测试
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.scraping.health_monitor import HealthMonitor


@pytest.fixture
def mock_agent_manager():
    """创建 mock agent manager

    提供接口：
    - agents: dict[str, agent] 代理字典
    - replace_agent(agent_id) -> str 异步替换接口，返回新代理 ID
    """
    manager = MagicMock()
    manager.agents = {}
    manager.replace_agent = AsyncMock(return_value="new_agent")
    return manager


@pytest.mark.asyncio
async def test_health_monitor_start_stop(mock_agent_manager):
    """HealthMonitor 启动和停止"""
    monitor = HealthMonitor(mock_agent_manager, check_interval=0.1)

    await monitor.start()
    await asyncio.sleep(0.2)
    await monitor.stop()

    assert monitor._running is False


@pytest.mark.asyncio
async def test_health_monitor_maybe_replace(mock_agent_manager):
    """连续不健康触发替换

    场景：单个 agent 长时间未活跃（last_active=0.0），默认 stale_timeout=300s
    因此首次检测即触发立即替换（条件2：僵死超时）。
    """
    monitor = HealthMonitor(
        mock_agent_manager, check_interval=0.1, unhealthy_threshold=2
    )

    # 添加不健康代理
    agent = MagicMock()
    agent.health.state = "unhealthy"
    agent.health.health_score = 0.2
    agent.health.last_active = 0.0
    mock_agent_manager.agents = {"agent_0": agent}

    await monitor.start()
    await asyncio.sleep(0.3)  # 等待 2 次检查

    # 验证替换被调用
    assert mock_agent_manager.replace_agent.call_count >= 1

    await monitor.stop()


@pytest.mark.asyncio
async def test_health_monitor_stale_timeout(mock_agent_manager):
    """僵死代理触发立即替换

    场景：agent 健康分高（state=healthy）但 300ms 未活跃，超过 stale_timeout=0.2s
    触发立即替换路径（条件2）。
    """
    import time

    monitor = HealthMonitor(
        mock_agent_manager, check_interval=0.1, stale_timeout=0.2
    )

    # 添加长时间未活跃代理
    agent = MagicMock()
    agent.health.state = "healthy"
    agent.health.health_score = 0.8
    agent.health.last_active = time.monotonic() - 0.3  # 300ms 前活跃
    mock_agent_manager.agents = {"agent_0": agent}

    await monitor.start()
    await asyncio.sleep(0.2)

    # 验证替换被调用
    assert mock_agent_manager.replace_agent.call_count >= 1

    await monitor.stop()
