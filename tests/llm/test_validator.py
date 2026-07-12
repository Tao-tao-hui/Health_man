"""DualLayerValidator 单元测试

验证双层验证器：结构化校验 + 语义校验。
"""
from scripts.llm.validator import DualLayerValidator, ValidationResult


class TestDualLayerValidator:
    """DualLayerValidator 测试套件"""

    def test_valid_data_passes_both_layers(self):
        """测试合法数据通过双层验证"""
        validator = DualLayerValidator()
        data = {
            "indicator_id": "IND-01",
            "name_cn": "体脂率",
            "unit": "%",
            "statistics": {
                "p5": 10.0, "p25": 15.0, "p50": 20.0,
                "p75": 25.0, "p95": 30.0,
                "mean": 20.5, "sd": 5.0, "n_subjects": 100,
            },
            "extraction_confidence": 0.9,
        }
        result = validator.validate(data, "IND-01")
        assert result.is_valid is True
        assert result.confidence == 0.9
        assert "structure" in result.layer_passed
        assert "semantic" in result.layer_passed

    def test_missing_required_field_fails_structure(self):
        """测试缺少必填字段未通过结构化校验"""
        validator = DualLayerValidator()
        data = {
            "indicator_id": "IND-01",
            # 缺少 name_cn, unit, statistics, extraction_confidence
        }
        result = validator.validate(data, "IND-01")
        assert result.is_valid is False
        assert "structure" not in result.layer_passed
        assert len(result.errors) > 0

    def test_out_of_range_value_fails_semantic(self):
        """测试数值越界未通过语义校验"""
        validator = DualLayerValidator()
        data = {
            "indicator_id": "IND-01",
            "name_cn": "体脂率",
            "unit": "%",
            "statistics": {
                "p5": 150.0,  # 体脂率 150% 越界
                "p25": 15.0, "p50": 20.0, "p75": 25.0, "p95": 30.0,
                "mean": 20.5, "sd": 5.0, "n_subjects": 100,
            },
            "extraction_confidence": 0.9,
        }
        result = validator.validate(data, "IND-01")
        assert result.is_valid is False
        assert "semantic" not in result.layer_passed

    def test_low_confidence_rejected(self):
        """测试 confidence <0.5 被拒绝"""
        validator = DualLayerValidator()
        data = {
            "indicator_id": "IND-01",
            "name_cn": "体脂率",
            "unit": "%",
            "statistics": {
                "p5": 10.0, "p25": 15.0, "p50": 20.0,
                "p75": 25.0, "p95": 30.0,
                "mean": 20.5, "sd": 5.0, "n_subjects": 100,
            },
            "extraction_confidence": 0.3,
        }
        result = validator.validate(data, "IND-01")
        assert result.is_valid is False
        assert result.confidence < 0.5
