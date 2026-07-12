"""Layer B 端到端流水线

整合检索 → 下载 → 提取 → 校验 → 存储 → 审计全流程。

流水线步骤：
1. 通过 adapter.list_files() 检索文献/数据集
2. 下载文件到 dest_dir
3. 校验文件完整性
4. 体量审计（500MB 上限）
5. 记录到提取日志
6. 生成三层元数据
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.data.extraction_log import ExtractionLogManager
from scripts.data.literature_metadata_generator import LiteratureMetadataGenerator
from scripts.data.quality_checker import QualityChecker, QualityReport
from scripts.data.source_adapter import SourceAdapter
from scripts.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """流水线执行结果"""
    success: bool
    downloaded_count: int = 0
    failed_count: int = 0
    total_bytes: int = 0
    quality_report: QualityReport | None = None
    errors: list[str] = field(default_factory=list)


class LayerBPipeline:
    """Layer B 端到端流水线

    Args:
        max_size_mb: 体量上限（MB），默认 500
        log_manager: 提取日志管理器（可选）
        metadata_generator: 元数据生成器（可选）
    """

    def __init__(
        self,
        max_size_mb: int = 500,
        log_manager: ExtractionLogManager | None = None,
        metadata_generator: LiteratureMetadataGenerator | None = None,
        audit_log_path: Path | None = None,
    ):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.log_manager = log_manager or ExtractionLogManager()
        self.metadata_generator = metadata_generator or LiteratureMetadataGenerator()
        self.quality_checker = QualityChecker()
        # 审计日志器（防篡改哈希链，默认写入 B_literature/_logs/audit.jsonl）
        default_audit_path = Path(
            "e:/Health_man/data/knowledge/chinese_reference/B_literature/_logs/audit.jsonl"
        )
        self.audit_logger = AuditLogger(audit_log_path or default_audit_path)

    def run(self, adapter: SourceAdapter, dest_dir: Path) -> PipelineResult:
        """执行完整流水线

        Args:
            adapter: 数据源适配器
            dest_dir: 目标存储目录

        Returns:
            流水线执行结果
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        errors: list[str] = []
        downloaded_count = 0
        failed_count = 0
        total_bytes = 0

        # Step 1: 检索文件列表
        try:
            files = adapter.list_files()
            logger.info("检索到 %d 个文件", len(files))
        except Exception as e:
            error_msg = f"检索失败: {e}"
            logger.error(error_msg)
            return PipelineResult(success=False, errors=[error_msg])

        # Step 2: 逐个下载
        for file_meta in files:
            try:
                file_path = adapter.download(file_meta, dest_dir)
                file_size = file_path.stat().st_size
                total_bytes += file_size
                downloaded_count += 1
                logger.info("下载成功: %s (%d bytes)", file_meta.get("filename", ""), file_size)

                # 记录到提取日志
                self.log_manager.add_entry(
                    pmid=str(file_meta.get("pmid", file_meta.get("filename", ""))),
                    title=file_meta.get("title", ""),
                    source=adapter.__class__.__name__,
                )
                # 记录审计日志（防篡改哈希链）
                self.audit_logger.log(
                    operation="download",
                    target=str(file_path),
                    success=True,
                    source=adapter.__class__.__name__,
                    filename=file_meta.get("filename", ""),
                    size_bytes=file_size,
                )
            except Exception as e:
                failed_count += 1
                error_msg = f"下载失败 {file_meta.get('filename', '')}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                # 记录审计日志（防篡改哈希链）
                self.audit_logger.log(
                    operation="download",
                    target=file_meta.get("filename", ""),
                    success=False,
                    source=adapter.__class__.__name__,
                    error=str(e),
                )

        # Step 3: 体量审计
        audit = self.audit_size(dest_dir)
        if not audit["within_limit"]:
            error_msg = f"体量超限: {audit['total_bytes']} > {self.max_size_bytes}"
            errors.append(error_msg)
            logger.error(error_msg)

        # Step 4: 保存提取日志
        try:
            self.log_manager.save()
        except Exception as e:
            errors.append(f"日志保存失败: {e}")

        # Step 5: 生成元数据
        # Layer B 文献为 XML/PDF 格式，需后续 PdfTableExtractor 处理才能得到结构化 DataFrame
        # 此处跳过质量校验（quality_report 保持 None），待提取后由独立流程填充
        quality_report = None
        try:
            adapter_meta = adapter.get_metadata_template()
            logger.info("跳过质量校验：文献数据待 PdfTableExtractor 提取后填充")
            self.metadata_generator.generate_l0(
                adapter_meta, quality_report,
                output_path=dest_dir / "_metadata" / "L0_card.json"
            )
        except Exception as e:
            errors.append(f"元数据生成失败: {e}")

        success = failed_count == 0 and audit["within_limit"]
        return PipelineResult(
            success=success,
            downloaded_count=downloaded_count,
            failed_count=failed_count,
            total_bytes=total_bytes,
            quality_report=quality_report,
            errors=errors,
        )

    def audit_size(self, dest_dir: Path) -> dict[str, Any]:
        """体量审计

        Args:
            dest_dir: 目标目录

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

        logger.info("体量审计: %.2f MB / %.2f MB (within_limit=%s)",
                     total_mb, limit_mb, within_limit)

        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_mb, 2),
            "limit_mb": limit_mb,
            "within_limit": within_limit,
        }
