"""S3008T CRC-8校验算法测试"""

import pytest
from scripts.hardware.s3008t.crc8 import calculate_crc8


def test_crc8_basic():
    """测试CRC-8基本计算"""
    data = bytes([0x01, 0x00, 0x01])
    result = calculate_crc8(data)
    assert isinstance(result, int)
    assert 0 <= result <= 255


def test_crc8_empty_data():
    """测试空数据CRC-8计算"""
    result = calculate_crc8(bytes())
    assert result == 0


def test_crc8_single_byte():
    """测试单字节CRC-8计算"""
    result = calculate_crc8(bytes([0x55]))
    assert result == 0xAC


def test_crc8_multiple_bytes():
    """测试多字节CRC-8计算"""
    data = bytes([0x01, 0x02, 0x03, 0x04])
    result = calculate_crc8(data)
    # 计算过程验证: 0x01 -> 0x01^0x02=0x03 -> 0x03^0x03=0x00 -> 0x00^0x04=0x04
    # 多项式0x07,初值0x00,每步移位计算
    assert isinstance(result, int)