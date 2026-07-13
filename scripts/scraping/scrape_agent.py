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
