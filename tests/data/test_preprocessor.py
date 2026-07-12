"""测试 5 步预处理器"""
from pathlib import Path

import pandas as pd
import pytest

from scripts.data.preprocessor import Preprocessor


@pytest.fixture
def sample_df():
    """模拟 NHANES 风格的测试数据"""
    return pd.DataFrame({
        "SEQN": [1, 2, 3, 4, 5],
        "BMXBMI": [22.5, 25.0, 28.3, 999.0, 18.5],  # 999 是异常值
        "RIAGENDR": [1, 0, 1, 0, 1],
        "RIDAGEYR": [25, 35, 45, 55, 200],  # 200 是异常年龄
        "BMXWT": [70.0, 65.0, 80.0, 55.0, None],  # 含缺失值
    })


@pytest.fixture
def preprocessor(tmp_path):
    """创建预处理器实例（使用临时指标映射）"""
    mapping_path = tmp_path / "indicator_mapping.json"
    mapping_path.write_text(
        '{"indicator_mapping": {"BMXBMI": "bmi", "BMXWT": "weight_kg", "RIAGENDR": "gender", "RIDAGEYR": "age"}}',
        encoding="utf-8",
    )
    return Preprocessor(mapping_path=mapping_path)


def test_step1_field_names_standardized(sample_df, preprocessor):
    """Step 1: 字段名必须标准化为 indicator_id"""
    result = preprocessor.process(sample_df)
    assert "bmi" in result.columns
    assert "weight_kg" in result.columns
    assert "gender" in result.columns
    assert "age" in result.columns
    assert "BMXBMI" not in result.columns


def test_step3_outliers_flagged(sample_df, preprocessor):
    """Step 3: 异常值必须被标记（不删除）"""
    result = preprocessor.process(sample_df)
    # BMI=999 应被标记为异常
    bmi_outliers = result[result["bmi"] > 100]
    assert len(bmi_outliers) == 0  # 生理范围过滤后删除
    # age=200 应被过滤
    assert result["age"].max() <= 99


def test_step4_missing_values_filled(sample_df, preprocessor):
    """Step 4: 缺失值必须被填充或标记"""
    result = preprocessor.process(sample_df)
    # weight_kg 原本有 1 个缺失值，应被填充
    assert result["weight_kg"].isna().sum() == 0


def test_step5_age_grouped(sample_df, preprocessor):
    """Step 5: 必须添加 age_group 分组列"""
    result = preprocessor.process(sample_df)
    assert "age_group" in result.columns
    # 25 → 18-39, 35 → 18-39, 45 → 40-59, 55 → 40-59
    age_groups = result["age_group"].tolist()
    assert "18-39" in age_groups
    assert "40-59" in age_groups


def test_process_returns_dataframe(sample_df, preprocessor):
    """process 必须返回 DataFrame"""
    result = preprocessor.process(sample_df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
