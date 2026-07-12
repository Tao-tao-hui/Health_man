"""LlmMetadataGenerator 单元测试

验证 Layer C 三层元数据生成。
"""
import json
from pathlib import Path

from scripts.llm.llm_metadata_generator import LlmMetadataGenerator
from scripts.llm.llm_pipeline import LlmPipelineResult


def make_test_pipeline_result() -> LlmPipelineResult:
    """创建测试用流水线结果"""
    return LlmPipelineResult(
        success=True,
        total_extracted=10,
        total_validated=8,
        total_rejected=2,
        total_tokens_consumed=5000,
    )


class TestLlmMetadataGenerator:
    """LlmMetadataGenerator 测试套件"""

    def test_generate_l0_returns_dict_with_llm_fields(self, tmp_path):
        """测试 L0 包含 LLM 特定字段"""
        gen = LlmMetadataGenerator()
        result = make_test_pipeline_result()
        l0 = gen.generate_l0(result, output_path=tmp_path / "l0.json")
        assert l0["dataset_id"] == "C_llm_distilled"
        assert "extraction_method" in l0
        assert l0["total_extracted"] == 10
        assert l0["total_validated"] == 8
        assert (tmp_path / "l0.json").exists()

    def test_generate_l1_returns_field_dict(self, tmp_path):
        """测试 L1 返回字段字典"""
        gen = LlmMetadataGenerator()
        data = [
            {"indicator_id": "IND-01", "name_cn": "体脂率", "unit": "%"},
            {"indicator_id": "IND-01", "name_cn": "体脂率", "unit": "%"},
        ]
        l1 = gen.generate_l1(data, output_path=tmp_path / "l1.json")
        assert "fields" in l1
        assert l1["row_count"] == 2
        assert (tmp_path / "l1.json").exists()

    def test_generate_l2_returns_markdown(self, tmp_path):
        """测试 L2 返回 Markdown"""
        gen = LlmMetadataGenerator()
        result = make_test_pipeline_result()
        l2 = gen.generate_l2(result, output_path=tmp_path / "l2.md")
        assert isinstance(l2, str)
        assert "C_llm_distilled" in l2
        assert (tmp_path / "l2.md").exists()
