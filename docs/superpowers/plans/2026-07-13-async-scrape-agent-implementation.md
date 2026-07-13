# 子代理架构直接数据抓取方案实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现基于 asyncio 协程的子代理架构，包含动态代理管理、负载均衡、健康监控和自动替换能力，覆盖三类医学数据源（公开 API、中文学术数据库、医学网站/指南）。

**Architecture:** 单进程 asyncio 代理池架构，6 个核心组件（ScrapeAgent/AgentManager/LoadBalancer/HealthMonitor/ResultAggregator/Config），复用现有 CircuitBreaker/TokenBucketLimiter/AuditLogger/CredentialManager 四件套，新增 aiohttp + beautifulsoup4 轻量依赖。

**Tech Stack:** Python 3.12+, asyncio, aiohttp 3.9+, beautifulsoup4 4.12+, lxml 5.1+, pytest-asyncio 0.23+, pyyaml 6.0+

## Global Constraints

| 约束 | 值 |
|------|-----|
| 并发模型 | asyncio 协程（单进程） |
| 最大代理数 | 20 |
| 资源开销目标 | < 100MB 内存 |
| 健康检查间隔 | 30 秒 |
| 连续不健康阈值 | 3 次 |
| 僵死超时 | 300 秒（5 分钟） |
| 健康分算法 | 0.4×成功率 + 0.3×(1-归一化延迟) + 0.3×(1-错误率) |
| 重试策略 | 指数退避 1s/2s/4s，最多 3 次 |
| 请求超时 | 30 秒 |
| 测试框架 | pytest-asyncio |

---

## 文件结构

```
scripts/scraping/
├── __init__.py
├── scrape_agent.py       # ScrapeAgent — 单代理抓取+解析
├── agent_manager.py       # AgentManager — 生命周期管理+代理池
├── load_balancer.py       # LoadBalancer — 加权轮询分发
├── health_monitor.py      # HealthMonitor — 心跳检测+自动替换
├── result_aggregator.py   # ResultAggregator — 去重+质量评分+存储
└── config.py              # 配置加载

config/
└── scrape_sources.yaml    # 数据源与代理池配置

tests/scraping/
├── __init__.py
├── conftest.py            # 测试 fixtures
├── test_scrape_agent.py   # ScrapeAgent 测试
├── test_agent_manager.py  # AgentManager 测试
├── test_load_balancer.py  # LoadBalancer 测试
├── test_health_monitor.py # HealthMonitor 测试
└── test_result_aggregator.py  # ResultAggregator 测试
```

---

## Task 1: 配置模块与数据结构

**Files:**
- Create: `scripts/scraping/config.py`
- Create: `scripts/scraping/scrape_agent.py` (数据结构部分)
- Create: `tests/scraping/test_scrape_agent.py` (数据结构测试)
- Create: `tests/scraping/test_config.py`

**Interfaces:**
- Produces: `AgentHealth`, `ScrapeTask`, `ScrapeResult` dataclasses
- Produces: `SourceConfig`, `PoolConfig` dataclasses
- Produces: `load_config()` function

- [ ] **Step 1: 创建测试文件并写入数据结构测试**

```python
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
```

```python
# tests/scraping/test_config.py
import pytest
from pathlib import Path
from scripts.scraping.config import SourceConfig, PoolConfig, load_config


def test_source_config():
    """SourceConfig 数据结构正确"""
    config = SourceConfig(
        name="pubmed",
        source_type="api",
        base_url="https://example.com/",
        rate_limit_capacity=3,
        rate_limit_refill=3.0,
        circuit_failure_threshold=5,
        circuit_recovery_timeout=30.0,
        parser="pubmed_xml",
        headers={},
        enabled=True,
    )
    assert config.name == "pubmed"
    assert config.source_type == "api"
    assert config.enabled is True


def test_pool_config():
    """PoolConfig 默认值正确"""
    config = PoolConfig()
    assert config.max_agents == 20
    assert config.health_check_interval == 30.0
    assert config.unhealthy_threshold == 3
    assert config.stale_timeout == 300.0


def test_load_config(tmp_path):
    """从 YAML 文件加载配置正确"""
    yaml_content = """
sources:
  - name: test_source
    type: api
    base_url: https://test.com/
    rate_limit:
      capacity: 2
      refill_rate: 2.0
    circuit_breaker:
      failure_threshold: 3
      recovery_timeout: 45.0
    parser: json
    enabled: true

pool:
  max_agents: 10
  health_check_interval: 20.0
"""
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(yaml_content, encoding="utf-8")
    
    sources, pool = load_config(config_path)
    
    assert len(sources) == 1
    assert sources[0].name == "test_source"
    assert sources[0].source_type == "api"
    assert sources[0].rate_limit_capacity == 2
    assert pool.max_agents == 10
    assert pool.health_check_interval == 20.0
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
python -m pytest tests/scraping/test_scrape_agent.py tests/scraping/test_config.py -v --tb=short
```

Expected: FAIL with "ModuleNotFoundError: No module named 'scripts.scraping'"

- [ ] **Step 3: 实现数据结构和配置模块**

