"""合规性管理模块

提供数据合规性管理和隐私保护能力，包含：
1. 法规合规检查
2. 数据安全策略管理
3. 隐私保护机制
4. 访问控制与审计
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compliance_manager")


class ComplianceStandard(Enum):
    """合规标准"""
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PHIPA = "phipa"
    PIPL = "pipl"
    ISO_27001 = "iso_27001"
    HL7_FHIR = "hl7_fhir"


class PrivacyLevel(Enum):
    """隐私级别"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SENSITIVE = "sensitive"


class AccessLevel(Enum):
    """访问级别"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class ComplianceStatus(Enum):
    """合规状态"""
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"


class DataProtectionMethod(Enum):
    """数据保护方法"""
    ENCRYPTION = "encryption"
    MASKING = "masking"
    ANONYMIZATION = "anonymization"
    PSEUDONYMIZATION = "pseudonymization"
    ACCESS_CONTROL = "access_control"
    AUDIT_LOGGING = "audit_logging"


@dataclass
class ComplianceRequirement:
    """合规要求"""
    requirement_id: str
    standard: ComplianceStandard
    title: str
    description: str
    applicable_entities: List[str]
    priority: str = "high"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DataSecurityPolicy:
    """数据安全策略"""
    policy_id: str
    name: str
    description: str
    privacy_level: PrivacyLevel
    protection_methods: List[DataProtectionMethod]
    encryption_algorithm: Optional[str] = "AES-256"
    retention_period_days: int = 365
    access_controls: Dict[str, AccessLevel] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AccessControlEntry:
    """访问控制条目"""
    entry_id: str
    user_id: str
    resource_id: str
    access_level: AccessLevel
    granted_by: str
    granted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    revoked: bool = False


@dataclass
class AuditLog:
    """审计日志"""
    log_id: str
    user_id: str
    action: str
    resource_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    ip_address: Optional[str] = None
    success: bool = True
    details: Optional[str] = None


@dataclass
class ComplianceCheckResult:
    """合规检查结果"""
    check_id: str
    requirement_id: str
    standard: ComplianceStandard
    status: ComplianceStatus
    message: str
    affected_resources: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DataSubjectRequest:
    """数据主体请求"""
    request_id: str
    subject_id: str
    request_type: str
    status: str = "pending"
    details: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    response: Optional[str] = None


class ComplianceManager:
    """合规性管理核心类"""

    def __init__(self):
        self.requirements: Dict[str, ComplianceRequirement] = {}
        self.policies: Dict[str, DataSecurityPolicy] = {}
        self.access_controls: Dict[str, AccessControlEntry] = {}
        self.audit_logs: List[AuditLog] = []
        self.subject_requests: Dict[str, DataSubjectRequest] = {}
        self._initialize_default_requirements()
        self._initialize_default_policies()

    def _initialize_default_requirements(self) -> None:
        """初始化默认合规要求"""
        requirements_config = [
            ComplianceRequirement(
                requirement_id="REQ_HIPAA_1",
                standard=ComplianceStandard.HIPAA,
                title="访问控制",
                description="实施技术策略和程序，确保只有经授权的人员才能访问电子受保护健康信息(ePHI)",
                applicable_entities=["USER", "DEVICE", "DATA"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_HIPAA_2",
                standard=ComplianceStandard.HIPAA,
                title="审计追踪",
                description="记录和检查对电子受保护健康信息(ePHI)的所有访问和修改",
                applicable_entities=["DATA", "SYSTEM"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_HIPAA_3",
                standard=ComplianceStandard.HIPAA,
                title="数据完整性",
                description="实施技术策略和程序，确保电子受保护健康信息(ePHI)在传输和存储过程中不被未经授权修改或破坏",
                applicable_entities=["DATA", "SYSTEM"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_GDPR_1",
                standard=ComplianceStandard.GDPR,
                title="数据最小化",
                description="只收集和处理实现特定目的所必需的最少数据",
                applicable_entities=["DATA", "USER"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_GDPR_2",
                standard=ComplianceStandard.GDPR,
                title="数据主体权利",
                description="确保数据主体有权访问、更正、删除其个人数据",
                applicable_entities=["USER", "DATA"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_GDPR_3",
                standard=ComplianceStandard.GDPR,
                title="数据保护影响评估",
                description="对可能对个人权利和自由造成高风险的处理活动进行评估",
                applicable_entities=["SYSTEM", "DATA"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_PIPL_1",
                standard=ComplianceStandard.PIPL,
                title="个人信息保护",
                description="遵循合法、正当、必要原则处理个人信息",
                applicable_entities=["USER", "DATA"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_PIPL_2",
                standard=ComplianceStandard.PIPL,
                title="跨境数据传输",
                description="个人信息出境需经安全评估或认证",
                applicable_entities=["DATA", "SYSTEM"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_ISO_27001_1",
                standard=ComplianceStandard.ISO_27001,
                title="信息安全策略",
                description="制定并维护信息安全策略",
                applicable_entities=["SYSTEM", "ORG"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_ISO_27001_2",
                standard=ComplianceStandard.ISO_27001,
                title="资产管理",
                description="对信息资产进行分类和管理",
                applicable_entities=["DATA", "SYSTEM"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_HL7_FHIR_1",
                standard=ComplianceStandard.HL7_FHIR,
                title="数据交换标准",
                description="遵循HL7 FHIR标准进行健康数据交换",
                applicable_entities=["DATA", "INTERFACE"]
            ),
            ComplianceRequirement(
                requirement_id="REQ_HL7_FHIR_2",
                standard=ComplianceStandard.HL7_FHIR,
                title="资源验证",
                description="确保FHIR资源符合规范要求",
                applicable_entities=["DATA", "SYSTEM"]
            )
        ]

        for req in requirements_config:
            self.requirements[req.requirement_id] = req

    def _initialize_default_policies(self) -> None:
        """初始化默认安全策略"""
        policies_config = [
            DataSecurityPolicy(
                policy_id="POLICY_SENSITIVE_DATA",
                name="敏感数据保护策略",
                description="用户ID、姓名、出生日期等敏感个人信息的保护策略",
                privacy_level=PrivacyLevel.SENSITIVE,
                protection_methods=[DataProtectionMethod.ENCRYPTION, DataProtectionMethod.ACCESS_CONTROL, DataProtectionMethod.AUDIT_LOGGING],
                encryption_algorithm="AES-256",
                retention_period_days=730,
                access_controls={"ADMIN": AccessLevel.ADMIN, "DOCTOR": AccessLevel.READ}
            ),
            DataSecurityPolicy(
                policy_id="POLICY_HEALTH_DATA",
                name="健康数据保护策略",
                description="血氧饱和度、心率、BMI等健康数据的保护策略",
                privacy_level=PrivacyLevel.CONFIDENTIAL,
                protection_methods=[DataProtectionMethod.ENCRYPTION, DataProtectionMethod.ACCESS_CONTROL, DataProtectionMethod.AUDIT_LOGGING],
                encryption_algorithm="AES-256",
                retention_period_days=3650,
                access_controls={"ADMIN": AccessLevel.ADMIN, "DOCTOR": AccessLevel.READ, "USER": AccessLevel.READ}
            ),
            DataSecurityPolicy(
                policy_id="POLICY_DEVICE_DATA",
                name="设备数据保护策略",
                description="设备ID、设备状态等设备相关数据的保护策略",
                privacy_level=PrivacyLevel.INTERNAL,
                protection_methods=[DataProtectionMethod.ACCESS_CONTROL, DataProtectionMethod.AUDIT_LOGGING],
                retention_period_days=365,
                access_controls={"ADMIN": AccessLevel.ADMIN, "TECHNICIAN": AccessLevel.READ}
            ),
            DataSecurityPolicy(
                policy_id="POLICY_PUBLIC_DATA",
                name="公开数据策略",
                description="公开健康知识、标准参考值等公开数据的策略",
                privacy_level=PrivacyLevel.PUBLIC,
                protection_methods=[],
                retention_period_days=0
            )
        ]

        for policy in policies_config:
            self.policies[policy.policy_id] = policy

    def add_requirement(self, requirement: ComplianceRequirement) -> None:
        """添加合规要求"""
        if requirement.requirement_id in self.requirements:
            logger.warning(f"合规要求已存在，将更新: {requirement.requirement_id}")
        else:
            logger.info(f"添加合规要求: {requirement.requirement_id}")
        self.requirements[requirement.requirement_id] = requirement

    def get_requirement(self, requirement_id: str) -> Optional[ComplianceRequirement]:
        """获取合规要求"""
        return self.requirements.get(requirement_id)

    def get_requirements_by_standard(self, standard: ComplianceStandard) -> List[ComplianceRequirement]:
        """按标准获取合规要求"""
        return [r for r in self.requirements.values() if r.standard == standard]

    def add_policy(self, policy: DataSecurityPolicy) -> None:
        """添加安全策略"""
        if policy.policy_id in self.policies:
            logger.warning(f"安全策略已存在，将更新: {policy.policy_id}")
        else:
            logger.info(f"添加安全策略: {policy.policy_id}")
        self.policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> Optional[DataSecurityPolicy]:
        """获取安全策略"""
        return self.policies.get(policy_id)

    def get_policy_by_privacy_level(self, level: PrivacyLevel) -> List[DataSecurityPolicy]:
        """按隐私级别获取策略"""
        return [p for p in self.policies.values() if p.privacy_level == level and p.enabled]

    def grant_access(self, user_id: str, resource_id: str, access_level: AccessLevel, granted_by: str) -> AccessControlEntry:
        """授予访问权限"""
        entry_id = f"ACE_{user_id}_{resource_id}"
        entry = AccessControlEntry(
            entry_id=entry_id,
            user_id=user_id,
            resource_id=resource_id,
            access_level=access_level,
            granted_by=granted_by
        )
        self.access_controls[entry_id] = entry
        self._log_audit(user_id, "GRANT_ACCESS", resource_id, details=f"Access level: {access_level.value}")
        logger.info(f"授予访问权限: {user_id} -> {resource_id} ({access_level.value})")
        return entry

    def check_access(self, user_id: str, resource_id: str, required_level: AccessLevel) -> bool:
        """检查访问权限"""
        entry_id = f"ACE_{user_id}_{resource_id}"
        entry = self.access_controls.get(entry_id)

        if not entry or entry.revoked:
            self._log_audit(user_id, "ACCESS_DENIED", resource_id, success=False, details="No access entry or revoked")
            return False

        access_levels = {AccessLevel.NONE: 0, AccessLevel.READ: 1, AccessLevel.WRITE: 2, AccessLevel.ADMIN: 3}
        if access_levels.get(entry.access_level, 0) >= access_levels.get(required_level, 0):
            self._log_audit(user_id, "ACCESS_GRANTED", resource_id, details=f"Required: {required_level.value}, Actual: {entry.access_level.value}")
            return True
        else:
            self._log_audit(user_id, "ACCESS_DENIED", resource_id, success=False, details=f"Required: {required_level.value}, Actual: {entry.access_level.value}")
            return False

    def revoke_access(self, user_id: str, resource_id: str) -> None:
        """撤销访问权限"""
        entry_id = f"ACE_{user_id}_{resource_id}"
        if entry_id in self.access_controls:
            self.access_controls[entry_id].revoked = True
            self._log_audit(user_id, "REVOKE_ACCESS", resource_id)
            logger.info(f"撤销访问权限: {user_id} -> {resource_id}")
        else:
            logger.warning(f"访问控制条目不存在: {entry_id}")

    def _log_audit(self, user_id: str, action: str, resource_id: str, ip_address: str = None, success: bool = True, details: str = None) -> None:
        """记录审计日志"""
        log = AuditLog(
            log_id=f"AUDIT_{datetime.now().timestamp()}",
            user_id=user_id,
            action=action,
            resource_id=resource_id,
            ip_address=ip_address,
            success=success,
            details=details
        )
        self.audit_logs.append(log)

    def get_audit_logs(self, user_id: str = "", action: str = "", limit: int = 100) -> List[AuditLog]:
        """获取审计日志"""
        logs = self.audit_logs.copy()
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]
        if action:
            logs = [l for l in logs if action.lower() in l.action.lower()]
        return logs[-limit:]

    def create_data_subject_request(self, subject_id: str, request_type: str, details: str = None) -> DataSubjectRequest:
        """创建数据主体请求"""
        request = DataSubjectRequest(
            request_id=f"DSR_{subject_id}_{datetime.now().timestamp()}",
            subject_id=subject_id,
            request_type=request_type,
            details=details
        )
        self.subject_requests[request.request_id] = request
        self._log_audit("SYSTEM", "CREATE_DSR", request.request_id, details=f"Type: {request_type}")
        logger.info(f"创建数据主体请求: {request.request_id}")
        return request

    def process_data_subject_request(self, request_id: str, response: str) -> None:
        """处理数据主体请求"""
        if request_id in self.subject_requests:
            request = self.subject_requests[request_id]
            request.status = "processed"
            request.response = response
            request.processed_at = datetime.now()
            self._log_audit("SYSTEM", "PROCESS_DSR", request_id, details=f"Response: {response}")
            logger.info(f"处理数据主体请求: {request_id}")
        else:
            logger.warning(f"数据主体请求不存在: {request_id}")

    def execute_compliance_check(self, requirement_id: str) -> ComplianceCheckResult:
        """执行合规检查"""
        requirement = self.requirements.get(requirement_id)
        if not requirement:
            return ComplianceCheckResult(
                check_id=f"CHECK_{requirement_id}_{datetime.now().timestamp()}",
                requirement_id=requirement_id,
                standard=ComplianceStandard.HIPAA,
                status=ComplianceStatus.NOT_APPLICABLE,
                message="合规要求不存在"
            )

        status = ComplianceStatus.COMPLIANT
        message = "符合要求"
        recommendations = []

        if requirement.requirement_id == "REQ_HIPAA_1":
            if not self.access_controls:
                status = ComplianceStatus.WARNING
                message = "未配置访问控制"
                recommendations = ["配置访问控制策略", "定义角色权限"]

        elif requirement.requirement_id == "REQ_HIPAA_2":
            if len(self.audit_logs) < 10:
                status = ComplianceStatus.WARNING
                message = "审计日志不足"
                recommendations = ["启用审计日志记录"]

        elif requirement.requirement_id == "REQ_GDPR_2":
            pending_requests = [r for r in self.subject_requests.values() if r.status == "pending"]
            if pending_requests:
                status = ComplianceStatus.WARNING
                message = f"存在{len(pending_requests)}个待处理的数据主体请求"
                recommendations = ["及时处理数据主体请求"]

        result = ComplianceCheckResult(
            check_id=f"CHECK_{requirement_id}_{datetime.now().timestamp()}",
            requirement_id=requirement_id,
            standard=requirement.standard,
            status=status,
            message=message,
            recommendations=recommendations
        )

        return result

    def execute_all_compliance_checks(self) -> List[ComplianceCheckResult]:
        """执行所有合规检查"""
        results = []
        for requirement_id in self.requirements:
            result = self.execute_compliance_check(requirement_id)
            results.append(result)
        return results

    def generate_compliance_report(self) -> Dict:
        """生成合规报告"""
        results = self.execute_all_compliance_checks()

        compliant_count = sum(1 for r in results if r.status == ComplianceStatus.COMPLIANT)
        warning_count = sum(1 for r in results if r.status == ComplianceStatus.WARNING)
        non_compliant_count = sum(1 for r in results if r.status == ComplianceStatus.NON_COMPLIANT)

        report = {
            "report_generated_at": datetime.now().isoformat(),
            "summary": {
                "total_requirements": len(self.requirements),
                "compliant_count": compliant_count,
                "warning_count": warning_count,
                "non_compliant_count": non_compliant_count,
                "compliance_rate": compliant_count / len(self.requirements) if self.requirements else 0
            },
            "check_results": [
                {
                    "check_id": r.check_id,
                    "requirement_id": r.requirement_id,
                    "standard": r.standard.value,
                    "status": r.status.value,
                    "message": r.message,
                    "recommendations": r.recommendations
                }
                for r in results
            ],
            "policies_summary": {
                "total_policies": len(self.policies),
                "enabled_policies": sum(1 for p in self.policies.values() if p.enabled),
                "policies_by_privacy_level": {
                    level.value: sum(1 for p in self.policies.values() if p.privacy_level == level)
                    for level in PrivacyLevel
                }
            },
            "access_controls_summary": {
                "total_entries": len(self.access_controls),
                "active_entries": sum(1 for e in self.access_controls.values() if not e.revoked)
            },
            "audit_logs_summary": {
                "total_logs": len(self.audit_logs),
                "successful_actions": sum(1 for l in self.audit_logs if l.success),
                "failed_actions": sum(1 for l in self.audit_logs if not l.success)
            },
            "data_subject_requests_summary": {
                "total_requests": len(self.subject_requests),
                "pending_requests": sum(1 for r in self.subject_requests.values() if r.status == "pending"),
                "processed_requests": sum(1 for r in self.subject_requests.values() if r.status == "processed")
            }
        }

        return report


compliance_manager = ComplianceManager()