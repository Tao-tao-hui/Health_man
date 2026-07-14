"""血氧数据处理器

负责处理BMH08002模块采集的血氧、心率、PI等数据
"""

from typing import Optional
from scripts.hardware.models import HardwareData, ProcessedData


class SpO2Processor:
    """
    血氧数据处理器

    支持血氧、心率、PI值验证，信号质量评估等功能
    """

    SPO2_MIN = 70
    SPO2_MAX = 99
    HR_MIN = 30
    HR_MAX = 250
    PI_MAX = 20.0

    def validate_spo2(self, spo2: int) -> bool:
        """
        验证血氧值是否在有效范围内

        注意：性能指标标注70~99%，通信字节允许35~99%
        实际使用以性能指标70~99%为准

        Args:
            spo2: 血氧值(%)

        Returns:
            True表示有效，False表示无效
        """
        return self.SPO2_MIN <= spo2 <= self.SPO2_MAX

    def validate_heart_rate(self, hr: int) -> bool:
        """验证心率是否在有效范围内"""
        return self.HR_MIN <= hr <= self.HR_MAX

    def validate_pi(self, pi: float) -> bool:
        """
        验证PI值是否在有效范围内

        注意：性能指标标注0.5~25%，通信字节允许0~20.0%
        实际使用以通信字节0~20.0%为准

        Args:
            pi: 灌注指数(%)

        Returns:
            True表示有效，False表示无效
        """
        return 0 <= pi <= self.PI_MAX

    def evaluate_signal_quality(self, pi: Optional[float] = None) -> float:
        """
        评估信号质量

        PI值越大，信号质量越好
        PI < 0.5%时精度下降

        Args:
            pi: 灌注指数(%)

        Returns:
            信号质量评分(0~1)
        """
        if pi is None:
            return 0.5

        if pi < 0.5:
            return min(0.5, pi * 2)
        elif pi < 2.0:
            return 0.5 + (pi - 0.5) * 0.2
        else:
            return min(1.0, 0.8 + (pi - 2.0) * 0.01)

    def process(self, hardware_data: HardwareData) -> ProcessedData:
        """
        处理血氧数据

        Args:
            hardware_data: 硬件原始数据

        Returns:
            处理后的健康数据
        """
        processed = ProcessedData()

        if hardware_data.spo2 is not None:
            processed.spo2 = float(hardware_data.spo2)

        if hardware_data.heart_rate is not None:
            processed.heart_rate = float(hardware_data.heart_rate)

        if hardware_data.pi is not None:
            processed.pi = hardware_data.pi

        if hardware_data.hrv is not None:
            processed.hrv = float(hardware_data.hrv)

        processed.measurement_time = hardware_data.timestamp

        quality_score = self._calculate_data_quality(hardware_data)
        processed.data_quality = quality_score

        return processed

    def _calculate_data_quality(self, hardware_data: HardwareData) -> float:
        """
        计算数据质量评分

        Returns:
            数据质量评分(0~1)
        """
        score = 1.0

        if hardware_data.spo2 is not None:
            if not self.validate_spo2(hardware_data.spo2):
                score -= 0.4

        if hardware_data.heart_rate is not None:
            if not self.validate_heart_rate(hardware_data.heart_rate):
                score -= 0.3

        pi_quality = self.evaluate_signal_quality(hardware_data.pi)
        score = min(score, pi_quality)

        if hardware_data.signal_quality is not None:
            score = min(score, hardware_data.signal_quality)

        return max(0.0, score)