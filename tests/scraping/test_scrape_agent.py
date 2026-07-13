# tests/scraping/test_scrape_agent.py - 数据结构测试
import pytest
from dataclasses import asdict
from scripts.scraping.scrape_agent import AgentHealth, ScrapeTask, ScrapeResult


def test_agent_health_defaults():
    """AgentHealth 默认值正确"""
    health = AgentHealth()
    assert health.health_score == 1.0
    assert health.success_rate == 1.0
    assert health.avg_latency_ms == 0.0
    assert health.error_count == 0
    assert health.state == "healthy"


def test_agent_health_state_transition():
    """健康分与状态映射正确"""
    # healthy: >= 0.7
    health = AgentHealth(health_score=0.8)
    assert health.state == "healthy"

    # degraded: 0.3 <= score < 0.7
    health = AgentHealth(health_score=0.5)
    assert health.state == "degraded"

    # unhealthy: < 0.3
    health = AgentHealth(health_score=0.2)
    assert health.state == "unhealthy"


def test_scrape_task_defaults():
    """ScrapeTask 默认值正确"""
    task = ScrapeTask(
        task_id="test-001",
        source_type="api",
        url="https://example.com",
        parse_rules={"format": "json"},
    )
    assert task.priority == 0
    assert task.metadata == {}


def test_scrape_task_priority():
    """ScrapeTask 优先级正确"""
    task = ScrapeTask(
        task_id="test-001",
        source_type="html",
        url="https://example.com",
        parse_rules={},
        priority=2,
        metadata={"keyword": "BIA"},
    )
    assert task.priority == 2
    assert task.metadata == {"keyword": "BIA"}


def test_scrape_result_defaults():
    """ScrapeResult 默认值正确"""
    result = ScrapeResult(task_id="test-001", success=True)
    assert result.data is None
    assert result.raw_content == ""
    assert result.url == ""
    assert result.agent_id == ""
    assert result.error == ""
    assert result.latency_ms == 0.0
    assert result.quality_score == 0.0
