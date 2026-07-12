"""LlmPipeline 单元测试

验证端到端流水线整合功能。
使用 FakeModelAdapter 模拟 LLM。
"""
import json
from pathlib import Path

from scripts.llm.llm_pipeline import LlmPipeline, LlmPipelineResult
from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.validator import DualLayerValidator
from scripts.llm.master_orchestrator import MasterOrchestrator


class FakeModelAdapter(ModelAdapter):
    """用于测试的假模型适配器"""

    def chat(self, prompt: str, system: str | None = None) -> dict:
        return {
            "content": json.dumps({
                "indicator_id": "IND-01",
                "name_cn": "体脂率",
                "unit": "%",
                "statistics": {
                    "p5": 10.0, "p25": 15.0, "p50": 20.0,
                    "p75": 25.0, "p95": 30.0,
                    "mean": 20.5, "sd": 5.0, "n_subjects": 100,
                },
                "extraction_confidence": 0.9,
            }),
            "tokens_used": 100,
            "model_id": "fake-model",
            "latency_ms": 50,
        }

    def health_check(self) -> bool:
        return True

    def get_model_info(self) -> dict:
        return {"model_id": "fake-model"}


def _make_pipeline(tmp_path: Path, **kwargs) -> LlmPipeline:
    """使用临时目录构造 pipeline，避免硬编码路径副作用

    Args:
        tmp_path: 临时目录
        **kwargs: 透传给 LlmPipeline 构造函数（如 max_size_mb）
    """
    templates_dir = tmp_path / "prompt_templates"
    templates_dir.mkdir()
    (templates_dir / "extract_reference_range.txt").write_text(
        "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
    )
    lib = PromptTemplateLibrary(templates_dir)
    validator = DualLayerValidator()
    adapter = FakeModelAdapter()
    master = MasterOrchestrator(adapter, lib, validator)
    audit_path = tmp_path / "audit.jsonl"
    return LlmPipeline(master, audit_log_path=audit_path, **kwargs)


class TestLlmPipeline:
    """LlmPipeline 测试套件"""

    def test_run_returns_pipeline_result(self, tmp_path):
        """测试流水线返回结果对象"""
        pipeline = _make_pipeline(tmp_path)
        tasks = [
            {
                "indicator_id": "IND-01",
                "literature_texts": ["文献1"],
                "prompt_template": "extract_reference_range",
            }
        ]
        result = pipeline.run(tasks, tmp_path)
        assert isinstance(result, LlmPipelineResult)
        assert result.success is True
        assert result.total_extracted == 1

    def test_run_creates_output_files(self, tmp_path):
        """测试流水线在目标目录创建输出文件"""
        pipeline = _make_pipeline(tmp_path)
        tasks = [
            {
                "indicator_id": "IND-01",
                "literature_texts": ["文献1"],
                "prompt_template": "extract_reference_range",
            }
        ]
        pipeline.run(tasks, tmp_path)
        # 验证蒸馏数据文件已创建
        output_files = list(tmp_path.glob("*_distilled.json"))
        assert len(output_files) > 0

    def test_audit_size_under_limit(self, tmp_path):
        """测试体量审计在限制内"""
        pipeline = _make_pipeline(tmp_path)
        (tmp_path / "a.json").write_bytes(b'{"data": "test"}')
        audit = pipeline.audit_size(tmp_path)
        assert audit["total_bytes"] > 0
        assert audit["within_limit"] is True

    def test_audit_size_exceeds_limit(self, tmp_path):
        """测试体量审计超限"""
        pipeline = _make_pipeline(tmp_path, max_size_mb=0.0001)
        (tmp_path / "big.json").write_bytes(b"x" * 200)
        audit = pipeline.audit_size(tmp_path)
        assert audit["within_limit"] is False
