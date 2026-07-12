"""主代理（MasterOrchestrator）

职责：调度子代理执行蒸馏任务，聚合结果。
设计模式：Master-Worker，主代理统一调度，子代理并行执行。
"""
import logging
import uuid
from typing import Any

from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.task_types import TaskBrief, TaskResult
from scripts.llm.validator import DualLayerValidator
from scripts.llm.workers import ExtractionWorker, ValidationWorker
from scripts.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """主代理

    Args:
        model_adapter: LLM 模型适配器
        prompt_library: 提示词模板库
        validator: 双层验证器
        audit_logger: 审计日志器（可选）
    """

    def __init__(
        self,
        model_adapter: ModelAdapter,
        prompt_library: PromptTemplateLibrary,
        validator: DualLayerValidator,
        audit_logger: AuditLogger | None = None,
    ):
        self.model_adapter = model_adapter
        self.prompt_library = prompt_library
        self.validator = validator
        self.audit_logger = audit_logger

    def dispatch_extraction(
        self,
        indicator_id: str,
        literature_texts: list[str],
        prompt_template: str = "extract_reference_range",
    ) -> list[TaskResult]:
        """分发提取任务到 ExtractionWorker

        Args:
            indicator_id: 目标指标 ID
            literature_texts: 文献文本列表
            prompt_template: 提示词模板名

        Returns:
            提取结果列表
        """
        worker = ExtractionWorker(
            self.model_adapter, self.prompt_library, self.audit_logger
        )
        results: list[TaskResult] = []
        for text in literature_texts:
            brief = TaskBrief(
                task_id=str(uuid.uuid4()),
                task_type="extraction",
                indicator_id=indicator_id,
                literature_text=text,
                prompt_template=prompt_template,
            )
            result = worker.execute(brief)
            results.append(result)
        return results

    def dispatch_validation(
        self,
        extraction_results: list[TaskResult],
        indicator_id: str,
    ) -> list[TaskResult]:
        """分发验证任务到 ValidationWorker

        Args:
            extraction_results: 提取结果列表
            indicator_id: 指标 ID

        Returns:
            验证后结果列表
        """
        worker = ValidationWorker(self.validator, self.audit_logger)
        validated: list[TaskResult] = []
        for result in extraction_results:
            v_result = worker.execute(result, indicator_id)
            validated.append(v_result)
        return validated

    def run(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """执行完整蒸馏流程

        Args:
            tasks: 任务列表，每个任务含 indicator_id, literature_texts, prompt_template

        Returns:
            含 total_tasks, successful, failed, results 的聚合结果
        """
        all_results: list[TaskResult] = []
        for task in tasks:
            indicator_id = task["indicator_id"]
            texts = task["literature_texts"]
            template = task.get("prompt_template", "extract_reference_range")

            # 阶段 1: 提取
            extracted = self.dispatch_extraction(indicator_id, texts, template)
            # 阶段 2: 验证
            validated = self.dispatch_validation(extracted, indicator_id)
            all_results.extend(validated)

        successful = sum(1 for r in all_results if r.success)
        failed = len(all_results) - successful
        total_tokens = sum(r.tokens_consumed for r in all_results)

        logger.info(
            "蒸馏完成: total=%d, success=%d, failed=%d, tokens=%d",
            len(all_results), successful, failed, total_tokens,
        )

        return {
            "total_tasks": len(all_results),
            "successful": successful,
            "failed": failed,
            "total_tokens_consumed": total_tokens,
            "results": all_results,
        }
