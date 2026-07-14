"""S3008T体脂芯片通信协议测试"""

import pytest
from scripts.hardware.s3008t.protocol import S3008TProtocol


def test_build_command():
    """测试构建命令帧"""
    protocol = S3008TProtocol()

    cmd = protocol.build_command(0x01, [0x01])
    assert len(cmd) == 4
    assert cmd[0] == 3
    assert cmd[1] == 0x01
    assert cmd[2] == 0x01


def test_build_set_weight_command():
    """测试构建设置体重命令"""
    protocol = S3008TProtocol()

    cmd = protocol.build_command(0x03, [0x02, 0x58])
    assert len(cmd) == 5
    assert cmd[0] == 4
    assert cmd[1] == 0x03
    assert cmd[2] == 0x02
    assert cmd[3] == 0x58


def test_parse_response():
    """测试解析响应帧"""
    protocol = S3008TProtocol()

    response = bytes([0x03, 0x08, 0x01, 0xAF])
    result = protocol.parse_response(response)

    assert result['cmd'] == 0x08
    assert result['data'] == [0x01]
    assert 'impedance' not in result


def test_parse_response_crc_failure():
    """测试CRC校验失败"""
    protocol = S3008TProtocol()

    response = bytes([0x03, 0x08, 0x01, 0x00])
    with pytest.raises(ValueError, match="CRC mismatch"):
        protocol.parse_response(response)


def test_build_set_weight():
    """测试构建设置体重便捷方法"""
    protocol = S3008TProtocol()

    cmd = protocol.build_set_weight(60.0)
    assert len(cmd) == 5
    assert cmd[0] == 4
    assert cmd[1] == 0x03
    assert cmd[2] == 0x02
    assert cmd[3] == 0x58


def test_build_set_height():
    """测试构建设置身高便捷方法"""
    protocol = S3008TProtocol()

    cmd = protocol.build_set_height(175)
    assert len(cmd) == 4
    assert cmd[1] == 0x04
    assert cmd[2] == 175


def test_build_set_age():
    """测试构建设置年龄便捷方法"""
    protocol = S3008TProtocol()

    cmd = protocol.build_set_age(35)
    assert len(cmd) == 4
    assert cmd[1] == 0x05
    assert cmd[2] == 35


def test_build_set_gender():
    """测试构建设置性别便捷方法"""
    protocol = S3008TProtocol()

    cmd = protocol.build_set_gender(1)
    assert len(cmd) == 4
    assert cmd[1] == 0x06
    assert cmd[2] == 1


def test_build_read_result():
    """测试构建读取结果命令"""
    protocol = S3008TProtocol()

    cmd = protocol.build_read_result()
    assert len(cmd) == 3
    assert cmd[0] == 2
    assert cmd[1] == 0x08