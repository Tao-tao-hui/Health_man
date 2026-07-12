"""LiteratureMetadataGenerator 单元测试

验证 Layer B 三层元数据生成功能。
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.data.literature_metadata_generator import LiteratureMetadataGenerator
from scripts.data.quality_checker import QualityReport


def make_test_quality_report() -> QualityReport:
    """创建测试用质量报告"""
    return QualityReport(
        completeness=0.85,
        validity=0.90,
        consistency=0.80,
        overall=0.85,
        grade="B",
        row_count=50,
        column_count=5,
        issues=[],
    )


class TestLiteratureMetadataGenerator:
    """LiteratureMetadataGenerator 测试套件"""

    def test_generate_l0_returns_dict_with_literature_fields(self, tmp_path):
        """测试 L0 包含文献特定字段"""
        gen = LiteratureMetadataGenerator()
        meta = {"dataset_id": "PubMed_Literature", "source_url": "https://pubmed.ncbi.nlm.nih.gov/"}
        qr = make_test_quality_report()
        l0 = gen.generate_l0(meta, qr, output_path=tmp_path / "l0.json")
        assert l0["dataset_id"] == "PubMed_Literature"
        assert "quality" in l0
        assert l0["quality"]["grade"] == "B"
        # 验证文件已写入
        assert (tmp_path / "l0.json").exists()

    def test_generate_l1_returns_field_dict(self, tmp_path):
        """测试 L1 返回字段字典"""
        gen = LiteratureMetadataGenerator()
        df = pd.DataFrame({"pmid": ["1", "2"], "title": ["A", "B"]})
        l1 = gen.generate_l1(df, output_path=tmp_path / "l1.json")
        assert "fields" in l1
        assert l1["row_count"] == 2
        assert len(l1["fields"]) == 2

    def test_generate_l2_returns_markdown(self, tmp_path):
        """测试 L2 返回 Markdown 文本"""
        gen = LiteratureMetadataGenerator()
        meta = {"dataset_id": "GASC_2025", "known_bias": "样本偏倚", "population": "全球成人"}
        qr = make_test_quality_report()
        l2 = gen.generate_l2(meta, qr, output_path=tmp_path / "l2.md")
        assert isinstance(l2, str)
        assert "GASC_2025" in l2
        assert (tmp_path / "l2.md").exists()

    def test_generate_l0_includes_extraction_method(self, tmp_path):
        """测试 L0 包含提取方法字段"""
        gen = LiteratureMetadataGenerator()
        meta = {"dataset_id": "Test", "extraction_method": "PyMuPDF + 人工校验"}
        qr = make_test_quality_report()
        l0 = gen.generate_l0(meta, qr)
        assert "extraction_method" in l0
