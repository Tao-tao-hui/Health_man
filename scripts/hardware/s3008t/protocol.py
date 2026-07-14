"""S3008T体脂芯片通信协议实现

帧格式: [Length] [CMD] [DataN] [CRC-8]
Length = CMD(1) + DataN(N) + CRC(1)
"""

from .crc8 import calculate_crc8


class S3008TProtocol:
    """
    S3008T体脂芯片通信协议实现

    支持命令帧构建和响应帧解析，包含便捷方法用于常见操作
    """

    def build_command(self, cmd: int, data: list = None) -> bytes:
        """
        构建命令帧

        Args:
            cmd: 命令号(0x01~0x08)
            data: 数据字节列表

        Returns:
            完整的命令帧字节
        """
        if data is None:
            data = []

        data_bytes = bytes([cmd] + data)
        length = len(data_bytes) + 1
        crc = calculate_crc8(data_bytes)

        return bytes([length]) + data_bytes + bytes([crc])

    def parse_response(self, response: bytes) -> dict:
        """
        解析响应帧

        Args:
            response: 响应帧字节

        Returns:
            解析后的字典，包含cmd, data, impedance等字段

        Raises:
            ValueError: 响应长度无效或CRC校验失败
        """
        if len(response) < 3:
            raise ValueError("Invalid response length")

        length = response[0]
        cmd = response[1]
        data = list(response[2:-1])
        crc = response[-1]

        expected_crc = calculate_crc8(response[1:-1])
        if crc != expected_crc:
            raise ValueError(f"CRC mismatch: expected {expected_crc}, got {crc}")

        result = {
            'length': length,
            'cmd': cmd,
            'data': data
        }

        if cmd == 0x08 and len(data) >= 2:
            result['impedance'] = (data[0] << 8) | data[1]

        return result

    def build_set_weight(self, weight_kg: float) -> bytes:
        """构建设置体重命令"""
        weight_scaled = int(weight_kg * 10)
        data = [(weight_scaled >> 8) & 0xFF, weight_scaled & 0xFF]
        return self.build_command(0x03, data)

    def build_set_height(self, height_cm: int) -> bytes:
        """构建设置身高命令"""
        return self.build_command(0x04, [height_cm])

    def build_set_age(self, age: int) -> bytes:
        """构建设置年龄命令"""
        return self.build_command(0x05, [age])

    def build_set_gender(self, gender: int) -> bytes:
        """构建设置性别命令"""
        return self.build_command(0x06, [gender])

    def build_set_user_type(self, user_type: int) -> bytes:
        """构建设置用户类型命令"""
        return self.build_command(0x07, [user_type])

    def build_read_result(self) -> bytes:
        """构建读取测量结果命令"""
        return self.build_command(0x08)