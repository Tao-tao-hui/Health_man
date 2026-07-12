"""测试下载调度器"""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.data.download_scheduler import DownloadScheduler, DownloadResult
from scripts.data.source_adapter import SourceAdapter


class FakeAdapter(SourceAdapter):
    """用于测试的假适配器"""

    def list_files(self):
        return [
            {"url": "http://test.com/a.csv", "filename": "a.csv", "expected_size_bytes": 100},
            {"url": "http://test.com/b.csv", "filename": "b.csv", "expected_size_bytes": 200},
        ]

    def download(self, file_meta, dest_dir):
        dest = Path(dest_dir) / file_meta["filename"]
        dest.write_bytes(b"x" * file_meta["expected_size_bytes"])
        return dest

    def verify_checksum(self, file_path, expected_sha256):
        return True  # 测试中跳过校验

    def get_metadata_template(self):
        return {"dataset_id": "FAKE"}


def test_scheduler_downloads_all_files(tmp_path):
    """调度器必须下载所有文件"""
    adapter = FakeAdapter()
    scheduler = DownloadScheduler(max_concurrent=2, max_size_mb=1)
    results = scheduler.schedule_download(adapter, tmp_path)
    assert len(results) == 2
    assert all(r.success for r in results)
    # 验证文件已写入
    assert (tmp_path / "a.csv").exists()
    assert (tmp_path / "b.csv").exists()


def test_scheduler_respects_size_limit(tmp_path):
    """单文件超限时必须跳过并标记"""
    adapter = FakeAdapter()
    # 设 max_size_mb=0（实际阈值约 0.0001MB），b.csv 200 bytes 超限
    scheduler = DownloadScheduler(max_concurrent=1, max_size_mb=0)
    # 用 monkeypatch 调整阈值
    scheduler.max_file_size_bytes = 150  # b.csv 200 bytes 超限
    results = scheduler.schedule_download(adapter, tmp_path)
    # a.csv 100 bytes 通过，b.csv 200 bytes 超限
    assert results[0].success is True
    assert results[1].success is False
    assert "exceeds size limit" in results[1].error_message


def test_scheduler_retries_on_failure(tmp_path):
    """下载失败必须重试"""
    adapter = FakeAdapter()
    call_count = {"download": 0}

    original_download = adapter.download

    def flaky_download(file_meta, dest_dir):
        call_count["download"] += 1
        if call_count["download"] < 3:  # 前 2 次失败
            raise ConnectionError("network error")
        return original_download(file_meta, dest_dir)

    adapter.download = flaky_download
    scheduler = DownloadScheduler(max_concurrent=1, max_size_mb=10, max_retries=3)
    results = scheduler.schedule_download(adapter, tmp_path)
    assert results[0].success is True
    # a.csv 重试 2 次后第 3 次成功（call 1,2,3），b.csv 第 4 次成功
    assert call_count["download"] == 4


def test_scheduler_returns_download_results(tmp_path):
    """结果必须含 filename, path, success, error_message, duration_seconds"""
    adapter = FakeAdapter()
    scheduler = DownloadScheduler(max_concurrent=2, max_size_mb=10)
    results = scheduler.schedule_download(adapter, tmp_path)
    for r in results:
        assert hasattr(r, "filename")
        assert hasattr(r, "path")
        assert hasattr(r, "success")
        assert hasattr(r, "error_message")
        assert hasattr(r, "duration_seconds")
        assert isinstance(r.duration_seconds, float)
