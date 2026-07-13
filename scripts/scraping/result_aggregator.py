# scripts/scraping/result_aggregator.py - 结果聚合器
"""结果聚合器

对 ScrapeAgent 返回的 ScrapeResult 进行：
  1. URL 去重（规范化后 SHA256 + LRU 缓存）
  2. 数据质量评分（字段完整性 60% + 取值合理性 40%）
  3. 路由存储为 JSON 文件（按数据源名称分目录）
  4. 累计统计信息（提交数 / 去重数 / 存储数 / 平均质量分）

去重规范化规则：
  - 全部转小写
  - 剥离 #fragment
  - 查询参数按字典序排序

存储路径布局：
  <dest_dir>/<source_name>/data/<url_hash_前16位>.json
"""
import hashlib
import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from scripts.scraping.scrape_agent import ScrapeResult

logger = logging.getLogger(__name__)


class ResultAggregator:
    """结果聚合器

    通过 submit() 接收 ScrapeResult，按去重 / 评分 / 路由顺序处理后返回存储路径。
    重复或失败结果返回 None。
    """

    def __init__(
        self,
        dest_dir: Path,
        audit_logger=None,
        dedup_cache_size: int = 10000,
    ):
        """初始化结果聚合器

        Args:
            dest_dir: JSON 文件存储根目录
            audit_logger: 可选的审计日志器（需提供 log(operation, target, success, **extra) 方法）
            dedup_cache_size: LRU 去重缓存容量，默认 10000
        """
        self.dest_dir = Path(dest_dir)
        self.audit_logger = audit_logger
        # OrderedDict 实现 LRU：尾部插入、头部淘汰（popitem(last=False)）
        self._dedup_cache: "OrderedDict[str, None]" = OrderedDict()
        self._dedup_cache_size = dedup_cache_size
        self._stats = {
            "total_submitted": 0,
            "total_deduplicated": 0,
            "total_stored": 0,
            "avg_quality": 0.0,
        }

    def submit(self, result: ScrapeResult) -> Optional[Path]:
        """提交一个抓取结果

        处理顺序：统计 → 成功检查 → URL 去重 → 质量评分 → 路由存储 → 审计日志

        Args:
            result: ScrapeAgent 返回的结果对象

        Returns:
            存储成功返回写入文件的 Path；重复或失败返回 None
        """
        self._stats["total_submitted"] += 1

        # 失败结果不存储（仍计入 total_submitted）
        if not result.success:
            return None

        # URL 去重：命中则跳过存储
        url_hash = self._url_hash(result.url)
        if self._is_duplicate(url_hash):
            self._stats["total_deduplicated"] += 1
            return None

        # 质量评分：写回 result.quality_score 供下游使用
        quality_score = self._score_quality(result.data)
        result.quality_score = quality_score

        # 路由存储为 JSON 文件
        dest_path = self._route_storage(result)

        # 审计日志（可选）
        if self.audit_logger:
            self.audit_logger.log(
                operation="scrape_result",
                target=result.url,
                success=True,
                quality_score=quality_score,
            )

        # 滑动平均质量分
        self._stats["total_stored"] += 1
        self._stats["avg_quality"] = (
            (self._stats["avg_quality"] * (self._stats["total_stored"] - 1) + quality_score)
            / self._stats["total_stored"]
        )

        return dest_path

    def _url_hash(self, url: str) -> str:
        """URL 规范化 + SHA256 哈希

        规范化步骤：
          1. 全部转小写
          2. 剥离 #fragment
          3. 查询参数按字典序排序

        Args:
            url: 原始 URL

        Returns:
            64 字符 SHA256 十六进制摘要
        """
        # 转小写
        url = url.lower()
        # 去 fragment
        if "#" in url:
            url = url[: url.index("#")]

        # 排序查询参数（让 ?a=1&b=2 与 ?b=2&a=1 视为同一 URL）
        if "?" in url:
            base, query = url.split("?", 1)
            params = sorted(query.split("&"))
            url = f"{base}?{'&'.join(params)}"

        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _is_duplicate(self, url_hash: str) -> bool:
        """检查 URL 哈希是否已存在于 LRU 缓存

        命中时不更新缓存顺序（保持 LRU 简化语义）；未命中则插入，
        缓存超出容量时淘汰最久未访问项。

        Args:
            url_hash: _url_hash 返回的哈希摘要

        Returns:
            True 表示重复，False 表示新 URL（已写入缓存）
        """
        if url_hash in self._dedup_cache:
            return True

        # 添加到缓存并执行 LRU 淘汰
        self._dedup_cache[url_hash] = None
        if len(self._dedup_cache) > self._dedup_cache_size:
            self._dedup_cache.popitem(last=False)

        return False

    def _score_quality(self, data: Optional[dict]) -> float:
        """数据质量评分

        评分公式：字段完整性 * 0.6 + 取值合理性 * 0.4

        - 字段完整性：必填字段（name, value）的填充比例
        - 取值合理性：数值字段在合理范围 [0, 1000] 内为 1.0，否则 0.5；
          非数值或不存在时默认 1.0（不扣分）

        Args:
            data: ScrapeResult.data 字典

        Returns:
            质量分 [0.0, 1.0]
        """
        if not data:
            return 0.0

        # 必填字段：name, value
        required_fields = ["name", "value"]
        total_required = len(required_fields)
        filled_required = sum(1 for f in required_fields if data.get(f) is not None)
        field_completeness = filled_required / total_required

        # 数值合理性检查
        value_validity = 1.0
        value = data.get("value")
        if isinstance(value, (int, float)):
            # 检查是否在合理范围
            if value < 0 or value > 1000:
                value_validity = 0.5

        return field_completeness * 0.6 + value_validity * 0.4

    def _route_storage(self, result: ScrapeResult) -> Path:
        """路由存储：写入 JSON 文件

        路径规则：<dest_dir>/<source_name>/data/<url_hash_前16位>.json
        source_name 从 agent_id 前缀切分（如 "agent_0" -> "agent"），
        无下划线时使用 "unknown"。

        Args:
            result: 已评分的 ScrapeResult

        Returns:
            实际写入的文件路径
        """
        # 文件名取 URL 哈希前 16 位（足以区分典型规模 URL 集）
        url_hash = self._url_hash(result.url)
        filename = f"{url_hash[:16]}.json"

        # 创建目标目录（按数据源分目录）
        source_name = result.agent_id.split("_")[0] if "_" in result.agent_id else "unknown"
        source_dir = self.dest_dir / source_name / "data"
        source_dir.mkdir(parents=True, exist_ok=True)

        # 写入 JSON（UTF-8 + 缩进，便于人工审查）
        dest_path = source_dir / filename
        result_dict = {
            "task_id": result.task_id,
            "success": result.success,
            "data": result.data,
            "url": result.url,
            "agent_id": result.agent_id,
            "timestamp": result.timestamp,
            "latency_ms": result.latency_ms,
            "quality_score": result.quality_score,
        }
        dest_path.write_text(
            json.dumps(result_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return dest_path

    def get_statistics(self) -> dict:
        """获取累计统计信息

        Returns:
            dict 包含 total_submitted / total_deduplicated / total_stored / avg_quality
        """
        return dict(self._stats)
