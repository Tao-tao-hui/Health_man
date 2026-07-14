"""数据治理框架核心模块

提供完整的数据治理体系，包含：
1. 数据治理组织架构与职责定义
2. 数据治理工作流程管理
3. 数据治理策略配置
4. 治理成效评估机制
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("governance_framework")


class GovernanceRole(Enum):
    """数据治理角色定义"""
    DATA_OWNER = "data_owner"
    DATA_STEWARD = "data_steward"
    DATA_ADMIN = "data_admin"
    DATA_USER = "data_user"
    DATA_AUDITOR = "data_auditor"
    DATA_ARCHITECT = "data_architect"
    CLINICAL_EXPERT = "clinical_expert"


class GovernanceLevel(Enum):
    """治理级别定义"""
    ENTERPRISE = "enterprise"
    DOMAIN = "domain"
    SYSTEM = "system"
    DATASET = "dataset"


@dataclass
class RoleDefinition:
    """角色定义"""
    role: GovernanceRole
    level: GovernanceLevel
    responsibilities: List[str]
    authority: List[str]
    required_skills: List[str]


@dataclass
class GovernancePolicy:
    """治理策略"""
    policy_id: str
    name: str
    description: str
    applicable_level: GovernanceLevel
    enforcement_level: str  # strict, advisory, informational
    effective_date: datetime
    expiration_date: Optional[datetime] = None
    related_regulations: List[str] = field(default_factory=list)


@dataclass
class WorkflowStage:
    """工作流阶段"""
    stage_id: str
    name: str
    description: str
    required_roles: List[GovernanceRole]
    approval_required: bool = False
    timeout_days: Optional[int] = None


@dataclass
class WorkflowInstance:
    """工作流实例"""
    workflow_id: str
    name: str
    stages: List[WorkflowStage]
    current_stage: int = 0
    status: str = "pending"  # pending, in_progress, completed, rejected
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


@dataclass
class GovernanceMetric:
    """治理成效指标"""
    metric_id: str
    name: str
    description: str
    calculation_method: str
    target_value: float
    current_value: Optional[float] = None
    trend: Optional[str] = None  # improving, stable, declining


@dataclass
class GovernanceReport:
    """治理报告"""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    metrics: List[GovernanceMetric]
    issues: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class DataGovernanceFramework:
    """数据治理框架核心类"""

    def __init__(self, config_path: Optional[str] = None):
        self.roles: Dict[str, RoleDefinition] = {}
        self.policies: Dict[str, GovernancePolicy] = {}
        self.workflows: Dict[str, WorkflowInstance] = {}
        self.metrics: Dict[str, GovernanceMetric] = {}
        self.reports: List[GovernanceReport] = []
        
        self.knowledge_graph = None
        self.indicator_system = None
        self.metadata_manager = None
        self.quality_assurance = None
        self.compliance_manager = None
        
        if config_path:
            self.load_config(config_path)
        else:
            self._initialize_default_config()

    def _initialize_default_config(self) -> None:
        """初始化默认配置"""
        self._define_roles()
        self._define_policies()
        self._define_workflows()
        self._define_metrics()

    def _define_roles(self) -> None:
        """定义数据治理角色"""
        roles_config = [
            RoleDefinition(
                role=GovernanceRole.DATA_OWNER,
                level=GovernanceLevel.ENTERPRISE,
                responsibilities=[
                    "负责数据资产的整体战略规划",
                    "审批重大数据治理决策",
                    "确保数据治理与业务目标对齐",
                    "分配数据治理资源"
                ],
                authority=[
                    "审批数据治理政策",
                    "决策数据保留与销毁策略",
                    "授权数据访问权限"
                ],
                required_skills=["业务战略", "风险管理", "领导力"]
            ),
            RoleDefinition(
                role=GovernanceRole.DATA_STEWARD,
                level=GovernanceLevel.DOMAIN,
                responsibilities=[
                    "执行数据质量监控与改进",
                    "维护数据标准与规范",
                    "协调数据问题解决",
                    "培训数据使用者"
                ],
                authority=[
                    "制定数据标准",
                    "审批数据质量规则",
                    "处理数据质量问题"
                ],
                required_skills=["数据管理", "领域知识", "沟通协调"]
            ),
            RoleDefinition(
                role=GovernanceRole.CLINICAL_EXPERT,
                level=GovernanceLevel.DOMAIN,
                responsibilities=[
                    "验证医疗指标的临床合理性",
                    "审核健康评估算法的医学准确性",
                    "制定临床知识关联规则",
                    "提供专业医学建议"
                ],
                authority=[
                    "审批临床标准配置",
                    "验证指标体系设计",
                    "确认医学知识图谱内容"
                ],
                required_skills=["临床医学", "医学统计学", "健康评估"]
            ),
            RoleDefinition(
                role=GovernanceRole.DATA_ADMIN,
                level=GovernanceLevel.SYSTEM,
                responsibilities=[
                    "管理数据系统基础设施",
                    "执行数据安全策略",
                    "维护数据访问控制",
                    "监控系统运行状态"
                ],
                authority=[
                    "配置系统安全设置",
                    "管理用户访问权限",
                    "执行数据备份与恢复"
                ],
                required_skills=["系统管理", "网络安全", "数据库管理"]
            ),
            RoleDefinition(
                role=GovernanceRole.DATA_AUDITOR,
                level=GovernanceLevel.ENTERPRISE,
                responsibilities=[
                    "审计数据治理政策执行情况",
                    "验证数据质量保证措施",
                    "检查合规性要求满足情况",
                    "报告治理成效与问题"
                ],
                authority=[
                    "访问所有数据治理记录",
                    "执行合规性审计",
                    "报告审计发现"
                ],
                required_skills=["审计", "合规", "数据分析"]
            ),
            RoleDefinition(
                role=GovernanceRole.DATA_ARCHITECT,
                level=GovernanceLevel.SYSTEM,
                responsibilities=[
                    "设计数据架构与模型",
                    "规划数据集成方案",
                    "定义数据接口标准",
                    "优化数据存储与检索"
                ],
                authority=[
                    "设计数据模型",
                    "制定数据接口规范",
                    "审批技术实施方案"
                ],
                required_skills=["数据建模", "系统架构", "ETL设计"]
            ),
            RoleDefinition(
                role=GovernanceRole.DATA_USER,
                level=GovernanceLevel.DATASET,
                responsibilities=[
                    "遵守数据使用规范",
                    "报告数据质量问题",
                    "保护数据安全与隐私",
                    "正确解读数据结果"
                ],
                authority=[
                    "访问授权范围内的数据",
                    "提交数据质量反馈",
                    "使用标准数据分析工具"
                ],
                required_skills=["数据使用", "数据解读", "合规意识"]
            )
        ]

        for role_def in roles_config:
            self.roles[role_def.role.value] = role_def

    def _define_policies(self) -> None:
        """定义治理政策"""
        policies_config = [
            GovernancePolicy(
                policy_id="POLICY_DQ_001",
                name="数据质量保证政策",
                description="确保所有健康数据符合预设的质量标准",
                applicable_level=GovernanceLevel.DATASET,
                enforcement_level="strict",
                effective_date=datetime(2026, 7, 1),
                related_regulations=["ISO 8000", "HIMSS Data Quality Framework"]
            ),
            GovernancePolicy(
                policy_id="POLICY_SEC_001",
                name="数据安全保护政策",
                description="保护健康数据的机密性、完整性和可用性",
                applicable_level=GovernanceLevel.SYSTEM,
                enforcement_level="strict",
                effective_date=datetime(2026, 7, 1),
                related_regulations=["GDPR", "《个人信息保护法》", "HIPAA"]
            ),
            GovernancePolicy(
                policy_id="POLICY_PV_001",
                name="数据隐私保护政策",
                description="确保健康数据处理符合隐私法规要求",
                applicable_level=GovernanceLevel.ENTERPRISE,
                enforcement_level="strict",
                effective_date=datetime(2026, 7, 1),
                related_regulations=["GDPR", "《个人信息保护法》", "《健康医疗数据安全指南》"]
            ),
            GovernancePolicy(
                policy_id="POLICY_LC_001",
                name="数据生命周期管理政策",
                description="规范健康数据从创建到销毁的全过程管理",
                applicable_level=GovernanceLevel.DOMAIN,
                enforcement_level="strict",
                effective_date=datetime(2026, 7, 1),
                related_regulations=["《数据安全法》", "医疗数据管理规范"]
            ),
            GovernancePolicy(
                policy_id="POLICY_STD_001",
                name="数据标准规范政策",
                description="统一健康数据的命名、格式和编码标准",
                applicable_level=GovernanceLevel.DOMAIN,
                enforcement_level="advisory",
                effective_date=datetime(2026, 7, 1),
                related_regulations=["HL7 FHIR", "ICD-10", "SNOMED CT"]
            ),
            GovernancePolicy(
                policy_id="POLICY_CLIN_001",
                name="临床知识关联政策",
                description="确保所有健康指标与临床知识准确关联",
                applicable_level=GovernanceLevel.DOMAIN,
                enforcement_level="strict",
                effective_date=datetime(2026, 7, 1),
                related_regulations=["医学指南", "临床实践标准"]
            )
        ]

        for policy in policies_config:
            self.policies[policy.policy_id] = policy

    def _define_workflows(self) -> None:
        """定义治理工作流"""
        # 数据质量问题处理流程
        dq_workflow = WorkflowInstance(
            workflow_id="WF_DQ_001",
            name="数据质量问题处理流程",
            stages=[
                WorkflowStage(
                    stage_id="DQ_01",
                    name="问题发现",
                    description="通过质量监控系统或用户反馈发现数据质量问题",
                    required_roles=[GovernanceRole.DATA_USER, GovernanceRole.DATA_STEWARD],
                    approval_required=False
                ),
                WorkflowStage(
                    stage_id="DQ_02",
                    name="问题评估",
                    description="数据治理专员评估问题严重程度和影响范围",
                    required_roles=[GovernanceRole.DATA_STEWARD],
                    approval_required=True,
                    timeout_days=3
                ),
                WorkflowStage(
                    stage_id="DQ_03",
                    name="问题修复",
                    description="执行数据修复措施",
                    required_roles=[GovernanceRole.DATA_STEWARD, GovernanceRole.DATA_ADMIN],
                    approval_required=False
                ),
                WorkflowStage(
                    stage_id="DQ_04",
                    name="验证确认",
                    description="验证修复效果，确认问题已解决",
                    required_roles=[GovernanceRole.DATA_STEWARD],
                    approval_required=True,
                    timeout_days=2
                )
            ]
        )

        # 临床知识更新流程
        clinical_workflow = WorkflowInstance(
            workflow_id="WF_CLIN_001",
            name="临床知识更新流程",
            stages=[
                WorkflowStage(
                    stage_id="CLIN_01",
                    name="知识采集",
                    description="收集最新医学指南、研究成果和专家意见",
                    required_roles=[GovernanceRole.CLINICAL_EXPERT],
                    approval_required=False
                ),
                WorkflowStage(
                    stage_id="CLIN_02",
                    name="知识评估",
                    description="评估新知识的证据等级和适用性",
                    required_roles=[GovernanceRole.CLINICAL_EXPERT],
                    approval_required=True,
                    timeout_days=7
                ),
                WorkflowStage(
                    stage_id="CLIN_03",
                    name="系统更新",
                    description="更新知识图谱和相关指标配置",
                    required_roles=[GovernanceRole.DATA_ARCHITECT, GovernanceRole.CLINICAL_EXPERT],
                    approval_required=False
                ),
                WorkflowStage(
                    stage_id="CLIN_04",
                    name="验证测试",
                    description="验证更新后系统的准确性和一致性",
                    required_roles=[GovernanceRole.DATA_STEWARD, GovernanceRole.CLINICAL_EXPERT],
                    approval_required=True,
                    timeout_days=5
                ),
                WorkflowStage(
                    stage_id="CLIN_05",
                    name="发布上线",
                    description="正式发布更新内容",
                    required_roles=[GovernanceRole.DATA_OWNER],
                    approval_required=True
                )
            ]
        )

        # 指标变更流程
        indicator_workflow = WorkflowInstance(
            workflow_id="WF_IND_001",
            name="指标变更流程",
            stages=[
                WorkflowStage(
                    stage_id="IND_01",
                    name="需求提出",
                    description="提出指标新增或修改需求",
                    required_roles=[GovernanceRole.DATA_USER, GovernanceRole.CLINICAL_EXPERT],
                    approval_required=False
                ),
                WorkflowStage(
                    stage_id="IND_02",
                    name="临床验证",
                    description="临床专家验证指标的医学合理性",
                    required_roles=[GovernanceRole.CLINICAL_EXPERT],
                    approval_required=True,
                    timeout_days=5
                ),
                WorkflowStage(
                    stage_id="IND_03",
                    name="技术设计",
                    description="设计指标的数据模型和计算逻辑",
                    required_roles=[GovernanceRole.DATA_ARCHITECT],
                    approval_required=True,
                    timeout_days=5
                ),
                WorkflowStage(
                    stage_id="IND_04",
                    name="开发实现",
                    description="实现指标计算和关联逻辑",
                    required_roles=[GovernanceRole.DATA_ADMIN],
                    approval_required=False
                ),
                WorkflowStage(
                    stage_id="IND_05",
                    name="测试验证",
                    description="测试指标计算的准确性和稳定性",
                    required_roles=[GovernanceRole.DATA_STEWARD],
                    approval_required=True,
                    timeout_days=5
                )
            ]
        )

        self.workflows[dq_workflow.workflow_id] = dq_workflow
        self.workflows[clinical_workflow.workflow_id] = clinical_workflow
        self.workflows[indicator_workflow.workflow_id] = indicator_workflow

    def _define_metrics(self) -> None:
        """定义治理成效指标"""
        metrics_config = [
            GovernanceMetric(
                metric_id="METRIC_DQ_001",
                name="数据完整性",
                description="数据字段填充率",
                calculation_method="已填充字段数 / 总字段数",
                target_value=0.95
            ),
            GovernanceMetric(
                metric_id="METRIC_DQ_002",
                name="数据准确性",
                description="数据值符合业务规则的比例",
                calculation_method="有效数据记录数 / 总记录数",
                target_value=0.98
            ),
            GovernanceMetric(
                metric_id="METRIC_DQ_003",
                name="数据一致性",
                description="跨系统数据一致性",
                calculation_method="一致记录数 / 比对记录数",
                target_value=0.99
            ),
            GovernanceMetric(
                metric_id="METRIC_DQ_004",
                name="数据唯一性",
                description="无重复记录比例",
                calculation_method="唯一记录数 / 总记录数",
                target_value=1.0
            ),
            GovernanceMetric(
                metric_id="METRIC_SEC_001",
                name="安全事件发生率",
                description="安全事件发生频率",
                calculation_method="安全事件数 / 数据访问次数",
                target_value=0.0
            ),
            GovernanceMetric(
                metric_id="METRIC_COM_001",
                name="合规性达标率",
                description="满足合规要求的比例",
                calculation_method="通过合规检查项数 / 总检查项数",
                target_value=1.0
            ),
            GovernanceMetric(
                metric_id="METRIC_KG_001",
                name="知识图谱准确率",
                description="临床知识关联的准确性",
                calculation_method="正确关联数 / 总关联数",
                target_value=0.98
            ),
            GovernanceMetric(
                metric_id="METRIC_KG_002",
                name="知识更新时效性",
                description="新知识从发布到系统更新的时间",
                calculation_method="更新天数",
                target_value=30
            ),
            GovernanceMetric(
                metric_id="METRIC_WF_001",
                name="流程效率",
                description="治理流程平均处理时间",
                calculation_method="总处理天数 / 完成流程数",
                target_value=10
            )
        ]

        for metric in metrics_config:
            self.metrics[metric.metric_id] = metric

    def load_config(self, config_path: str) -> None:
        """加载配置文件"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            self._initialize_default_config()
            return

        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if 'roles' in config:
            for role_data in config['roles']:
                role_def = RoleDefinition(
                    role=GovernanceRole(role_data['role']),
                    level=GovernanceLevel(role_data['level']),
                    responsibilities=role_data['responsibilities'],
                    authority=role_data['authority'],
                    required_skills=role_data['required_skills']
                )
                self.roles[role_def.role.value] = role_def

        if 'policies' in config:
            for policy_data in config['policies']:
                policy = GovernancePolicy(
                    policy_id=policy_data['policy_id'],
                    name=policy_data['name'],
                    description=policy_data['description'],
                    applicable_level=GovernanceLevel(policy_data['applicable_level']),
                    enforcement_level=policy_data['enforcement_level'],
                    effective_date=datetime.fromisoformat(policy_data['effective_date']),
                    expiration_date=datetime.fromisoformat(policy_data['expiration_date']) 
                        if policy_data.get('expiration_date') else None,
                    related_regulations=policy_data.get('related_regulations', [])
                )
                self.policies[policy.policy_id] = policy

        logger.info(f"配置文件加载完成: {config_path}")

    def save_config(self, config_path: str) -> None:
        """保存配置文件"""
        config = {
            'roles': [
                {
                    'role': r.role.value,
                    'level': r.level.value,
                    'responsibilities': r.responsibilities,
                    'authority': r.authority,
                    'required_skills': r.required_skills
                }
                for r in self.roles.values()
            ],
            'policies': [
                {
                    'policy_id': p.policy_id,
                    'name': p.name,
                    'description': p.description,
                    'applicable_level': p.applicable_level.value,
                    'enforcement_level': p.enforcement_level,
                    'effective_date': p.effective_date.isoformat(),
                    'expiration_date': p.expiration_date.isoformat() if p.expiration_date else None,
                    'related_regulations': p.related_regulations
                }
                for p in self.policies.values()
            ]
        }

        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logger.info(f"配置文件已保存: {config_path}")

    def get_role_definition(self, role: GovernanceRole) -> Optional[RoleDefinition]:
        """获取角色定义"""
        return self.roles.get(role.value)

    def get_policy(self, policy_id: str) -> Optional[GovernancePolicy]:
        """获取政策"""
        return self.policies.get(policy_id)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowInstance]:
        """获取工作流"""
        return self.workflows.get(workflow_id)

    def update_metric(self, metric_id: str, value: float) -> None:
        """更新治理指标值"""
        if metric_id in self.metrics:
            metric = self.metrics[metric_id]
            if metric.current_value is not None:
                metric.trend = "improving" if value > metric.current_value else (
                    "declining" if value < metric.current_value else "stable"
                )
            metric.current_value = value
            logger.info(f"指标更新: {metric_id} = {value}")
        else:
            logger.warning(f"指标不存在: {metric_id}")

    def generate_report(self, period_start: datetime, period_end: datetime) -> GovernanceReport:
        """生成治理报告"""
        report_id = f"REPORT_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}"
        metrics_list = list(self.metrics.values())
        
        issues = []
        for metric in metrics_list:
            if metric.current_value is not None:
                if metric.calculation_method == "更新天数" or metric.calculation_method == "总处理天数 / 完成流程数":
                    if metric.current_value > metric.target_value:
                        issues.append({
                            'metric_id': metric.metric_id,
                            'metric_name': metric.name,
                            'issue': f"当前值 {metric.current_value} 超过目标值 {metric.target_value}",
                            'severity': 'high' if metric.current_value > metric.target_value * 2 else 'medium'
                        })
                else:
                    if metric.current_value < metric.target_value:
                        issues.append({
                            'metric_id': metric.metric_id,
                            'metric_name': metric.name,
                            'issue': f"当前值 {metric.current_value} 未达到目标值 {metric.target_value}",
                            'severity': 'high' if metric.current_value < metric.target_value * 0.9 else 'medium'
                        })

        recommendations = []
        if issues:
            recommendations.append("建议优先处理高严重性的数据质量问题")
            recommendations.append("加强数据质量监控和预警机制")
            recommendations.append("定期审查数据治理政策的执行情况")

        report = GovernanceReport(
            report_id=report_id,
            generated_at=datetime.now(),
            period_start=period_start,
            period_end=period_end,
            metrics=metrics_list,
            issues=issues,
            recommendations=recommendations
        )

        self.reports.append(report)
        logger.info(f"治理报告已生成: {report_id}")

        return report

    def advance_workflow(self, workflow_id: str, approver_role: GovernanceRole) -> bool:
        """推进工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.error(f"工作流不存在: {workflow_id}")
            return False

        current_stage = workflow.stages[workflow.current_stage]
        
        if current_stage.approval_required and approver_role not in current_stage.required_roles:
            logger.error(f"角色 {approver_role.value} 无权审批阶段 {current_stage.stage_id}")
            return False

        if workflow.current_stage < len(workflow.stages) - 1:
            workflow.current_stage += 1
            workflow.status = "in_progress"
            workflow.updated_at = datetime.now()
            logger.info(f"工作流 {workflow_id} 已推进到阶段 {workflow.stages[workflow.current_stage].stage_id}")
        else:
            workflow.status = "completed"
            workflow.updated_at = datetime.now()
            logger.info(f"工作流 {workflow_id} 已完成")

        return True

    def get_roles_by_level(self, level: GovernanceLevel) -> List[RoleDefinition]:
        """按治理级别获取角色"""
        return [r for r in self.roles.values() if r.level == level]

    def get_policies_by_level(self, level: GovernanceLevel) -> List[GovernancePolicy]:
        """按治理级别获取政策"""
        return [p for p in self.policies.values() if p.applicable_level == level]

    def set_knowledge_graph(self, kg) -> None:
        """设置知识图谱引用"""
        self.knowledge_graph = kg

    def set_indicator_system(self, is_) -> None:
        """设置指标体系引用"""
        self.indicator_system = is_

    def set_metadata_manager(self, mm) -> None:
        """设置元数据管理器引用"""
        self.metadata_manager = mm

    def set_quality_assurance(self, qa) -> None:
        """设置质量保证引用"""
        self.quality_assurance = qa

    def set_compliance_manager(self, cm) -> None:
        """设置合规管理器引用"""
        self.compliance_manager = cm

    def get_current_time(self) -> str:
        """获取当前时间"""
        return datetime.now().isoformat()

    def generate_report(self, period_start: datetime = None, period_end: datetime = None) -> dict:
        """生成治理报告"""
        if period_start is None:
            period_start = datetime.now().replace(day=1)
        if period_end is None:
            period_end = datetime.now()

        report_id = f"REPORT_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}"
        metrics_list = list(self.metrics.values())
        
        issues = []
        for metric in metrics_list:
            if metric.current_value is not None:
                if metric.calculation_method == "更新天数" or metric.calculation_method == "总处理天数 / 完成流程数":
                    if metric.current_value > metric.target_value:
                        issues.append({
                            'metric_id': metric.metric_id,
                            'metric_name': metric.name,
                            'issue': f"当前值 {metric.current_value} 超过目标值 {metric.target_value}",
                            'severity': 'high' if metric.current_value > metric.target_value * 2 else 'medium'
                        })
                else:
                    if metric.current_value < metric.target_value:
                        issues.append({
                            'metric_id': metric.metric_id,
                            'metric_name': metric.name,
                            'issue': f"当前值 {metric.current_value} 未达到目标值 {metric.target_value}",
                            'severity': 'high' if metric.current_value < metric.target_value * 0.9 else 'medium'
                        })

        recommendations = []
        if issues:
            recommendations.append("建议优先处理高严重性的数据质量问题")
            recommendations.append("加强数据质量监控和预警机制")
            recommendations.append("定期审查数据治理政策的执行情况")

        report = {
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "summary": {
                "total_roles": len(self.roles),
                "total_policies": len(self.policies),
                "total_workflows": len(self.workflows),
                "total_metrics": len(self.metrics),
                "open_issues": len(issues)
            },
            "roles": [
                {
                    "role": r.role.value,
                    "level": r.level.value,
                    "responsibilities_count": len(r.responsibilities),
                    "authority_count": len(r.authority)
                }
                for r in self.roles.values()
            ],
            "policies": [
                {
                    "policy_id": p.policy_id,
                    "name": p.name,
                    "level": p.applicable_level.value,
                    "enforcement": p.enforcement_level
                }
                for p in self.policies.values()
            ],
            "workflows": [
                {
                    "workflow_id": w.workflow_id,
                    "name": w.name,
                    "stage_count": len(w.stages),
                    "current_stage": w.current_stage,
                    "status": w.status
                }
                for w in self.workflows.values()
            ],
            "metrics": [
                {
                    "metric_id": m.metric_id,
                    "name": m.name,
                    "description": m.description,
                    "target_value": m.target_value,
                    "current_value": m.current_value,
                    "trend": m.trend
                }
                for m in metrics_list
            ],
            "issues": issues,
            "recommendations": recommendations
        }

        logger.info(f"治理报告已生成: {report_id}")
        return report


governance_framework = DataGovernanceFramework()