```python
# scripts/scraping/scrape_agent.py - 数据结构部分
"""子代理模块

ScrapeAgent: 单个子代理，负责 HTTP 抓取和内容解析
数据结构: AgentHealth, ScrapeTask, ScrapeResult
"""
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

import aiohttp
from bs4 import BeautifulSoup

from scripts.utils.audit_logger import AuditLogger
from scripts.utils.circuit_breaker import CircuitBreaker
from scripts.utils.rate_limiter import TokenBucketLimiter

logger = logging.getLogger(__name__)


@dataclass
class AgentHealth:
    """代理健康状态"""
    health_score: float = 1.0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    error_count: int = 0
    last_active: float = 0.0
    state: str = "healthy"

    @property
    def state(self) -> str:
        """根据健康分计算状态"""
        if self.health_score >= 0.7:
            return "healthy"
        elif self.health_score >= 0.3:
            return "degraded"
        else:
            return "unhealthy"


@dataclass
class ScrapeTask:
    """抓取任务"""
    task_id: str
    source_type: str
    url: str
    parse_rules: dict
    priority: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class ScrapeResult:
    """抓取结果"""
    task_id: str
    success: bool
    data: dict | None = None
    raw_content: str = ""
    url: str = ""
    agent_id: str = ""
    timestamp: str = ""
    error: str = ""
    latency_ms: float = 0.0
    quality_score: float = 0.0
```

```python
# scripts/scraping/config.py
"""子代理架构配置模块"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SourceConfig:
    """数据源配置"""
    name: str
    source_type: str
    base_url: str
    rate_limit_capacity: int
    rate_limit_refill: float
    circuit_failure_threshold: int
    circuit_recovery_timeout: float
    parser: str
    headers: dict
    enabled: bool = True


@dataclass
class PoolConfig:
    """代理池配置"""
    max_agents: int = 20
    health_check_interval: float = 30.0
    unhealthy_threshold: int = 3
    stale_timeout: float = 300.0


def load_config(config_path: Path) -> tuple[list[SourceConfig], PoolConfig]:
    """从 YAML 文件加载配置

    Args:
        config_path: YAML 配置文件路径

    Returns:
        (数据源配置列表, 代理池配置)
    """
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sources = []
    for source_data in data.get("sources", []):
        sources.append(SourceConfig(
            name=source_data["name"],
            source_type=source_data["type"],
            base_url=source_data["base_url"],
            rate_limit_capacity=source_data["rate_limit"]["capacity"],
            rate_limit_refill=source_data["rate_limit"]["refill_rate"],
            circuit_failure_threshold=source_data["circuit_breaker"]["failure_threshold"],
            circuit_recovery_timeout=source_data["circuit_breaker"]["recovery_timeout"],
            parser=source_data["parser"],
            headers=source_data.get("headers", {}),
            enabled=source_data.get("enabled", True),
        ))

    pool_data = data.get("pool", {})
    pool = PoolConfig(
        max_agents=pool_data.get("max_agents", 20),
        health_check_interval=pool_data.get("health_check_interval", 30.0),
        unhealthy_threshold=pool_data.get("unhealthy_threshold", 3),
        stale_timeout=pool_data.get("stale_timeout", 300.0),
    )

    return sources, pool
```

- [ ] **Step 4: 运行测试确认通过**

```powershell
python -m pytest tests/scraping/test_scrape_agent.py tests/scraping/test_config.py -v --tb=short
```

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add scripts/scraping/scrape_agent.py scripts/scraping/config.py tests/scraping/test_scrape_agent.py tests/scraping/test_config.py
git commit -m "feat: 子代理架构 - 数据结构与配置模块"
```

---

## Task 2: ScrapeAgent 核心实现

**Files:**
- Modify: `scripts/scraping/scrape_agent.py` (添加 ScrapeAgent 类)
- Create: `tests/scraping/test_scrape_agent.py` (扩展测试)

**Interfaces:**
- Consumes: `CircuitBreaker`, `TokenBucketLimiter`, `AuditLogger` (现有)
- Produces: `ScrapeAgent.execute(task) -> ScrapeResult`

- [ ] **Step 1: 写入 ScrapeAgent 测试**

```python
# tests/scraping/test_scrape_agent.py - ScrapeAgent 测试
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from scripts.scraping.scrape_agent import ScrapeAgent, ScrapeTask, ScrapeResult
from scripts.utils.circuit_breaker import CircuitBreaker
from scripts.utils.rate_limiter import TokenBucketLimiter


@pytest.fixture
def mock_circuit_breaker():
    cb = CircuitBreaker()
    return cb


@pytest.fixture
def mock_rate_limiter():
    rl = TokenBucketLimiter(capacity=10, refill_rate=10.0)
    return rl


