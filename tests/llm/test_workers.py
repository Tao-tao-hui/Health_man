"""ExtractionWorker 单元测试

验证提取子代理的 LLM 调用、JSON 解析和结果返回。
使用 FakeModelAdapter 模拟 LLM 响应。
"""
import json

from scripts.llm.workers import ExtractionWorker
from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.task_types import TaskBrief
from scripts.llm.validator import DualLayerValidator


class FakeModelAdapter(ModelAdapter):
    """用于测试的假模型适配器"""

    def __init__(self, response_content: str):
        self.response_content = response_content

    def chat(self, prompt: str, system: str | None = None) -> dict:
        return {
            "content": self.response_content,
            "tokens_used": 100,
            "model_id": "fake-model",
            "latency_ms": 50,
        }

    def health_check(self) -> bool:
        return True

    def get_model_info(self) -> dict:
        return {"model_id": "fake-model", "provider": "test"}


class TestExtractionWorker:
    """ExtractionWorker 测试套件"""

    def test_execute_returns_success_result(self, tmp_path):
        """测试成功提取返回成功结果"""
        # 准备模板
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)

        # 准备假 LLM 响应
        fake_response = json.dumps({
            "indicator_id": "IND-01",
            "name_cn": "体脂率",
            "unit": "%",
            "statistics": {
                "p5": 10.0, "p25": 15.0, "p50": 20.0,
                "p75": 25.0, "p95": 30.0,
                "mean": 20.5, "sd": 5.0, "n_subjects": 100,
            },
            "extraction_confidence": 0.9,
        })
        adapter = FakeModelAdapter(fake_response)
        worker = ExtractionWorker(adapter, lib)

        brief = TaskBrief(
            task_id="task-001",
            task_type="extraction",
            indicator_id="IND-01",
            literature_text="某文献",
            prompt_template="extract_reference_range",
        )
        result = worker.execute(brief)
        assert result.success is True
        assert result.data["indicator_id"] == "IND-01"
        assert result.confidence == 0.9
        assert result.model_used == "fake-model"

    def test_execute_returns_failure_on_invalid_json(self, tmp_path):
        """测试 LLM 返回非法 JSON 时返回失败结果"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)

        adapter = FakeModelAdapter("这不是合法的 JSON")
        worker = ExtractionWorker(adapter, lib)

        brief = TaskBrief(
            task_id="task-002",
            task_type="extraction",
            indicator_id="IND-01",
            literature_text="某文献",
            prompt_template="extract_reference_range",
        )
        result = worker.execute(brief)
        assert result.success is False
        assert len(result.errors) > 0


class TestValidationWorker:
    """ValidationWorker 测试套件"""

    def test_execute_valid_data_returns_accepted(self):
        """测试合法数据通过验证"""
        from scripts.llm.workers import ValidationWorker
        from scripts.llm.task_types import TaskResult

        validator = DualLayerValidator()
        worker = ValidationWorker(validator)

        result = TaskResult(
            task_id="task-001",
            success=True,
            data={
                "indicator_id": "IND-01",
                "name_cn": "体脂率",
                "unit": "%",
                "statistics": {
                    "p5": 10.0, "p25": 15.0, "p50": 20.0,
                    "p75": 25.0, "p95": 30.0,
                    "mean": 20.5, "sd": 5.0, "n_subjects": 100,
                },
                "extraction_confidence": 0.9,
            },
            confidence=0.9,
        )
        validated = worker.execute(result, "IND-01")
        assert validated.success is True
        assert validated.confidence == 0.9

    def test_execute_invalid_data_returns_rejected(self):
        """测试非法数据被拒绝"""
        from scripts.llm.workers import ValidationWorker
        from scripts.llm.task_types import TaskResult

        validator = DualLayerValidator()
        worker = ValidationWorker(validator)

        result = TaskResult(
            task_id="task-002",
            success=True,
            data={"indicator_id": "IND-01"},  # 缺少必填字段
            confidence=0.3,
        )
        validated = worker.execute(result, "IND-01")
        assert validated.success is False
        assert len(validated.errors) > 0
