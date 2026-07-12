"""TcmStandardLoader 单元测试

验证中医体质 9 型标准（ZYYXH/T157-2009）的加载和查询功能。

测试覆盖范围：
- 标准字典结构完整性（types / questions / scoring 三大顶层键）
- 9 型体质名称与字段完整性
- 60 题量表结构与归属合法性
- 题 23 不与题 14 重复（皮肤划痕症 vs 荨麻疹）
- 转化分公式与阈值定义
- 评分规则可查询
"""
import pytest
from pathlib import Path

from scripts.data.tcm_standard_loader import TcmStandardLoader


# ZYYXH/T157-2009 标准定义的 9 型体质名称
EXPECTED_NINE_TYPES = [
    "平和质", "气虚质", "阳虚质", "阴虚质",
    "痰湿质", "湿热质", "血瘀质", "气郁质", "特禀质"
]


class TestTcmStandardLoader:
    """TcmStandardLoader 测试套件"""

    def test_load_returns_dict(self):
        """测试加载返回标准字典"""
        loader = TcmStandardLoader()
        standard = loader.load()
        assert isinstance(standard, dict)
        # 顶层必须包含 types、questions、scoring 三个键
        assert "types" in standard
        assert "questions" in standard
        assert "scoring" in standard
        # 标准元信息
        assert "standard_id" in standard
        assert "standard_name" in standard

    def test_get_type_names_returns_nine_types(self):
        """测试返回 9 型名称列表"""
        loader = TcmStandardLoader()
        names = loader.get_type_names()
        assert len(names) == 9
        # ZYYXH/T157-2009 定义的 9 型必须全部存在
        for type_name in EXPECTED_NINE_TYPES:
            assert type_name in names, f"缺少体质类型: {type_name}"

    def test_get_questions_returns_sixty_items(self):
        """测试返回 60 题量表"""
        loader = TcmStandardLoader()
        questions = loader.get_questions()
        assert len(questions) == 60
        # 每题应含编号、问题文本、归属体质
        first_question = questions[0]
        assert "number" in first_question
        assert "text" in first_question
        assert "type" in first_question

    def test_get_type_description(self):
        """测试获取体质类型描述"""
        loader = TcmStandardLoader()
        description = loader.get_type_description("平和质")
        assert isinstance(description, dict)
        assert "features" in description
        assert "reference_range" in description

    def test_all_nine_types_have_complete_fields(self):
        """测试 9 型体质字段完整性（code/features/reference_range/prevalence_cn）"""
        loader = TcmStandardLoader()
        standard = loader.load()
        for type_name in EXPECTED_NINE_TYPES:
            type_data = standard["types"].get(type_name)
            assert type_data is not None, f"缺少体质类型: {type_name}"
            # 必须包含编码、特征描述、参考范围、流行病学数据
            assert "code" in type_data, f"{type_name} 缺少 code 字段"
            assert "features" in type_data, f"{type_name} 缺少 features 字段"
            assert "reference_range" in type_data, f"{type_name} 缺少 reference_range 字段"
            assert "prevalence_cn" in type_data, f"{type_name} 缺少 prevalence_cn 字段"

    def test_question_numbers_are_sequential_1_to_60(self):
        """测试 60 题编号从 1 到 60 连续"""
        loader = TcmStandardLoader()
        questions = loader.get_questions()
        numbers = [q["number"] for q in questions]
        assert numbers == list(range(1, 61)), "题目编号必须从 1 到 60 连续"

    def test_all_questions_belong_to_valid_type(self):
        """测试所有题目归属体质类型合法（必须属于 9 型之一）"""
        loader = TcmStandardLoader()
        questions = loader.get_questions()
        valid_types = set(EXPECTED_NINE_TYPES)
        for question in questions:
            assert question["type"] in valid_types, (
                f"题 {question['number']} 归属非法体质类型: {question['type']}"
            )

    def test_question_23_not_duplicate_of_question_14(self):
        """测试题 23 不与题 14 重复（皮肤划痕症 vs 荨麻疹）

        题 14: 您皮肤容易起荨麻疹吗？（特禀质 - 荨麻疹）
        题 23: 您皮肤一抓就红并出现划痕吗？（特禀质 - 皮肤划痕症）
        """
        loader = TcmStandardLoader()
        questions = loader.get_questions()
        question_14 = next(q for q in questions if q["number"] == 14)
        question_23 = next(q for q in questions if q["number"] == 23)
        # 文本必须不同
        assert question_14["text"] != question_23["text"], "题 23 不得与题 14 文本重复"
        # 题 23 应为皮肤划痕症（包含"划痕"关键词）
        assert "划痕" in question_23["text"], "题 23 应包含'划痕'关键词（皮肤划痕症）"
        # 题 14 应为荨麻疹
        assert "荨麻疹" in question_14["text"], "题 14 应包含'荨麻疹'关键词"

    def test_scoring_rule_contains_transformation_formula(self):
        """测试评分规则包含转化分公式"""
        loader = TcmStandardLoader()
        scoring = loader.get_scoring_rule()
        # 必须包含 5 级量表
        assert "scale" in scoring
        assert len(scoring["scale"]) == 5
        # 必须包含转化分公式定义
        assert "transformation_formula" in scoring, "评分规则必须包含 transformation_formula"
        formula = scoring["transformation_formula"]
        # 公式核心要素：raw_sum - question_count，除以 question_count * 4，乘以 100
        assert "raw_sum" in formula
        assert "question_count" in formula
        assert "100" in formula

    def test_scoring_threshold_is_60(self):
        """测试判定阈值 >= 60"""
        loader = TcmStandardLoader()
        scoring = loader.get_scoring_rule()
        assert "threshold" in scoring
        threshold_text = scoring["threshold"]
        # 阈值必须为 60
        assert "60" in threshold_text, "判定阈值必须为 60"

    def test_get_type_description_returns_empty_for_unknown_type(self):
        """测试查询未知体质类型返回空字典（不抛异常）"""
        loader = TcmStandardLoader()
        description = loader.get_type_description("不存在的体质")
        assert isinstance(description, dict)
        assert description == {}

    def test_get_scoring_rule_returns_dict(self):
        """测试 get_scoring_rule 返回字典"""
        loader = TcmStandardLoader()
        scoring = loader.get_scoring_rule()
        assert isinstance(scoring, dict)
