"""健康评分算法

综合健康评分 = 体成分评分(50%) + 心血管评分(50%)

注意: 当前权重分配基于专家共识(证据等级C)，后续需通过临床验证数据优化
"""

from typing import Dict
from scripts.hardware.models import ProcessedData
from scripts.clinical.standards import ClinicalStandards


class HealthScorer:
    """
    健康评分算法

    支持体成分评分、心血管评分和综合健康评分计算
    """

    def __init__(self):
        self.standards = ClinicalStandards()

    def _score_single_metric(self, value: float, normal_range: tuple) -> int:
        """
        计算单项指标评分

        Args:
            value: 指标值
            normal_range: 标准范围(min, max)

        Returns:
            评分(0~100)
        """
        if value is None:
            return 50

        min_val, max_val = normal_range

        if min_val <= value <= max_val:
            return 100
        elif value < min_val:
            deviation = min_val - value
            max_deviation = min_val * 0.2
            return max(0, 100 - int((deviation / max_deviation) * 100))
        else:
            deviation = value - max_val
            max_deviation = max_val * 0.2
            return max(0, 100 - int((deviation / max_deviation) * 100))

    def calculate_body_composition_score(self, data: ProcessedData) -> int:
        """
        计算体成分评分

        体成分评分 = Σ(单项指标评分 × 权重) / Σ(权重)

        Args:
            data: 处理后的健康数据

        Returns:
            体成分评分(0~100)
        """
        scores = []
        weights = []

        if data.body_fat_rate is not None and data.age is not None and data.sex is not None:
            body_fat_class = self.standards.classify_body_fat(data.body_fat_rate, data.sex, data.age)
            if body_fat_class == "normal":
                scores.append(100)
            elif body_fat_class in ["underweight", "warning"]:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(30)

        if data.bmi is not None:
            bmi_class = self.standards.classify_bmi(data.bmi)
            if bmi_class == "normal":
                scores.append(100)
            elif bmi_class in ["underweight", "overweight"]:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(20)

        if data.visceral_fat_level is not None:
            vf_class = self.standards.classify_visceral_fat(data.visceral_fat_level)
            if vf_class == "normal":
                scores.append(100)
            elif vf_class == "warning":
                scores.append(60)
            else:
                scores.append(30)
            weights.append(25)

        if data.muscle_mass is not None and data.weight_kg is not None:
            muscle_ratio = data.muscle_mass / data.weight_kg
            if muscle_ratio >= 0.45:
                scores.append(100)
            elif muscle_ratio >= 0.35:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(25)

        if not weights:
            return 50

        total_score = sum(s * w for s, w in zip(scores, weights))
        return total_score // sum(weights)

    def calculate_cardiovascular_score(self, data: ProcessedData) -> int:
        """
        计算心血管评分

        基于血氧、心率、PI等指标

        Args:
            data: 处理后的健康数据

        Returns:
            心血管评分(0~100)
        """
        scores = []
        weights = []

        if data.spo2 is not None:
            spo2_class = self.standards.classify_spo2(int(data.spo2))
            if spo2_class == "normal":
                scores.append(100)
            elif spo2_class == "mild_hypoxemia":
                scores.append(70)
            elif spo2_class == "moderate":
                scores.append(40)
            else:
                scores.append(20)
            weights.append(40)

        if data.heart_rate is not None:
            hr = data.heart_rate
            if 60 <= hr <= 80:
                scores.append(100)
            elif 50 <= hr < 60 or 80 < hr <= 100:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(30)

        if data.pi is not None:
            if data.pi >= 1.0:
                scores.append(100)
            elif data.pi >= 0.5:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(30)

        if not weights:
            return 50

        total_score = sum(s * w for s, w in zip(scores, weights))
        return total_score // sum(weights)

    def calculate_overall_score(self, data: ProcessedData) -> Dict[str, int]:
        """
        计算综合健康评分

        综合健康评分 = 体成分评分(50%) + 心血管评分(50%)

        Args:
            data: 处理后的健康数据

        Returns:
            包含各维度评分的字典
        """
        body_comp_score = self.calculate_body_composition_score(data)
        cardio_score = self.calculate_cardiovascular_score(data)
        overall_score = (body_comp_score + cardio_score) // 2

        return {
            'overall': overall_score,
            'body_composition': body_comp_score,
            'cardiovascular': cardio_score
        }