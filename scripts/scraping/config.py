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
