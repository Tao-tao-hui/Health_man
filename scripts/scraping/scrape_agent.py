# scripts/scraping/scrape_agent.py - 数据结构部分
"""子代理模块

ScrapeAgent: 单个子代理，负责 HTTP 抓取和内容解析
数据结构: AgentHealth, ScrapeTask, ScrapeResult
"""
import asyncio
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

    @property
    def state(self) -> str:
        """根据健康分计算状态（只读属性，不可直接设置）"""
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


class RateLimitError(Exception):
    """限流错误（HTTP 429）"""
    pass


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
        """初始化子代理

        Args:
            agent_id: 代理唯一标识
            source_config: 数据源配置（含 name/type/base_url/parser/headers 等）
            circuit_breaker: 熔断器实例（外部共享或独立）
            rate_limiter: 令牌桶限流器实例
            audit_logger: 可选的审计日志器
        """
        self.agent_id = agent_id
        self.source_config = source_config
        self.circuit_breaker = circuit_breaker
        self.rate_limiter = rate_limiter
        self.audit_logger = audit_logger
        self.health = AgentHealth()
        # 初始化 last_active 为当前时间，避免默认 0.0 被 HealthMonitor 误判为
        # 僵死代理并触发无限替换循环（新代理再次以 0.0 初始化）
        self.health.last_active = time.monotonic()
        # 滑动窗口：最近 20 次记录用于健康分计算
        self._latency_history: deque[float] = deque(maxlen=20)
        self._success_history: deque[bool] = deque(maxlen=20)
        # HTTP 会话懒加载（execute 首次调用时创建）
        self._http_session: aiohttp.ClientSession | None = None
        self._headers = source_config.get("headers", {})

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话（懒加载）

        多次调用复用同一会话，需通过 close() 显式关闭。
        """
        if self._http_session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self._http_session = aiohttp.ClientSession(timeout=timeout)
        return self._http_session

    async def fetch(self, url: str, params: dict = None) -> tuple[str, float]:
        """HTTP 请求获取原始内容

        Args:
            url: 目标 URL
            params: 可选的查询参数

        Returns:
            (响应内容, 延迟毫秒)

        Raises:
            RateLimitError: HTTP 429
            PermissionError: HTTP 403
        """
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
        """解析内容

        根据 source_config["parser"] 选择解析器：
        - json: 直接 json.loads
        - html/cnki_html/guideline_html: BeautifulSoup + CSS 选择器
        - pubmed_xml: ElementTree 解析
        - 其他: 原文返回

        Args:
            content: 待解析的原始文本
            parse_rules: 解析规则（如 {"selector": "h1"}）

        Returns:
            解析后的字典
        """
        # parse_rules["format"] 优先于 source_config["parser"]
        parser_type = parse_rules.get("format") or self.source_config.get("parser", "json")

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
        """执行完整抓取任务

        流程：熔断检查 → 限流获取 → HTTP 抓取 → 内容解析 → 健康分更新

        Args:
            task: 抓取任务

        Returns:
            ScrapeResult（含成功标志、数据或错误信息）
        """
        self.health.last_active = time.monotonic()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        # 熔断检查：OPEN 状态直接拒绝
        if not self.circuit_breaker.can_call():
            return ScrapeResult(
                task_id=task.task_id,
                success=False,
                url=task.url,
                agent_id=self.agent_id,
                timestamp=timestamp,
                error=f"熔断器已开启，状态: {self.circuit_breaker.state.value}",
            )

        # 限流获取（带重试，最多 3 次指数退避）
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
        """记录成功并更新健康分

        同步通知熔断器记录成功：HALF_OPEN 探测成功后归零 _failure_count 并回到
        CLOSED，避免熔断器开启后无法恢复。
        """
        self._success_history.append(True)
        self._latency_history.append(latency_ms)
        self.health.error_count = 0
        self._recalculate_health()
        # 同步熔断器成功记录，使其能从 HALF_OPEN 正常恢复到 CLOSED
        self.circuit_breaker.record_success()

    def record_failure(self, error: str) -> None:
        """记录失败并更新健康分"""
        self._success_history.append(False)
        self.health.error_count += 1
        self._recalculate_health()

    def _recalculate_health(self) -> None:
        """重算健康分

        公式: 0.4 * 成功率 + 0.3 * (1 - 归一化延迟) + 0.3 * (1 - 错误率)
        """
        if not self._success_history:
            return

        success_rate = sum(self._success_history) / len(self._success_history)

        avg_latency_ms = 0.0
        if self._latency_history:
            avg_latency_ms = sum(self._latency_history) / len(self._latency_history)
            normalized_latency = min(avg_latency_ms / 5000, 1.0)
        else:
            normalized_latency = 0.0

        error_rate = min(self.health.error_count / 10, 1.0)

        self.health.success_rate = success_rate
        self.health.avg_latency_ms = avg_latency_ms
        self.health.health_score = (
            0.4 * success_rate
            + 0.3 * (1 - normalized_latency)
            + 0.3 * (1 - error_rate)
        )

    def get_health(self) -> AgentHealth:
        """获取当前健康状态"""
        return self.health

    async def close(self) -> None:
        """关闭 HTTP 会话，释放连接资源"""
        if self._http_session:
            await self._http_session.close()
            self._http_session = None
