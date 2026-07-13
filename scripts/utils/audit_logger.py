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

    def verify_chain(self) -> bool:
        """验证审计日志哈希链完整性

        逐条重算每条日志的 SHA256，与日志中记录的 hash 字段比对。
        同时验证 prev_hash 链式引用是否正确。

        Returns:
            True 如果所有条目哈希链完整无篡改，False 如果发现任何不一致
        """
        if not self.log_path.exists():
            return True  # 空文件视为完整

        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        if not lines or not lines[0]:
            return True  # 空文件视为完整

        prev_hash = self.GENESIS_HASH
        for i, line in enumerate(lines):
            entry = json.loads(line)
            # 验证 prev_hash 链式引用
            if entry.get("prev_hash") != prev_hash:
                return False
            # 重算哈希（排除 hash 字段本身）
            entry_for_hash = {k: v for k, v in entry.items() if k != "hash"}
            entry_str = json.dumps(entry_for_hash, sort_keys=True, ensure_ascii=False)
            expected_hash = hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
            if entry.get("hash") != expected_hash:
                return False
            prev_hash = entry["hash"]

        return True

    def _load_last_hash(self) -> str:
        """加载最后一条日志的哈希（用于断点续链）"""
        if not self.log_path.exists():
            return self.GENESIS_HASH
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        if not lines or not lines[0]:
            return self.GENESIS_HASH
        last_entry = json.loads(lines[-1])
        # 缺失 hash 字段视为篡改/损坏信号，抛异常而非静默回退 GENESIS
        if "hash" not in last_entry:
            raise ValueError(f"审计日志最后一行缺少 hash 字段，可能被篡改: {self.log_path}")
        return last_entry["hash"]
