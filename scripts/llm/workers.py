"""子代理模块

ExtractionWorker: 提取子代理，调用 LLM API 提取结构化数据
ValidationWorker: 验证子代理，执行双层验证
"""
import json
import logging

from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.task_types import TaskBrief, TaskResult
from scripts.llm.validator import DualLayerValidator, ValidationResult
from scripts.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class ExtractionWorker:
    """提取子代理

    职责：调用 LLM API 提取结构化医学数据
    输入：TaskBrief（含文献文本 + 提示词模板）
    输出：TaskResult（含提取的结构化数据 + confidence）
    """

    def __init__(
        self,
        model_adapter: ModelAdapter,
        prompt_library: PromptTemplateLibrary,
        audit_logger: AuditLogger | None = None,
    ):
        self.model_adapter = model_adapter
        self.prompt_library = prompt_library
        self.audit_logger = audit_logger

    def execute(self, brief: TaskBrief) -> TaskResult:
        """执行提取任务

        Args:
            brief: 任务指令

        Returns:
            任务结果
        """
        try:
            # 渲染提示词模板
            prompt = self.prompt_library.render(
                brief.prompt_template,
                indicator_id=brief.indicator_id,
                literature_text=brief.literature_text,
            )

            # 调用 LLM
            response = self.model_adapter.chat(prompt)
            content = response["content"]

            # 解析 JSON
            data = json.loads(content)
            confidence = data.get("extraction_confidence", 0.0)

            logger.info(
                "提取成功: task=%s, confidence=%.2f, tokens=%d",
                brief.task_id, confidence, response["tokens_used"],
            )

            return TaskResult(
                task_id=brief.task_id,
                success=True,
                data=data,
                confidence=confidence,
                model_used=response["model_id"],
                tokens_consumed=response["tokens_used"],
                latency_ms=response["latency_ms"],
            )

        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {e}"
            logger.error(error_msg)
            return TaskResult(
                task_id=brief.task_id,
                success=False,
                errors=[error_msg],
                model_used=getattr(self.model_adapter, "get_model_info", lambda: {})().get("model_id", "unknown"),
            )
        except Exception as e:
            error_msg = f"提取失败: {e}"
            logger.error(error_msg)
            return TaskResult(
                task_id=brief.task_id,
                success=False,
                errors=[error_msg],
            )


class ValidationWorker:
    """验证子代理

    职责：对提取结果执行双层验证（结构化 + 语义）
    输入：TaskResult（含提取的数据）
    输出：TaskResult（含验证结果 + 调整后的 confidence）
    """

    def __init__(
        self,
        validator: DualLayerValidator,
        audit_logger: AuditLogger | None = None,
    ):
        self.validator = validator
        self.audit_logger = audit_logger

    def execute(self, result: TaskResult, indicator_id: str) -> TaskResult:
        """执行验证任务

        Args:
            result: 提取子代理返回的结果
            indicator_id: 指标 ID（用于语义校验范围查找）

        Returns:
            验证后的任务结果
        """
        # 如果提取本身就失败，直接返回
        if not result.success or result.data is None:
            return result

        # 执行双层验证
        validation = self.validator.validate(result.data, indicator_id)

        # 记录审计日志
        if self.audit_logger:
            self.audit_logger.log(
                operation="validation",
                target=indicator_id,
                success=validation.is_valid,
                confidence=validation.confidence,
                action=validation.action,
            )

        if validation.is_valid:
            logger.info(
                "验证通过: task=%s, confidence=%.2f, action=%s",
                result.task_id, validation.confidence, validation.action,
            )
            return TaskResult(
                task_id=result.task_id,
                success=True,
                data=result.data,
                confidence=validation.confidence,
                model_used=result.model_used,
                tokens_consumed=result.tokens_consumed,
                latency_ms=result.latency_ms,
            )
        else:
            logger.warning(
                "验证失败: task=%s, errors=%s",
                result.task_id, validation.errors,
            )
            return TaskResult(
                task_id=result.task_id,
                success=False,
                data=result.data,
                confidence=validation.confidence,
                errors=validation.errors,
                model_used=result.model_used,
                tokens_consumed=result.tokens_consumed,
                latency_ms=result.latency_ms,
            )
