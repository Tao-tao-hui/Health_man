# e:\Health_man\tests\data\test_quality_checker.py
"""测试质量校验器"""
import pandas as pd
import pytest

from scripts.data.quality_checker import QualityChecker, QualityReport


@pytest.fixture
def good_df():
    """高质量数据集"""
    return pd.DataFrame({
        "bmi": [22.5, 25.0, 28.3, 20.0, 23.5] * 20,
        "age": [25, 35, 45, 55, 30] * 20,
        "gender": [1, 0, 1, 0, 1] * 20,
        "weight_kg": [70, 65, 80, 55, 68] * 20,
    })


@pytest.fixture
def poor_df():
    """低质量数据集（缺失率高）"""
    return pd.DataFrame({
        "bmi": [22.5, None, None, None, 28.3] * 20,
        "age": [25, 35, None, None, 45] * 20,
        "gender": [1, 0, 1, None, 1] * 20,
    })


def test_quality_checker_returns_report(good_df):
    """check 必须返回 QualityReport 对象"""
    checker = QualityChecker()
    report = checker.check(good_df)
    assert isinstance(report, QualityReport)


def test_good_data_gets_grade_a(good_df):
    """高质量数据必须评级 A"""
    checker = QualityChecker()
    report = checker.check(good_df)
    assert report.grade == "A"
    assert report.completeness >= 0.9


def test_poor_data_gets_lower_grade(poor_df):
    """低质量数据必须评级 ≤ B"""
    checker = QualityChecker()
    report = checker.check(poor_df)
    assert report.grade in ["B", "C", "D"]
    assert report.completeness < 0.9


def test_report_has_all_metrics(good_df):
    """报告必须含 completeness/validity/consistency/overall"""
    checker = QualityChecker()
    report = checker.check(good_df)
    assert hasattr(report, "completeness")
    assert hasattr(report, "validity")
    assert hasattr(report, "consistency")
    assert hasattr(report, "overall")
    assert hasattr(report, "grade")
    assert 0 <= report.completeness <= 1
    assert 0 <= report.validity <= 1
    assert 0 <= report.overall <= 1
