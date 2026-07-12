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


def test_resume_chain_from_existing_log(tmp_path):
    """重新初始化时必须接续已有链的最后一哈希"""
    log_path = tmp_path / "audit.log"
    logger1 = AuditLogger(log_path=log_path)
    logger1.log("op1", "file1")
    first_hash = json.loads(log_path.read_text(encoding="utf-8").strip())["hash"]

    # 新实例指向同一文件
    logger2 = AuditLogger(log_path=log_path)
    logger2.log("op2", "file2")

    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").strip().split("\n")]
    # 第 2 条的 prev_hash 应等于第 1 条的 hash（断点续链）
    assert entries[1]["prev_hash"] == first_hash
    assert entries[1]["prev_hash"] == entries[0]["hash"]


def test_log_accepts_extra_fields(tmp_path):
    """log 必须支持 **extra 扩展字段"""
    logger = AuditLogger(log_path=tmp_path / "audit.log")
    logger.log("download", "nhanes.xpt", success=True, user="admin", bytes=1024)
    entry = json.loads((tmp_path / "audit.log").read_text(encoding="utf-8").strip())
    assert entry["user"] == "admin"
    assert entry["bytes"] == 1024
