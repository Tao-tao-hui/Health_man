"""子代理间通信数据结构

定义 TaskBrief（任务指令）和 TaskResult（任务结果），
用于 MasterOrchestrator 与 Worker 之间的通信。
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskBrief:
    """任务指令（Master → Worker）

    Attributes:
        task_id: 任务唯一标识
        task_type: 任务类型（extraction / validation / aggregation）
        indicator_id: 目标指标 ID
        literature_text: 文献文本片段
        prompt_template: 提示词模板名
        few_shot_examples: Few-shot 示例列表
        model_hint: 模型偏好（可选，如 "glm" / "kimi"）
    """
    task_id: str
    task_type: str
    indicator_id: str
    literature_text: str
    prompt_template: str
    few_shot_examples: list[dict[str, Any]] = field(default_factory=list)
    model_hint: str | None = None


@dataclass
class TaskResult:
    """任务结果（Worker → Master）

    Attributes:
        task_id: 任务唯一标识（与 TaskBrief 对应）
        success: 是否成功
        data: 提取的结构化数据（成功时）
        confidence: 置信度 0-1
        errors: 错误信息列表（失败时）
        model_used: 实际使用的模型 ID
        tokens_consumed: token 消耗量
        latency_ms: 延迟毫秒
    """
    task_id: str
    success: bool
    data: dict[str, Any] | None = None
    confidence: float = 0.0
    errors: list[str] = field(default_factory=list)
    model_used: str = ""
    tokens_consumed: int = 0
    latency_ms: int = 0
