# tests/scraping/test_agent_manager.py - AgentManager 代理管理器测试
import pytest
from unittest.mock import AsyncMock

from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import ScrapeTask, ScrapeResult


@pytest.fixture
def tmp_dest_dir(tmp_path):
    """临时结果目录"""
    return tmp_path / "test_dest"


@pytest.mark.asyncio
async def test_agent_manager_create_agent(tmp_dest_dir):
    """AgentManager 创建代理

    验证点：
    - create_agent 返回的 agent_id 写入 agents 字典
    - 字典内 ScrapeAgent 的 agent_id 属性与 key 一致
    """
    manager = AgentManager(
        max_agents=10,
        dest_dir=tmp_dest_dir,
    )

    source_config = {
        "name": "test_source",
        "type": "api",
        "base_url": "https://test.com/",
        "parser": "json",
        "headers": {},
        "rate_limit_capacity": 5,
        "rate_limit_refill": 5.0,
        "circuit_failure_threshold": 5,
        "circuit_recovery_timeout": 30.0,
    }

    agent_id = await manager.create_agent(source_config)

    assert agent_id in manager.agents
    assert manager.agents[agent_id].agent_id == agent_id


@pytest.mark.asyncio
async def test_agent_manager_destroy_agent(tmp_dest_dir):
    """AgentManager 销毁代理

    验证点：销毁后 agent_id 不再存在于 agents 字典
    """
    manager = AgentManager(dest_dir=tmp_dest_dir)

    source_config = {"name": "test", "type": "api", "base_url": "https://test.com/",
                    "parser": "json", "headers": {},
                    "rate_limit_capacity": 5, "rate_limit_refill": 5.0,
                    "circuit_failure_threshold": 5, "circuit_recovery_timeout": 30.0}
    agent_id = await manager.create_agent(source_config)

    await manager.destroy_agent(agent_id)

    assert agent_id not in manager.agents


@pytest.mark.asyncio
async def test_agent_manager_submit_task(tmp_dest_dir):
    """AgentManager 提交任务

    验证点：mock 代理 execute 后，submit_task 返回 success=True 的结果
    """
    manager = AgentManager(dest_dir=tmp_dest_dir)

    # 创建代理并 mock execute
    source_config = {"name": "test", "type": "api", "base_url": "https://test.com/",
                    "parser": "json", "headers": {},
                    "rate_limit_capacity": 5, "rate_limit_refill": 5.0,
                    "circuit_failure_threshold": 5, "circuit_recovery_timeout": 30.0}
    agent_id = await manager.create_agent(source_config)
    manager.agents[agent_id].execute = AsyncMock(return_value=ScrapeResult(
        task_id="t1",
        success=True,
        data={"name": "test"},
        url="https://test.com/data",
        agent_id=agent_id,
    ))

    task = ScrapeTask(task_id="t1", source_type="api", url="https://test.com/data", parse_rules={})
    result = await manager.submit_task(task)

    assert result.success is True
    assert result.data == {"name": "test"}

    await manager.shutdown()


@pytest.mark.asyncio
async def test_agent_manager_submit_batch(tmp_dest_dir):
    """AgentManager 批量提交任务

    验证点：两个任务并行执行，全部成功
    """
    manager = AgentManager(dest_dir=tmp_dest_dir)

    source_config = {"name": "test", "type": "api", "base_url": "https://test.com/",
                    "parser": "json", "headers": {},
                    "rate_limit_capacity": 10, "rate_limit_refill": 10.0,
                    "circuit_failure_threshold": 5, "circuit_recovery_timeout": 30.0}
    agent_id = await manager.create_agent(source_config)
    manager.agents[agent_id].execute = AsyncMock(return_value=ScrapeResult(
        task_id="t1",
        success=True,
        data={"name": "test"},
        url="https://test.com/data",
        agent_id=agent_id,
    ))

    tasks = [
        ScrapeTask(task_id="t1", source_type="api", url="https://test.com/data1", parse_rules={}),
        ScrapeTask(task_id="t2", source_type="api", url="https://test.com/data2", parse_rules={}),
    ]

    results = await manager.submit_batch(tasks)

    assert len(results) == 2
    assert all(r.success for r in results)

    await manager.shutdown()


def test_agent_manager_get_pool_status(tmp_dest_dir):
    """AgentManager 获取代理池状态

    验证点：返回的状态字典含 total_agents / healthy / degraded / unhealthy 字段
    """
    manager = AgentManager(dest_dir=tmp_dest_dir)
    status = manager.get_pool_status()

    assert "total_agents" in status
    assert "healthy" in status
    assert "degraded" in status
    assert "unhealthy" in status