@pytest.fixture
def source_config():
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

    with patch.object(agent, '_get_session') as mock_session:
        mock_resp = AsyncMock()
        mock_resp.text.return_value = '{"data": "test"}'
        mock_resp.status = 200
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

    with patch.object(agent, '_get_session') as mock_session:
        mock_resp = AsyncMock()
        mock_resp.text.return_value = '{"data": "test"}'
        mock_resp.status = 200
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
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
python -m pytest tests/scraping/test_scrape_agent.py -v --tb=short
```

Expected: FAIL with "ScrapeAgent has no attribute 'execute'"

- [ ] **Step 3: 实现 ScrapeAgent 类**

```python
# scripts/scraping/scrape_agent.py - 添加 ScrapeAgent 类
class ScrapeAgent:
    """子代理：独立抓取 + 解析 + 容错"""

    def __init__(
        self,
        agent_id: str,
        source_config: dict,
        circuit_breaker: CircuitBreaker,
        rate_limiter: TokenBucketLimiter,
        audit_logger: AuditLogger | None = None,
    ):
        self.agent_id = agent_id
        self.source_config = source_config
        self.circuit_breaker = circuit_breaker
        self.rate_limiter = rate_limiter
        self.audit_logger = audit_logger
        self.health = AgentHealth()
        self._latency_history: deque[float] = deque(maxlen=20)
        self._success_history: deque[bool] = deque(maxlen=20)
        self._http_session: aiohttp.ClientSession | None = None
        self._headers = source_config.get("headers", {})

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话（懒加载）"""
        if self._http_session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self._http_session = aiohttp.ClientSession(timeout=timeout)
        return self._http_session

    async def fetch(self, url: str, params: dict = None) -> tuple[str, float]:
        """HTTP 请求获取原始内容"""
        session = await self._get_session()
        start_time = time.monotonic()

        async with session.get(url, params=params, headers=self._headers) as resp:
            content = await resp.text()
            latency_ms = (time.monotonic() - start_time) * 1000

            if resp.status == 429:
                raise RateLimitError("HTTP 429: Too Many Requests")
            if resp.status == 403:
                raise PermissionError("HTTP 403: Forbidden")

            return content, latency_ms

    async def parse(self, content: str, parse_rules: dict) -> dict:
        """解析内容"""
        parser_type = self.source_config.get("parser", "json")

        if parser_type == "json":
            return json.loads(content)
        elif parser_type in ("html", "cnki_html", "guideline_html"):
            soup = BeautifulSoup(content, "lxml")
            selector = parse_rules.get("selector", "body")
            elements = soup.select(selector)
            return {
                "text": "\n".join(e.get_text(strip=True) for e in elements),
                "html": "\n".join(str(e) for e in elements),
                "count": len(elements),
            }
        elif parser_type == "pubmed_xml":
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            return {"xml": content}
        else:
            return {"raw": content}

    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        """执行完整抓取任务"""
        self.health.last_active = time.monotonic()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        # 熔断检查
        if not self.circuit_breaker.can_call():
            return ScrapeResult(
                task_id=task.task_id,
                success=False,
                url=task.url,
                agent_id=self.agent_id,
                timestamp=timestamp,
                error=f"熔断器已开启，状态: {self.circuit_breaker.state.value}",
            )

        # 限流获取（带重试）
        for attempt in range(3):
            if self.rate_limiter.acquire():
                break
            await asyncio.sleep(1.0 * (2 ** attempt))
        else:
            return ScrapeResult(
                task_id=task.task_id,
                success=False,
                url=task.url,
                agent_id=self.agent_id,
                timestamp=timestamp,
                error="限流拒绝，重试次数用尽",
            )

        try:
            # HTTP 抓取
            content, latency_ms = await self.fetch(task.url, task.metadata.get("params"))

            # 内容解析
            data = await self.parse(content, task.parse_rules)

            # 记录成功
            self.record_success(latency_ms)

            return ScrapeResult(
                task_id=task.task_id,
                success=True,
                data=data,
                raw_content=content,
                url=task.url,
                agent_id=self.agent_id,
                timestamp=timestamp,
                latency_ms=latency_ms,
            )

        except RateLimitError as e:
            self.record_failure(str(e))
            self.circuit_breaker.record_failure()
            return ScrapeResult(
                task_id=task.task_id,
                success=False,
                url=task.url,
                agent_id=self.agent_id,
                timestamp=timestamp,
                error=f"限流错误: {e}",
            )
        except PermissionError as e:
            self.record_failure(str(e))
            self.circuit_breaker.record_failure()
            return ScrapeResult(
                task_id=task.task_id,
                success=False,
                url=task.url,
                agent_id=self.agent_id,
                timestamp=timestamp,
                error=f"权限错误: {e}",
            )
        except Exception as e:
            self.record_failure(str(e))
            self.circuit_breaker.record_failure()
            return ScrapeResult(
                task_id=task.task_id,
                success=False,
                url=task.url,
                agent_id=self.agent_id,
                timestamp=timestamp,
                error=f"执行失败: {e}",
                raw_content="",
            )

    def record_success(self, latency_ms: float) -> None:
        """记录成功"""
        self._success_history.append(True)
        self._latency_history.append(latency_ms)
        self.health.error_count = 0
        self._recalculate_health()

    def record_failure(self, error: str) -> None:
        """记录失败"""
        self._success_history.append(False)
        self.health.error_count += 1
        self._recalculate_health()

    def _recalculate_health(self) -> None:
        """重算健康分"""
        if not self._success_history:
            return

        success_rate = sum(self._success_history) / len(self._success_history)

        if self._latency_history:
            avg_latency_ms = sum(self._latency_history) / len(self._latency_history)
            normalized_latency = min(avg_latency_ms / 5000, 1.0)
        else:
            normalized_latency = 0.0

        error_rate = min(self.health.error_count / 10, 1.0)

        self.health.success_rate = success_rate
        self.health.avg_latency_ms = avg_latency_ms if self._latency_history else 0.0
        self.health.health_score = (
            0.4 * success_rate
            + 0.3 * (1 - normalized_latency)
            + 0.3 * (1 - error_rate)
        )

    def get_health(self) -> AgentHealth:
        """获取当前健康状态"""
        return self.health

    async def close(self) -> None:
        """关闭 HTTP 会话"""
        if self._http_session:
            await self._http_session.close()
            self._http_session = None


class RateLimitError(Exception):
    """限流错误"""
    pass
```

- [ ] **Step 4: 运行测试确认通过**

```powershell
python -m pytest tests/scraping/test_scrape_agent.py -v --tb=short
```

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add scripts/scraping/scrape_agent.py tests/scraping/test_scrape_agent.py
git commit -m "feat: 子代理架构 - ScrapeAgent 核心实现（抓取+解析+容错+健康分）"
```

---

## Task 3: LoadBalancer 负载均衡器

**Files:**
- Create: `scripts/scraping/load_balancer.py`
- Create: `tests/scraping/test_load_balancer.py`

**Interfaces:**
- Consumes: `ScrapeAgent`, `ScrapeTask`
- Produces: `LoadBalancer.select_agent(task) -> ScrapeAgent | None`

- [ ] **Step 1: 写入 LoadBalancer 测试**

```python
# tests/scraping/test_load_balancer.py
import pytest
from unittest.mock import MagicMock

from scripts.scraping.load_balancer import LoadBalancer
from scripts.scraping.scrape_agent import ScrapeAgent, ScrapeTask


@pytest.fixture
def mock_agents():
    """创建 mock 代理字典"""
    agents = {}
    for i in range(3):
        agent = MagicMock(spec=ScrapeAgent)
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

    # 添加新代理
    new_agent = MagicMock(spec=ScrapeAgent)
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
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
python -m pytest tests/scraping/test_load_balancer.py -v --tb=short
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 LoadBalancer**

```python
# scripts/scraping/load_balancer.py
"""负载均衡器

