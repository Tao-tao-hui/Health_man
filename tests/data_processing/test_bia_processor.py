"""体成分数据处理器测试"""

import pytest
from scripts.data_processing.bia_processor import BIAProcessor
from scripts.hardware.models import HardwareData, ProcessedData


def test_bia_processor_basic():
    """测试体成分处理器基本功能"""
    processor = BIAProcessor()

    hardware_data = HardwareData(
        bia_impedance=450,
        timestamp=None
    )

    result = processor.process(
        hardware_data=hardware_data,
        height_cm=175,
        weight_kg=70.0,
        age=35,
        sex="M",
        user_type="Normal"
    )

    assert isinstance(result, ProcessedData)
    assert result.height_cm == 175
    assert result.weight_kg == 70.0


def test_impedance_validation():
    """测试阻抗值验证"""
    processor = BIAProcessor()

    assert processor.validate_impedance(450) is True
    assert processor.validate_impedance(200) is False
    assert processor.validate_impedance(1100) is False


def test_bmi_calculation():
    """测试BMI计算"""
    processor = BIAProcessor()

    bmi = processor.calculate_bmi(70.0, 175)
    assert abs(bmi - 22.86) < 0.01


def test_height_validation():
    """测试身高验证"""
    processor = BIAProcessor()

    assert processor.validate_height(175) is True
    assert processor.validate_height(80) is False
    assert processor.validate_height(230) is False


def test_weight_validation():
    """测试体重验证"""
    processor = BIAProcessor()

    assert processor.validate_weight(70.0) is True
    assert processor.validate_weight(15.0) is False
    assert processor.validate_weight(350.0) is False


def test_data_quality_calculation():
    """测试数据质量评分计算"""
    processor = BIAProcessor()

    hardware_data = HardwareData(
        bia_impedance=450,
        signal_quality=0.9
    )

    quality = processor._calculate_data_quality(hardware_data, 175, 70.0)
    assert 0.0 <= quality <= 1.0


def test_data_quality_with_invalid_impedance():
    """测试无效阻抗值对数据质量的影响"""
    processor = BIAProcessor()

    hardware_data = HardwareData(
        bia_impedance=200,
        signal_quality=0.9
    )

    quality = processor._calculate_data_quality(hardware_data, 175, 70.0)
    assert quality < 0.9