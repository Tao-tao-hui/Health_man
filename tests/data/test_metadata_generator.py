# e:\Health_man\tests\data\test_metadata_generator.py
"""测试元数据生成器"""
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.data.metadata_generator import MetadataGenerator
from scripts.data.quality_checker import QualityReport


@pytest.fixture
def sample_report():
    return QualityReport(
        completeness=0.95,
        validity=0.98,
        consistency=0.92,
        overall=0.95,
        grade="A",
        row_count=100,
        column_count=10,
        issues=[],
    )


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "bmi": [22.5, 25.0],
        "age": [25, 35],
        "gender": [1, 0],
    })


def test_generate_l0_card(tmp_path, sample_report):
    """L0 数据集卡片必须含必填字段"""
    adapter_meta = {
        "dataset_id": "NHANES_2017_2020",
        "source_url": "https://wwwn.cdc.gov/",
        "license": "Public Domain",
        "region": "US",
        "sample_size": 9092,
    }
    gen = MetadataGenerator()
    l0 = gen.generate_l0(adapter_meta, sample_report, output_path=tmp_path / "L0.json")

    assert l0["dataset_id"] == "NHANES_2017_2020"
    assert l0["source_url"] == "https://wwwn.cdc.gov/"
    assert l0["license"] == "Public Domain"
    assert l0["quality"]["grade"] == "A"
    assert l0["quality"]["overall"] == 0.95
    assert "generated_at" in l0
    # 文件已写入
    assert (tmp_path / "L0.json").exists()


def test_generate_l1_fields(tmp_path, sample_df):
    """L1 字段字典必须含每个字段的类型与缺失率"""
    gen = MetadataGenerator()
    l1 = gen.generate_l1(sample_df, output_path=tmp_path / "L1.json")

    assert "fields" in l1
    assert len(l1["fields"]) == 3
    field_names = [f["name"] for f in l1["fields"]]
    assert "bmi" in field_names
    assert "age" in field_names
    for field in l1["fields"]:
        assert "type" in field
        assert "missing_rate" in field


def test_generate_l2_usage(tmp_path, sample_report):
    """L2 使用说明必须含适用场景与偏差声明"""
    adapter_meta = {
        "dataset_id": "NHANES_2017_2020",
        "known_bias": "种族分布与中国人群有差异",
    }
    gen = MetadataGenerator()
    l2 = gen.generate_l2(adapter_meta, sample_report, output_path=tmp_path / "L2.md")

    assert "NHANES_2017_2020" in l2
    assert "种族分布与中国人群有差异" in l2
    assert "A" in l2  # 质量评级
    assert (tmp_path / "L2.md").exists()
