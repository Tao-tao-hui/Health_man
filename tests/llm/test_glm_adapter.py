"""GlmAdapter 单元测试

验证 GLM-4-Flash 模型适配器实现。
使用 mock 模拟 HTTP 请求，避免真实 API 调用。
"""
from unittest.mock import MagicMock, patch

from scripts.llm.glm_adapter import GlmAdapter


class TestGlmAdapter:
    """GlmAdapter 测试套件"""

    def test_chat_returns_expected_dict(self):
        """测试 chat 返回包含必要字段的字典"""
        adapter = GlmAdapter(api_key="fake-key")
        mock_response = {
            "choices": [{"message": {"content": '{"indicator_id": "test"}'}}],
            "usage": {"total_tokens": 150},
            "model": "glm-4-flash",
        }
        with patch("scripts.llm.glm_adapter.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            result = adapter.chat("提取参考范围")
        assert "content" in result
        assert "tokens_used" in result
        assert "model_id" in result
        assert "latency_ms" in result
        assert result["tokens_used"] == 150
        assert result["model_id"] == "glm-4-flash"

    def test_health_check_returns_true_on_success(self):
        """测试健康检查在模型可用时返回 True"""
        adapter = GlmAdapter(api_key="fake-key")
        with patch("scripts.llm.glm_adapter.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert adapter.health_check() is True

    def test_health_check_returns_false_on_failure(self):
        """测试健康检查在模型不可用时返回 False"""
        adapter = GlmAdapter(api_key="fake-key")
        with patch("scripts.llm.glm_adapter.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=500)
            assert adapter.health_check() is False

    def test_get_model_info_returns_dict(self):
        """测试 get_model_info 返回模型信息"""
        adapter = GlmAdapter(api_key="fake-key")
        info = adapter.get_model_info()
        assert info["model_id"] == "glm-4-flash"
        assert info["provider"] == "zhipu"
        assert "context_length" in info
        assert "max_tokens" in info
