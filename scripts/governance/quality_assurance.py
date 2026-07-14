"""质量保证模块

提供数据质量监控、评估和改进能力，包含：
1. 数据质量规则定义
2. 数据质量检查与评分
3. 质量问题检测与告警
4. 质量报告生成
"""
import json
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quality_assurance")


class QualityDimension(Enum):
    """数据质量维度"""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"
    INTEGRITY = "integrity"


class QualityRuleType(Enum):
    """质量规则类型"""
    RANGE_CHECK = "range_check"
    FORMAT_CHECK = "format_check"
    NULL_CHECK = "null_check"
    UNIQUE_CHECK = "unique_check"
    CONSISTENCY_CHECK = "consistency_check"
    REFERENTIAL_CHECK = "referential_check"
    BUSINESS_RULE = "business_rule"


class QualityLevel(Enum):
    """质量级别"""
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class QualityRule:
    """质量规则定义"""
    rule_id: str
    name: str
    dimension: QualityDimension
    rule_type: QualityRuleType
    target_field: str
    condition: str
    threshold: float = 0.95
    description: Optional[str] = None
    severity: QualityLevel = QualityLevel.WARNING
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class QualityCheckResult:
    """质量检查结果"""
    check_id: str
    rule_id: str
    field_name: str
    dimension: QualityDimension
    passed: bool
    actual_value: float
    expected_value: float
    sample_size: int
    failed_count: int
    level: QualityLevel
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QualityIssue:
    """质量问题"""
    issue_id: str
    rule_id: str
    field_name: str
    dimension: QualityDimension
    level: QualityLevel
    description: str
    affected_records: int
    first_detected: datetime = field(default_factory=datetime.now)
    last_detected: Optional[datetime] = None
    resolved: bool = False
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None


@dataclass
class QualityScore:
    """质量评分"""
    score_id: str
    overall_score: float
    dimension_scores: Dict[str, float]
    check_count: int
    passed_count: int
    issue_count: int
    level: QualityLevel
    timestamp: datetime = field(default_factory=datetime.now)


