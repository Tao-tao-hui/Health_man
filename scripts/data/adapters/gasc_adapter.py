"""GASC 2025 PDF 附录专用提取器

GASC（Global Adult Size Chart）2025 是 PMID:40620559 的附录数据，
包含全球成人人体测量参考值。

本提取器专门处理 GASC 2025 PDF 的表格结构，
提取指标参考范围（BMI、体脂率、内脏脂肪等）。
基于 Task 3 实现的 PdfTableExtractor，通过组合方式复用其表格检测能力，
并在其上叠加 GASC 特定的字段解析与元数据生成逻辑。
"""
import logging
from pathlib import Path
from typing import Any

from scripts.data.pdf_extractor import PdfTableExtractor

logger = logging.getLogger(__name__)


class GascPdfExtractor:
    """GASC 2025 PDF 附录专用提取器

    基于 PdfTableExtractor，增加 GASC 特定的表格解析逻辑：
    - 识别 GASC 附录表格的列结构（Indicator/Male Mean/Female Mean/Reference Range）
    - 将每行转为结构化指标字典
    - 生成 GASC L0 元数据模板

    采用组合而非继承，避免暴露 PdfTableExtractor 的底层 API，
    仅对外暴露 GASC 语义化的 extract / get_metadata_template 方法。
    """

    # GASC 2025 文献标识
    PMID = "40620559"
    DATASET_ID = "GASC_2025"

    def __init__(self) -> None:
        # 组合 PdfTableExtractor，复用其 find_tables 检测能力
        self.table_extractor = PdfTableExtractor()

    def extract(self, pdf_path: Path) -> dict[str, Any]:
        """从 GASC 2025 PDF 提取指标参考范围

        Args:
            pdf_path: GASC 2025 PDF 文件路径

        Returns:
            含以下键的字典:
            - indicators: 指标参考范围列表，每项含 name/male_mean/female_mean/reference_range
            - source_pages: 数据来源页码列表（与表格所在页对应）
            - source: 数据来源标识（"GASC_2025"）

        Raises:
            FileNotFoundError: 当 pdf_path 指向的文件不存在时
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"GASC PDF 文件不存在: {pdf_path}")

        # 复用 Task 3 的 PdfTableExtractor 检测视觉表格
        tables = self.table_extractor.extract_tables(pdf_path)
        indicators: list[dict[str, Any]] = []
        source_pages: list[int] = []

        for table in tables:
            rows = table["rows"]
            page_num = table["page_number"]
            source_pages.append(page_num)

            # 尝试匹配 GASC 表格结构
            # 预期列顺序：Indicator, Male Mean, Female Mean, Reference Range
            # 此处不强制校验 headers 文本，避免受表头细微差异影响；
            # 仅要求行至少 4 列，按位置提取
            for row in rows:
                if len(row) < 4:
                    continue
                indicators.append({
                    "name": str(row[0]).strip() if row[0] else "",
                    "male_mean": self._parse_numeric(row[1]),
                    "female_mean": self._parse_numeric(row[2]),
                    "reference_range": str(row[3]).strip() if row[3] else "",
                })

        logger.info(
            "GASC 2025 提取完成: %d 个指标，%d 页",
            len(indicators), len(source_pages),
        )
        return {
            "indicators": indicators,
            "source_pages": source_pages,
            "source": self.DATASET_ID,
        }

    def get_metadata_template(self) -> dict[str, Any]:
        """返回 GASC 2025 的 L0 元数据模板

        模板字段遵循 Layer B 数据治理 L0 规范，
        用于在 Layer A/B 元数据登记中标识 GASC 数据集。
        """
        return {
            "dataset_id": self.DATASET_ID,
            "pmid": self.PMID,
            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{self.PMID}/",
            "license": "Open Access（CC-BY）",
            "region": "Global",
            "sample_size": 0,  # 由实际提取结果填充
            "cycle": "2025",
            "update_frequency": "不定期（随论文发布）",
            "population": "全球成人（含中国子集）",
            "known_bias": "样本以欧美人群为主，中国子集较小",
            "feasibility_score": 3.90,
        }

    def _parse_numeric(self, value: Any) -> float | None:
        """尝试将值解析为浮点数

        GASC 表格中数值列可能含空字符串或非数值文本，
        无法解析时返回 None，避免抛出异常中断整体提取流程。
        """
        if value is None:
            return None
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            return None
