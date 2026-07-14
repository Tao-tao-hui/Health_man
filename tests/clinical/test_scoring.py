"""健康评分算法测试"""

import pytest
from scripts.clinical.scoring import HealthScorer
from scripts.hardware.models import ProcessedData


def test_body_composition_score():
    """测试体成分评分"""
    scorer = HealthScorer()

    data = ProcessedData(
        body_fat_rate=22.5,
        bmi=24.8,
        visceral_fat_level=8,
        muscle_mass=55.0,
        age=35,
        sex="M",
        height_cm=175.0,
        weight_kg=70.0
    )

    score = scorer.calculate_body_composition_score(data)
    assert 0 <= score <= 100


def test_cardiovascular_score():
    """测试心血管评分"""
    scorer = HealthScorer()

    data = ProcessedData(
        spo2=98.0,
        heart_rate=75.0,
        pi=6.2,
        hrv=10.0
    )

    score = scorer.calculate_cardiovascular_score(data)
    assert 0 <= score <= 100


def test_overall_score():
    """测试综合健康评分"""
    scorer = HealthScorer()

    data = ProcessedData(
        body_fat_rate=22.5,
        bmi=24.8,
        visceral_fat_level=8,
        muscle_mass=55.0,
        spo2=98.0,
        heart_rate=75.0,
        age=35,
        sex="M",
        height_cm=175.0,
        weight_kg=70.0
    )

    scores = scorer.calculate_overall_score(data)

    assert scores['overall'] == (scores['body_composition'] + scores['cardiovascular']) // 2
    assert 0 <= scores['overall'] <= 100


def test_body_composition_score_all_normal():
    """测试所有指标正常时的体成分评分"""
    scorer = HealthScorer()

    data = ProcessedData(
        body_fat_rate=14.0,
        bmi=22.0,
        visceral_fat_level=8,
        muscle_mass=55.0,
        age=35,
        sex="M",
        height_cm=175.0,
        weight_kg=70.0
    )

    score = scorer.calculate_body_composition_score(data)
    assert score >= 80


def test_cardiovascular_score_all_normal():
    """测试所有指标正常时的心血管评分"""
    scorer = HealthScorer()

    data = ProcessedData(
        spo2=97.0,
        heart_rate=70.0,
        pi=1.5
    )

    score = scorer.calculate_cardiovascular_score(data)
    assert score >= 80


def test_cardiovascular_score_low_spo2():
    """测试血氧偏低时的心血管评分"""
    scorer = HealthScorer()

    data = ProcessedData(
        spo2=92.0,
        heart_rate=75.0,
        pi=1.0
    )

    score = scorer.calculate_cardiovascular_score(data)
    assert score < 100