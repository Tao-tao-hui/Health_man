"""PDF 表格提取器

使用 PyMuPDF (fitz) 从 PDF 文件中提取表格数据。
输出结构化 JSON 或 pandas DataFrame。

适用场景：
- GASC 2025 附录表格提取
- 中华医学会指南 PDF 表格提取
- PubMed 全文 PDF 表格提取
"""
import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pandas as pd

logger = logging.getLogger(__name__)


class PdfTableExtractor:
    """PDF 表格提取器

    使用 PyMuPDF 的 find_tables() API 检测页面中的表格区域，
    并将其转换为结构化数据（dict 列表或 pandas DataFrame）。

    find_tables() 返回 TableFinder 对象（可迭代，每次迭代产出一个 Table），
    每个 Table 通过 extract() 方法返回二维列表（行为列表，列为单元格值）。
    """

    def extract_tables(self, pdf_path: Path) -> list[dict[str, Any]]:
        """从 PDF 提取所有表格

        遍历 PDF 每一页，调用 find_tables() 检测视觉表格结构
        （依赖表格边框线），将每个表格转为结构化 dict。

        Args:
            pdf_path: PDF 文件路径

        Returns:
            表格列表，每个表格含:
            - page_number: 页码（从 0 开始）
            - table_index: 该页内表格序号（从 0 开始）
            - headers: 列名列表（取自表格第一行）
            - rows: 行数据列表（每行为单元格值列表，不含表头行）

        Raises:
            FileNotFoundError: 当 pdf_path 指向的文件不存在时
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        tables_result: list[dict[str, Any]] = []
        doc = fitz.open(str(pdf_path))
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                # 使用 find_tables 检测当前页的表格
                try:
                    tables = page.find_tables()
                except Exception:
                    # find_tables 在某些 PyMuPDF 版本中可能不可用或该页无表格
                    logger.debug("第 %d 页 find_tables 异常或无表格", page_num)
                    continue
                # TableFinder 可迭代，每次产出 Table 对象
                for table_idx, table in enumerate(tables):
                    extracted = table.extract()
                    if not extracted:
                        # 空表格跳过
                        continue
                    # 第一行作为表头，其余作为数据行
                    headers = extracted[0] if extracted else []
                    rows = extracted[1:] if len(extracted) > 1 else []
                    tables_result.append({
                        "page_number": page_num,
                        "table_index": table_idx,
                        "headers": headers,
                        "rows": rows,
                    })
                    logger.info(
                        "第 %d 页表格 %d: %d 行 %d 列",
                        page_num, table_idx, len(rows), len(headers),
                    )
        finally:
            doc.close()
        return tables_result

    def extract_to_dataframe(self, pdf_path: Path) -> list[pd.DataFrame]:
        """从 PDF 提取表格并转为 DataFrame

        内部调用 extract_tables() 获取结构化数据后，
        将每个表格转为 pandas DataFrame（headers 作为列名）。

        Args:
            pdf_path: PDF 文件路径

        Returns:
            DataFrame 列表，每个表格一个 DataFrame。
            当表格无表头或无数据行时，返回列名缺失的空 DataFrame。

        Raises:
            FileNotFoundError: 当 pdf_path 指向的文件不存在时
        """
        tables = self.extract_tables(pdf_path)
        dataframes = []
        for table in tables:
            headers = table["headers"]
            rows = table["rows"]
            if headers and rows:
                # 有表头和数据行：使用 headers 作为列名
                df = pd.DataFrame(rows, columns=headers)
            else:
                # 无表头或无数据行：返回默认列名的 DataFrame
                df = pd.DataFrame(rows)
            dataframes.append(df)
        return dataframes
