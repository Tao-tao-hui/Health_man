"""指标体系设计模块

提供指标体系的设计、管理和评估能力，包含：
1. 指标定义与分类
2. 指标提取与映射
3. 指标计算与评估
4. 指标与知识关联机制
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("indicator_system")


class IndicatorCategory(Enum):
    """指标分类"""
    BODY_COMPOSITION = "body_composition"
    CARDIOVASCULAR = "cardiovascular"
    METABOLIC = "metabolic"
    MUSCULOSKELETAL = "musculoskeletal"
    NUTRITIONAL = "nutritional"
    GENERAL_HEALTH = "general_health"


class IndicatorDataType(Enum):
    """指标数据类型"""
    INTEGER = "integer"
    FLOAT = "float"
    PERCENTAGE = "percentage"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


class IndicatorSource(Enum):
    """指标数据来源"""
    S3008T = "s3008t"
    BMH08002 = "bmh08002"
    CALCULATED = "calculated"
    USER_INPUT = "user_input"
    EXTERNAL_API = "external_api"


class IndicatorLevel(Enum):
    """指标级别"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DERIVED = "derived"


@dataclass
class IndicatorDefinition:
    """指标定义"""
    indicator_id: str
    name: str
    category: IndicatorCategory
    data_type: IndicatorDataType
    unit: str
    source: IndicatorSource
    level: IndicatorLevel
    name_en: Optional[str] = None
    description: Optional[str] = None
    calculation_formula: Optional[str] = None
    reference_range: Optional[Dict[str, Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    precision: int = 1
    tags: List[str] = field(default_factory=list)
    related_knowledge_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


@dataclass
class IndicatorMapping:
    """指标映射"""
    mapping_id: str
    source_field: str
    target_indicator_id: str
    transformation_rule: Optional[str] = None
    validation_rule: Optional[str] = None
    confidence_score: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class IndicatorScore:
    """指标评分"""
    indicator_id: str
    raw_value: float
    normalized_value: Optional[float] = None
    score: int = 0
    grade: Optional[str] = None
    interpretation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IndicatorSet:
    """指标集合"""
    set_id: str
    name: str
    description: Optional[str] = None
    indicator_ids: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class IndicatorSystem:
    """指标体系核心类"""

    def __init__(self, knowledge_graph=None):
        self.indicators: Dict[str, IndicatorDefinition] = {}
        self.mappings: Dict[str, IndicatorMapping] = {}
        self.sets: Dict[str, IndicatorSet] = {}
        self.knowledge_graph = knowledge_graph
        self._initialize_default_indicators()

    def _initialize_default_indicators(self) -> None:
        """初始化默认指标定义"""
        indicators = [
            IndicatorDefinition(
                indicator_id="BMI",
                name="BMI",
                name_en="Body Mass Index",
                category=IndicatorCategory.BODY_COMPOSITION,
                data_type=IndicatorDataType.FLOAT,
                unit="kg/m²",
                source=IndicatorSource.CALCULATED,
                level=IndicatorLevel.PRIMARY,
                description="身体质量指数，衡量人体胖瘦程度",
                calculation_formula="weight_kg / (height_cm / 100)²",
                reference_range={
                    "underweight": {"max": 18.5},
                    "normal": {"min": 18.5, "max": 25.0},
                    "overweight": {"min": 25.0, "max": 30.0},
                    "obese": {"min": 30.0}
                },
                min_value=10,
                max_value=80,
                precision=1,
                tags=["肥胖评估", "WHO标准"],
                related_knowledge_ids=["STD_WHO_BMI", "IND_BMI"]
            ),
            IndicatorDefinition(
                indicator_id="BODY_FAT_RATE",
                name="体脂率",
                name_en="Body Fat Rate",
                category=IndicatorCategory.BODY_COMPOSITION,
                data_type=IndicatorDataType.PERCENTAGE,
                unit="%",
                source=IndicatorSource.EXTERNAL_API,
                level=IndicatorLevel.PRIMARY,
                description="身体脂肪重量占总体重的百分比",
                min_value=3,
                max_value=60,
                precision=1,
                tags=["体成分", "BIA"],
                related_knowledge_ids=["STD_BESTHEALTH_BODYFAT", "IND_BODY_FAT"]
            ),
            IndicatorDefinition(
                indicator_id="VISCERAL_FAT_LEVEL",
                name="内脏脂肪等级",
                name_en="Visceral Fat Level",
                category=IndicatorCategory.BODY_COMPOSITION,
                data_type=IndicatorDataType.INTEGER,
                unit="等级",
                source=IndicatorSource.EXTERNAL_API,
                level=IndicatorLevel.PRIMARY,
                description="内脏脂肪含量的分级评估",
                reference_range={
                    "normal": {"max": 9},
                    "warning": {"min": 10, "max": 14},
                    "danger": {"min": 15}
                },
                min_value=1,
                max_value=50,
                precision=0,
                tags=["内脏脂肪", "代谢风险"],
                related_knowledge_ids=["STD_VISCERAL_FAT", "IND_VISCERAL_FAT"]
            ),
            IndicatorDefinition(
                indicator_id="SPO2",
                name="血氧饱和度",
                name_en="Blood Oxygen Saturation",
                category=IndicatorCategory.CARDIOVASCULAR,
                data_type=IndicatorDataType.PERCENTAGE,
                unit="%",
                source=IndicatorSource.BMH08002,
                level=IndicatorLevel.PRIMARY,
                description="动脉血液中氧合血红蛋白占全部可结合血红蛋白的百分比",
                reference_range={
                    "normal": {"min": 95, "max": 100},
                    "mild_hypoxemia": {"min": 91, "max": 94},
                    "moderate_hypoxemia": {"min": 86, "max": 90},
                    "severe_hypoxemia": {"max": 85}
                },
                min_value=70,
                max_value=100,
                precision=0,
                tags=["血氧", "PPG"],
                related_knowledge_ids=["STD_SPO2", "IND_SPO2"]
            ),
            IndicatorDefinition(
                indicator_id="HEART_RATE",
                name="心率",
                name_en="Heart Rate",
                category=IndicatorCategory.CARDIOVASCULAR,
                data_type=IndicatorDataType.INTEGER,
                unit="BPM",
                source=IndicatorSource.BMH08002,
                level=IndicatorLevel.PRIMARY,
                description="心脏每分钟跳动次数",
                reference_range={
                    "bradycardia": {"max": 59},
                    "normal": {"min": 60, "max": 100},
                    "tachycardia": {"min": 101}
                },
                min_value=30,
                max_value=250,
                precision=0,
                tags=["心率", "PPG"],
                related_knowledge_ids=["STD_HEART_RATE", "IND_HEART_RATE"]
            ),
            IndicatorDefinition(
                indicator_id="PI",
                name="灌注指数",
                name_en="Perfusion Index",
                category=IndicatorCategory.CARDIOVASCULAR,
                data_type=IndicatorDataType.PERCENTAGE,
                unit="%",
                source=IndicatorSource.BMH08002,
                level=IndicatorLevel.SECONDARY,
                description="反映末梢循环灌注情况的指标",
                min_value=0,
                max_value=20,
                precision=1,
                tags=["灌注", "信号质量"],
                related_knowledge_ids=["IND_PI"]
            ),
            IndicatorDefinition(
                indicator_id="HRV",
                name="心率变异性",
                name_en="Heart Rate Variability",
                category=IndicatorCategory.CARDIOVASCULAR,
                data_type=IndicatorDataType.FLOAT,
                unit="ms",
                source=IndicatorSource.BMH08002,
                level=IndicatorLevel.SECONDARY,
                description="连续心跳之间时间间隔的变异性",
                min_value=5,
                max_value=150,
                precision=0,
                tags=["自主神经", "压力评估"],
                related_knowledge_ids=["IND_HRV"]
            ),
            IndicatorDefinition(
                indicator_id="MUSCLE_MASS",
                name="肌肉量",
                name_en="Muscle Mass",
                category=IndicatorCategory.MUSCULOSKELETAL,
                data_type=IndicatorDataType.FLOAT,
                unit="kg",
                source=IndicatorSource.EXTERNAL_API,
                level=IndicatorLevel.SECONDARY,
                description="身体肌肉组织的重量",
                precision=1,
                tags=["肌肉", "BIA"],
                related_knowledge_ids=["IND_MUSCLE_MASS"]
            ),
            IndicatorDefinition(
                indicator_id="BONE_MASS",
                name="骨量",
                name_en="Bone Mass",
                category=IndicatorCategory.MUSCULOSKELETAL,
                data_type=IndicatorDataType.FLOAT,
                unit="kg",
                source=IndicatorSource.EXTERNAL_API,
                level=IndicatorLevel.SECONDARY,
                description="骨骼组织的重量",
                precision=1,
                tags=["骨骼", "BIA"],
                related_knowledge_ids=["IND_BONE_MASS"]
            ),
            IndicatorDefinition(
                indicator_id="BMR",
                name="基础代谢率",
                name_en="Basal Metabolic Rate",
                category=IndicatorCategory.METABOLIC,
                data_type=IndicatorDataType.INTEGER,
                unit="Kcal",
                source=IndicatorSource.CALCULATED,
                level=IndicatorLevel.DERIVED,
                description="人体在清醒而又极端安静状态下的能量代谢率",
                calculation_formula="男性: 10×weight + 6.25×height - 5×age + 5; 女性: 10×weight + 6.25×height - 5×age - 161",
                precision=0,
                tags=["代谢", "能量"],
                related_knowledge_ids=["IND_BMR"]
            ),
            IndicatorDefinition(
                indicator_id="WATER_RATE",
                name="水分率",
                name_en="Water Rate",
                category=IndicatorCategory.NUTRITIONAL,
                data_type=IndicatorDataType.PERCENTAGE,
                unit="%",
                source=IndicatorSource.EXTERNAL_API,
                level=IndicatorLevel.SECONDARY,
                description="身体水分占总体重的百分比",
                reference_range={
                    "normal": {"min": 50, "max": 65}
                },
                min_value=30,
                max_value=80,
                precision=1,
                tags=["水分", "BIA"]
            ),
            IndicatorDefinition(
                indicator_id="PROTEIN_RATE",
                name="蛋白质率",
                name_en="Protein Rate",
                category=IndicatorCategory.NUTRITIONAL,
                data_type=IndicatorDataType.PERCENTAGE,
                unit="%",
                source=IndicatorSource.EXTERNAL_API,
                level=IndicatorLevel.SECONDARY,
                description="身体蛋白质占总体重的百分比",
                precision=1,
                tags=["蛋白质", "BIA"]
            )
        ]

        for indicator in indicators:
            self.indicators[indicator.indicator_id] = indicator

        self._initialize_indicator_sets()

    def _initialize_indicator_sets(self) -> None:
        """初始化指标集合"""
        sets_config = [
            IndicatorSet(
                set_id="SET_BASIC",
                name="基础指标集",
                description="日常健康监测基础指标",
                indicator_ids=["BMI", "BODY_FAT_RATE", "SPO2", "HEART_RATE"],
                domain="general"
            ),
            IndicatorSet(
                set_id="SET_BODY_COMPOSITION",
                name="体成分指标集",
                description="全面体成分分析指标",
                indicator_ids=["BMI", "BODY_FAT_RATE", "VISCERAL_FAT_LEVEL", "MUSCLE_MASS", "BONE_MASS", "WATER_RATE", "PROTEIN_RATE", "BMR"],
                domain="body_composition"
            ),
            IndicatorSet(
                set_id="SET_CARDIOVASCULAR",
                name="心血管指标集",
                description="心血管健康监测指标",
                indicator_ids=["SPO2", "HEART_RATE", "PI", "HRV"],
                domain="cardiovascular"
            ),
            IndicatorSet(
                set_id="SET_METABOLIC",
                name="代谢指标集",
                description="代谢健康评估指标",
                indicator_ids=["BMI", "BODY_FAT_RATE", "VISCERAL_FAT_LEVEL", "BMR"],
                domain="metabolic"
            ),
            IndicatorSet(
                set_id="SET_SLEEP",
                name="睡眠监测指标集",
                description="睡眠健康监测指标",
                indicator_ids=["SPO2", "HEART_RATE", "HRV"],
                domain="sleep"
            )
        ]

        for indicator_set in sets_config:
            self.sets[indicator_set.set_id] = indicator_set

    def add_indicator(self, indicator: IndicatorDefinition) -> None:
        """添加指标定义"""
        if indicator.indicator_id in self.indicators:
            logger.warning(f"指标已存在，将更新: {indicator.indicator_id}")
            indicator.updated_at = datetime.now()
        else:
            logger.info(f"添加指标: {indicator.indicator_id}")
        self.indicators[indicator.indicator_id] = indicator

    def get_indicator(self, indicator_id: str) -> Optional[IndicatorDefinition]:
        """获取指标定义"""
        return self.indicators.get(indicator_id)

    def get_indicators_by_category(self, category: IndicatorCategory) -> List[IndicatorDefinition]:
        """按分类获取指标"""
        return [i for i in self.indicators.values() if i.category == category]

    def get_indicators_by_source(self, source: IndicatorSource) -> List[IndicatorDefinition]:
        """按来源获取指标"""
        return [i for i in self.indicators.values() if i.source == source]

    def get_indicator_set(self, set_id: str) -> Optional[IndicatorSet]:
        """获取指标集合"""
        return self.sets.get(set_id)

    def get_indicators_in_set(self, set_id: str) -> List[IndicatorDefinition]:
        """获取指标集合中的所有指标"""
        indicator_set = self.sets.get(set_id)
        if not indicator_set:
            return []
        return [self.indicators.get(id_) for id_ in indicator_set.indicator_ids if self.indicators.get(id_)]

    def extract_indicators_from_knowledge(self, knowledge_node_ids: List[str]) -> List[IndicatorDefinition]:
        """从知识图谱中提取指标"""
        if not self.knowledge_graph:
            logger.warning("未配置知识图谱，无法提取指标")
            return []

        indicators = []
        for node_id in knowledge_node_ids:
            node = self.knowledge_graph.get_node(node_id)
            if node and node.node_type.value == "indicator":
                indicator_id = node.node_id.replace("IND_", "")
                if indicator_id in self.indicators:
                    indicators.append(self.indicators[indicator_id])
                else:
                    new_indicator = IndicatorDefinition(
                        indicator_id=indicator_id,
                        name=node.name,
                        name_en=node.name_en,
                        category=self._infer_category(node),
                        data_type=self._infer_data_type(node),
                        unit=node.attributes.get("unit", ""),
                        source=self._infer_source(node),
                        level=IndicatorLevel.PRIMARY,
                        description=node.description
                    )
                    indicators.append(new_indicator)
                    self.add_indicator(new_indicator)

        return indicators

    def _infer_category(self, node) -> IndicatorCategory:
        """推断指标分类"""
        name_lower = node.name.lower()
        if any(keyword in name_lower for keyword in ["体脂", "脂肪", "肌肉", "骨骼", "水分", "bmi"]):
            return IndicatorCategory.BODY_COMPOSITION
        elif any(keyword in name_lower for keyword in ["血氧", "心率", "灌注", "hrv"]):
            return IndicatorCategory.CARDIOVASCULAR
        elif any(keyword in name_lower for keyword in ["代谢", "bmr"]):
            return IndicatorCategory.METABOLIC
        else:
            return IndicatorCategory.GENERAL_HEALTH

    def _infer_data_type(self, node) -> IndicatorDataType:
        """推断数据类型"""
        unit = node.attributes.get("unit", "")
        if "%" in unit:
            return IndicatorDataType.PERCENTAGE
        elif unit in ["kg", "cm", "ms", "bpm"]:
            return IndicatorDataType.FLOAT if node.attributes.get("precision", 1) > 0 else IndicatorDataType.INTEGER
        else:
            return IndicatorDataType.FLOAT

    def _infer_source(self, node) -> IndicatorSource:
        """推断数据来源"""
        data_source = node.attributes.get("data_source", "")
        if "S3008T" in data_source:
            return IndicatorSource.S3008T
        elif "BMH08002" in data_source:
            return IndicatorSource.BMH08002
        elif "算法" in data_source or "公式" in data_source:
            return IndicatorSource.CALCULATED
        elif "API" in data_source:
            return IndicatorSource.EXTERNAL_API
        else:
            return IndicatorSource.USER_INPUT

    def calculate_indicator_score(self, indicator_id: str, value: float, **kwargs) -> IndicatorScore:
        """计算指标评分"""
        indicator = self.indicators.get(indicator_id)
        if not indicator:
            return IndicatorScore(indicator_id=indicator_id, raw_value=value, score=0)

        score = 0
        grade = None
        interpretation = None
        normalized_value = None

        if indicator.reference_range:
            normalized_value = self._normalize_value(value, indicator)
            score, grade = self._calculate_score(value, indicator, **kwargs)
            interpretation = self._generate_interpretation(indicator, grade, value)

        return IndicatorScore(
            indicator_id=indicator_id,
            raw_value=value,
            normalized_value=normalized_value,
            score=score,
            grade=grade,
            interpretation=interpretation
        )

    def _normalize_value(self, value: float, indicator: IndicatorDefinition) -> float:
        """归一化指标值"""
        if indicator.min_value is not None and indicator.max_value is not None:
            return (value - indicator.min_value) / (indicator.max_value - indicator.min_value)
        return value

    def _calculate_score(self, value: float, indicator: IndicatorDefinition, **kwargs) -> tuple:
        """计算指标评分和等级"""
        if not indicator.reference_range:
            return 50, "unknown"

        ranges = indicator.reference_range

        for category, limits in ranges.items():
            min_val = limits.get("min", float("-inf"))
            max_val = limits.get("max", float("inf"))

            if min_val <= value <= max_val:
                if category == "normal":
                    return 100, "normal"
                elif category in ["warning", "mild_hypoxemia"]:
                    return 70, "warning"
                elif category in ["overweight", "moderate_hypoxemia"]:
                    return 40, "warning"
                elif category in ["obese", "severe_hypoxemia", "danger"]:
                    return 20, "danger"
                elif category in ["underweight", "bradycardia", "tachycardia"]:
                    return 60, "warning"

        return 50, "unknown"

    def _generate_interpretation(self, indicator: IndicatorDefinition, grade: str, value: float) -> str:
        """生成指标解读"""
        interpretations = {
            "normal": f"{indicator.name}值 {value}{indicator.unit} 处于正常范围，继续保持",
            "warning": f"{indicator.name}值 {value}{indicator.unit} 需要关注，建议咨询专业人士",
            "danger": f"{indicator.name}值 {value}{indicator.unit} 异常，建议尽快就医评估",
            "unknown": f"{indicator.name}值 {value}{indicator.unit}，暂无参考标准"
        }
        return interpretations.get(grade, f"{indicator.name}值 {value}{indicator.unit}")

    def validate_indicator_value(self, indicator_id: str, value: float) -> Dict[str, Any]:
        """验证指标值"""
        indicator = self.indicators.get(indicator_id)
        if not indicator:
            return {"valid": False, "reason": "指标不存在"}

        if indicator.min_value is not None and value < indicator.min_value:
            return {
                "valid": False,
                "reason": f"值低于最小值 {indicator.min_value}{indicator.unit}",
                "min": indicator.min_value,
                "max": indicator.max_value
            }

        if indicator.max_value is not None and value > indicator.max_value:
            return {
                "valid": False,
                "reason": f"值高于最大值 {indicator.max_value}{indicator.unit}",
                "min": indicator.min_value,
                "max": indicator.max_value
            }

        return {"valid": True, "reason": "值在有效范围内", "min": indicator.min_value, "max": indicator.max_value}

    def map_source_field(self, source_field: str, source_system: str = "") -> Optional[str]:
        """映射源字段到指标"""
        for mapping in self.mappings.values():
            if mapping.source_field == source_field:
                if source_system and mapping.transformation_rule and source_system in mapping.transformation_rule:
                    return mapping.target_indicator_id
                elif not source_system:
                    return mapping.target_indicator_id
        return None

    def add_mapping(self, mapping: IndicatorMapping) -> None:
        """添加指标映射"""
        self.mappings[mapping.mapping_id] = mapping
        logger.info(f"添加指标映射: {mapping.mapping_id}")

    def generate_indicator_report(self) -> Dict:
        """生成指标体系报告"""
        report = {
            "report_generated_at": datetime.now().isoformat(),
            "summary": {
                "total_indicators": len(self.indicators),
                "total_sets": len(self.sets),
                "total_mappings": len(self.mappings),
                "indicators_by_category": {
                    cat.value: sum(1 for i in self.indicators.values() if i.category == cat)
                    for cat in IndicatorCategory
                },
                "indicators_by_source": {
                    src.value: sum(1 for i in self.indicators.values() if i.source == src)
                    for src in IndicatorSource
                }
            },
            "indicators": [
                {
                    "indicator_id": i.indicator_id,
                    "name": i.name,
                    "name_en": i.name_en,
                    "category": i.category.value,
                    "source": i.source.value,
                    "level": i.level.value,
                    "unit": i.unit,
                    "min_value": i.min_value,
                    "max_value": i.max_value,
                    "tags": i.tags,
                    "related_knowledge": i.related_knowledge_ids
                }
                for i in self.indicators.values()
            ],
            "sets": [
                {
                    "set_id": s.set_id,
                    "name": s.name,
                    "description": s.description,
                    "domain": s.domain,
                    "indicator_count": len(s.indicator_ids),
                    "indicator_ids": s.indicator_ids
                }
                for s in self.sets.values()
            ]
        }

        return report


indicator_system = IndicatorSystem()