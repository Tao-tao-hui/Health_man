# tests/scraping/test_result_aggregator.py - ResultAggregator 结果聚合器测试
"""ResultAggregator 单元测试

覆盖：URL 去重、质量评分、路由存储、统计信息四个核心能力。
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from scripts.scraping.result_aggregator import ResultAggregator
from scripts.scraping.scrape_agent import ScrapeResult


@pytest.fixture
def tmp_dest_dir(tmp_path):
    """临时目标根目录（pytest tmp_path 自动清理）"""
    return tmp_path / "test_dest"


@pytest.fixture
def aggregator(tmp_dest_dir):
    """默认 ResultAggregator 实例"""
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