加权轮询选择最优代理执行任务。
"""
import logging
import random
from typing import Optional

from scripts.scraping.scrape_agent import ScrapeAgent, ScrapeTask

logger = logging.getLogger(__name__)


class LoadBalancer:
    """加权轮询负载均衡器"""

    def __init__(self, agents: dict[str, ScrapeAgent]):
        self.agents = agents

    def select_agent(self, task: ScrapeTask) -> Optional[ScrapeAgent]:
        """选择最优代理"""
        # 过滤可用代理：非熔断 + 非 unhealthy
        available = []
        for agent_id, agent in self.agents.items():
            if not agent.circuit_breaker.can_call():
                continue
            if agent.health.state == "unhealthy":
                continue
            # 根据 source_type 筛选
            if task.source_type and agent.source_config.get("type") != task.source_type:
                continue
            available.append(agent)

        if not available:
            logger.warning("无可用代理执行任务: %s", task.task_id)
            return None

        # 加权随机选择
        weights = [agent.health.health_score for agent in available]
        total_weight = sum(weights)

        if total_weight == 0:
            # 所有代理权重为 0，随机选择
            return random.choice(available)

        # 加权随机
        random_val = random.uniform(0, total_weight)
        current = 0
        for agent, weight in zip(available, weights):
            current += weight
            if current >= random_val:
                logger.debug("选择代理 %s (健康分=%.2f)", agent.agent_id, weight)
                return agent

        return available[-1]

    def update_weights(self) -> None:
        """重新计算权重（健康分已实时更新，此方法预留）"""
        pass

    def add_agent(self, agent_id: str, agent: ScrapeAgent) -> None:
        """添加新代理"""
        self.agents[agent_id] = agent
        logger.info("添加代理: %s", agent_id)

    def remove_agent(self, agent_id: str) -> None:
        """移除代理"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info("移除代理: %s", agent_id)

    def get_available_count(self) -> int:
        """获取可用代理数"""
        count = 0
        for agent in self.agents.values():
            if agent.circuit_breaker.can_call() and agent.health.state != "unhealthy":
                count += 1
        return count
```

- [ ] **Step 4: 运行测试确认通过**

```powershell
python -m pytest tests/scraping/test_load_balancer.py -v --tb=short
```

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add scripts/scraping/load_balancer.py tests/scraping/test_load_balancer.py
git commit -m "feat: 子代理架构 - LoadBalancer 加权轮询负载均衡"
```

---

## Task 4: ResultAggregator 结果聚合器

**Files:**
- Create: `scripts/scraping/result_aggregator.py`
- Create: `tests/scraping/test_result_aggregator.py`

**Interfaces:**
- Consumes: `ScrapeResult`
- Produces: `ResultAggregator.submit(result) -> Path | None`

