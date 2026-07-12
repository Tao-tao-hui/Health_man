"""测试审计日志"""
import json
from pathlib import Path

from scripts.utils.audit_logger import AuditLogger


def test_log_writes_jsonl(tmp_path):
    """日志必须以 JSONL 格式写入"""
    logger = AuditLogger(log_path=tmp_path / "audit.log")
    logger.log("download", "nhanes_demo_j.xpt", success=True)
    content = (tmp_path / "audit.log").read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["operation"] == "download"
    assert entry["target"] == "nhanes_demo_j.xpt"
    assert entry["success"] is True


def test_hash_chain_links_entries(tmp_path):
    """每条日志必须含前一条的哈希，形成链"""
    logger = AuditLogger(log_path=tmp_path / "audit.log")
    logger.log("op1", "file1")
    logger.log("op2", "file2")
    entries = [json.loads(line) for line in (tmp_path / "audit.log").read_text().strip().split("\n")]
    # 第 2 条的 prev_hash 应等于第 1 条的 hash
    assert entries[1]["prev_hash"] == entries[0]["hash"]
    # 第 1 条的 prev_hash 应为初始值
    assert entries[0]["prev_hash"] == "GENESIS"


def test_log_has_timestamp(tmp_path):
    """每条日志必须含时间戳"""
    logger = AuditLogger(log_path=tmp_path / "audit.log")
    logger.log("test", "file")
    entry = json.loads((tmp_path / "audit.log").read_text().strip())
    assert "timestamp" in entry
    assert "T" in entry["timestamp"]  # ISO 格式
