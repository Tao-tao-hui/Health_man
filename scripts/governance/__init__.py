"""数据治理体系模块

提供全面的数据治理能力，包含以下核心模块：
1. governance_framework - 数据治理框架核心
2. knowledge_graph - 医疗专业知识图谱
3. indicator_system - 指标体系设计
4. metadata_manager - 元数据管理
5. quality_assurance - 质量保证
6. compliance_manager - 合规性管理
"""

from .governance_framework import (
    DataGovernanceFramework,
    RoleDefinition,
    GovernancePolicy,
    WorkflowInstance,
    GovernanceMetric,
    GovernanceReport
)

from .knowledge_graph import (
    MedicalKnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelation,
    ClinicalStandard,
    KnowledgeVersion
)

from .indicator_system import (
    IndicatorSystem,
    IndicatorDefinition,
    IndicatorMapping,
    IndicatorScore,
    IndicatorSet,
    IndicatorCategory,
    IndicatorDataType,
    IndicatorSource,
    IndicatorLevel
)

from .metadata_manager import (
    MetadataManager,
    DataElement,
    DataLineage,
    TagDefinition,
    SemanticMapping,
    MetadataRecord,
    MetadataType,
    DataClassification,
    TagType,
    LineageDirection
)

from .quality_assurance import (
    QualityAssurance,
    QualityRule,
    QualityCheckResult,
    QualityIssue,
    QualityScore,
    QualityDimension,
    QualityRuleType,
    QualityLevel
)

from .compliance_manager import (
    ComplianceManager,
    ComplianceRequirement,
    DataSecurityPolicy,
    AccessControlEntry,
    AuditLog,
    ComplianceCheckResult,
    DataSubjectRequest,
    ComplianceStandard,
    PrivacyLevel,
    AccessLevel,
    ComplianceStatus,
    DataProtectionMethod
)