- [ ] **Step 1: 写入 ResultAggregator 测试**

```python
# tests/scraping/test_result_aggregator.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from scripts.scraping.result_aggregator import ResultAggregator
from scripts.scraping.scrape_agent import ScrapeResult


@pytest.fixture
def tmp_dest_dir(tmp_path):
    return tmp_path / "test_dest"


@pytest.fixture
def aggregator(tmp_dest_dir):
    return ResultAggregator(dest_dir=tmp_dest_dir)


def test_result_aggregator_deduplication(aggregator):
    """去重功能正确"""
    result1 = ScrapeResult(
        task_id="t1",
        success=True,
        url="https://test.com/data?a=1&b=2",
        agent_id="agent_0",
    )
    result2 = ScrapeResult(
        task_id="t2",
        success=True,
        url="https://test.com/data?b=2&a=1",  # 相同 URL，参数顺序不同
        agent_id="agent_0",
    )

    path1 = aggregator.submit(result1)
    path2 = aggregator.submit(result2)

    assert path1 is not None
    assert path2 is None  # 重复


def test_result_aggregator_quality_score(aggregator):
    """质量评分正确"""
    # 完整数据
    result = ScrapeResult(
        task_id="t1",
        success=True,
        data={"name": "test", "value": 100, "unit": "%"},
        url="https://test.com/data",
        agent_id="agent_0",
    )

    path = aggregator.submit(result)

    assert result.quality_score > 0.8


def test_result_aggregator_storage(aggregator):
    """结果存储正确"""
    result = ScrapeResult(
        task_id="t1",
        success=True,
        data={"name": "test"},
        url="https://test.com/data",
        agent_id="agent_0",
    )

    path = aggregator.submit(result)

    assert path is not None
    assert path.exists()


def test_result_aggregator_get_statistics(aggregator):
    """统计信息正确"""
    result = ScrapeResult(
        task_id="t1",
        success=True,
        data={"name": "test"},
        url="https://test.com/data",
        agent_id="agent_0",
    )

    aggregator.submit(result)
    stats = aggregator.get_statistics()

    assert stats["total_submitted"] == 1
    assert stats["total_stored"] == 1
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
python -m pytest tests/scraping/test_result_aggregator.py -v --tb=short
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 ResultAggregator**

```python
# scripts/scraping/result_aggregator.py
"""结果聚合器

对 ScrapeAgent 返回的结果进行去重、质量评分和路由存储。
"""
import hashlib
import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from scripts.scraping.scrape_agent import ScrapeResult

logger = logging.getLogger(__name__)


class ResultAggregator:
    """结果聚合器"""

    def __init__(
        self,
        dest_dir: Path,
        audit_logger=None,
        dedup_cache_size: int = 10000,
    ):
        self.dest_dir = dest_dir
        self.audit_logger = audit_logger
        self._dedup_cache: OrderedDict[str, None] = OrderedDict()
        self._dedup_cache_size = dedup_cache_size
        self._stats = {
            "total_submitted": 0,
            "total_deduplicated": 0,
            "total_stored": 0,
            "avg_quality": 0.0,
        }

    def submit(self, result: ScrapeResult) -> Optional[Path]:
        """提交结果"""
        self._stats["total_submitted"] += 1

        if not result.success:
            return None

        # URL 去重
        url_hash = self._url_hash(result.url)
        if self._is_duplicate(url_hash):
            self._stats["total_deduplicated"] += 1
            return None

        # 质量评分
        quality_score = self._score_quality(result.data)
        result.quality_score = quality_score

        # 路由存储
        dest_path = self._route_storage(result)

        # 审计日志
        if self.audit_logger:
            self.audit_logger.log(
                operation="scrape_result",
                target=result.url,
                success=True,
                quality_score=quality_score,
            )

        self._stats["total_stored"] += 1
        self._stats["avg_quality"] = (
            (self._stats["avg_quality"] * (self._stats["total_stored"] - 1) + quality_score)
            / self._stats["total_stored"]
        )

        return dest_path

    def _url_hash(self, url: str) -> str:
        """URL 规范化 + SHA256 哈希"""
        # 转小写、去 fragment、排序查询参数
        url = url.lower()
        if "#" in url:
            url = url[: url.index("#")]

        # 排序查询参数
        if "?" in url:
            base, query = url.split("?", 1)
            params = sorted(query.split("&"))
            url = f"{base}?{'&'.join(params)}"

        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _is_duplicate(self, url_hash: str) -> bool:
        """检查是否重复（LRU 缓存）"""
        if url_hash in self._dedup_cache:
            return True

        # 添加到缓存
        self._dedup_cache[url_hash] = None
        # LRU 淘汰
        if len(self._dedup_cache) > self._dedup_cache_size:
            self._dedup_cache.popitem(last=False)

        return False

    def _score_quality(self, data: Optional[dict]) -> float:
        """质量评分"""
        if not data:
            return 0.0

        # 必填字段：name, value, unit
        required_fields = ["name", "value"]
        total_required = len(required_fields)
        filled_required = sum(1 for f in required_fields if data.get(f) is not None)
        field_completeness = filled_required / total_required

        # 数值合理性检查
        value_validity = 1.0
        value = data.get("value")
        if isinstance(value, (int, float)):
            # 检查是否在合理范围
            if value < 0 or value > 1000:
                value_validity = 0.5

        return field_completeness * 0.6 + value_validity * 0.4

    def _route_storage(self, result: ScrapeResult) -> Path:
        """路由存储"""
        # 生成文件名（URL 哈希前 16 位）
        url_hash = self._url_hash(result.url)
        filename = f"{url_hash[:16]}.json"

        # 创建目标目录
        source_name = result.agent_id.split("_")[0] if "_" in result.agent_id else "unknown"
        source_dir = self.dest_dir / source_name / "data"
        source_dir.mkdir(parents=True, exist_ok=True)

        # 写入 JSON
        dest_path = source_dir / filename
        result_dict = {
            "task_id": result.task_id,
            "success": result.success,
            "data": result.data,
            "url": result.url,
            "agent_id": result.agent_id,
            "timestamp": result.timestamp,
            "latency_ms": result.latency_ms,
            "quality_score": result.quality_score,
        }
        dest_path.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2), encoding="utf-8")

        return dest_path

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return dict(self._stats)
```

- [ ] **Step 4: 运行测试确认通过**

```powershell
python -m pytest tests/scraping/test_result_aggregator.py -v --tb=short
```

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add scripts/scraping/result_aggregator.py tests/scraping/test_result_aggregator.py
git commit -m "feat: 子代理架构 - ResultAggregator 去重+质量评分+路由存储"
```

