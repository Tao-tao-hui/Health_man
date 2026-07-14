"""数据模型测试"""

import pytest
from datetime import datetime
from scripts.hardware.models import HardwareData, ProcessedData, HealthAssessment


def test_hardware_data_initialization():
    """测试硬件数据模型初始化"""
    data = HardwareData(
        bia_impedance=450,
        spo2=98,
        heart_rate=75,
        pi=6.2,
        hrv=10,
        timestamp=datetime.now()
    )

    assert data.bia_impedance == 450
    assert data.spo2 == 98
    assert data.heart_rate == 75
    assert data.pi == 6.2
    assert data.hrv == 10
    assert data.signal_quality is None


def test_processed_data_initialization():
    """测试处理后数据模型初始化"""
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

    assert data.body_fat_rate == 22.5
    assert data.bmi == 24.8
    assert data.visceral_fat_level == 8
    assert data.user_type == "Normal"


def test_health_assessment_initialization():
    """测试健康评估模型初始化"""
    assessment = HealthAssessment(
        overall_score=85,
        component_scores={'body_composition': 88, 'cardiovascular': 82},
        alerts=[],
        recommendations=['建议每周运动3次'],
        evidence_level='C'
    )

    assert assessment.overall_score == 85
    assert assessment.disclaimer == "本评估结果为保健级参考值，不可用于临床诊断。"


def test_hardware_data_default_values():
    """测试硬件数据模型默认值"""
    data = HardwareData()

    assert data.bia_impedance is None
    assert data.spo2 is None
    assert data.heart_rate is None
    assert data.pi is None
    assert data.hrv is None
    assert data.timestamp is None
    assert data.signal_quality is None
    assert data.device_id is None


def test_processed_data_default_values():
    """测试处理后数据模型默认值"""
    data = ProcessedData()

    assert data.body_fat_rate is None
    assert data.bmi is None
    assert data.visceral_fat_level is None
    assert data.user_type == "Normal"
    assert data.data_quality is None


def test_health_assessment_default_values():
    """测试健康评估模型默认值"""
    assessment = HealthAssessment()

    assert assessment.overall_score is None
    assert assessment.component_scores is None
    assert assessment.alerts == []
    assert assessment.recommendations == []
    assert assessment.trend_analysis is None
    assert assessment.evidence_level is None