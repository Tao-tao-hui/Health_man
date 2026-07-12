"""LLM 模型适配器抽象基类

所有具体模型适配器（GlmAdapter/QwenAdapter/DeepSeekAdapter 等）必须继承本类
并实现全部抽象方法。
设计目标：插件式扩展，新增模型仅需实现接口，无需修改既有代码。
镜像 Phase 1-2 的 SourceAdapter 设计模式。
"""
from abc import ABC, abstractmethod
from typing import Any


class ModelAdapter(ABC):
    """LLM 模型适配器抽象基类

    子类必须实现以下 3 个方法：
    - chat(): 调用 LLM 进行对话
    - health_check(): 检查模型是否可用
    - get_model_info(): 返回模型元信息
    """

    @abstractmethod
    def chat(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        """调用 LLM 进行对话

        Args:
            prompt: 用户提示词
            system: 系统提示词（可选）

        Returns:
            含以下字段的字典：
            - content: str — LLM 响应文本
            - tokens_used: int — 消耗的 token 总数
            - model_id: str — 实际使用的模型 ID
            - latency_ms: int — 响应延迟（毫秒）
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """检查模型是否可用

        Returns:
            模型是否健康可用
        """
        ...

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            含 model_id, provider, max_tokens, context_length 等字段的字典
        """
        ...
