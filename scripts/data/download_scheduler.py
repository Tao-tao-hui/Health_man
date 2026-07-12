"""下载调度器

职责：
- 调度并发下载（asyncio + ThreadPoolExecutor）
- 体量控制（超限自动跳过）
- 重试退避（指数退避）
- 返回下载结果（含耗时、成功标志、错误信息）

不负责：
- 格式转换（由 FormatConverter 负责）
- 质量校验（由 QualityChecker 负责）
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.data.source_adapter import SourceAdapter

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """单个文件下载结果"""
    filename: str
    path: Path | None
    success: bool
    error_message: str = ""
    duration_seconds: float = 0.0
    file_size_bytes: int = 0


class DownloadScheduler:
    """下载调度器

    Args:
        max_concurrent: 最大并发数
        max_size_mb: 单文件大小上限（MB）
        max_retries: 最大重试次数
        base_delay: 退避基础延迟（秒）
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        max_size_mb: int = 500,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        self.max_concurrent = max_concurrent
        self.max_size_mb = max_size_mb
        self.max_retries = max_retries
        self.base_delay = base_delay
        # max_file_size_bytes 用于测试中精细调整（生产中由 max_size_mb 派生）
        self.max_file_size_bytes = max_size_mb * 1024 * 1024

    def schedule_download(
        self,
        adapter: SourceAdapter,
        dest_dir: Path,
    ) -> list[DownloadResult]:
        """调度下载所有文件

        Args:
            adapter: 数据源适配器
            dest_dir: 目标目录

        Returns:
            下载结果列表（与 list_files 顺序一致）
        """
        files = adapter.list_files()
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        results: list[DownloadResult] = []
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            future_to_file = {
                executor.submit(self._download_with_retry, adapter, f, dest_dir): f
                for f in files
            }
            for future in as_completed(future_to_file):
                file_meta = future_to_file[future]
                try:
                    result = future.result()
                except Exception as e:
                    logger.exception("下载 %s 时发生未捕获异常", file_meta["filename"])
                    result = DownloadResult(
                        filename=file_meta["filename"],
                        path=None,
                        success=False,
                        error_message=str(e),
                    )
                results.append(result)

        # 按原始顺序排序
        filename_order = [f["filename"] for f in files]
        results.sort(key=lambda r: filename_order.index(r.filename))
        return results

    def _download_with_retry(
        self,
        adapter: SourceAdapter,
        file_meta: dict[str, Any],
        dest_dir: Path,
    ) -> DownloadResult:
        """带重试的下载单个文件"""
        filename = file_meta["filename"]
        expected_size = file_meta.get("expected_size_bytes", 0)

        # 体量检查
        if expected_size > self.max_file_size_bytes:
            return DownloadResult(
                filename=filename,
                path=None,
                success=False,
                error_message=f"文件大小 {expected_size} bytes exceeds size limit {self.max_file_size_bytes} bytes",
            )

        last_error = ""
        for attempt in range(self.max_retries + 1):
            start_time = time.monotonic()
            try:
                path = adapter.download(file_meta, dest_dir)
                duration = time.monotonic() - start_time
                actual_size = path.stat().st_size if path.exists() else 0
                logger.info("下载成功: %s (%d bytes, %.2fs)", filename, actual_size, duration)
                return DownloadResult(
                    filename=filename,
                    path=path,
                    success=True,
                    duration_seconds=duration,
                    file_size_bytes=actual_size,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "下载失败 (attempt %d/%d): %s - %s",
                    attempt + 1,
                    self.max_retries + 1,
                    filename,
                    last_error,
                )
                if attempt < self.max_retries:
                    # 指数退避
                    delay = self.base_delay * (2**attempt)
                    time.sleep(delay)

        return DownloadResult(
            filename=filename,
            path=None,
            success=False,
            error_message=f"重试 {self.max_retries} 次后仍失败: {last_error}",
        )
