# tests/scraping/test_load_balancer.py - LoadBalancer 负载均衡器测试
import pytest
from unittest.mock import MagicMock

from scripts.scraping.load_balancer import LoadBalancer
from scripts.scraping.scrape_agent import ScrapeTask


@pytest.fixture
def mock_agents():
    """创建 mock 代理字典

    生成 3 个 mock 代理：
    - agent_0: health_score=0.8（healthy）
    - agent_1: health_score=0.6（degraded）
    - agent_2: health_score=0.4（degraded）
    所有代理默认熔断器关闭、source_type=api。
    """
    agents = {}
    for i in range(3):
        # 注意：不使用 spec=ScrapeAgent，因为 agent_id / circuit_breaker /
        # health / source_config 均为 __init__ 中设置的实例属性，不属于类属性，
        # spec 会拒绝访问这些属性导致测试报错。
        agent = MagicMock()
        agent.agent_id = f"agent_{i}"
        agent.source_config = {"type": "api"}
        agent.circuit_breaker.can_call.return_value = True
        agent.circuit_breaker.state.value = "closed"
        agent.health.health_score = 0.8 - i * 0.2  # 0.8, 0.6, 0.4
        agent.health.state = "healthy" if agent.health.health_score >= 0.7 else "degraded"
        agents[f"agent_{i}"] = agent
    return agents


def test_load_balancer_select_agent(mock_agents):
    """LoadBalancer 能选择代理"""
    lb = LoadBalancer(mock_agents)

    task = ScrapeTask(task_id="t1", source_type="api", url="https://test.com/", parse_rules={})
    agent = lb.select_agent(task)

    assert agent is not None
    assert agent.agent_id in mock_agents


def test_load_balancer_filter_circuit_open(mock_agents):
    """LoadBalancer 过滤熔断代理"""
    mock_agents["agent_0"].circuit_breaker.can_call.return_value = False

    lb = LoadBalancer(mock_agents)

    task = ScrapeTask(task_id="t1", source_type="api", url="https://test.com/", parse_rules={})
    agent = lb.select_agent(task)

    # 不应选择 agent_0（熔断）
    assert agent is not None
    assert agent.agent_id != "agent_0"


def test_load_balancer_filter_unhealthy(mock_agents):
    """LoadBalancer 过滤 unhealthy 代理"""
    mock_agents["agent_2"].health.state = "unhealthy"
    mock_agents["agent_2"].health.health_score = 0.2

    lb = LoadBalancer(mock_agents)

    task = ScrapeTask(task_id="t1", source_type="api", url="https://test.com/", parse_rules={})
    agent = lb.select_agent(task)

    # 不应选择 agent_2（unhealthy）
    assert agent is not None
    assert agent.agent_id != "agent_2"


def test_load_balancer_no_available_agents(mock_agents):
    """无可用代理时返回 None"""
    for agent in mock_agents.values():
        agent.circuit_breaker.can_call.return_value = False

    lb = LoadBalancer(mock_agents)

    task = ScrapeTask(task_id="t1", source_type="api", url="https://test.com/", parse_rules={})
    agent = lb.select_agent(task)

    assert agent is None


def test_load_balancer_add_remove_agent(mock_agents):
    """添加和移除代理"""
    lb = LoadBalancer(mock_agents)

    # 添加新代理（同 mock_agents，不使用 spec）
    new_agent = MagicMock()
    new_agent.agent_id = "new_agent"
    new_agent.source_config = {"type": "api"}
    new_agent.circuit_breaker.can_call.return_value = True
    new_agent.circuit_breaker.state.value = "closed"
    new_agent.health.health_score = 0.9
    new_agent.health.state = "healthy"
    lb.add_agent("new_agent", new_agent)

    assert lb.get_available_count() == 4

    # 移除代理
    lb.remove_agent("agent_0")
    assert lb.get_available_count() == 3
