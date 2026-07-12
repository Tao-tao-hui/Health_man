"""测试格式转换器"""
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from scripts.data.format_converter import FormatConverter


def test_convert_xpt_to_parquet(tmp_path):
    """XPT 文件必须能转换为 Parquet"""
    # 准备：用 pandas 创建测试数据并写为 XPT
    df = pd.DataFrame({
        "SEQN": [1, 2, 3],
        "BMXBMI": [22.5, 25.0, 28.3],
        "RIAGENDR": [1, 0, 1],
        "RIDAGEYR": [25, 35, 45],
    })
    xpt_path = tmp_path / "test.xpt"
    # pyreadstat 写 XPT
    import pyreadstat
    pyreadstat.write_xport(df, str(xpt_path), table_name="TEST")

    # 执行转换
    converter = FormatConverter()
    parquet_path = converter.convert_xpt_to_parquet(xpt_path, tmp_path / "out.parquet")

    # 验证
    assert parquet_path.exists()
    result_df = pd.read_parquet(parquet_path)
    assert len(result_df) == 3
    assert "BMXBMI" in result_df.columns


def test_convert_csv_to_parquet(tmp_path):
    """CSV 文件必须能转换为 Parquet"""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("SEQN,BMI,gender,age\n1,22.5,1,25\n2,25.0,0,35\n", encoding="utf-8")

    converter = FormatConverter()
    parquet_path = converter.convert_csv_to_parquet(csv_path, tmp_path / "out.parquet")

    assert parquet_path.exists()
    result_df = pd.read_parquet(parquet_path)
    assert len(result_df) == 2
    assert "BMI" in result_df.columns


def test_convert_csv_with_gbk_encoding(tmp_path):
    """GBK 编码的 CSV 必须能正确转换为 UTF-8 Parquet"""
    csv_path = tmp_path / "test_gbk.csv"
    # 写一个 GBK 编码的 CSV
    content = "姓名,年龄\n张三,25\n李四,35\n"
    csv_path.write_bytes(content.encode("gbk"))

    converter = FormatConverter()
    parquet_path = converter.convert_csv_to_parquet(
        csv_path, tmp_path / "out.parquet", encoding="gbk"
    )

    result_df = pd.read_parquet(parquet_path)
    assert len(result_df) == 2
    # UTF-8 编码的中文应该正确显示
    assert "姓名" in result_df.columns


def test_convert_invalid_xpt_raises_error(tmp_path):
    """无效 XPT 文件必须抛出明确异常"""
    invalid_path = tmp_path / "invalid.xpt"
    invalid_path.write_bytes(b"not a valid xpt file")

    converter = FormatConverter()
    with pytest.raises(ValueError, match="XPT"):
        converter.convert_xpt_to_parquet(invalid_path, tmp_path / "out.parquet")
