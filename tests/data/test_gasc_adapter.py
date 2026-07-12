"""GascPdfExtractor 单元测试

验证 GASC 2025 PDF 附录专用提取功能。

GASC（Global Adult Size Chart）2025 是 PMID:40620559 的附录数据，
包含全球成人人体测量参考值（BMI、体脂率、内脏脂肪等）。

测试 PDF 创建方式：使用 page.draw_line() 绘制表格边框线，
使 find_tables() 能检测到视觉表格结构（与 Task 3 PdfTableExtractor 测试一致）。
"""
import pytest
import fitz  # PyMuPDF
from pathlib import Path

from scripts.data.adapters.gasc_adapter import GascPdfExtractor


class TestGascPdfExtractor:
    """GascPdfExtractor 测试套件"""

    def _create_test_gasc_pdf(self, tmp_path: Path) -> Path:
        """创建模拟 GASC 2025 PDF（绘制表格边框线，便于 find_tables 检测）

        绘制 4 行 x 4 列表格（1 表头行 + 3 数据行）：
        - 表头：Indicator, Male Mean, Female Mean, Reference Range
        - 数据行：BMI, Body Fat %, Visceral Fat
        使用 draw_line 绘制水平/垂直边框线，再用 insert_text 填充单元格内容。
        """
        pdf_path = tmp_path / "gasc_2025_supplement.pdf"
        doc = fitz.open()
        page = doc.new_page()
        # 表格几何参数：4 行 x 4 列
        rows, cols = 4, 4
        x0, y0, x1, y1 = 50, 50, 550, 200
        row_height = (y1 - y0) / rows
        col_width = (x1 - x0) / cols
        # 绘制水平边框线（rows+1 条）
        for i in range(rows + 1):
            page.draw_line((x0, y0 + i * row_height), (x1, y0 + i * row_height))
        # 绘制垂直边框线（cols+1 条）
        for j in range(cols + 1):
            page.draw_line((x0 + j * col_width, y0), (x0 + j * col_width, y1))
        # 填充单元格内容（模拟 GASC 附录中的参考范围表格）
        data = [
            ["Indicator", "Male Mean", "Female Mean", "Reference Range"],
            ["BMI", "24.2", "22.8", "18.5-24.9"],
            ["Body Fat %", "17.5", "25.2", "10-25"],
            ["Visceral Fat", "8.2", "6.5", "1-9"],
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

    def test_extract_returns_dict_with_indicators(self, tmp_path):
        """测试提取返回含指标数据的字典（结构 + 内容验证）"""
        pdf_path = self._create_test_gasc_pdf(tmp_path)
        extractor = GascPdfExtractor()
        result = extractor.extract(pdf_path)
        # 验证返回类型为字典
        assert isinstance(result, dict)
        # 验证包含 indicators 键且为列表
        assert "indicators" in result
        assert isinstance(result["indicators"], list)
        # 验证至少提取出 3 个指标（BMI、Body Fat %、Visceral Fat）
        assert len(result["indicators"]) >= 3

    def test_extract_indicator_fields_contain_gasc_values(self, tmp_path):
        """测试提取的指标字段包含 GASC 特定数值（验证内容，不只是类型）"""
        pdf_path = self._create_test_gasc_pdf(tmp_path)
        extractor = GascPdfExtractor()
        result = extractor.extract(pdf_path)
        indicators = result["indicators"]
        # 找到 BMI 指标行
        bmi = next(
            (ind for ind in indicators if ind.get("name") == "BMI"),
            None,
        )
        assert bmi is not None, "应在指标列表中找到 BMI"
        # 验证 BMI 的男性均值、女性均值、参考范围
        assert bmi["male_mean"] == pytest.approx(24.2)
        assert bmi["female_mean"] == pytest.approx(22.8)
        assert bmi["reference_range"] == "18.5-24.9"

    def test_get_metadata_template_has_gasc_fields(self):
        """测试 L0 元数据模板包含 GASC 特定字段"""
        extractor = GascPdfExtractor()
        meta = extractor.get_metadata_template()
        # 验证数据集 ID
        assert meta["dataset_id"] == "GASC_2025"
        # 验证 PMID
        assert "pmid" in meta
        assert meta["pmid"] == "40620559"

    def test_get_metadata_template_contains_required_l0_fields(self):
        """测试元数据模板包含 L0 必备字段（region/license/source_url 等）"""
        extractor = GascPdfExtractor()
        meta = extractor.get_metadata_template()
        # L0 模板必备字段
        for key in ("dataset_id", "pmid", "source_url", "license",
                    "region", "sample_size", "cycle", "population"):
            assert key in meta, f"L0 元数据应包含 {key}"
        # 验证 source_url 中包含 PMID
        assert "40620559" in meta["source_url"]

    def test_extract_nonexistent_file_raises(self):
        """测试不存在文件抛出 FileNotFoundError"""
        extractor = GascPdfExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract(Path("nonexistent_gasc.pdf"))

    def test_extract_preserves_source_page_info(self, tmp_path):
        """测试提取结果保留源页码（包含 0 号页）"""
        pdf_path = self._create_test_gasc_pdf(tmp_path)
        extractor = GascPdfExtractor()
        result = extractor.extract(pdf_path)
        # 验证包含 source_pages 键
        assert "source_pages" in result
        # 验证 source_pages 为非空列表
        assert isinstance(result["source_pages"], list)
        assert len(result["source_pages"]) >= 1
        # 测试 PDF 为单页，页码应为 0
        assert 0 in result["source_pages"]

    def test_extract_result_contains_source_field(self, tmp_path):
        """测试提取结果标识数据来源为 GASC_2025"""
        pdf_path = self._create_test_gasc_pdf(tmp_path)
        extractor = GascPdfExtractor()
        result = extractor.extract(pdf_path)
        # 验证来源标识（source 字段）
        assert result.get("source") == "GASC_2025"
