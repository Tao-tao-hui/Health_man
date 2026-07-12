"""ModelAdapter 抽象基类单元测试

验证抽象基类定义和方法签名。
镜像 Phase 1-2 的 SourceAdapter 设计模式。
"""
import pytest
from abc import ABC

from scripts.llm.model_adapter import ModelAdapter


class TestModelAdapter:
    """ModelAdapter 抽象基类测试套件"""

    def test_model_adapter_is_abstract_class(self):
        """测试 ModelAdapter 是抽象基类，无法直接实例化"""
        with pytest.raises(TypeError, match="abstract"):
            ModelAdapter()

    def test_model_adapter_inherits_from_abc(self):
        """测试 ModelAdapter 继承自 ABC"""
        assert issubclass(ModelAdapter, ABC)

    def test_complete_subclass_can_instantiate(self):
        """测试实现全部抽象方法的子类可以实例化"""

        class FakeModelAdapter(ModelAdapter):
            """用于测试的完整实现"""

            def chat(self, prompt: str, system: str | None = None) -> dict:
                return {
                    "content": "模拟响应",
                    "tokens_used": 100,
                    "model_id": "fake-model",
                    "latency_ms": 50,
                }

            def health_check(self) -> bool:
                return True

            def get_model_info(self) -> dict:
                return {"model_id": "fake-model", "provider": "test"}

        adapter = FakeModelAdapter()
        result = adapter.chat("测试提示词")
        assert result["content"] == "模拟响应"
        assert result["tokens_used"] == 100
        assert adapter.health_check() is True
        assert adapter.get_model_info()["model_id"] == "fake-model"

    def test_incomplete_subclass_raises_type_error(self):
        """测试未实现全部抽象方法的子类无法实例化"""

        class IncompleteAdapter(ModelAdapter):
            """缺少 health_check 实现"""
            def chat(self, prompt: str, system: str | None = None) -> dict:
                return {}
            def get_model_info(self) -> dict:
                return {}

        with pytest.raises(TypeError, match="abstract"):
            IncompleteAdapter()
