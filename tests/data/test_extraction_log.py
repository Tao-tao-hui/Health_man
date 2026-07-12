"""ExtractionLogManager 单元测试

验证文献提取日志的增删查改和 CSV 持久化。
"""
import pytest
from pathlib import Path

from scripts.data.extraction_log import ExtractionLogManager


class TestExtractionLogManager:
    """ExtractionLogManager 测试套件"""

    def test_add_entry_creates_record(self, tmp_path):
        """测试添加条目创建记录"""
        log_path = tmp_path / "extraction_log.csv"
        manager = ExtractionLogManager(log_path)
        manager.add_entry("34567890", "Body composition study", "pubmed")
        records = manager.get_all()
        assert len(records) == 1
        assert records[0]["pmid"] == "34567890"
        assert records[0]["status"] == "pending"

    def test_update_status_changes_record(self, tmp_path):
        """测试更新状态"""
        log_path = tmp_path / "extraction_log.csv"
        manager = ExtractionLogManager(log_path)
        manager.add_entry("34567890", "Test", "pubmed")
        manager.update_status("34567890", "extracted")
        records = manager.get_all()
        assert records[0]["status"] == "extracted"

    def test_get_pending_returns_only_pending(self, tmp_path):
        """测试 get_pending 只返回 pending 状态"""
        log_path = tmp_path / "extraction_log.csv"
        manager = ExtractionLogManager(log_path)
        manager.add_entry("111", "Title A", "pubmed", status="pending")
        manager.add_entry("222", "Title B", "pubmed", status="extracted")
        manager.add_entry("333", "Title C", "figshare", status="pending")
        pending = manager.get_pending()
        assert len(pending) == 2
        pmids = [r["pmid"] for r in pending]
        assert "111" in pmids
        assert "333" in pmids

    def test_save_and_load_roundtrip(self, tmp_path):
        """测试保存和加载的往返一致性"""
        log_path = tmp_path / "extraction_log.csv"
        manager1 = ExtractionLogManager(log_path)
        manager1.add_entry("111", "Title A", "pubmed")
        manager1.add_entry("222", "Title B", "figshare")
        manager1.save()

        manager2 = ExtractionLogManager(log_path)
        manager2.load()
        records = manager2.get_all()
        assert len(records) == 2
        assert records[0]["pmid"] == "111"
