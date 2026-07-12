"""Layer C 端到端流水线

整合：主代理调度 → 提取子代理 → 验证子代理 → 存储 → 审计 → 元数据
流水线步骤：
1. MasterOrchestrator 调度提取+验证
2. 通过验证的数据写入 C_llm_distilled/
3. 审计日志记录（哈希链防篡改）
4. 体量审计（500MB 上限）
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.llm.master_orchestrator import MasterOrchestrator
from scripts.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclass
class LlmPipelineResult:
    """流水线执行结果"""
    success: bool
    total_extracted: int = 0
    total_validated: int = 0
    total_rejected: int = 0
    total_tokens_consumed: int = 0
    errors: list[str] = field(default_factory=list)


class LlmPipeline:
    """Layer C 端到端流水线

    Args:
        master: 主代理
        max_size_mb: 体量上限（MB），默认 500
        audit_log_path: 审计日志路径
    """

    def __init__(
        self,
        master: MasterOrchestrator,
        max_size_mb: int = 500,
        audit_log_path: Path | None = None,
    ):
        self.master = master
        self.max_size_bytes = max_size_mb * 1024 * 1024
        default_audit_path = Path(
            "data/knowledge/chinese_reference/C_llm_distilled/_logs/llm_audit_log.jsonl"
        )
        self.audit_logger = AuditLogger(audit_log_path or default_audit_path)

    def run(
        self,
        tasks: list[dict[str, Any]],
        dest_dir: Path,
    ) -> LlmPipelineResult:
        """执行完整蒸馏流水线

        Args:
            tasks: 任务列表
            dest_dir: 目标存储目录

        Returns:
            流水线执行结果
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # 阶段 1: 主代理调度提取+验证
        try:
            master_result = self.master.run(tasks)
        except Exception as e:
            error_msg = f"主代理调度失败: {e}"
            logger.error(error_msg)
            return LlmPipelineResult(success=False, errors=[error_msg])

        # 阶段 2: 存储通过验证的数据
        results = master_result.get("results", [])
        total_extracted = master_result["total_tasks"]
        total_validated = 0
        total_rejected = 0
        errors: list[str] = []

        for result in results:
            if result.success and result.data:
                # 按 indicator_id 组织存储
                indicator_id = result.data.get("indicator_id", "unknown")
                output_path = dest_dir / f"{indicator_id}_distilled.json"
                try:
                    # 追加模式写入（同一指标可能多文献）
                    existing = []
                    if output_path.exists():
                        existing = json.loads(output_path.read_text(encoding="utf-8"))
                        if not isinstance(existing, list):
                            existing = [existing]
                    existing.append(result.data)
                    output_path.write_text(
                        json.dumps(existing, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    total_validated += 1
                    # 记录审计日志
                    self.audit_logger.log(
                        operation="llm_distill",
                        target=str(output_path),
                        success=True,
                        confidence=result.confidence,
                        model=result.model_used,
                    )
                except Exception as e:
                    errors.append(f"存储失败 {indicator_id}: {e}")
            else:
                total_rejected += 1
                self.audit_logger.log(
                    operation="llm_distill",
                    target=result.task_id,
                    success=False,
                    errors=result.errors,
                )

        # 阶段 3: 体量审计
        audit = self.audit_size(dest_dir)
        if not audit["within_limit"]:
            errors.append(
                f"体量超限: {audit['total_bytes']} > {self.max_size_bytes}"
            )

        success = total_rejected == 0 and audit["within_limit"] and len(errors) == 0
        logger.info(
            "Layer C 流水线完成: extracted=%d, validated=%d, rejected=%d, tokens=%d",
            total_extracted, total_validated, total_rejected,
            master_result["total_tokens_consumed"],
        )

        return LlmPipelineResult(
            success=success,
            total_extracted=total_extracted,
            total_validated=total_validated,
            total_rejected=total_rejected,
            total_tokens_consumed=master_result["total_tokens_consumed"],
            errors=errors,
        )

    def audit_size(self, dest_dir: Path) -> dict[str, Any]:
        """体量审计

        Returns:
            含 total_bytes, total_mb, limit_mb, within_limit 的字典
        """
        dest_dir = Path(dest_dir)
        total_bytes = 0
        if dest_dir.exists():
            for file_path in dest_dir.rglob("*"):
                if file_path.is_file():
                    total_bytes += file_path.stat().st_size

        total_mb = total_bytes / (1024 * 1024)
        limit_mb = self.max_size_bytes / (1024 * 1024)
        within_limit = total_bytes <= self.max_size_bytes

        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_mb, 2),
            "limit_mb": limit_mb,
            "within_limit": within_limit,
        }