---

## Task 5: HealthMonitor 健康监控

**Files:**
- Create: `scripts/scraping/health_monitor.py`
- Create: `tests/scraping/test_health_monitor.py`

**Interfaces:**
- Consumes: `AgentManager`, `ScrapeAgent`
- Produces: `HealthMonitor.start()`, `HealthMonitor.stop()`

- [ ] **Step 1: 写入 HealthMonitor 测试**

```python
# tests/scraping/test_health_monitor.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from scripts.scraping.health_monitor import HealthMonitor


@pytest.fixture
def mock_agent_manager():
    """创建 mock agent manager"""
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
    """连续不健康触发替换"""
    monitor = HealthMonitor(mock_agent_manager, check_interval=0.1, unhealthy_threshold=2)

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
    """僵死代理触发立即替换"""
    import time
    monitor = HealthMonitor(mock_agent_manager, check_interval=0.1, stale_timeout=0.2)

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
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
python -m pytest tests/scraping/test_health_monitor.py -v --tb=short
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 HealthMonitor**

```python
# scripts/scraping/health_monitor.py
"""健康监控器

后台协程，周期性检测代理健康，触发自动替换。
"""
import asyncio
import logging
import time
from typing import Optional

from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import AgentHealth, ScrapeAgent

logger = logging.getLogger(__name__)


class HealthMonitor:
    """后台健康监控协程"""

    def __init__(
        self,
        agent_manager: AgentManager,
        check_interval: float = 30.0,
        unhealthy_threshold: int = 3,
        stale_timeout: float = 300.0,
    ):
        self.agent_manager = agent_manager
        self.check_interval = check_interval
        self.unhealthy_threshold = unhealthy_threshold
        self.stale_timeout = stale_timeout
        self._unhealthy_counts: dict[str, int] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动后台监控协程"""
        self._running = True
        self._task = asyncio.create_task(self._run_periodic_check())
        logger.info("健康监控器已启动，检查间隔: %.1fs", self.check_interval)

    async def stop(self) -> None:
        """停止监控"""
        self._running = False
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        logger.info("健康监控器已停止")

    async def _run_periodic_check(self) -> None:
        """周期性检测循环"""
        while self._running:
            await self._check_all_agents()
            await asyncio.sleep(self.check_interval)

    async def _check_all_agents(self) -> None:
        """检测所有代理"""
        for agent_id, agent in list(self.agent_manager.agents.items()):
            try:
                health = agent.get_health()
                self._update_unhealthy_count(agent_id, health)
                await self._maybe_replace(agent_id)
            except Exception as e:
                logger.warning("健康检测异常 %s: %s", agent_id, e)

    def _update_unhealthy_count(self, agent_id: str, health: AgentHealth) -> None:
        """更新连续不健康计数"""
        if health.state == "unhealthy":
            self._unhealthy_counts[agent_id] = self._unhealthy_counts.get(agent_id, 0) + 1
        else:
            self._unhealthy_counts[agent_id] = 0

    async def _maybe_replace(self, agent_id: str) -> None:
        """判断是否需要替换代理"""
        count = self._unhealthy_counts.get(agent_id, 0)
        agent = self.agent_manager.agents.get(agent_id)
        if not agent:
            return

        # 条件1：连续不健康次数超阈值
        if count >= self.unhealthy_threshold:
            logger.warning("代理 %s 连续 %d 次不健康，触发替换", agent_id, count)
            new_id = await self.agent_manager.replace_agent(agent_id)
            self._unhealthy_counts.pop(agent_id, None)
            self._unhealthy_counts[new_id] = 0
            return

        # 条件2：超过 stale_timeout 无响应
        if time.monotonic() - agent.health.last_active > self.stale_timeout:
            logger.warning("代理 %s 超过 %.0fs 无响应，立即替换", agent_id, self.stale_timeout)
            new_id = await self.agent_manager.replace_agent(agent_id)
            self._unhealthy_counts.pop(agent_id, None)
            self._unhealthy_counts[new_id] = 0
```

- [ ] **Step 4: 运行测试确认通过**

```powershell
python -m pytest tests/scraping/test_health_monitor.py -v --tb=short
```

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add scripts/scraping/health_monitor.py tests/scraping/test_health_monitor.py
git commit -m "feat: 子代理架构 - HealthMonitor 健康监控与自动替换"
```

---

## Task 6: AgentManager 代理管理器

**Files:**
- Create: `scripts/scraping/agent_manager.py`
- Create: `tests/scraping/test_agent_manager.py`

**Interfaces:**
- Consumes: `ScrapeAgent`, `LoadBalancer`, `HealthMonitor`, `ResultAggregator`, `config`
- Produces: `AgentManager.submit_task() -> ScrapeResult`, `AgentManager.submit_batch() -> list[ScrapeResult]`

- [ ] **Step 1: 写入 AgentManager 测试**

```python
# tests/scraping/test_agent_manager.py
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import ScrapeTask, ScrapeResult


@pytest.fixture
def tmp_dest_dir(tmp_path):
    return tmp_path / "test_dest"


@pytest.mark.asyncio
async def test_agent_manager_create_agent(tmp_dest_dir):
    """AgentManager 创建代理"""
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
    """AgentManager 销毁代理"""
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
    """AgentManager 提交任务"""
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
    """AgentManager 批量提交任务"""
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
    """AgentManager 获取代理池状态"""
    manager = AgentManager(dest_dir=tmp_dest_dir)
    status = manager.get_pool_status()

    assert "total_agents" in status
    assert "healthy" in status
    assert "degraded" in status
    assert "unhealthy" in status
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
python -m pytest tests/scraping/test_agent_manager.py -v --tb=short
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 AgentManager**

```python
# scripts/scraping/agent_manager.py
"""代理池管理器

