"""双层验证器

Layer 1: 结构化校验 — JSON Schema 严格校验，字段类型/范围/必填完整性
Layer 2: 语义校验 — 数值范围合理性、单位一致性、关键词黑名单过滤

基于 Spec §7.6.5 三层防护体系设计。
"""
import jsonschema
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# 结构化校验 Schema（Layer 1）
EXTRACTION_SCHEMA = {
    "type": "object",
    "required": [
        "indicator_id", "name_cn", "unit",
        "statistics", "extraction_confidence",
    ],
    "properties": {
        "indicator_id": {"type": "string"},
        "name_cn": {"type": "string"},
        "name_en": {"type": "string"},
        "unit": {"type": "string"},
        "population": {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "age_range": {"type": "string"},
                "gender": {"type": "string"},
            },
        },
        "statistics": {
            "type": "object",
            "required": ["n_subjects"],
            "properties": {
                "p5": {"type": ["number", "null"]},
                "p25": {"type": ["number", "null"]},
                "p50": {"type": ["number", "null"]},
                "p75": {"type": ["number", "null"]},
                "p95": {"type": ["number", "null"]},
                "mean": {"type": ["number", "null"]},
                "sd": {"type": ["number", "null"]},
                "n_subjects": {"type": "integer"},
            },
        },
        "source_pmid": {"type": "string"},
        "extraction_confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}

# 语义校验范围（Layer 2）— 各指标的合理范围
INDICATOR_RANGES = {
    "IND-01": {"name": "体脂率", "unit": "%", "min": 0, "max": 60},
    "IND-02": {"name": "BMI", "unit": "kg/m²", "min": 10, "max": 80},
    "IND-10": {"name": "骨骼肌", "unit": "kg", "min": 10, "max": 100},
    "IND-15": {"name": "SpO₂", "unit": "%", "min": 70, "max": 100},
    "IND-18": {"name": "心率", "unit": "bpm", "min": 30, "max": 220},
    "IND-19": {"name": "HRV_RMSSD", "unit": "ms", "min": 0, "max": 500},
    "IND-20": {"name": "HRV_SDNN", "unit": "ms", "min": 0, "max": 500},
    "default": {"min": 0, "max": 10000},
}

# 关键词黑名单（Spec §7.6.6）
KEYWORD_BLACKLIST = [
    "诊断", "确诊", "治疗", "处方", "痊愈", "治愈",
    "药物推荐", "疗法治愈",
]

# confidence 阈值
CONFIDENCE_REJECT_THRESHOLD = 0.5
CONFIDENCE_REVIEW_THRESHOLD = 0.7


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    confidence: float
    errors: list[str] = field(default_factory=list)
    layer_passed: list[str] = field(default_factory=list)
    action: str = "accept"  # accept | review | reject


class DualLayerValidator:
    """双层验证器"""

    def validate(self, data: dict[str, Any], indicator_id: str) -> ValidationResult:
        """执行双层验证

        Args:
            data: LLM 提取的结构化数据
            indicator_id: 指标 ID（用于语义校验范围查找）

        Returns:
            验证结果
        """
        errors: list[str] = []
        layer_passed: list[str] = []

        # Layer 1: 结构化校验
        try:
            jsonschema.validate(instance=data, schema=EXTRACTION_SCHEMA)
            layer_passed.append("structure")
        except jsonschema.ValidationError as e:
            errors.append(f"Structure error: {e.message}")

        # Layer 2: 语义校验（仅在结构化校验通过后执行）
        if "structure" in layer_passed:
            semantic_errors = self._check_semantic(data, indicator_id)
            if semantic_errors:
                errors.extend(semantic_errors)
            else:
                layer_passed.append("semantic")

        # confidence 评估
        confidence = data.get("extraction_confidence", 0.0)

        # 综合判定
        is_valid = len(layer_passed) == 2 and confidence >= CONFIDENCE_REJECT_THRESHOLD

        # action 判定
        if not is_valid and confidence < CONFIDENCE_REJECT_THRESHOLD:
            action = "reject"
        elif confidence < CONFIDENCE_REVIEW_THRESHOLD:
            action = "review"
        else:
            action = "accept"

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            errors=errors,
            layer_passed=layer_passed,
            action=action,
        )

    def _check_semantic(
        self, data: dict[str, Any], indicator_id: str
    ) -> list[str]:
        """语义校验：数值范围 + 关键词黑名单"""
        errors: list[str] = []

        # 数值范围检查
        stats = data.get("statistics", {})
        range_info = INDICATOR_RANGES.get(
            indicator_id, INDICATOR_RANGES["default"]
        )
        min_val = range_info["min"]
        max_val = range_info["max"]

        for key in ["p5", "p25", "p50", "p75", "p95", "mean"]:
            val = stats.get(key)
            if val is not None and (val < min_val or val > max_val):
                errors.append(
                    f"Semantic error: {key}={val} out of range "
                    f"[{min_val}, {max_val}] for {indicator_id}"
                )

        # 关键词黑名单检查
        name_cn = data.get("name_cn", "")
        for keyword in KEYWORD_BLACKLIST:
            if keyword in name_cn:
                errors.append(f"Semantic error: blacklisted keyword '{keyword}' in name_cn")

        return errors
