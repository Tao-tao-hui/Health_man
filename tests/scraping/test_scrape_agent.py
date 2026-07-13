# tests/scraping/test_scrape_agent.py - 数据结构测试
import pytest
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

from scripts.scraping.scrape_agent import (
    AgentHealth,
    ScrapeAgent,
    ScrapeResult,
    ScrapeTask,
)
from scripts.utils.circuit_breaker import CircuitBreaker, CircuitState
from scripts.utils.rate_limiter import TokenBucketLimiter


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


# ============================================================
# ScrapeAgent 测试 (Task 2 追加)
# ============================================================


@pytest.fixture
def mock_circuit_breaker():
    """熔断器 fixture：默认状态 CLOSED，允许调用"""
    cb = CircuitBreaker()
    return cb


@pytest.fixture
def mock_rate_limiter():
    """限流器 fixture：高容量、高速率，acquire() 总返回 True"""
    rl = TokenBucketLimiter(capacity=10, refill_rate=10.0)
    return rl


@pytest.fixture
def source_config():
    """数据源配置 fixture"""
    return {
        "name": "test_source",
        "type": "api",
        "base_url": "https://test.com/",
        "parser": "json",
        "headers": {},
    }


@pytest.mark.asyncio
async def test_scrape_agent_execute_success(source_config, mock_circuit_breaker, mock_rate_limiter):
    """ScrapeAgent 执行成功"""
    agent = ScrapeAgent(
        agent_id="test_agent",
        source_config=source_config,
        circuit_breaker=mock_circuit_breaker,
        rate_limiter=mock_rate_limiter,
    )

    with patch.object(agent, "_get_session") as mock_session:
        # patch.object 把 _get_session 替换为 AsyncMock（async 方法自动检测）。
        # AsyncMock 的子属性默认也是 AsyncMock，会导致 session.get() 返回 coroutine
        # 而不是 async context manager。这里显式将 return_value 设为同步 MagicMock，
        # 使 .get() 同步调用返回带 __aenter__/__aexit__ 的对象（MagicMock 自动
        # 把这两个 dunder 配置为 AsyncMock）。
        mock_resp = AsyncMock()
        mock_resp.text.return_value = '{"data": "test"}'
        mock_resp.status = 200
        mock_session.return_value = MagicMock()
        mock_session.return_value.get.return_value.__aenter__.return_value = mock_resp

        task = ScrapeTask(
            task_id="task-001",
            source_type="api",
            url="https://test.com/data",
            parse_rules={"format": "json"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data == {"data": "test"}
        assert result.agent_id == "test_agent"

    await agent.close()


@pytest.mark.asyncio
async def test_scrape_agent_circuit_open(source_config, mock_rate_limiter):
    """熔断器开启时返回失败"""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
    cb.record_failure()  # 触发熔断

    agent = ScrapeAgent(
        agent_id="test_agent",
        source_config=source_config,
        circuit_breaker=cb,
        rate_limiter=mock_rate_limiter,
    )

    task = ScrapeTask(
        task_id="task-001",
        source_type="api",
        url="https://test.com/data",
        parse_rules={},
    )

    result = await agent.execute(task)

    assert result.success is False
    assert "熔断" in result.error

    await agent.close()


@pytest.mark.asyncio
async def test_scrape_agent_health_update_on_success(source_config, mock_circuit_breaker, mock_rate_limiter):
    """成功后健康分更新"""
    agent = ScrapeAgent(
        agent_id="test_agent",
        source_config=source_config,
        circuit_breaker=mock_circuit_breaker,
        rate_limiter=mock_rate_limiter,
    )

    with patch.object(agent, "_get_session") as mock_session:
        # 同 test_scrape_agent_execute_success：显式将 return_value 设为 MagicMock，
        # 避免 AsyncMock 自动传播导致 session.get() 返回 coroutine。
        mock_resp = AsyncMock()
        mock_resp.text.return_value = '{"data": "test"}'
        mock_resp.status = 200
        mock_session.return_value = MagicMock()
        mock_session.return_value.get.return_value.__aenter__.return_value = mock_resp

        task = ScrapeTask(task_id="t1", source_type="api", url="https://test.com/", parse_rules={})
        await agent.execute(task)

    # 健康分应为 1.0（首次成功）
    assert agent.health.success_rate == 1.0
    assert agent.health.state == "healthy"

    await agent.close()


@pytest.mark.asyncio
async def test_scrape_agent_parse_json(source_config, mock_circuit_breaker, mock_rate_limiter):
    """JSON 解析正确"""
    agent = ScrapeAgent(
        agent_id="test_agent",
        source_config=source_config,
        circuit_breaker=mock_circuit_breaker,
        rate_limiter=mock_rate_limiter,
    )

    content = '{"name": "test", "value": 123}'
    result = await agent.parse(content, {"format": "json"})

    assert result == {"name": "test", "value": 123}

    await agent.close()


@pytest.mark.asyncio
async def test_scrape_agent_parse_html(source_config, mock_circuit_breaker, mock_rate_limiter):
    """HTML 解析正确"""
    source_config["parser"] = "html"
    agent = ScrapeAgent(
        agent_id="test_agent",
        source_config=source_config,
        circuit_breaker=mock_circuit_breaker,
        rate_limiter=mock_rate_limiter,
    )

    content = "<html><body><h1>Test Title</h1><div class='content'>Content</div></body></html>"
    result = await agent.parse(content, {"format": "html", "selector": "h1"})

    assert "Test Title" in result["text"]

    await agent.close()


# ============================================================
# 最终审查修复测试
# ============================================================


def test_scrape_agent_record_success_resets_circuit_breaker(
    source_config, mock_rate_limiter
):
    """record_success 同步重置熔断器失败计数

    验证 Critical #1：ScrapeAgent.record_success 必须调用
    circuit_breaker.record_success，否则熔断器开启后无法恢复
    （HALF_OPEN 探测成功后无法回到 CLOSED，_failure_count 永不归零）。
    """
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    # 累计 2 次失败（尚未触发熔断，但 _failure_count=2）
    cb.record_failure()
    cb.record_failure()
    assert cb._failure_count == 2

    agent = ScrapeAgent(
        agent_id="test_agent",
        source_config=source_config,
        circuit_breaker=cb,
        rate_limiter=mock_rate_limiter,
    )

    # 成功记录应同步重置熔断器
    agent.record_success(100.0)

    assert cb._failure_count == 0
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_scrape_agent_init_last_active(source_config, mock_circuit_breaker, mock_rate_limiter):
    """新建代理 last_active 初始化为当前时间

    验证 Critical #2：ScrapeAgent.__init__ 必须将 health.last_active
    设为 time.monotonic()，避免默认 0.0 导致 HealthMonitor 误判为僵死
    并触发无限替换循环。
    """
    import time

    before = time.monotonic()
    agent = ScrapeAgent(
        agent_id="test_agent",
        source_config=source_config,
        circuit_breaker=mock_circuit_breaker,
        rate_limiter=mock_rate_limiter,
    )
    after = time.monotonic()

    # last_active 必须在构造前后时间区间内（而非默认 0.0）
    assert before <= agent.health.last_active <= after

    await agent.close()