管理所有 ScrapeAgent 的生命周期，提供任务提交入口。
"""
import asyncio
import logging
import uuid
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
    """代理池管理器"""

    def __init__(
        self,
        max_agents: int = 20,
        health_check_interval: float = 30.0,
        config_path: Optional[Path] = None,
        audit_logger: Optional[AuditLogger] = None,
        dest_dir: Optional[Path] = None,
    ):
        self.max_agents = max_agents
        self.agents: dict[str, ScrapeAgent] = {}
        self.load_balancer = LoadBalancer(self.agents)
        self.health_monitor = HealthMonitor(self, health_check_interval)
        self.result_aggregator = ResultAggregator(dest_dir or Path("data/scraping"), audit_logger)
        self.audit_logger = audit_logger
        self._agent_counter = 0
        self._config_path = config_path

    async def initialize(self) -> None:
        """从配置文件加载所有启用的数据源"""
        if not self._config_path:
            logger.warning("未指定配置文件路径，跳过初始化")
            return

        sources, pool = load_config(self._config_path)
        self.max_agents = pool.max_agents
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
        """动态创建代理"""
        if len(self.agents) >= self.max_agents:
            raise ValueError(f"代理池已满，最大代理数: {self.max_agents}")

        self._agent_counter += 1
        agent_id = f"{source_config['name']}_{self._agent_counter}"

        # 创建熔断器和限流器
        circuit_breaker = CircuitBreaker(
            failure_threshold=source_config.get("circuit_failure_threshold", 5),
            recovery_timeout=source_config.get("circuit_recovery_timeout", 30.0),
        )
        rate_limiter = TokenBucketLimiter(
            capacity=source_config.get("rate_limit_capacity", 5),
            refill_rate=source_config.get("rate_limit_refill", 5.0),
        )

        # 创建代理
        agent = ScrapeAgent(
            agent_id=agent_id,
            source_config=source_config,
            circuit_breaker=circuit_breaker,
            rate_limiter=rate_limiter,
            audit_logger=self.audit_logger,
        )

        self.agents[agent_id] = agent
        self.load_balancer.add_agent(agent_id, agent)

        logger.info("创建代理: %s", agent_id)
        return agent_id

    async def destroy_agent(self, agent_id: str) -> None:
        """销毁代理"""
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        await agent.close()
        del self.agents[agent_id]
        self.load_balancer.remove_agent(agent_id)

        logger.info("销毁代理: %s", agent_id)

    async def replace_agent(self, agent_id: str) -> str:
        """替换不健康代理"""
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
        """提交任务到代理池"""
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

        # 处理结果
        if result.success:
            self.result_aggregator.submit(result)

        return result

    async def submit_batch(self, tasks: list[ScrapeTask]) -> list[ScrapeResult]:
        """批量提交任务（并行执行）"""
        tasks_coroutines = [self.submit_task(task) for task in tasks]
        results = await asyncio.gather(*tasks_coroutines)
        return results

    def get_pool_status(self) -> dict:
        """代理池状态概览"""
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
        """关闭所有代理"""
        await self.health_monitor.stop()

        for agent_id in list(self.agents.keys()):
            await self.destroy_agent(agent_id)

        logger.info("代理池已关闭")
```

- [ ] **Step 4: 运行测试确认通过**

```powershell
python -m pytest tests/scraping/test_agent_manager.py -v --tb=short
```

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add scripts/scraping/agent_manager.py tests/scraping/test_agent_manager.py
git commit -m "feat: 子代理架构 - AgentManager 代理池管理与任务分发"
```

---

## Task 7: 配置文件与集成测试

**Files:**
- Create: `config/scrape_sources.yaml`
- Create: `scripts/scraping/__init__.py`
- Create: `tests/scraping/conftest.py`
- Run: `pytest tests/scraping/`

**Interfaces:**
- Produces: 完整的 scraping 模块导出
- Produces: 数据源配置文件

- [ ] **Step 1: 创建配置文件和 __init__.py**

```yaml
# config/scrape_sources.yaml
sources:
  - name: pubmed
    type: api
    base_url: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
    rate_limit:
      capacity: 3
      refill_rate: 3.0
    circuit_breaker:
      failure_threshold: 5
      recovery_timeout: 30.0
    parser: pubmed_xml
    enabled: true

  - name: cnki
    type: html
    base_url: https://kns.cnki.net/
    rate_limit:
      capacity: 1
      refill_rate: 0.5
    circuit_breaker:
      failure_threshold: 3
      recovery_timeout: 60.0
    parser: cnki_html
    headers:
      User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      Accept-Language: "zh-CN,zh;q=0.9"
    enabled: true

  - name: medical_guideline
    type: html
    base_url: https://www.cma.org.cn/
    rate_limit:
      capacity: 2
      refill_rate: 1.0
    circuit_breaker:
      failure_threshold: 3
      recovery_timeout: 45.0
    parser: guideline_html
    enabled: true

pool:
  max_agents: 20
  health_check_interval: 30.0
  unhealthy_threshold: 3
  stale_timeout: 300.0
```

```python
# scripts/scraping/__init__.py
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
```

- [ ] **Step 2: 创建 conftest.py**

```python
# tests/scraping/conftest.py
"""测试配置文件

