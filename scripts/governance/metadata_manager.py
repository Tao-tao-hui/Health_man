"""元数据管理模块

提供元数据的定义、存储、查询和管理能力，包含：
1. 数据字典管理
2. 数据血缘追踪
3. 标签体系管理
4. 语义映射
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metadata_manager")


class MetadataType(Enum):
    """元数据类型"""
    DATA_ELEMENT = "data_element"
    DATASET = "dataset"
    TABLE = "table"
    COLUMN = "column"
    INDICATOR = "indicator"
    SERVICE = "service"
    INTERFACE = "interface"
    PROCESS = "process"
    STANDARD = "standard"


class DataClassification(Enum):
    """数据分类级别"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SENSITIVE = "sensitive"


class TagType(Enum):
    """标签类型"""
    BUSINESS = "business"
    TECHNICAL = "technical"
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    SEMANTIC = "semantic"


class LineageDirection(Enum):
    """血缘方向"""
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"


@dataclass
class DataElement:
    """数据元素"""
    element_id: str
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    data_type: str = "string"
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    nullable: bool = True
    default_value: Optional[Any] = None
    classification: DataClassification = DataClassification.INTERNAL
    tags: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    standard_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


@dataclass
class DataLineage:
    """数据血缘"""
    lineage_id: str
    source_id: str
    target_id: str
    transformation: Optional[str] = None
    confidence: float = 1.0
    direction: LineageDirection = LineageDirection.DOWNSTREAM
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TagDefinition:
    """标签定义"""
    tag_id: str
    name: str
    tag_type: TagType
    description: Optional[str] = None
    parent_tag_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SemanticMapping:
    """语义映射"""
    mapping_id: str
    source_concept: str
    target_concept: str
    mapping_type: str = "equivalent"
    confidence: float = 1.0
    reference: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MetadataRecord:
    """元数据记录"""
    metadata_id: str
    name: str
    metadata_type: MetadataType
    description: Optional[str] = None
    version: str = "1.0"
    owner: Optional[str] = None
    data_elements: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    lineage_ids: List[str] = field(default_factory=list)
    classification: DataClassification = DataClassification.INTERNAL
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class MetadataManager:
    """元数据管理核心类"""

    def __init__(self):
        self.data_elements: Dict[str, DataElement] = {}
        self.lineages: Dict[str, DataLineage] = {}
        self.tags: Dict[str, TagDefinition] = {}
        self.semantic_mappings: Dict[str, SemanticMapping] = {}
        self.metadata_records: Dict[str, MetadataRecord] = {}
        self._initialize_default_tags()
        self._initialize_default_classifications()

    def _initialize_default_tags(self) -> None:
        """初始化默认标签"""
        tags_config = [
            TagDefinition(tag_id="TAG_BODY_COMPOSITION", name="体成分", tag_type=TagType.BUSINESS, description="与体成分相关的数据"),
            TagDefinition(tag_id="TAG_CARDIOVASCULAR", name="心血管", tag_type=TagType.BUSINESS, description="与心血管相关的数据"),
            TagDefinition(tag_id="TAG_METABOLIC", name="代谢", tag_type=TagType.BUSINESS, description="与代谢相关的数据"),
            TagDefinition(tag_id="TAG_MUSCULOSKELETAL", name="肌肉骨骼", tag_type=TagType.BUSINESS, description="与肌肉骨骼相关的数据"),
            TagDefinition(tag_id="TAG_NUTRITIONAL", name="营养", tag_type=TagType.BUSINESS, description="与营养相关的数据"),
            TagDefinition(tag_id="TAG_REALTIME", name="实时数据", tag_type=TagType.TECHNICAL, description="实时采集的数据"),
            TagDefinition(tag_id="TAG_HISTORICAL", name="历史数据", tag_type=TagType.TECHNICAL, description="历史存储的数据"),
            TagDefinition(tag_id="TAG_CALCULATED", name="计算数据", tag_type=TagType.TECHNICAL, description="通过计算得到的数据"),
            TagDefinition(tag_id="TAG_HIGH_QUALITY", name="高质量", tag_type=TagType.QUALITY, description="数据质量评分高"),
            TagDefinition(tag_id="TAG_WARNING", name="质量警告", tag_type=TagType.QUALITY, description="数据质量存在问题"),
            TagDefinition(tag_id="TAG_PHI", name="个人健康信息", tag_type=TagType.COMPLIANCE, description="包含个人健康信息"),
            TagDefinition(tag_id="TAG_PII", name="个人身份信息", tag_type=TagType.COMPLIANCE, description="包含个人身份信息"),
            TagDefinition(tag_id="TAG_HIPAA_COMPLIANT", name="HIPAA合规", tag_type=TagType.COMPLIANCE, description="符合HIPAA标准"),
            TagDefinition(tag_id="TAG_WHO_STANDARD", name="WHO标准", tag_type=TagType.SEMANTIC, description="符合WHO标准"),
            TagDefinition(tag_id="TAG_CLINICAL_GRADE", name="临床级", tag_type=TagType.SEMANTIC, description="临床级数据标准"),
        ]

        for tag in tags_config:
            self.tags[tag.tag_id] = tag

    def _initialize_default_classifications(self) -> None:
        """初始化默认数据分类"""
        default_elements = [
            DataElement(element_id="DE_USER_ID", name="用户ID", name_en="User ID", data_type="string", length=36, nullable=False, classification=DataClassification.SENSITIVE),
            DataElement(element_id="DE_USER_NAME", name="用户名", name_en="User Name", data_type="string", length=50, classification=DataClassification.SENSITIVE),
            DataElement(element_id="DE_BIRTH_DATE", name="出生日期", name_en="Birth Date", data_type="date", classification=DataClassification.SENSITIVE),
            DataElement(element_id="DE_GENDER", name="性别", name_en="Gender", data_type="string", length=10, classification=DataClassification.CONFIDENTIAL),
            DataElement(element_id="DE_HEIGHT", name="身高", name_en="Height", data_type="float", precision=3, scale=1, classification=DataClassification.CONFIDENTIAL),
            DataElement(element_id="DE_WEIGHT", name="体重", name_en="Weight", data_type="float", precision=4, scale=1, classification=DataClassification.CONFIDENTIAL),
            DataElement(element_id="DE_BMI", name="BMI", name_en="BMI", data_type="float", precision=4, scale=1, classification=DataClassification.INTERNAL),
            DataElement(element_id="DE_BODY_FAT_RATE", name="体脂率", name_en="Body Fat Rate", data_type="float", precision=4, scale=1, classification=DataClassification.INTERNAL),
            DataElement(element_id="DE_VISCERAL_FAT", name="内脏脂肪等级", name_en="Visceral Fat Level", data_type="integer", classification=DataClassification.INTERNAL),
            DataElement(element_id="DE_SPO2", name="血氧饱和度", name_en="SPO2", data_type="float", precision=3, scale=0, classification=DataClassification.CONFIDENTIAL),
            DataElement(element_id="DE_HEART_RATE", name="心率", name_en="Heart Rate", data_type="integer", classification=DataClassification.CONFIDENTIAL),
            DataElement(element_id="DE_HRV", name="心率变异性", name_en="HRV", data_type="float", precision=5, scale=0, classification=DataClassification.CONFIDENTIAL),
            DataElement(element_id="DE_MUSCLE_MASS", name="肌肉量", name_en="Muscle Mass", data_type="float", precision=4, scale=1, classification=DataClassification.INTERNAL),
            DataElement(element_id="DE_BONE_MASS", name="骨量", name_en="Bone Mass", data_type="float", precision=4, scale=1, classification=DataClassification.INTERNAL),
            DataElement(element_id="DE_BMR", name="基础代谢率", name_en="BMR", data_type="integer", classification=DataClassification.INTERNAL),
            DataElement(element_id="DE_MEASURE_TIME", name="测量时间", name_en="Measure Time", data_type="datetime", nullable=False, classification=DataClassification.INTERNAL),
            DataElement(element_id="DE_DEVICE_ID", name="设备ID", name_en="Device ID", data_type="string", length=64, classification=DataClassification.CONFIDENTIAL),
            DataElement(element_id="DE_DATA_SOURCE", name="数据来源", name_en="Data Source", data_type="string", length=50, classification=DataClassification.INTERNAL),
        ]

        for element in default_elements:
            self.data_elements[element.element_id] = element

    def add_data_element(self, element: DataElement) -> None:
        """添加数据元素"""
        if element.element_id in self.data_elements:
            logger.warning(f"数据元素已存在，将更新: {element.element_id}")
            element.updated_at = datetime.now()
        else:
            logger.info(f"添加数据元素: {element.element_id}")
        self.data_elements[element.element_id] = element

    def get_data_element(self, element_id: str) -> Optional[DataElement]:
        """获取数据元素"""
        return self.data_elements.get(element_id)

    def search_data_elements(self, keyword: str = "", classification: Optional[DataClassification] = None) -> List[DataElement]:
        """搜索数据元素"""
        results = []
        for element in self.data_elements.values():
            match_keyword = not keyword or (keyword.lower() in element.name.lower() or keyword.lower() in element.element_id.lower())
            match_classification = not classification or element.classification == classification
            if match_keyword and match_classification:
                results.append(element)
        return results

    def add_lineage(self, lineage: DataLineage) -> None:
        """添加数据血缘"""
        self.lineages[lineage.lineage_id] = lineage
        logger.info(f"添加数据血缘: {lineage.lineage_id}")

    def get_lineage(self, lineage_id: str) -> Optional[DataLineage]:
        """获取数据血缘"""
        return self.lineages.get(lineage_id)

    def get_upstream_lineages(self, target_id: str) -> List[DataLineage]:
        """获取上游血缘"""
        return [l for l in self.lineages.values() if l.target_id == target_id and l.direction == LineageDirection.DOWNSTREAM]

    def get_downstream_lineages(self, source_id: str) -> List[DataLineage]:
        """获取下游血缘"""
        return [l for l in self.lineages.values() if l.source_id == source_id and l.direction == LineageDirection.DOWNSTREAM]

    def add_tag(self, tag: TagDefinition) -> None:
        """添加标签"""
        self.tags[tag.tag_id] = tag
        logger.info(f"添加标签: {tag.tag_id}")

    def get_tag(self, tag_id: str) -> Optional[TagDefinition]:
        """获取标签"""
        return self.tags.get(tag_id)

    def get_tags_by_type(self, tag_type: TagType) -> List[TagDefinition]:
        """按类型获取标签"""
        return [t for t in self.tags.values() if t.tag_type == tag_type]

    def tag_data_element(self, element_id: str, tag_id: str) -> None:
        """给数据元素打标签"""
        element = self.data_elements.get(element_id)
        tag = self.tags.get(tag_id)
        if element and tag:
            if tag_id not in element.tags:
                element.tags.append(tag_id)
                logger.info(f"给数据元素 {element_id} 添加标签 {tag_id}")
            else:
                logger.warning(f"数据元素 {element_id} 已包含标签 {tag_id}")
        else:
            logger.warning(f"数据元素 {element_id} 或标签 {tag_id} 不存在")

    def add_semantic_mapping(self, mapping: SemanticMapping) -> None:
        """添加语义映射"""
        self.semantic_mappings[mapping.mapping_id] = mapping
        logger.info(f"添加语义映射: {mapping.mapping_id}")

    def get_semantic_mapping(self, mapping_id: str) -> Optional[SemanticMapping]:
        """获取语义映射"""
        return self.semantic_mappings.get(mapping_id)

    def find_semantic_mappings(self, source_concept: str = "", target_concept: str = "") -> List[SemanticMapping]:
        """查找语义映射"""
        results = []
        for mapping in self.semantic_mappings.values():
            match_source = not source_concept or source_concept.lower() in mapping.source_concept.lower()
            match_target = not target_concept or target_concept.lower() in mapping.target_concept.lower()
            if match_source and match_target:
                results.append(mapping)
        return results

    def add_metadata_record(self, record: MetadataRecord) -> None:
        """添加元数据记录"""
        if record.metadata_id in self.metadata_records:
            logger.warning(f"元数据记录已存在，将更新: {record.metadata_id}")
            record.updated_at = datetime.now()
        else:
            logger.info(f"添加元数据记录: {record.metadata_id}")
        self.metadata_records[record.metadata_id] = record

    def get_metadata_record(self, metadata_id: str) -> Optional[MetadataRecord]:
        """获取元数据记录"""
        return self.metadata_records.get(metadata_id)

    def get_metadata_by_type(self, metadata_type: MetadataType) -> List[MetadataRecord]:
        """按类型获取元数据记录"""
        return [r for r in self.metadata_records.values() if r.metadata_type == metadata_type]

    def generate_metadata_report(self) -> Dict:
        """生成元数据报告"""
        report = {
            "report_generated_at": datetime.now().isoformat(),
            "summary": {
                "total_data_elements": len(self.data_elements),
                "total_lineages": len(self.lineages),
                "total_tags": len(self.tags),
                "total_semantic_mappings": len(self.semantic_mappings),
                "total_metadata_records": len(self.metadata_records),
                "elements_by_classification": {
                    cls.value: sum(1 for e in self.data_elements.values() if e.classification == cls)
                    for cls in DataClassification
                },
                "tags_by_type": {
                    ttype.value: sum(1 for t in self.tags.values() if t.tag_type == ttype)
                    for ttype in TagType
                }
            },
            "data_elements": [
                {
                    "element_id": e.element_id,
                    "name": e.name,
                    "name_en": e.name_en,
                    "data_type": e.data_type,
                    "classification": e.classification.value,
                    "tags": e.tags
                }
                for e in self.data_elements.values()
            ],
            "tags": [
                {
                    "tag_id": t.tag_id,
                    "name": t.name,
                    "tag_type": t.tag_type.value,
                    "description": t.description
                }
                for t in self.tags.values()
            ]
        }

        return report


metadata_manager = MetadataManager()