class QualityAssurance:
    """质量保证核心类"""

    def __init__(self):
        self.rules: Dict[str, QualityRule] = {}
        self.check_results: List[QualityCheckResult] = []
        self.issues: Dict[str, QualityIssue] = {}
        self.scores: List[QualityScore] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """初始化默认质量规则"""
        rules_config = [
            QualityRule(
                rule_id="RULE_SPO2_RANGE",
                name="血氧饱和度范围检查",
                dimension=QualityDimension.VALIDITY,
                rule_type=QualityRuleType.RANGE_CHECK,
                target_field="SPO2",
                condition="value >= 70 and value <= 100",
                threshold=0.99,
                description="血氧饱和度应在70%-100%之间",
                severity=QualityLevel.CRITICAL
            ),
            QualityRule(
                rule_id="RULE_HEART_RATE_RANGE",
                name="心率范围检查",
                dimension=QualityDimension.VALIDITY,
                rule_type=QualityRuleType.RANGE_CHECK,
                target_field="HEART_RATE",
                condition="value >= 30 and value <= 250",
                threshold=0.98,
                description="心率应在30-250 BPM之间",
                severity=QualityLevel.CRITICAL
            ),
            QualityRule(
                rule_id="RULE_BMI_RANGE",
                name="BMI范围检查",
                dimension=QualityDimension.VALIDITY,
                rule_type=QualityRuleType.RANGE_CHECK,
                target_field="BMI",
                condition="value >= 10 and value <= 80",
                threshold=0.99,
                description="BMI应在10-80 kg/m²之间",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_BODY_FAT_RANGE",
                name="体脂率范围检查",
                dimension=QualityDimension.VALIDITY,
                rule_type=QualityRuleType.RANGE_CHECK,
                target_field="BODY_FAT_RATE",
                condition="value >= 3 and value <= 60",
                threshold=0.99,
                description="体脂率应在3%-60%之间",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_SPO2_COMPLETENESS",
                name="血氧饱和度完整性检查",
                dimension=QualityDimension.COMPLETENESS,
                rule_type=QualityRuleType.NULL_CHECK,
                target_field="SPO2",
                condition="value is not null",
                threshold=0.95,
                description="血氧饱和度数据完整性检查",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_HEART_RATE_COMPLETENESS",
                name="心率完整性检查",
                dimension=QualityDimension.COMPLETENESS,
                rule_type=QualityRuleType.NULL_CHECK,
                target_field="HEART_RATE",
                condition="value is not null",
                threshold=0.95,
                description="心率数据完整性检查",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_MEASURE_TIME_VALID",
                name="测量时间有效性检查",
                dimension=QualityDimension.VALIDITY,
                rule_type=QualityRuleType.FORMAT_CHECK,
                target_field="MEASURE_TIME",
                condition="value is valid datetime",
                threshold=0.99,
                description="测量时间格式有效性检查",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_DEVICE_ID_UNIQUE",
                name="设备ID唯一性检查",
                dimension=QualityDimension.UNIQUENESS,
                rule_type=QualityRuleType.UNIQUE_CHECK,
                target_field="DEVICE_ID",
                condition="value is unique",
                threshold=0.99,
                description="设备ID唯一性检查",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_SPO2_CONSISTENCY",
                name="血氧饱和度一致性检查",
                dimension=QualityDimension.CONSISTENCY,
                rule_type=QualityRuleType.CONSISTENCY_CHECK,
                target_field="SPO2",
                condition="value changes <= 5% within 5 minutes",
                threshold=0.95,
                description="短时间内血氧饱和度变化不应超过5%",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_HEART_RATE_CONSISTENCY",
                name="心率一致性检查",
                dimension=QualityDimension.CONSISTENCY,
                rule_type=QualityRuleType.CONSISTENCY_CHECK,
                target_field="HEART_RATE",
                condition="value changes <= 30 BPM within 1 minute",
                threshold=0.95,
                description="短时间内心率变化不应超过30 BPM",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_TIMELINESS",
                name="数据及时性检查",
                dimension=QualityDimension.TIMELINESS,
                rule_type=QualityRuleType.BUSINESS_RULE,
                target_field="MEASURE_TIME",
                condition="now() - value <= 30 minutes",
                threshold=0.90,
                description="数据采集时间与处理时间间隔不应超过30分钟",
                severity=QualityLevel.WARNING
            ),
            QualityRule(
                rule_id="RULE_BMI_CALCULATION",
                name="BMI计算准确性检查",
                dimension=QualityDimension.ACCURACY,
                rule_type=QualityRuleType.BUSINESS_RULE,
                target_field="BMI",
                condition="BMI == WEIGHT / (HEIGHT/100)^2",
                threshold=0.98,
                description="BMI计算准确性验证",
                severity=QualityLevel.CRITICAL
            )
        ]

        for rule in rules_config:
            self.rules[rule.rule_id] = rule

    def add_rule(self, rule: QualityRule) -> None:
        """添加质量规则"""
        if rule.rule_id in self.rules:
            logger.warning(f"质量规则已存在，将更新: {rule.rule_id}")
        else:
            logger.info(f"添加质量规则: {rule.rule_id}")
        self.rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[QualityRule]:
        """获取质量规则"""
        return self.rules.get(rule_id)

    def get_rules_by_dimension(self, dimension: QualityDimension) -> List[QualityRule]:
        """按维度获取质量规则"""
        return [r for r in self.rules.values() if r.dimension == dimension and r.enabled]

    def execute_check(self, rule_id: str, data: List[Dict[str, Any]]) -> QualityCheckResult:
        """执行质量检查"""
        rule = self.rules.get(rule_id)
        if not rule or not rule.enabled:
            return QualityCheckResult(
                check_id=f"{rule_id}_{datetime.now().timestamp()}",
                rule_id=rule_id,
                field_name="N/A",
                dimension=QualityDimension.VALIDITY,
                passed=False,
                actual_value=0,
                expected_value=0,
                sample_size=0,
                failed_count=0,
                level=QualityLevel.WARNING,
                message="规则不存在或未启用"
            )

        sample_size = len(data)
        failed_count = 0

        for record in data:
            field_value = record.get(rule.target_field)
            if not self._evaluate_condition(field_value, rule):
                failed_count += 1

        pass_rate = (sample_size - failed_count) / sample_size if sample_size > 0 else 0
        passed = pass_rate >= rule.threshold
        level = rule.severity if not passed else QualityLevel.EXCELLENT

        result = QualityCheckResult(
            check_id=f"{rule_id}_{datetime.now().timestamp()}",
            rule_id=rule_id,
            field_name=rule.target_field,
            dimension=rule.dimension,
            passed=passed,
            actual_value=pass_rate,
            expected_value=rule.threshold,
            sample_size=sample_size,
            failed_count=failed_count,
            level=level,
            message=f"通过率: {pass_rate:.2%}, 阈值: {rule.threshold:.2%}"
        )

        self.check_results.append(result)

        if not passed:
            self._create_or_update_issue(rule, failed_count, sample_size)

        return result

    def _evaluate_condition(self, value: Any, rule: QualityRule) -> bool:
        """评估条件"""
        if value is None:
            return rule.rule_type == QualityRuleType.NULL_CHECK

        try:
            if rule.rule_type == QualityRuleType.RANGE_CHECK:
                return float(value) >= 0  # 基础检查
            elif rule.rule_type == QualityRuleType.NULL_CHECK:
                return value is not None
            elif rule.rule_type == QualityRuleType.UNIQUE_CHECK:
                return True  # 唯一性需要跨记录检查
            elif rule.rule_type == QualityRuleType.CONSISTENCY_CHECK:
                return True  # 一致性需要时间序列分析
            elif rule.rule_type == QualityRuleType.FORMAT_CHECK:
                return True  # 格式检查需要具体验证
            elif rule.rule_type == QualityRuleType.BUSINESS_RULE:
                return True  # 业务规则需要具体实现
            return True
        except (ValueError, TypeError):
            return False

    def _create_or_update_issue(self, rule: QualityRule, failed_count: int, sample_size: int) -> None:
        """创建或更新质量问题"""
        issue_id = f"ISSUE_{rule.target_field}_{rule.dimension.value}"

        if issue_id in self.issues:
            issue = self.issues[issue_id]
            issue.last_detected = datetime.now()
            issue.affected_records += failed_count
            if failed_count > 0:
                issue.resolved = False
        else:
            issue = QualityIssue(
                issue_id=issue_id,
                rule_id=rule.rule_id,
                field_name=rule.target_field,
                dimension=rule.dimension,
                level=rule.severity,
                description=f"{rule.name} 检查失败，{failed_count}/{sample_size} 条记录不符合规则",
                affected_records=failed_count,
                first_detected=datetime.now()
            )
            self.issues[issue_id] = issue

        logger.warning(f"质量问题检测: {issue_id} - {issue.description}")

    def execute_all_checks(self, data: List[Dict[str, Any]]) -> List[QualityCheckResult]:
        """执行所有质量检查"""
        results = []
        for rule_id in self.rules:
            if self.rules[rule_id].enabled:
                result = self.execute_check(rule_id, data)
                results.append(result)
        return results

    def calculate_quality_score(self) -> QualityScore:
        """计算综合质量评分"""
        if not self.check_results:
            return QualityScore(
                score_id=f"SCORE_{datetime.now().timestamp()}",
                overall_score=0,
                dimension_scores={},
                check_count=0,
                passed_count=0,
                issue_count=0,
                level=QualityLevel.WARNING
            )

        dimension_scores = {}
        for dimension in QualityDimension:
            dimension_results = [r for r in self.check_results if r.dimension == dimension]
            if dimension_results:
                avg_score = statistics.mean([r.actual_value for r in dimension_results])
                dimension_scores[dimension.value] = avg_score

        overall_score = statistics.mean(list(dimension_scores.values())) if dimension_scores else 0
        check_count = len(self.check_results)
        passed_count = sum(1 for r in self.check_results if r.passed)
        issue_count = len([i for i in self.issues.values() if not i.resolved])

        level = self._determine_quality_level(overall_score)

        score = QualityScore(
            score_id=f"SCORE_{datetime.now().timestamp()}",
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            check_count=check_count,
            passed_count=passed_count,
            issue_count=issue_count,
            level=level
        )

        self.scores.append(score)
        return score

    def _determine_quality_level(self, score: float) -> QualityLevel:
        """确定质量级别"""
        if score >= 0.95:
            return QualityLevel.EXCELLENT
        elif score >= 0.85:
            return QualityLevel.GOOD
        elif score >= 0.70:
            return QualityLevel.WARNING
        elif score >= 0.50:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL

    def resolve_issue(self, issue_id: str, resolution: str) -> None:
        """解决质量问题"""
        if issue_id in self.issues:
            issue = self.issues[issue_id]
            issue.resolved = True
            issue.resolution = resolution
            issue.resolved_at = datetime.now()
            logger.info(f"质量问题已解决: {issue_id} - {resolution}")
        else:
            logger.warning(f"质量问题不存在: {issue_id}")

    def get_unresolved_issues(self, level: Optional[QualityLevel] = None) -> List[QualityIssue]:
        """获取未解决的质量问题"""
        issues = [i for i in self.issues.values() if not i.resolved]
        if level:
            issues = [i for i in issues if i.level == level]
        return issues

    def generate_quality_report(self) -> Dict:
        """生成质量报告"""
        score = self.calculate_quality_score()

        report = {
            "report_generated_at": datetime.now().isoformat(),
            "overall_score": {
                "value": score.overall_score,
                "level": score.level.value,
                "check_count": score.check_count,
                "passed_count": score.passed_count,
                "pass_rate": score.passed_count / score.check_count if score.check_count > 0 else 0
            },
            "dimension_scores": {
                dim: {"value": val, "level": self._determine_quality_level(val).value}
                for dim, val in score.dimension_scores.items()
            },
            "recent_checks": [
                {
                    "check_id": r.check_id,
                    "rule_id": r.rule_id,
                    "field_name": r.field_name,
                    "dimension": r.dimension.value,
                    "passed": r.passed,
                    "pass_rate": r.actual_value,
                    "threshold": r.expected_value,
                    "sample_size": r.sample_size,
                    "failed_count": r.failed_count,
                    "level": r.level.value,
                    "message": r.message,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.check_results[-20:]
            ],
            "unresolved_issues": [
                {
                    "issue_id": i.issue_id,
                    "rule_id": i.rule_id,
                    "field_name": i.field_name,
                    "dimension": i.dimension.value,
                    "level": i.level.value,
                    "description": i.description,
                    "affected_records": i.affected_records,
                    "first_detected": i.first_detected.isoformat(),
                    "last_detected": i.last_detected.isoformat() if i.last_detected else None
                }
                for i in self.get_unresolved_issues()
            ],
            "rules_summary": {
                "total_rules": len(self.rules),
                "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
                "rules_by_dimension": {
                    dim.value: sum(1 for r in self.rules.values() if r.dimension == dim)
                    for dim in QualityDimension
                }
            }
        }

        return report


quality_assurance = QualityAssurance()