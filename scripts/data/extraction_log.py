"""文献提取日志管理器

管理文献提取记录的生命周期：
- pending: 待提取
- extracted: 已提取（自动/半自动）
- verified: 已人工校验
- rejected: 已拒绝（数据质量问题）

日志文件持久化为 CSV，支持断点续传。
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class ExtractionLogManager:
    """文献提取日志管理器

    Args:
        log_path: CSV 日志文件路径
    """

    # CSV 列定义
    COLUMNS = ["pmid", "title", "source", "status", "created_at", "updated_at"]

    # 合法状态值
    VALID_STATUSES = {"pending", "extracted", "verified", "rejected"}

    def __init__(self, log_path: Path | None = None):
        self.log_path = Path(log_path) if log_path else Path(
            "e:/Health_man/data/knowledge/chinese_reference/B_literature/_logs/literature_extraction_log.csv"
        )
        self._records: list[dict[str, Any]] = []
        # 尝试加载已有日志
        if self.log_path.exists():
            self.load()

    def add_entry(
        self,
        pmid: str,
        title: str,
        source: str,
        status: str = "pending",
    ) -> None:
        """添加一条提取记录

        Args:
            pmid: 文献 PMID 或唯一标识
            title: 文献标题
            source: 数据来源（pubmed/figshare/gasc 等）
            status: 初始状态（默认 pending）
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"非法状态: {status}，合法值: {self.VALID_STATUSES}")
        now = datetime.now().isoformat()
        self._records.append({
            "pmid": pmid,
            "title": title,
            "source": source,
            "status": status,
            "created_at": now,
            "updated_at": now,
        })
        logger.info("添加提取记录: pmid=%s, source=%s", pmid, source)

    def update_status(self, pmid: str, status: str) -> None:
        """更新指定文献的提取状态

        Args:
            pmid: 文献 PMID
            status: 新状态
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"非法状态: {status}，合法值: {self.VALID_STATUSES}")
        for record in self._records:
            if record["pmid"] == pmid:
                record["status"] = status
                record["updated_at"] = datetime.now().isoformat()
                logger.info("更新状态: pmid=%s → %s", pmid, status)
                return
        logger.warning("未找到 pmid=%s 的记录", pmid)

    def get_pending(self) -> list[dict[str, Any]]:
        """返回所有 pending 状态的记录"""
        return [r for r in self._records if r["status"] == "pending"]

    def get_all(self) -> list[dict[str, Any]]:
        """返回所有记录"""
        return list(self._records)

    def save(self) -> Path:
        """保存日志到 CSV

        Returns:
            保存的文件路径
        """
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self._records, columns=self.COLUMNS)
        df.to_csv(self.log_path, index=False, encoding="utf-8")
        logger.info("保存提取日志: %d 条记录 → %s", len(self._records), self.log_path)
        return self.log_path

    def load(self) -> None:
        """从 CSV 加载日志"""
        if not self.log_path.exists():
            logger.warning("日志文件不存在: %s", self.log_path)
            return
        df = pd.read_csv(self.log_path, encoding="utf-8", dtype=str)
        self._records = df.to_dict("records")
        logger.info("加载提取日志: %d 条记录 ← %s", len(self._records), self.log_path)
