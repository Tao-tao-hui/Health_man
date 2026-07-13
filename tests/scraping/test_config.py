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
