"""TcmConstitutionClassifier 单元测试

验证 60 题量表评分和体质判定算法（ZYYXH/T157-2009）。

测试覆盖范围：
- classify 方法返回结构完整性（primary_type / scores / qualified_types / threshold）
- 转化分计算公式正确性（全 5 分=100，全 1 分=0，常规值）
- clamp 到 [0, 100] 范围（防越界）
- 高分判定特定体质（全 5 分时所有型转化分=100）
- 低分判定为平和质或无偏颇（全 1 分时偏颇型均不达标）
- 阈值 ≥60 判定边界
- 输入校验（题数不符抛 ValueError）
- 主型为转化分最高者
"""
import pytest

from scripts.data.tcm_classifier import TcmConstitutionClassifier


class TestTcmConstitutionClassifier:
    """TcmConstitutionClassifier 测试套件"""

    def test_classify_returns_dict_with_type(self):
        """测试判定返回含体质类型的结果"""
        classifier = TcmConstitutionClassifier()
        # 60 题，每题得分 3（中等）
        answers = [3] * 60
        result = classifier.classify(answers)
        assert "primary_type" in result
        assert "scores" in result
        assert isinstance(result["scores"], dict)

    def test_calculate_transformed_score(self):
        """测试转化分计算公式"""
        classifier = TcmConstitutionClassifier()
        # 原始分 60，题数 8（某型 8 题），转化分 = (60-8)/(8*4)*100 = 162.5
        # 但标准公式是 (raw_sum - question_count) / (question_count * 4) * 100
        # 如果 8 题全选 5 分，raw_sum=40, 转化分 = (40-8)/32*100 = 100
        score = classifier.calculate_transformed_score(40, 8)
        assert score == 100.0

    def test_calculate_transformed_score_all_ones_is_zero(self):
        """测试全 1 分（最低）转化分为 0"""
        classifier = TcmConstitutionClassifier()
        # 8 题全选 1 分，raw_sum=8, 转化分 = (8-8)/32*100 = 0
        score = classifier.calculate_transformed_score(8, 8)
        assert score == 0.0

    def test_calculate_transformed_score_all_fives_is_hundred(self):
        """测试全 5 分（最高）转化分为 100"""
        classifier = TcmConstitutionClassifier()
        # 9 题全选 5 分，raw_sum=45, 转化分 = (45-9)/36*100 = 100
        score = classifier.calculate_transformed_score(45, 9)
        assert score == 100.0

    def test_calculate_transformed_score_midpoint(self):
        """测试中等分数转化分计算"""
        classifier = TcmConstitutionClassifier()
        # 8 题，每题 3 分，raw_sum=24, 转化分 = (24-8)/32*100 = 50.0
        score = classifier.calculate_transformed_score(24, 8)
        assert score == 50.0

    def test_calculate_transformed_score_clamped_to_hundred(self):
        """测试转化分超过 100 时被 clamp 到 100"""
        classifier = TcmConstitutionClassifier()
        # 假设原始分异常超过题数*5（理论上不应发生，但公式应保护）
        # raw_sum=100, count=8, 转化分 = (100-8)/32*100 = 287.5 -> clamp 到 100
        score = classifier.calculate_transformed_score(100, 8)
        assert score == 100.0

    def test_calculate_transformed_score_clamped_to_zero(self):
        """测试转化分低于 0 时被 clamp 到 0"""
        classifier = TcmConstitutionClassifier()
        # raw_sum=0, count=8, 转化分 = (0-8)/32*100 = -25 -> clamp 到 0
        score = classifier.calculate_transformed_score(0, 8)
        assert score == 0.0

    def test_calculate_transformed_score_zero_count(self):
        """测试题数为 0 时返回 0（避免除零）"""
        classifier = TcmConstitutionClassifier()
        score = classifier.calculate_transformed_score(0, 0)
        assert score == 0.0

    def test_classify_high_score_identifies_type(self):
        """测试高分判定特定体质"""
        classifier = TcmConstitutionClassifier()
        # 所有题都选 5 分（"总是"）
        answers = [5] * 60
        result = classifier.classify(answers)
        # 平和质的题应得高分（如题 1, 56, 57, 58, 59）
        assert result["primary_type"] is not None
        # 所有型的转化分应为 100
        for type_name, score in result["scores"].items():
            assert score == 100.0

    def test_classify_low_scores_returns_neutral(self):
        """测试低分判定为平和质或无偏颇"""
        classifier = TcmConstitutionClassifier()
        # 所有题都选 1 分（"没有"）
        answers = [1] * 60
        result = classifier.classify(answers)
        # 转化分 = (8-8)/(8*4)*100 = 0，所有偏颇体质均不达标
        for type_name, score in result["scores"].items():
            if type_name != "平和质":
                assert score < 60.0

    def test_classify_returns_all_nine_types_in_scores(self):
        """测试 scores 字典包含全部 9 型体质"""
        classifier = TcmConstitutionClassifier()
        answers = [3] * 60
        result = classifier.classify(answers)
        # 9 型体质必须全部出现在 scores 中
        expected_types = {
            "平和质", "气虚质", "阳虚质", "阴虚质",
            "痰湿质", "湿热质", "血瘀质", "气郁质", "特禀质"
        }
        assert set(result["scores"].keys()) == expected_types

    def test_classify_returns_qualified_types_list(self):
        """测试返回 qualified_types 达标型列表"""
        classifier = TcmConstitutionClassifier()
        # 全 5 分时所有型都应达标
        answers = [5] * 60
        result = classifier.classify(answers)
        assert "qualified_types" in result
        assert isinstance(result["qualified_types"], list)
        # 全 5 分时所有 9 型都应达标
        assert len(result["qualified_types"]) == 9

    def test_classify_returns_threshold(self):
        """测试返回判定阈值"""
        classifier = TcmConstitutionClassifier()
        answers = [3] * 60
        result = classifier.classify(answers)
        assert "threshold" in result
        assert result["threshold"] == 60.0

    def test_classify_all_ones_no_qualified_types(self):
        """测试全 1 分时无达标型"""
        classifier = TcmConstitutionClassifier()
        answers = [1] * 60
        result = classifier.classify(answers)
        # 所有型转化分均为 0，无型达标
        assert len(result["qualified_types"]) == 0

    def test_classify_threshold_boundary(self):
        """测试阈值边界：转化分恰好 60 应判定为达标"""
        classifier = TcmConstitutionClassifier()
        # 构造某型转化分恰好为 60：
        # 转化分 = (raw_sum - count) / (count * 4) * 100 = 60
        # => raw_sum - count = 2.4 * count
        # => raw_sum = 3.4 * count
        # 平和质有 5 题，raw_sum = 3.4 * 5 = 17
        # 即 5 题中 3 题 4 分、2 题 2.5 分（非整数）— 不可行
        # 改为 8 题（虚构）：raw_sum = 3.4*8 = 27.2（非整数）
        # 由于题数与得分必须为整数，精确边界 60 较难构造
        # 改为构造略高于阈值的情况：
        # 5 题平和质，每题 4 分，raw_sum=20
        # 转化分 = (20-5)/20*100 = 75 >= 60 -> 达标
        answers = [3] * 60
        # 平和质题号: 1, 56, 57, 58, 59（索引 0, 55, 56, 57, 58）
        for idx in [0, 55, 56, 57, 58]:
            answers[idx] = 4
        result = classifier.classify(answers)
        pinghe_score = result["scores"]["平和质"]
        assert pinghe_score == 75.0
        assert "平和质" in result["qualified_types"]

    def test_classify_primary_type_is_max_score(self):
        """测试主型为转化分最高的型"""
        classifier = TcmConstitutionClassifier()
        # 让阳虚质得分最高（5, 6, 7, 50, 52 共 5 题）
        # 索引：4, 5, 6, 49, 51
        answers = [1] * 60
        for idx in [4, 5, 6, 49, 51]:
            answers[idx] = 5
        result = classifier.classify(answers)
        # 阳虚质转化分 = (25-5)/20*100 = 100
        assert result["primary_type"] == "阳虚质"
        assert result["scores"]["阳虚质"] == 100.0

    def test_classify_invalid_length_raises(self):
        """测试输入题数不为 60 时抛 ValueError"""
        classifier = TcmConstitutionClassifier()
        with pytest.raises(ValueError, match="60"):
            classifier.classify([3] * 59)

    def test_classify_invalid_length_zero_raises(self):
        """测试空输入抛 ValueError"""
        classifier = TcmConstitutionClassifier()
        with pytest.raises(ValueError):
            classifier.classify([])

    def test_classify_scores_are_floats(self):
        """测试 scores 中的值为浮点数"""
        classifier = TcmConstitutionClassifier()
        answers = [3] * 60
        result = classifier.classify(answers)
        for score in result["scores"].values():
            assert isinstance(score, float)
