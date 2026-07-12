"""审计日志（防篡改）

特性：
- JSONL 格式（每行一条 JSON）
- 哈希链：每条日志含前一条的 SHA256
- ISO 时间戳
- append-only（仅追加）
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path


class AuditLogger:
    """审计日志器

    Args:
        log_path: 日志文件路径
    """

    GENESIS_HASH = "GENESIS"

    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._load_last_hash()

    def log(
        self,
        operation: str,
        target: str,
        success: bool = True,
        **extra,
    ) -> None:
        """记录一条审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "target": target,
            "success": success,
            "prev_hash": self._last_hash,
        }
        entry.update(extra)
        # 计算当前条目的哈希
        entry_str = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry["hash"] = hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
        # 追加写入
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._last_hash = entry["hash"]

    def _load_last_hash(self) -> str:
        """加载最后一条日志的哈希（用于断点续链）"""
        if not self.log_path.exists():
            return self.GENESIS_HASH
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        if not lines or not lines[0]:
            return self.GENESIS_HASH
        last_entry = json.loads(lines[-1])
        return last_entry.get("hash", self.GENESIS_HASH)
