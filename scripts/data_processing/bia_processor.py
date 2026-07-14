"""体成分数据处理器

负责处理S3008T芯片采集的阻抗数据，计算体成分指标
"""

from typing import Optional
from scripts.hardware.models import HardwareData, ProcessedData


class BIAProcessor:
    """
    体成分数据处理器

    支持阻抗值验证、BMI计算、数据质量评估等功能
    """

    IMPEDANCE_MIN = 300
    IMPEDANCE_MAX = 1000

    def validate_impedance(self, impedance: int) -> bool:
        """
        验证阻抗值是否在有效范围内

        Args:
            impedance: 阻抗值(Ω)

        Returns:
            True表示有效，False表示无效
        """
        return self.IMPEDANCE_MIN <= impedance <= self.IMPEDANCE_MAX

    def validate_height(self, height_cm: float) -> bool:
        """验证身高是否在有效范围内"""
        return 90 <= height_cm <= 220

    def validate_weight(self, weight_kg: float) -> bool:
        """验证体重是否在有效范围内"""
        return 20 <= weight_kg <= 300

    def calculate_bmi(self, weight_kg: float, height_cm: float) -> float:
        """
        计算BMI

        Args:
            weight_kg: 体重(kg)
            height_cm: 身高(cm)

        Returns:
            BMI值
        """
        height_m = height_cm / 100
        return weight_kg / (height_m ** 2)

    def process(self,
                hardware_data: HardwareData,
                height_cm: float,
                weight_kg: float,
                age: int,
                sex: str,
                user_type: str = "Normal") -> ProcessedData:
        """
        处理体成分数据

        Args:
            hardware_data: 硬件原始数据
            height_cm: 身高(cm)
            weight_kg: 体重(kg)
            age: 年龄
            sex: 性别(M/F)
            user_type: 用户类型(Normal/Athlete)

        Returns:
            处理后的健康数据
        """
        processed = ProcessedData()

        processed.age = age
        processed.sex = sex
        processed.height_cm = height_cm
        processed.weight_kg = weight_kg
        processed.user_type = user_type
        processed.measurement_time = hardware_data.timestamp

        processed.bmi = self.calculate_bmi(weight_kg, height_cm)

        quality_score = self._calculate_data_quality(hardware_data, height_cm, weight_kg)
        processed.data_quality = quality_score

        return processed

    def _calculate_data_quality(self,
                                hardware_data: HardwareData,
                                height_cm: float,
                                weight_kg: float) -> float:
        """
        计算数据质量评分

        Returns:
            数据质量评分(0~1)
        """
        score = 1.0

        if hardware_data.bia_impedance is not None:
            if not self.validate_impedance(hardware_data.bia_impedance):
                score -= 0.3

        if not self.validate_height(height_cm):
            score -= 0.3

        if not self.validate_weight(weight_kg):
            score -= 0.3

        if hardware_data.signal_quality is not None:
            score = min(score, hardware_data.signal_quality)

        return max(0.0, score)