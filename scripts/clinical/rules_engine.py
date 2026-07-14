"""风险预警规则引擎

根据临床标准和检测数据，识别潜在的健康风险并生成预警
"""

from typing import List, Dict
from scripts.hardware.models import ProcessedData
from scripts.clinical.standards import ClinicalStandards


class RulesEngine:
    """
    风险预警规则引擎

    支持多维度健康风险预警，包含证据等级标注
    """

    def __init__(self):
        self.standards = ClinicalStandards()
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict]:
        """
        加载预警规则

        证据等级说明:
        - A: 有充分临床证据支持
        - B: 有中等临床证据支持
        - C: 基于专家共识或观察性研究
        """
        return [
            {
                "id": "rule_001",
                "name": "内脏脂肪高危预警",
                "condition": self._check_visceral_fat_high,
                "severity": "high",
                "action": "建议就医评估",
                "evidence_level": "B"
            },
            {
                "id": "rule_002",
                "name": "血氧偏低预警",
                "condition": self._check_spo2_low,
                "severity": "medium",
                "action": "建议观察并保持室内通风",
                "evidence_level": "C"
            },
            {
                "id": "rule_003",
                "name": "心率异常预警",
                "condition": self._check_heart_rate_abnormal,
                "severity": "medium",
                "action": "建议关注心率变化，如有不适请咨询医生",
                "evidence_level": "C"
            },
            {
                "id": "rule_004",
                "name": "肥胖风险预警",
                "condition": self._check_obesity_risk,
                "severity": "medium",
                "action": "建议控制饮食、增加运动",
                "evidence_level": "B"
            }
        ]

    def _check_visceral_fat_high(self, data: ProcessedData) -> bool:
        """检查内脏脂肪是否高危(VFAL >= 15)"""
        return data.visceral_fat_level is not None and data.visceral_fat_level >= 15

    def _check_spo2_low(self, data: ProcessedData) -> bool:
        """检查血氧是否偏低(< 95%)"""
        return data.spo2 is not None and data.spo2 < 95.0

    def _check_heart_rate_abnormal(self, data: ProcessedData) -> bool:
        """检查心率是否异常(静息心率 > 100 BPM 或 < 50 BPM)"""
        if data.heart_rate is None:
            return False
        return data.heart_rate > 100 or data.heart_rate < 50

    def _check_obesity_risk(self, data: ProcessedData) -> bool:
        """检查肥胖风险(BMI >= 28 或 体脂率超过标准上限)"""
        if data.bmi is not None and data.bmi >= 28:
            return True

        if data.body_fat_rate is not None and data.age is not None and data.sex is not None:
            body_fat_class = self.standards.classify_body_fat(
                data.body_fat_rate, data.sex, data.age
            )
            if body_fat_class in ["overweight", "obese"]:
                return True

        return False

    def evaluate(self, data: ProcessedData) -> List[Dict]:
        """
        评估数据并生成预警

        Args:
            data: 处理后的健康数据

        Returns:
            预警列表
        """
        alerts = []

        for rule in self.rules:
            condition_func = rule["condition"]
            if condition_func(data):
                alerts.append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "action": rule["action"],
                    "evidence_level": rule["evidence_level"]
                })

        return alerts