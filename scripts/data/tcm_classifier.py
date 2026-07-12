"""中医体质 60 题量表判定算法

基于 ZYYXH/T157-2009《中医体质分类与判定》标准。

评分流程：
1. 收集 60 题原始得分（1-5 分量表）
2. 按体质类型分组计算原始总分
3. 计算转化分：transformed = (raw_sum - count) / (count * 4) * 100
4. 转化分 >= 60 判定为该型体质
5. 取转化分最高的型作为主型（primary_type）

转化分公式说明：
- 全 5 分（最高）：raw_sum = count * 5, transformed = (5c - c)/(4c)*100 = 100
- 全 1 分（最低）：raw_sum = count * 1, transformed = (c - c)/(4c)*100 = 0
- 转化分范围 clamp 到 [0, 100]
"""
import logging
from typing import Any

from scripts.data.tcm_standard_loader import TcmStandardLoader

logger = logging.getLogger(__name__)


class TcmConstitutionClassifier:
    """中医体质 60 题量表判定器

    基于 ZYYXH/T157-2009 标准的体质判定算法。

    Args:
        loader: TcmStandardLoader 实例（默认使用标准路径）
    """

    # 判定阈值：转化分 >= 60 判定为该型体质
    THRESHOLD = 60.0

    # 标准量表题数
    EXPECTED_QUESTION_COUNT = 60

    # 转化分上下界
    SCORE_MIN = 0.0
    SCORE_MAX = 100.0

    def __init__(self, loader: TcmStandardLoader | None = None):
        """初始化判定器

        Args:
            loader: TcmStandardLoader 实例；为 None 时使用默认标准路径加载
        """
        self.loader = loader or TcmStandardLoader()
        self.questions = self.loader.get_questions()
        self.scoring_rule = self.loader.get_scoring_rule()

    def classify(self, answers: list[int]) -> dict[str, Any]:
        """判定体质类型

        Args:
            answers: 60 题原始得分列表，每题为 1-5 的整数

        Returns:
            含以下键的字典:
            - primary_type: 主型体质名称（转化分最高的型）
            - scores: 各型转化分字典 {type_name: score}
            - qualified_types: 达到阈值的型列表
            - threshold: 判定阈值

        Raises:
            ValueError: 输入答案数不等于 60
        """
        # 输入校验：必须为 60 题
        if len(answers) != self.EXPECTED_QUESTION_COUNT:
            raise ValueError(
                f"需要 {self.EXPECTED_QUESTION_COUNT} 题答案，收到 {len(answers)} 题"
            )

        # 按体质类型分组累计原始分
        type_raw_scores: dict[str, list[int]] = {}
        for question, answer in zip(self.questions, answers):
            type_name = question["type"]
            if type_name not in type_raw_scores:
                type_raw_scores[type_name] = []
            type_raw_scores[type_name].append(answer)

        # 计算各型转化分
        transformed_scores: dict[str, float] = {}
        for type_name, scores in type_raw_scores.items():
            raw_sum = sum(scores)
            question_count = len(scores)
            transformed = self.calculate_transformed_score(raw_sum, question_count)
            # 保留两位小数，便于展示和断言
            transformed_scores[type_name] = round(transformed, 2)

        # 确定主型（转化分最高者）
        primary_type = max(transformed_scores, key=transformed_scores.get)

        # 达到阈值的型
        qualified_types = [
            type_name
            for type_name, score in transformed_scores.items()
            if score >= self.THRESHOLD
        ]

        logger.info(
            "体质判定完成: 主型=%s, 达标型=%s, 阈值=%.1f",
            primary_type,
            qualified_types,
            self.THRESHOLD,
        )

        return {
            "primary_type": primary_type,
            "scores": transformed_scores,
            "qualified_types": qualified_types,
            "threshold": self.THRESHOLD,
        }

    def calculate_transformed_score(self, raw_sum: int, question_count: int) -> float:
        """计算转化分

        公式：transformed = (raw_sum - question_count) / (question_count * 4) * 100

        边界处理：
        - question_count == 0：返回 0.0（避免除零）
        - 计算结果 clamp 到 [0, 100] 范围

        Args:
            raw_sum: 原始总分
            question_count: 题目数

        Returns:
            转化分（0-100 的浮点数）
        """
        # 题数为 0 时无法计算，直接返回 0
        if question_count == 0:
            return 0.0

        # 应用转化分公式
        transformed = (raw_sum - question_count) / (question_count * 4) * 100

        # clamp 到 [0, 100] 范围，防止越界
        clamped = max(self.SCORE_MIN, min(self.SCORE_MAX, transformed))

        return float(clamped)