class HealthDataGovernanceSystem:
    """健康数据治理系统集成类

    将所有数据治理模块整合在一起，提供统一的访问入口。
    """

    def __init__(self):
        self.governance_framework = DataGovernanceFramework()
        self.knowledge_graph = MedicalKnowledgeGraph()
        self.indicator_system = IndicatorSystem(knowledge_graph=self.knowledge_graph)
        self.metadata_manager = MetadataManager()
        self.quality_assurance = QualityAssurance()
        self.compliance_manager = ComplianceManager()
        self._initialize_integration()

    def _initialize_integration(self) -> None:
        """初始化模块间的集成关系"""
        self.governance_framework.set_knowledge_graph(self.knowledge_graph)
        self.governance_framework.set_indicator_system(self.indicator_system)
        self.governance_framework.set_metadata_manager(self.metadata_manager)
        self.governance_framework.set_quality_assurance(self.quality_assurance)
        self.governance_framework.set_compliance_manager(self.compliance_manager)

    def generate_comprehensive_report(self) -> dict:
        """生成综合数据治理报告"""
        report = {
            "report_generated_at": self.governance_framework.get_current_time(),
            "modules": {
                "governance_framework": self.governance_framework.generate_report(),
                "knowledge_graph": self.knowledge_graph.generate_report(),
                "indicator_system": self.indicator_system.generate_indicator_report(),
                "metadata_manager": self.metadata_manager.generate_metadata_report(),
                "quality_assurance": self.quality_assurance.generate_quality_report(),
                "compliance_manager": self.compliance_manager.generate_compliance_report()
            },
            "summary": self._generate_summary()
        }
        return report

    def _generate_summary(self) -> dict:
        """生成报告摘要"""
        governance_report = self.governance_framework.generate_report()
        quality_report = self.quality_assurance.generate_quality_report()
        compliance_report = self.compliance_manager.generate_compliance_report()
        indicator_report = self.indicator_system.generate_indicator_report()
        metadata_report = self.metadata_manager.generate_metadata_report()
        knowledge_report = self.knowledge_graph.generate_report()

        return {
            "total_roles": governance_report.get("summary", {}).get("total_roles", 0),
            "total_policies": governance_report.get("summary", {}).get("total_policies", 0),
            "total_knowledge_nodes": knowledge_report.get("summary", {}).get("total_nodes", 0),
            "total_indicators": indicator_report.get("summary", {}).get("total_indicators", 0),
            "total_data_elements": metadata_report.get("summary", {}).get("total_data_elements", 0),
            "quality_score": quality_report.get("overall_score", {}).get("value", 0),
            "compliance_rate": compliance_report.get("summary", {}).get("compliance_rate", 0)
        }

    def run_all_quality_checks(self, data: list) -> list:
        """运行所有质量检查"""
        return self.quality_assurance.execute_all_checks(data)

    def run_all_compliance_checks(self) -> list:
        """运行所有合规检查"""
        return self.compliance_manager.execute_all_compliance_checks()

    def calculate_indicator_score(self, indicator_id: str, value: float, **kwargs) -> dict:
        """计算指标评分"""
        score = self.indicator_system.calculate_indicator_score(indicator_id, value, **kwargs)
        return {
            "indicator_id": score.indicator_id,
            "raw_value": score.raw_value,
            "normalized_value": score.normalized_value,
            "score": score.score,
            "grade": score.grade,
            "interpretation": score.interpretation
        }

    def validate_indicator_value(self, indicator_id: str, value: float) -> dict:
        """验证指标值"""
        return self.indicator_system.validate_indicator_value(indicator_id, value)

    def check_access(self, user_id: str, resource_id: str, access_level: str) -> bool:
        """检查访问权限"""
        level_map = {
            "read": AccessLevel.READ,
            "write": AccessLevel.WRITE,
            "admin": AccessLevel.ADMIN,
            "none": AccessLevel.NONE
        }
        return self.compliance_manager.check_access(user_id, resource_id, level_map.get(access_level, AccessLevel.NONE))

    def grant_access(self, user_id: str, resource_id: str, access_level: str, granted_by: str) -> None:
        """授予访问权限"""
        level_map = {
            "read": AccessLevel.READ,
            "write": AccessLevel.WRITE,
            "admin": AccessLevel.ADMIN,
            "none": AccessLevel.NONE
        }
        self.compliance_manager.grant_access(user_id, resource_id, level_map.get(access_level, AccessLevel.NONE), granted_by)


health_data_governance_system = HealthDataGovernanceSystem()


__all__ = [
    "DataGovernanceFramework",
    "MedicalKnowledgeGraph",
    "IndicatorSystem",
    "MetadataManager",
    "QualityAssurance",
    "ComplianceManager",
    "HealthDataGovernanceSystem",
    "health_data_governance_system",
    "RoleDefinition",
    "GovernancePolicy",
    "WorkflowInstance",
    "GovernanceMetric",
    "GovernanceReport",
    "KnowledgeNode",
    "KnowledgeRelation",
    "ClinicalStandard",
    "KnowledgeVersion",
    "IndicatorDefinition",
    "IndicatorMapping",
    "IndicatorScore",
    "IndicatorSet",
    "IndicatorCategory",
    "IndicatorDataType",
    "IndicatorSource",
    "IndicatorLevel",
    "DataElement",
    "DataLineage",
    "TagDefinition",
    "SemanticMapping",
    "MetadataRecord",
    "MetadataType",
    "DataClassification",
    "TagType",
    "LineageDirection",
    "QualityRule",
    "QualityCheckResult",
    "QualityIssue",
    "QualityScore",
    "QualityDimension",
    "QualityRuleType",
    "QualityLevel",
    "ComplianceRequirement",
    "DataSecurityPolicy",
    "AccessControlEntry",
    "AuditLog",
    "ComplianceCheckResult",
    "DataSubjectRequest",
    "ComplianceStandard",
    "PrivacyLevel",
    "AccessLevel",
    "ComplianceStatus",
    "DataProtectionMethod"
]