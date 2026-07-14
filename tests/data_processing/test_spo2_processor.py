"""血氧数据处理器测试"""

import pytest
from scripts.data_processing.spo2_processor import SpO2Processor
from scripts.hardware.models import HardwareData, ProcessedData


def test_spo2_processor_basic():
    """测试血氧处理器基本功能"""
    processor = SpO2Processor()

    hardware_data = HardwareData(
        spo2=98,
        heart_rate=75,
        pi=6.2,
        hrv=10,
        timestamp=None
    )

    result = processor.process(hardware_data)

    assert isinstance(result, ProcessedData)
    assert result.spo2 == 98.0
    assert result.heart_rate == 75.0
    assert result.pi == 6.2
    assert result.hrv == 10.0


def test_spo2_range_validation():
    """测试血氧范围验证"""
    processor = SpO2Processor()

    assert processor.validate_spo2(95) is True
    assert processor.validate_spo2(70) is True
    assert processor.validate_spo2(69) is False
    assert processor.validate_spo2(100) is False


def test_pi_signal_quality():
    """测试PI值信号质量评估"""
    processor = SpO2Processor()

    assert processor.evaluate_signal_quality(pi=1.0) >= 0.6
    assert processor.evaluate_signal_quality(pi=2.0) >= 0.8
    assert processor.evaluate_signal_quality(pi=0.2) < 0.5


def test_heart_rate_validation():
    """测试心率验证"""
    processor = SpO2Processor()

    assert processor.validate_heart_rate(75) is True
    assert processor.validate_heart_rate(30) is True
    assert processor.validate_heart_rate(25) is False
    assert processor.validate_heart_rate(260) is False


def test_pi_validation():
    """测试PI值验证"""
    processor = SpO2Processor()

    assert processor.validate_pi(6.2) is True
    assert processor.validate_pi(0.0) is True
    assert processor.validate_pi(25.0) is False


def test_signal_quality_with_none_pi():
    """测试PI值为None时的信号质量评估"""
    processor = SpO2Processor()

    quality = processor.evaluate_signal_quality(pi=None)
    assert quality == 0.5


def test_data_quality_calculation():
    """测试数据质量评分计算"""
    processor = SpO2Processor()

    hardware_data = HardwareData(
        spo2=95,
        heart_rate=75,
        pi=1.5,
        signal_quality=0.9
    )

    quality = processor._calculate_data_quality(hardware_data)
    assert 0.0 <= quality <= 1.0


def test_data_quality_with_invalid_spo2():
    """测试无效血氧值对数据质量的影响"""
    processor = SpO2Processor()

    hardware_data = HardwareData(
        spo2=65,
        heart_rate=75,
        pi=1.5
    )

    quality = processor._calculate_data_quality(hardware_data)
    assert quality < 1.0