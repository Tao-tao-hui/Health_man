"""TaskBrief 与 TaskResult 数据结构测试

验证子代理间通信的数据结构定义。
"""
from scripts.llm.task_types import TaskBrief, TaskResult


class TestTaskTypes:
    """任务数据结构测试套件"""

    def test_task_brief_creation(self):
        """测试 TaskBrief 创建"""
        brief = TaskBrief(
            task_id="task-001",
            task_type="extraction",
            indicator_id="IND-01",
            literature_text="某文献内容",
            prompt_template="extract_reference_range",
            few_shot_examples=[{"input": "a", "output": "b"}],
        )
        assert brief.task_id == "task-001"
        assert brief.task_type == "extraction"
        assert brief.indicator_id == "IND-01"
        assert brief.literature_text == "某文献内容"
        assert brief.prompt_template == "extract_reference_range"
        assert len(brief.few_shot_examples) == 1

    def test_task_result_success(self):
        """测试 TaskResult 成功状态"""
        result = TaskResult(
            task_id="task-001",
            success=True,
            data={"indicator_id": "IND-01"},
            confidence=0.9,
            model_used="glm-4-flash",
            tokens_consumed=150,
            latency_ms=500,
        )
        assert result.success is True
        assert result.data["indicator_id"] == "IND-01"
        assert result.confidence == 0.9
        assert len(result.errors) == 0

    def test_task_result_failure_with_errors(self):
        """测试 TaskResult 失败状态含错误"""
        result = TaskResult(
            task_id="task-002",
            success=False,
            errors=["JSON parse Error", "timeout"],
        )
        assert result.success is False
        assert result.data is None
        assert len(result.errors) == 2
