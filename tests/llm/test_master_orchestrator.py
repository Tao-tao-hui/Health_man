"""MasterOrchestrator 单元测试

验证主代理的任务调度和结果聚合功能。
使用 FakeModelAdapter 模拟 LLM。
"""
import json

from scripts.llm.master_orchestrator import MasterOrchestrator
from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.validator import DualLayerValidator


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


class TestMasterOrchestrator:
    """MasterOrchestrator 测试套件"""

    def test_dispatch_extraction_returns_results(self, tmp_path):
        """测试分发提取任务返回结果列表"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        validator = DualLayerValidator()
        adapter = FakeModelAdapter()

        master = MasterOrchestrator(adapter, lib, validator)
        results = master.dispatch_extraction(
            "IND-01", ["文献1内容", "文献2内容"]
        )
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.confidence == 0.9 for r in results)

    def test_dispatch_validation_returns_validated(self, tmp_path):
        """测试分发验证任务返回验证后结果"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        validator = DualLayerValidator()
        adapter = FakeModelAdapter()

        master = MasterOrchestrator(adapter, lib, validator)
        extracted = master.dispatch_extraction("IND-01", ["文献1"])
        validated = master.dispatch_validation(extracted, "IND-01")
        assert len(validated) == 1
        assert validated[0].success is True

    def test_run_full_pipeline(self, tmp_path):
        """测试完整蒸馏流程"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        validator = DualLayerValidator()
        adapter = FakeModelAdapter()

        master = MasterOrchestrator(adapter, lib, validator)
        tasks = [
            {
                "indicator_id": "IND-01",
                "literature_texts": ["文献1", "文献2"],
                "prompt_template": "extract_reference_range",
            }
        ]
        result = master.run(tasks)
        assert result["total_tasks"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
