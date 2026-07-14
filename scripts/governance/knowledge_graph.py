"""医疗专业知识图谱模块

提供医疗专业知识的结构化存储、管理和查询能力，包含：
1. 知识图谱节点与关系定义
2. 临床标准与指南管理
3. 知识更新与版本控制
4. 知识与指标关联机制
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowledge_graph")


class EvidenceLevel(Enum):
    """证据等级定义"""
    LEVEL_A = "A"
    LEVEL_B = "B"
    LEVEL_C = "C"


class KnowledgeType(Enum):
    """知识类型定义"""
    CLINICAL_STANDARD = "clinical_standard"
    GUIDELINE = "guideline"
    DIAGNOSTIC_CRITERIA = "diagnostic_criteria"
    TREATMENT_RECOMMENDATION = "treatment_recommendation"
    HEALTH_ASSESSMENT = "health_assessment"
    RISK_ASSESSMENT = "risk_assessment"
    REFERENCE_RANGE = "reference_range"


class NodeType(Enum):
    """知识图谱节点类型"""
    DISEASE = "disease"
    SYMPTOM = "symptom"
    INDICATOR = "indicator"
    STANDARD = "standard"
    GUIDELINE = "guideline"
    TREATMENT = "treatment"
    POPULATION = "population"
    EVIDENCE = "evidence"


class RelationType(Enum):
    """知识图谱关系类型"""
    HAS_SYMPTOM = "has_symptom"
    HAS_INDICATOR = "has_indicator"
    HAS_STANDARD = "has_standard"
    BASED_ON = "based_on"
    REFERENCES = "references"
    APPLIES_TO = "applies_to"
    INDICATES = "indicates"
    RELATED_TO = "related_to"
    RECOMMENDS = "recommends"


@dataclass
class KnowledgeNode:
    """知识节点"""
    node_id: str
    node_type: NodeType
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


@dataclass
class KnowledgeRelation:
    """知识关系"""
    relation_id: str
    source_node_id: str
    target_node_id: str
    relation_type: RelationType
    description: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ClinicalStandard:
    """临床标准"""
    standard_id: str
    name: str
    domain: str
    standard_type: KnowledgeType
    evidence_level: EvidenceLevel
    name_en: Optional[str] = None
    version: str = "1.0"
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None
    criteria: List[Dict] = field(default_factory=list)
    reference_ranges: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


@dataclass
class KnowledgeVersion:
    """知识版本记录"""
    version_id: str
    object_type: str
    object_id: str
    version_number: str
    change_type: str  # create, update, delete
    changes: Dict[str, Any] = field(default_factory=dict)
    author: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_status: str = "pending"  # pending, approved, rejected
    reviewed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


class MedicalKnowledgeGraph:
    """医疗专业知识图谱核心类"""

    def __init__(self, storage_path: Optional[str] = None):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.relations: Dict[str, KnowledgeRelation] = {}
        self.standards: Dict[str, ClinicalStandard] = {}
        self.versions: Dict[str, KnowledgeVersion] = {}
        self.indicator_mappings: Dict[str, List[str]] = {}
        
        self.storage_path = Path(storage_path) if storage_path else None
        
        if self.storage_path and self.storage_path.exists():
            self.load_from_storage()
        else:
            self._initialize_default_knowledge()

    def _initialize_default_knowledge(self) -> None:
        """初始化默认医疗知识"""
        self._create_indicator_nodes()
        self._create_disease_nodes()
        self._create_relations()
        self._create_clinical_standards()

    def _create_indicator_nodes(self) -> None:
        """创建指标节点"""
        indicators = [
            KnowledgeNode(
                node_id="IND_BMI",
                node_type=NodeType.INDICATOR,
                name="BMI",
                name_en="Body Mass Index",
                description="身体质量指数，衡量人体胖瘦程度",
                attributes={
                    "unit": "kg/m²",
                    "measurement_method": "weight / height²",
                    "data_source": "S3008T + 身高体重输入"
                }
            ),
            KnowledgeNode(
                node_id="IND_BODY_FAT",
                node_type=NodeType.INDICATOR,
                name="体脂率",
                name_en="Body Fat Rate",
                description="身体脂肪重量占总体重的百分比",
                attributes={
                    "unit": "%",
                    "measurement_method": "BIA生物电阻抗分析",
                    "data_source": "S3008T + BestHealth TwoLegs算法"
                }
            ),
            KnowledgeNode(
                node_id="IND_VISCERAL_FAT",
                node_type=NodeType.INDICATOR,
                name="内脏脂肪等级",
                name_en="Visceral Fat Level",
                description="内脏脂肪含量的分级评估",
                attributes={
                    "unit": "等级(1~50)",
                    "measurement_method": "BIA生物电阻抗分析",
                    "data_source": "S3008T + BestHealth TwoLegs算法"
                }
            ),
            KnowledgeNode(
                node_id="IND_SPO2",
                node_type=NodeType.INDICATOR,
                name="血氧饱和度",
                name_en="Blood Oxygen Saturation",
                description="动脉血液中氧合血红蛋白占全部可结合血红蛋白的百分比",
                attributes={
                    "unit": "%",
                    "measurement_method": "PPG光电容积脉搏波",
                    "data_source": "BMH08002"
                }
            ),
            KnowledgeNode(
                node_id="IND_HEART_RATE",
                node_type=NodeType.INDICATOR,
                name="心率",
                name_en="Heart Rate",
                description="心脏每分钟跳动次数",
                attributes={
                    "unit": "BPM",
                    "measurement_method": "PPG光电容积脉搏波",
                    "data_source": "BMH08002"
                }
            ),
            KnowledgeNode(
                node_id="IND_PI",
                node_type=NodeType.INDICATOR,
                name="灌注指数",
                name_en="Perfusion Index",
                description="反映末梢循环灌注情况的指标",
                attributes={
                    "unit": "%",
                    "measurement_method": "PPG光电容积脉搏波",
                    "data_source": "BMH08002"
                }
            ),
            KnowledgeNode(
                node_id="IND_HRV",
                node_type=NodeType.INDICATOR,
                name="心率变异性",
                name_en="Heart Rate Variability",
                description="连续心跳之间时间间隔的变异性",
                attributes={
                    "unit": "ms",
                    "measurement_method": "PPG光电容积脉搏波",
                    "data_source": "BMH08002"
                }
            ),
            KnowledgeNode(
                node_id="IND_MUSCLE_MASS",
                node_type=NodeType.INDICATOR,
                name="肌肉量",
                name_en="Muscle Mass",
                description="身体肌肉组织的重量",
                attributes={
                    "unit": "kg",
                    "measurement_method": "BIA生物电阻抗分析",
                    "data_source": "S3008T + BestHealth TwoLegs算法"
                }
            ),
            KnowledgeNode(
                node_id="IND_BONE_MASS",
                node_type=NodeType.INDICATOR,
                name="骨量",
                name_en="Bone Mass",
                description="骨骼组织的重量",
                attributes={
                    "unit": "kg",
                    "measurement_method": "BIA生物电阻抗分析",
                    "data_source": "S3008T + BestHealth TwoLegs算法"
                }
            ),
            KnowledgeNode(
                node_id="IND_BMR",
                node_type=NodeType.INDICATOR,
                name="基础代谢率",
                name_en="Basal Metabolic Rate",
                description="人体在清醒而又极端安静的状态下，不受肌肉活动、环境温度、食物及精神紧张等影响时的能量代谢率",
                attributes={
                    "unit": "Kcal",
                    "measurement_method": "Mifflin-St Jeor公式",
                    "data_source": "身高体重年龄性别"
                }
            )
        ]

        for indicator in indicators:
            self.nodes[indicator.node_id] = indicator
            self.indicator_mappings[indicator.name] = [indicator.node_id]
            if indicator.name_en:
                self.indicator_mappings[indicator.name_en] = [indicator.node_id]

    def _create_disease_nodes(self) -> None:
        """创建疾病节点"""
        diseases = [
            KnowledgeNode(
                node_id="DISEASE_OBESITY",
                node_type=NodeType.DISEASE,
                name="肥胖症",
                name_en="Obesity",
                description="体内脂肪堆积过多和(或)分布异常，体重超过正常值",
                attributes={
                    "icd_code": "E66",
                    "severity_levels": ["轻度", "中度", "重度"]
                }
            ),
            KnowledgeNode(
                node_id="DISEASE_HYPERTENSION",
                node_type=NodeType.DISEASE,
                name="高血压",
                name_en="Hypertension",
                description="以体循环动脉血压持续升高为主要特征的心血管疾病",
                attributes={
                    "icd_code": "I10",
                    "severity_levels": ["1级", "2级", "3级"]
                }
            ),
            KnowledgeNode(
                node_id="DISEASE_DIABETES",
                node_type=NodeType.DISEASE,
                name="糖尿病",
                name_en="Diabetes Mellitus",
                description="一组以高血糖为特征的代谢性疾病",
                attributes={
                    "icd_code": "E11",
                    "types": ["1型", "2型"]
                }
            ),
            KnowledgeNode(
                node_id="DISEASE_SLEEP_APNEA",
                node_type=NodeType.DISEASE,
                name="睡眠呼吸暂停",
                name_en="Sleep Apnea",
                description="睡眠中反复出现呼吸暂停和低通气的疾病",
                attributes={
                    "icd_code": "G47.3",
                    "types": ["阻塞性", "中枢性", "混合性"]
                }
            ),
            KnowledgeNode(
                node_id="DISEASE_HYPOXEMIA",
                node_type=NodeType.DISEASE,
                name="低氧血症",
                name_en="Hypoxemia",
                description="血液中氧气水平低于正常范围",
                attributes={
                    "icd_code": "J96",
                    "severity_levels": ["轻度", "中度", "重度"]
                }
            )
        ]

        for disease in diseases:
            self.nodes[disease.node_id] = disease

    def _create_relations(self) -> None:
        """创建知识关系"""
        relations = [
            KnowledgeRelation(
                relation_id="REL_OBESITY_BMI",
                source_node_id="DISEASE_OBESITY",
                target_node_id="IND_BMI",
                relation_type=RelationType.HAS_INDICATOR,
                description="肥胖症诊断参考BMI指标",
                attributes={"importance": "high"}
            ),
            KnowledgeRelation(
                relation_id="REL_OBESITY_FAT",
                source_node_id="DISEASE_OBESITY",
                target_node_id="IND_BODY_FAT",
                relation_type=RelationType.HAS_INDICATOR,
                description="肥胖症诊断参考体脂率指标",
                attributes={"importance": "high"}
            ),
            KnowledgeRelation(
                relation_id="REL_OBESITY_VF",
                source_node_id="DISEASE_OBESITY",
                target_node_id="IND_VISCERAL_FAT",
                relation_type=RelationType.HAS_INDICATOR,
                description="肥胖症诊断参考内脏脂肪等级",
                attributes={"importance": "high"}
            ),
            KnowledgeRelation(
                relation_id="REL_APNEA_SPO2",
                source_node_id="DISEASE_SLEEP_APNEA",
                target_node_id="IND_SPO2",
                relation_type=RelationType.HAS_INDICATOR,
                description="睡眠呼吸暂停监测血氧饱和度",
                attributes={"importance": "critical"}
            ),
            KnowledgeRelation(
                relation_id="REL_APNEA_HRV",
                source_node_id="DISEASE_SLEEP_APNEA",
                target_node_id="IND_HRV",
                relation_type=RelationType.HAS_INDICATOR,
                description="睡眠呼吸暂停监测心率变异性",
                attributes={"importance": "medium"}
            ),
            KnowledgeRelation(
                relation_id="REL_HYPOXEMIA_SPO2",
                source_node_id="DISEASE_HYPOXEMIA",
                target_node_id="IND_SPO2",
                relation_type=RelationType.HAS_INDICATOR,
                description="低氧血症诊断参考血氧饱和度",
                attributes={"importance": "critical"}
            ),
            KnowledgeRelation(
                relation_id="REL_HYPERTENSION_HR",
                source_node_id="DISEASE_HYPERTENSION",
                target_node_id="IND_HEART_RATE",
                relation_type=RelationType.HAS_INDICATOR,
                description="高血压监测心率",
                attributes={"importance": "medium"}
            ),
            KnowledgeRelation(
                relation_id="REL_DIABETES_BMI",
                source_node_id="DISEASE_DIABETES",
                target_node_id="IND_BMI",
                relation_type=RelationType.HAS_INDICATOR,
                description="糖尿病风险评估参考BMI",
                attributes={"importance": "medium"}
            ),
            KnowledgeRelation(
                relation_id="REL_DIABETES_FAT",
                source_node_id="DISEASE_DIABETES",
                target_node_id="IND_BODY_FAT",
                relation_type=RelationType.HAS_INDICATOR,
                description="糖尿病风险评估参考体脂率",
                attributes={"importance": "medium"}
            )
        ]

        for relation in relations:
            self.relations[relation.relation_id] = relation

    def _create_clinical_standards(self) -> None:
        """创建临床标准"""
        standards = [
            ClinicalStandard(
                standard_id="STD_WHO_BMI",
                name="WHO BMI标准",
                name_en="WHO BMI Standards",
                domain="肥胖评估",
                standard_type=KnowledgeType.REFERENCE_RANGE,
                evidence_level=EvidenceLevel.LEVEL_A,
                version="1.0",
                source="WHO",
                source_url="https://www.who.int/",
                description="世界卫生组织制定的BMI分类标准",
                reference_ranges={
                    "bmi": {
                        "underweight": {"max": 18.5},
                        "normal": {"min": 18.5, "max": 25.0},
                        "overweight": {"min": 25.0, "max": 30.0},
                        "obese": {"min": 30.0}
                    }
                }
            ),
            ClinicalStandard(
                standard_id="STD_BESTHEALTH_BODYFAT",
                name="BestHealth体脂率标准",
                name_en="BestHealth Body Fat Standards",
                domain="体成分评估",
                standard_type=KnowledgeType.REFERENCE_RANGE,
                evidence_level=EvidenceLevel.LEVEL_C,
                version="1.0",
                source="BestHealth",
                description="BestHealth TwoLegs算法内置的体成分判定阈值（制造商标准）",
                reference_ranges={
                    "body_fat_male_18_39": {
                        "underweight": {"max": 11.0},
                        "normal": {"min": 11.0, "max": 16.9},
                        "warning": {"min": 17.0, "max": 21.9},
                        "overweight": {"min": 22.0, "max": 26.9},
                        "obese": {"min": 27.0}
                    },
                    "body_fat_male_40_59": {
                        "underweight": {"max": 12.0},
                        "normal": {"min": 12.0, "max": 17.9},
                        "warning": {"min": 18.0, "max": 22.9},
                        "overweight": {"min": 23.0, "max": 27.9},
                        "obese": {"min": 28.0}
                    },
                    "body_fat_male_60_plus": {
                        "underweight": {"max": 14.0},
                        "normal": {"min": 14.0, "max": 19.9},
                        "warning": {"min": 20.0, "max": 24.9},
                        "overweight": {"min": 25.0, "max": 29.9},
                        "obese": {"min": 30.0}
                    },
                    "body_fat_female_18_39": {
                        "underweight": {"max": 21.0},
                        "normal": {"min": 21.0, "max": 27.9},
                        "warning": {"min": 28.0, "max": 34.9},
                        "overweight": {"min": 35.0, "max": 39.9},
                        "obese": {"min": 40.0}
                    },
                    "body_fat_female_40_59": {
                        "underweight": {"max": 22.0},
                        "normal": {"min": 22.0, "max": 28.9},
                        "warning": {"min": 29.0, "max": 35.9},
                        "overweight": {"min": 36.0, "max": 40.9},
                        "obese": {"min": 41.0}
                    },
                    "body_fat_female_60_plus": {
                        "underweight": {"max": 23.0},
                        "normal": {"min": 23.0, "max": 29.9},
                        "warning": {"min": 30.0, "max": 36.9},
                        "overweight": {"min": 37.0, "max": 41.9},
                        "obese": {"min": 42.0}
                    }
                },
                notes="本标准为制造商专有标准，非官方临床标准，临床应用时应结合权威医学标准进行验证"
            ),
            ClinicalStandard(
                standard_id="STD_SPO2",
                name="血氧饱和度标准",
                name_en="SpO2 Standards",
                domain="血氧评估",
                standard_type=KnowledgeType.REFERENCE_RANGE,
                evidence_level=EvidenceLevel.LEVEL_A,
                version="1.0",
                source="AHA",
                source_url="https://www.heart.org/",
                description="美国心脏协会制定的血氧饱和度分类标准",
                reference_ranges={
                    "spo2": {
                        "normal": {"min": 95, "max": 100},
                        "mild_hypoxemia": {"min": 91, "max": 94},
                        "moderate_hypoxemia": {"min": 86, "max": 90},
                        "severe_hypoxemia": {"max": 85}
                    }
                }
            ),
            ClinicalStandard(
                standard_id="STD_VISCERAL_FAT",
                name="内脏脂肪等级标准",
                name_en="Visceral Fat Level Standards",
                domain="肥胖评估",
                standard_type=KnowledgeType.REFERENCE_RANGE,
                evidence_level=EvidenceLevel.LEVEL_B,
                version="1.0",
                source="BestHealth",
                description="内脏脂肪等级判定标准",
                reference_ranges={
                    "visceral_fat": {
                        "normal": {"max": 9},
                        "warning": {"min": 10, "max": 14},
                        "danger": {"min": 15}
                    }
                }
            ),
            ClinicalStandard(
                standard_id="STD_HEART_RATE",
                name="心率标准",
                name_en="Heart Rate Standards",
                domain="心血管评估",
                standard_type=KnowledgeType.REFERENCE_RANGE,
                evidence_level=EvidenceLevel.LEVEL_A,
                version="1.0",
                source="AHA",
                source_url="https://www.heart.org/",
                description="美国心脏协会制定的静息心率标准",
                reference_ranges={
                    "heart_rate": {
                        "bradycardia": {"max": 59},
                        "normal": {"min": 60, "max": 100},
                        "tachycardia": {"min": 101}
                    }
                }
            )
        ]

        for standard in standards:
            self.standards[standard.standard_id] = standard

    def add_node(self, node: KnowledgeNode) -> None:
        """添加知识节点"""
        if node.node_id in self.nodes:
            logger.warning(f"节点已存在，将更新: {node.node_id}")
            node.updated_at = datetime.now()
        else:
            logger.info(f"添加节点: {node.node_id}")
        self.nodes[node.node_id] = node

    def add_relation(self, relation: KnowledgeRelation) -> None:
        """添加知识关系"""
        if relation.relation_id in self.relations:
            logger.warning(f"关系已存在，将更新: {relation.relation_id}")
            relation.updated_at = datetime.now()
        else:
            logger.info(f"添加关系: {relation.relation_id}")
        self.relations[relation.relation_id] = relation

    def add_standard(self, standard: ClinicalStandard) -> None:
        """添加临床标准"""
        if standard.standard_id in self.standards:
            logger.warning(f"标准已存在，将更新: {standard.standard_id}")
            standard.updated_at = datetime.now()
        else:
            logger.info(f"添加标准: {standard.standard_id}")
        self.standards[standard.standard_id] = standard
        self._create_version(standard)

    def _create_version(self, obj: Any, change_type: str = "create") -> None:
        """创建版本记录"""
        version_id = f"VER_{obj.__class__.__name__}_{obj.__dict__.get('standard_id', obj.__dict__.get('node_id', 'UNKNOWN'))}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        changes = {}
        for key, value in obj.__dict__.items():
            if key not in ['created_at', 'updated_at']:
                changes[key] = value

        version = KnowledgeVersion(
            version_id=version_id,
            object_type=obj.__class__.__name__,
            object_id=obj.__dict__.get('standard_id', obj.__dict__.get('node_id', 'UNKNOWN')),
            version_number=obj.__dict__.get('version', "1.0"),
            change_type=change_type,
            changes=changes
        )

        self.versions[version_id] = version
        logger.info(f"创建版本记录: {version_id}")

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取知识节点"""
        return self.nodes.get(node_id)

    def get_standard(self, standard_id: str) -> Optional[ClinicalStandard]:
        """获取临床标准"""
        return self.standards.get(standard_id)

    def get_relations_by_source(self, source_node_id: str) -> List[KnowledgeRelation]:
        """按源节点获取关系"""
        return [r for r in self.relations.values() if r.source_node_id == source_node_id]

    def get_relations_by_target(self, target_node_id: str) -> List[KnowledgeRelation]:
        """按目标节点获取关系"""
        return [r for r in self.relations.values() if r.target_node_id == target_node_id]

    def get_related_nodes(self, node_id: str, relation_type: str = None) -> List[KnowledgeNode]:
        """获取相关节点"""
        related = []
        for relation in self.relations.values():
            matches_type = not relation_type or relation.relation_type.value == relation_type
            if matches_type:
                if relation.source_node_id == node_id:
                    target_node = self.nodes.get(relation.target_node_id)
                    if target_node:
                        related.append(target_node)
                elif relation.target_node_id == node_id:
                    source_node = self.nodes.get(relation.source_node_id)
                    if source_node:
                        related.append(source_node)
        return related

    def get_indicators_for_disease(self, disease_id: str) -> List[KnowledgeNode]:
        """获取疾病相关的指标"""
        relations = self.get_relations_by_source(disease_id)
        indicator_ids = [r.target_node_id for r in relations if r.relation_type == RelationType.HAS_INDICATOR]
        return [self.nodes.get(id_) for id_ in indicator_ids if self.nodes.get(id_)]

    def get_diseases_for_indicator(self, indicator_id: str) -> List[KnowledgeNode]:
        """获取指标相关的疾病"""
        relations = self.get_relations_by_target(indicator_id)
        disease_ids = [r.source_node_id for r in relations if r.relation_type == RelationType.HAS_INDICATOR]
        return [self.nodes.get(id_) for id_ in disease_ids if self.nodes.get(id_)]

    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """搜索知识"""
        results = []
        query_lower = query.lower()

        for node in self.nodes.values():
            if (query_lower in node.name.lower() or 
                (node.name_en and query_lower in node.name_en.lower()) or
                (node.description and query_lower in node.description.lower())):
                results.append({
                    "type": "node",
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "name": node.name,
                    "name_en": node.name_en,
                    "description": node.description
                })

        for standard in self.standards.values():
            if (query_lower in standard.name.lower() or 
                (standard.name_en and query_lower in standard.name_en.lower()) or
                (standard.description and query_lower in standard.description.lower())):
                results.append({
                    "type": "standard",
                    "standard_id": standard.standard_id,
                    "name": standard.name,
                    "domain": standard.domain,
                    "evidence_level": standard.evidence_level.value
                })

        return results

    def get_reference_range(self, indicator_id: str, **kwargs) -> Optional[Dict]:
        """获取指标参考范围"""
        indicator = self.nodes.get(indicator_id)
        if not indicator:
            return None

        indicator_name = indicator.name

        for standard in self.standards.values():
            for range_key, range_value in standard.reference_ranges.items():
                if indicator_name.lower() in range_key.lower() or indicator_id.lower() in range_key.lower():
                    if "gender" in kwargs and "male" in range_key.lower() and kwargs["gender"].lower() == "female":
                        continue
                    if "gender" in kwargs and "female" in range_key.lower() and kwargs["gender"].lower() == "male":
                        continue
                    if "age" in kwargs:
                        if "18_39" in range_key and 18 <= kwargs["age"] <= 39:
                            return range_value
                        elif "40_59" in range_key and 40 <= kwargs["age"] <= 59:
                            return range_value
                        elif "60_plus" in range_key and kwargs["age"] >= 60:
                            return range_value
                    else:
                        return range_value

        return None

    def validate_indicator_value(self, indicator_id: str, value: float, **kwargs) -> Dict:
        """验证指标值是否在合理范围"""
        indicator = self.nodes.get(indicator_id)
        if not indicator:
            return {"valid": False, "reason": "指标不存在"}

        reference_range = self.get_reference_range(indicator_id, **kwargs)
        
        if not reference_range:
            return {"valid": True, "reason": "无参考范围", "range": None}

        min_val = None
        max_val = None
        for category, limits in reference_range.items():
            if "min" in limits:
                min_val = limits["min"]
            if "max" in limits:
                max_val = limits["max"]

        if min_val is not None and value < min_val:
            return {"valid": False, "reason": f"值低于下限 {min_val}", "range": reference_range}
        if max_val is not None and value > max_val:
            return {"valid": False, "reason": f"值高于上限 {max_val}", "range": reference_range}

        return {"valid": True, "reason": "值在参考范围内", "range": reference_range}

    def load_from_storage(self) -> None:
        """从存储加载知识图谱"""
        if not self.storage_path:
            return

        try:
            nodes_path = self.storage_path / "nodes.json"
            if nodes_path.exists():
                with open(nodes_path, 'r', encoding='utf-8') as f:
                    nodes_data = json.load(f)
                    for node_data in nodes_data:
                        node = KnowledgeNode(
                            node_id=node_data['node_id'],
                            node_type=NodeType(node_data['node_type']),
                            name=node_data['name'],
                            name_en=node_data.get('name_en'),
                            description=node_data.get('description'),
                            attributes=node_data.get('attributes', {}),
                            created_at=datetime.fromisoformat(node_data['created_at']),
                            updated_at=datetime.fromisoformat(node_data['updated_at']) if node_data.get('updated_at') else None
                        )
                        self.nodes[node.node_id] = node

            relations_path = self.storage_path / "relations.json"
            if relations_path.exists():
                with open(relations_path, 'r', encoding='utf-8') as f:
                    relations_data = json.load(f)
                    for relation_data in relations_data:
                        relation = KnowledgeRelation(
                            relation_id=relation_data['relation_id'],
                            source_node_id=relation_data['source_node_id'],
                            target_node_id=relation_data['target_node_id'],
                            relation_type=RelationType(relation_data['relation_type']),
                            description=relation_data.get('description'),
                            attributes=relation_data.get('attributes', {}),
                            created_at=datetime.fromisoformat(relation_data['created_at'])
                        )
                        self.relations[relation.relation_id] = relation

            standards_path = self.storage_path / "standards.json"
            if standards_path.exists():
                with open(standards_path, 'r', encoding='utf-8') as f:
                    standards_data = json.load(f)
                    for standard_data in standards_data:
                        standard = ClinicalStandard(
                            standard_id=standard_data['standard_id'],
                            name=standard_data['name'],
                            name_en=standard_data.get('name_en'),
                            domain=standard_data['domain'],
                            standard_type=KnowledgeType(standard_data['standard_type']),
                            evidence_level=EvidenceLevel(standard_data['evidence_level']),
                            version=standard_data.get('version', '1.0'),
                            effective_date=datetime.fromisoformat(standard_data['effective_date']) if standard_data.get('effective_date') else None,
                            expiration_date=datetime.fromisoformat(standard_data['expiration_date']) if standard_data.get('expiration_date') else None,
                            source=standard_data.get('source'),
                            source_url=standard_data.get('source_url'),
                            description=standard_data.get('description'),
                            criteria=standard_data.get('criteria', []),
                            reference_ranges=standard_data.get('reference_ranges', {}),
                            notes=standard_data.get('notes'),
                            created_at=datetime.fromisoformat(standard_data['created_at']),
                            updated_at=datetime.fromisoformat(standard_data['updated_at']) if standard_data.get('updated_at') else None
                        )
                        self.standards[standard.standard_id] = standard

            logger.info(f"知识图谱加载完成，节点数: {len(self.nodes)}, 关系数: {len(self.relations)}, 标准数: {len(self.standards)}")

        except Exception as e:
            logger.error(f"加载知识图谱失败: {e}")

    def save_to_storage(self) -> None:
        """保存知识图谱到存储"""
        if not self.storage_path:
            logger.warning("未设置存储路径，跳过保存")
            return

        self.storage_path.mkdir(parents=True, exist_ok=True)

        nodes_data = []
        for node in self.nodes.values():
            nodes_data.append({
                'node_id': node.node_id,
                'node_type': node.node_type.value,
                'name': node.name,
                'name_en': node.name_en,
                'description': node.description,
                'attributes': node.attributes,
                'created_at': node.created_at.isoformat(),
                'updated_at': node.updated_at.isoformat() if node.updated_at else None
            })

        with open(self.storage_path / "nodes.json", 'w', encoding='utf-8') as f:
            json.dump(nodes_data, f, ensure_ascii=False, indent=2)

        relations_data = []
        for relation in self.relations.values():
            relations_data.append({
                'relation_id': relation.relation_id,
                'source_node_id': relation.source_node_id,
                'target_node_id': relation.target_node_id,
                'relation_type': relation.relation_type.value,
                'description': relation.description,
                'attributes': relation.attributes,
                'created_at': relation.created_at.isoformat()
            })

        with open(self.storage_path / "relations.json", 'w', encoding='utf-8') as f:
            json.dump(relations_data, f, ensure_ascii=False, indent=2)

        standards_data = []
        for standard in self.standards.values():
            standards_data.append({
                'standard_id': standard.standard_id,
                'name': standard.name,
                'name_en': standard.name_en,
                'domain': standard.domain,
                'standard_type': standard.standard_type.value,
                'evidence_level': standard.evidence_level.value,
                'version': standard.version,
                'effective_date': standard.effective_date.isoformat() if standard.effective_date else None,
                'expiration_date': standard.expiration_date.isoformat() if standard.expiration_date else None,
                'source': standard.source,
                'source_url': standard.source_url,
                'description': standard.description,
                'criteria': standard.criteria,
                'reference_ranges': standard.reference_ranges,
                'notes': standard.notes,
                'created_at': standard.created_at.isoformat(),
                'updated_at': standard.updated_at.isoformat() if standard.updated_at else None
            })

        with open(self.storage_path / "standards.json", 'w', encoding='utf-8') as f:
            json.dump(standards_data, f, ensure_ascii=False, indent=2)

        logger.info(f"知识图谱保存完成，节点数: {len(self.nodes)}, 关系数: {len(self.relations)}, 标准数: {len(self.standards)}")

    def generate_report(self) -> Dict:
        """生成知识图谱报告"""
        return self.generate_knowledge_report()

    def generate_knowledge_report(self) -> Dict:
        """生成知识图谱报告"""
        report = {
            "report_generated_at": datetime.now().isoformat(),
            "summary": {
                "total_nodes": len(self.nodes),
                "total_relations": len(self.relations),
                "total_standards": len(self.standards),
                "total_versions": len(self.versions),
                "node_types": {
                    node_type.value: sum(1 for n in self.nodes.values() if n.node_type == node_type)
                    for node_type in NodeType
                },
                "evidence_levels": {
                    level.value: sum(1 for s in self.standards.values() if s.evidence_level == level)
                    for level in EvidenceLevel
                }
            },
            "indicators": [
                {
                    "node_id": node.node_id,
                    "name": node.name,
                    "name_en": node.name_en,
                    "unit": node.attributes.get("unit"),
                    "data_source": node.attributes.get("data_source")
                }
                for node in self.nodes.values() if node.node_type == NodeType.INDICATOR
            ],
            "diseases": [
                {
                    "node_id": node.node_id,
                    "name": node.name,
                    "name_en": node.name_en,
                    "icd_code": node.attributes.get("icd_code")
                }
                for node in self.nodes.values() if node.node_type == NodeType.DISEASE
            ],
            "relations": [
                {
                    "relation_id": rel.relation_id,
                    "source": self.nodes.get(rel.source_node_id, KnowledgeNode(node_id="unknown", node_type=NodeType.DISEASE, name="unknown")).name,
                    "target": self.nodes.get(rel.target_node_id, KnowledgeNode(node_id="unknown", node_type=NodeType.DISEASE, name="unknown")).name,
                    "relation_type": rel.relation_type.value,
                    "importance": rel.attributes.get("importance")
                }
                for rel in self.relations.values()
            ]
        }

        return report


knowledge_graph = MedicalKnowledgeGraph()