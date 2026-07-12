"""PdfTableExtractor 单元测试

验证 PyMuPDF 表格提取功能。
使用临时生成的 PDF 文件进行测试（不依赖外部 PDF）。

测试 PDF 创建方式：使用 page.draw_line() 绘制表格边框线，
使 find_tables() 能检测到视觉表格结构（仅 insert_text 无法被检测）。
"""
import pytest
import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path

from scripts.data.pdf_extractor import PdfTableExtractor


class TestPdfTableExtractor:
    """PdfTableExtractor 测试套件"""

    def _create_test_pdf(self, tmp_path: Path) -> Path:
        """创建含表格的测试 PDF（绘制表格边框线，便于 find_tables 检测）

        绘制 4 行 x 3 列表格（1 表头行 + 3 数据行），
        使用 draw_line 绘制水平/垂直边框线，再用 insert_text 填充单元格内容。
        """
        pdf_path = tmp_path / "test_table.pdf"
        doc = fitz.open()
        page = doc.new_page()
        # 表格几何参数：4 行 x 3 列
        rows, cols = 4, 3
        x0, y0, x1, y1 = 50, 50, 550, 200
        row_height = (y1 - y0) / rows
        col_width = (x1 - x0) / cols
        # 绘制水平边框线（rows+1 条）
        for i in range(rows + 1):
            page.draw_line((x0, y0 + i * row_height), (x1, y0 + i * row_height))
        # 绘制垂直边框线（cols+1 条）
        for j in range(cols + 1):
            page.draw_line((x0 + j * col_width, y0), (x0 + j * col_width, y1))
        # 填充单元格文本内容
        data = [
            ["Name", "Age", "BMI"],
            ["Zhang", "35", "24.5"],
            ["Li", "28", "22.1"],
            ["Wang", "42", "26.8"],
        ]
        for i, row in enumerate(data):
            for j, cell in enumerate(row):
                page.insert_text(
                    (x0 + j * col_width + 5, y0 + (i + 1) * row_height - 5),
                    cell, fontsize=10
                )
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_extract_tables_returns_list_and_content(self, tmp_path):
        """测试提取表格返回列表，并验证表格内容（headers/rows/page_number）"""
        pdf_path = self._create_test_pdf(tmp_path)
        extractor = PdfTableExtractor()
        tables = extractor.extract_tables(pdf_path)
        # 验证返回类型为列表
        assert isinstance(tables, list)
        # 验证至少检测到一个表格
        assert len(tables) >= 1
        table = tables[0]
        # 验证表格结构字段
        assert "page_number" in table
        assert "headers" in table
        assert "rows" in table
        # 验证页码（单页 PDF，页码从 0 开始）
        assert table["page_number"] == 0
        # 验证表头内容
        assert table["headers"] == ["Name", "Age", "BMI"]
        # 验证数据行数（3 行数据）
        assert len(table["rows"]) == 3
        # 验证第一行数据内容
        assert table["rows"][0] == ["Zhang", "35", "24.5"]
        # 验证最后一行数据内容
        assert table["rows"][2] == ["Wang", "42", "26.8"]

    def test_extract_to_dataframe_returns_dataframes_with_content(self, tmp_path):
        """测试提取为 DataFrame，并验证 DataFrame 内容（列名/行数/单元格值）"""
        pdf_path = self._create_test_pdf(tmp_path)
        extractor = PdfTableExtractor()
        dfs = extractor.extract_to_dataframe(pdf_path)
        # 验证返回类型为列表
        assert isinstance(dfs, list)
        # 验证至少返回一个 DataFrame
        assert len(dfs) >= 1
        df = dfs[0]
        # 验证每个元素是 DataFrame
        assert isinstance(df, pd.DataFrame)
        # 验证列名（表头）
        assert list(df.columns) == ["Name", "Age", "BMI"]
        # 验证数据行数（3 行）
        assert len(df) == 3
        # 验证第一行单元格值
        assert df.iloc[0]["Name"] == "Zhang"
        assert df.iloc[0]["Age"] == "35"
        assert df.iloc[0]["BMI"] == "24.5"
        # 验证最后一行单元格值
        assert df.iloc[2]["Name"] == "Wang"

    def test_extract_tables_empty_pdf(self, tmp_path):
        """测试空 PDF（无表格）返回空列表"""
        pdf_path = tmp_path / "empty.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(pdf_path))
        doc.close()
        extractor = PdfTableExtractor()
        tables = extractor.extract_tables(pdf_path)
        assert tables == []

    def test_extract_tables_nonexistent_file_raises(self):
        """测试不存在文件抛出 FileNotFoundError"""
        extractor = PdfTableExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract_tables(Path("nonexistent.pdf"))

    def test_extract_to_dataframe_nonexistent_file_raises(self):
        """测试 extract_to_dataframe 对不存在文件同样抛出 FileNotFoundError"""
        extractor = PdfTableExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract_to_dataframe(Path("nonexistent.pdf"))
