"""格式转换器

职责：
- XPT (SAS Transport) → Parquet + Snappy
- CSV (GBK/UTF-8) → Parquet + Snappy
- PDF 表格 → JSON（后续任务）

设计原则：
- 单一职责：仅负责格式转换，不做数据清洗
- 保留原始字段名（标准化由 Preprocessor 负责）
- 转换后记录行数与列数到日志（不在此处断言，由 QualityChecker 负责校验）
"""
import logging
from pathlib import Path

import pandas as pd
import pyreadstat

logger = logging.getLogger(__name__)


class FormatConverter:
    """格式转换器

    将各种源格式统一转换为 Parquet + Snappy 压缩格式。
    """

    def convert_xpt_to_parquet(
        self,
        xpt_path: Path,
        output_path: Path,
    ) -> Path:
        """将 SAS XPT 文件转换为 Parquet

        Args:
            xpt_path: XPT 文件路径
            output_path: 输出 Parquet 文件路径

        Returns:
            输出文件路径

        Raises:
            ValueError: XPT 文件无法解析
        """
        xpt_path = Path(xpt_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not xpt_path.exists():
            raise FileNotFoundError(f"XPT 文件不存在: {xpt_path}")

        try:
            df, meta = pyreadstat.read_xport(str(xpt_path))
        except Exception as e:
            raise ValueError(f"XPT 文件解析失败 {xpt_path}: {e}") from e

        logger.info(
            "XPT 转换: %s → %s (%d 行 %d 列)",
            xpt_path.name,
            output_path.name,
            len(df),
            len(df.columns),
        )

        df.to_parquet(output_path, compression="snappy", index=False)
        return output_path

    def convert_csv_to_parquet(
        self,
        csv_path: Path,
        output_path: Path,
        encoding: str = "utf-8",
    ) -> Path:
        """将 CSV 文件转换为 Parquet

        Args:
            csv_path: CSV 文件路径
            output_path: 输出 Parquet 文件路径
            encoding: 文件编码（默认 utf-8，中文文件可能需要 gbk）

        Returns:
            输出文件路径
        """
        csv_path = Path(csv_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

        df = pd.read_csv(csv_path, encoding=encoding)
        logger.info(
            "CSV 转换: %s → %s (%d 行 %d 列, encoding=%s)",
            csv_path.name,
            output_path.name,
            len(df),
            len(df.columns),
            encoding,
        )

        df.to_parquet(output_path, compression="snappy", index=False)
        return output_path
