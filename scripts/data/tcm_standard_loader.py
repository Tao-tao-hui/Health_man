"""中医体质 9 型标准加载器

加载 ZYYXH/T157-2009《中医体质分类与判定》标准数据。
标准包含：
- 9 型体质定义（平和质、气虚质、阳虚质、阴虚质、痰湿质、湿热质、血瘀质、气郁质、特禀质）
- 60 题量表（每题归属于一种体质）
- 评分规则（原始分 → 转化分 → 判定阈值）

转化分公式：transformed_score = (raw_sum - question_count) / (question_count * 4) * 100
判定阈值：转化分 >= 60 判定为该型体质
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TcmStandardLoader:
    """中医体质标准加载器

    加载并查询 ZYYXH/T157-2009《中医体质分类与判定》标准数据。

    Args:
        standard_path: tcm_constitution.json 路径（默认在 B_literature/_standards/）
    """

    # 默认标准文件路径：中医体质分类与判定国标
    DEFAULT_PATH = Path(
        "e:/Health_man/data/knowledge/chinese_reference/B_literature/_standards/tcm_constitution.json"
    )

    def __init__(self, standard_path: Path | None = None):
        """初始化加载器

        Args:
            standard_path: 自定义标准文件路径；为 None 时使用默认路径
        """
        self.standard_path = standard_path or self.DEFAULT_PATH

    def load(self) -> dict[str, Any]:
        """加载完整的中医体质标准

        Returns:
            含 types、questions、scoring 三个顶层键的标准字典

        Raises:
            FileNotFoundError: 标准文件不存在
            json.JSONDecodeError: JSON 格式错误
        """
        with open(self.standard_path, "r", encoding="utf-8") as file_handle:
            standard = json.load(file_handle)
        logger.info(
            "加载中医体质标准: %s, %d 型, %d 题",
            standard.get("standard_id", ""),
            len(standard.get("types", {})),
            len(standard.get("questions", [])),
        )
        return standard

    def get_type_names(self) -> list[str]:
        """返回 9 型体质名称列表

        Returns:
            体质名称列表（如 ["平和质", "气虚质", ...]）
        """
        standard = self.load()
        return list(standard["types"].keys())

    def get_questions(self) -> list[dict[str, Any]]:
        """返回 60 题量表

        Returns:
            题目列表，每题包含 number、text、type 三个字段
        """
        standard = self.load()
        return standard["questions"]

    def get_type_description(self, type_name: str) -> dict[str, Any]:
        """获取指定体质类型的描述

        Args:
            type_name: 体质名称（如"平和质"）

        Returns:
            含 code、features、reference_range、prevalence_cn 的字典；
            若体质名称不存在，返回空字典
        """
        standard = self.load()
        return standard["types"].get(type_name, {})

    def get_scoring_rule(self) -> dict[str, Any]:
        """获取评分规则

        Returns:
            评分规则字典，包含 scale、scale_labels、transformation、
            threshold、transformation_formula 五个字段
        """
        standard = self.load()
        return standard["scoring"]
