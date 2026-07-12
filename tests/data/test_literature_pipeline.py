"""LayerBPipeline 单元测试

验证端到端流水线整合功能。
使用 FakeAdapter 模拟数据源（避免真实网络请求）。
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from scripts.data.literature_pipeline import LayerBPipeline, PipelineResult
from scripts.data.source_adapter import SourceAdapter


class FakeAdapter(SourceAdapter):
    """用于测试的假适配器"""

    def list_files(self):
        return [
            {"url": "http://fake/test1.xml", "filename": "test1.xml", "expected_size_bytes": 100},
            {"url": "http://fake/test2.xml", "filename": "test2.xml", "expected_size_bytes": 200},
        ]

    def download(self, file_meta, dest_dir):
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / file_meta["filename"]
        path.write_bytes(b"<fake>content</fake>")
        return path

    def verify_checksum(self, file_path, expected_sha256):
        return True

    def get_metadata_template(self):
        return {"dataset_id": "Fake_Test", "source_url": "http://fake"}


class TestLayerBPipeline:
    """LayerBPipeline 测试套件"""

    def test_run_returns_pipeline_result(self, tmp_path):
        """测试流水线返回结果对象"""
        pipeline = LayerBPipeline()
        adapter = FakeAdapter()
        result = pipeline.run(adapter, tmp_path)
        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert result.downloaded_count == 2

    def test_run_creates_files_in_dest(self, tmp_path):
        """测试流水线在目标目录创建文件"""
        pipeline = LayerBPipeline()
        adapter = FakeAdapter()
        pipeline.run(adapter, tmp_path)
        assert (tmp_path / "test1.xml").exists()
        assert (tmp_path / "test2.xml").exists()

    def test_audit_size_under_limit(self, tmp_path):
        """测试体量审计在限制内"""
        pipeline = LayerBPipeline()
        (tmp_path / "a.xml").write_bytes(b"x" * 100)
        (tmp_path / "b.xml").write_bytes(b"y" * 200)
        audit = pipeline.audit_size(tmp_path)
        assert audit["total_bytes"] == 300
        assert audit["within_limit"] is True

    def test_audit_size_exceeds_limit(self, tmp_path):
        """测试体量审计超限"""
        pipeline = LayerBPipeline(max_size_mb=0.0001)  # 极小限制
        (tmp_path / "big.xml").write_bytes(b"x" * 200)
        audit = pipeline.audit_size(tmp_path)
        assert audit["within_limit"] is False
