"""临床标准知识库测试"""

import pytest
from scripts.clinical.standards import ClinicalStandards


def test_bmi_classification():
    """测试BMI分类"""
    standards = ClinicalStandards()

    assert standards.classify_bmi(17.5) == "underweight"
    assert standards.classify_bmi(22.0) == "normal"
    assert standards.classify_bmi(26.5) == "overweight"
    assert standards.classify_bmi(31.0) == "obese"


def test_body_fat_classification():
    """测试体脂率分类"""
    standards = ClinicalStandards()

    assert standards.classify_body_fat(10.0, "M", 30) == "underweight"
    assert standards.classify_body_fat(14.0, "M", 30) == "normal"
    assert standards.classify_body_fat(18.0, "M", 30) == "warning"
    assert standards.classify_body_fat(23.0, "M", 30) == "overweight"
    assert standards.classify_body_fat(28.0, "M", 30) == "obese"

    assert standards.classify_body_fat(20.0, "F", 30) == "underweight"
    assert standards.classify_body_fat(24.0, "F", 30) == "normal"
    assert standards.classify_body_fat(29.0, "F", 30) == "warning"
    assert standards.classify_body_fat(36.0, "F", 30) == "overweight"


def test_spo2_classification():
    """测试血氧分类"""
    standards = ClinicalStandards()

    assert standards.classify_spo2(97) == "normal"
    assert standards.classify_spo2(92) == "mild_hypoxemia"
    assert standards.classify_spo2(88) == "moderate"
    assert standards.classify_spo2(84) == "severe"


def test_visceral_fat_classification():
    """测试内脏脂肪等级分类"""
    standards = ClinicalStandards()

    assert standards.classify_visceral_fat(8) == "normal"
    assert standards.classify_visceral_fat(12) == "warning"
    assert standards.classify_visceral_fat(16) == "danger"


def test_body_fat_classification_male_elderly():
    """测试男性老年人的体脂率分类"""
    standards = ClinicalStandards()

    assert standards.classify_body_fat(15.0, "M", 65) == "normal"
    assert standards.classify_body_fat(21.0, "M", 65) == "warning"
    assert standards.classify_body_fat(26.0, "M", 65) == "overweight"


def test_body_fat_classification_female_elderly():
    """测试女性老年人的体脂率分类"""
    standards = ClinicalStandards()

    assert standards.classify_body_fat(25.0, "F", 65) == "normal"
    assert standards.classify_body_fat(31.0, "F", 65) == "warning"
    assert standards.classify_body_fat(38.0, "F", 65) == "overweight"