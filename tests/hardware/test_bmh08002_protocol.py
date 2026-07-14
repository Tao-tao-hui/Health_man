"""BMH08002血氧模块通信协议测试"""

import pytest
from scripts.hardware.bmh08002.uart_protocol import UARTProtocol


def test_build_uart_command():
    """测试构建UART命令帧"""
    protocol = UARTProtocol()

    cmd = protocol.build_command(0x01, 0x00, 0x00, 0x00)
    assert len(cmd) == 8
    assert cmd[0] == 0x55
    assert cmd[1] == 0xB1
    assert cmd[2] == 0x01
    assert cmd[7] == 0xAA


def test_parse_uart_data_frame():
    """测试解析UART数据帧"""
    protocol = UARTProtocol()

    data_frame = bytes([
        0x55, 0xB0, 0x02,
        0x62,
        0x4B,
        0x3E,
        0x0A,
        0x20,
        0x05,
        0x00, 0x00,
        0x00, 0x00,
        0xCC,
        0xAA
    ])

    result = protocol.parse_data_frame(data_frame)

    assert result['status'] == 0x02
    assert result['spo2'] == 98
    assert result['heart_rate'] == 75
    assert result['pi'] == 6.2
    assert result['hrv'] == 10


def test_parse_uart_data_frame_checksum_failure():
    """测试校验和失败"""
    protocol = UARTProtocol()

    data_frame = bytes([
        0x55, 0xB0, 0x02,
        0x62,
        0x4B,
        0x3E,
        0x0A,
        0x20,
        0x05,
        0x00, 0x00,
        0x00, 0x00,
        0x00,
        0xAA
    ])

    with pytest.raises(ValueError, match="Checksum mismatch"):
        protocol.parse_data_frame(data_frame)


def test_build_start_measurement():
    """测试构建开始测量命令"""
    protocol = UARTProtocol()

    cmd = protocol.build_start_measurement()
    assert len(cmd) == 8
    assert cmd[0] == 0x55
    assert cmd[1] == 0xB1
    assert cmd[2] == 0x01


def test_build_stop_measurement():
    """测试构建停止测量命令"""
    protocol = UARTProtocol()

    cmd = protocol.build_stop_measurement()
    assert len(cmd) == 8
    assert cmd[2] == 0x01
    assert cmd[5] == 0x01


def test_build_enter_sleep():
    """测试构建进入休眠命令"""
    protocol = UARTProtocol()

    cmd = protocol.build_enter_sleep()
    assert len(cmd) == 8
    assert cmd[2] == 0x01
    assert cmd[5] == 0x02


def test_build_get_result():
    """测试构建获取测量结果命令"""
    protocol = UARTProtocol()

    cmd = protocol.build_get_result()
    assert len(cmd) == 8
    assert cmd[2] == 0x03