为 scraping 模块提供共享的 pytest fixtures。
"""
import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（pytest-asyncio 需要）"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

- [ ] **Step 3: 运行集成测试**

```powershell
python -m pytest tests/scraping/ -v --tb=short
```

Expected: PASS (所有测试通过)

- [ ] **Step 4: 运行完整测试回归**

```powershell
python -m pytest tests/ -v --tb=short -x
```

Expected: PASS (所有项目测试通过)

- [ ] **Step 5: 提交**

```powershell
git add config/scrape_sources.yaml scripts/scraping/__init__.py tests/scraping/conftest.py
git commit -m "feat: 子代理架构 - 配置文件与集成测试完成"
```

---

## 自我审查

### 1. 设计文档覆盖率检查

| 设计文档需求 | 实现任务 | 状态 |
|-------------|---------|------|
| 子代理节点动态创建与管理 | Task 6 (AgentManager.create_agent/destroy_agent/replace_agent) | ✅ |
| 数据请求分发与负载均衡 | Task 3 (LoadBalancer.select_agent) | ✅ |
| 原始数据直接抓取与解析 | Task 2 (ScrapeAgent.fetch/parse/execute) | ✅ |
| 代理节点健康状态监控 | Task 5 (HealthMonitor._check_all_agents) | ✅ |
| 代理节点自动替换机制 | Task 5 (HealthMonitor._maybe_replace) | ✅ |
| 加权轮询负载均衡算法 | Task 3 (LoadBalancer.select_agent 加权随机) | ✅ |
| 健康分算法 | Task 2 (ScrapeAgent._recalculate_health) | ✅ |
| 反爬策略（限流/熔断/重试） | Task 2 (ScrapeAgent.execute) | ✅ |
| URL 去重与质量评分 | Task 4 (ResultAggregator) | ✅ |
| 配置文件加载 | Task 1 (config.load_config) | ✅ |
| 错误处理 | Task 2 (ScrapeAgent.execute 异常处理) | ✅ |

### 2. 占位符扫描

- [ ] 无 "TBD", "TODO", "implement later"
- [ ] 无 "Add appropriate error handling"
- [ ] 无 "Write tests for the above" (所有测试均已提供)
- [ ] 无 "Similar to Task N"

### 3. 类型一致性检查

- `AgentHealth.state` 属性在 Task 1 定义，Task 2/3/5/6 均正确使用
- `ScrapeTask.source_type` 在 Task 1 定义，Task 2/3/6 均正确使用
- `ScrapeResult.success` 在 Task 1 定义，Task 2/4/6 均正确使用
- `AgentManager.create_agent()` 返回类型 `str`，Task 6 和 Task 5 中 `replace_agent` 均正确调用

---

## 执行方式选择

**Plan complete and saved to `docs/superpowers/plans/2026-07-13-async-scrape-agent-implementation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?"
