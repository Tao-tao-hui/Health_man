"""BMH08002 UART通信协议实现

命令帧格式(8字节): 0x55 [CMD] [OP_Code] [Addr] [Data_H] [Data_L] [CheckSum] 0xAA
数据帧格式(15字节): 0x55 [CMD=0xB0] [Status] [SpO2] [HR] [PI] [HRV] [...] [CheckSum] 0xAA
"""

from .protocol import BMH08002Protocol


class UARTProtocol(BMH08002Protocol):
    """
    BMH08002 UART通信协议实现

    提供命令帧构建和数据帧解析功能
    """

    def build_command(self, op_code: int, addr: int, data_h: int, data_l: int) -> bytes:
        """
        构建UART命令帧

        Args:
            op_code: 操作码(0x01~0x06)
            addr: 寄存器地址
            data_h: 数据高字节
            data_l: 数据低字节

        Returns:
            完整的命令帧字节
        """
        cmd_bytes = bytes([self.CMD_COMMAND, op_code, addr, data_h, data_l])
        checksum = self.calculate_checksum(cmd_bytes)

        return bytes([self.HEAD]) + cmd_bytes + bytes([checksum, self.TAIL])

    def parse_data_frame(self, frame: bytes) -> dict:
        """
        解析UART数据帧(15字节)

        Args:
            frame: 数据帧字节

        Returns:
            解析后的测量数据字典

        Raises:
            ValueError: 帧长度无效、帧头帧尾错误或校验和失败
        """
        if len(frame) != 15:
            raise ValueError(f"Invalid frame length: expected 15, got {len(frame)}")

        if frame[0] != self.HEAD or frame[14] != self.TAIL:
            raise ValueError("Invalid frame head or tail")

        checksum = self.calculate_checksum(frame[1:13])
        if frame[13] != checksum:
            raise ValueError(f"Checksum mismatch: expected {checksum}, got {frame[13]}")

        return {
            'status': frame[2],
            'spo2': frame[3],
            'heart_rate': frame[4],
            'pi': frame[5] * 0.1,
            'hrv': frame[6],
            'pulse_height': frame[7],
            'systolic_time': frame[8],
            'ppg_adc1': (frame[9] << 8) | frame[10],
            'ppg_adc2': (frame[11] << 8) | frame[12]
        }

    def build_start_measurement(self) -> bytes:
        """构建开始测量命令"""
        return self.build_command(0x01, 0x00, 0x00, 0x00)

    def build_stop_measurement(self) -> bytes:
        """构建结束测量命令"""
        return self.build_command(0x01, 0x00, 0x00, 0x01)

    def build_enter_sleep(self) -> bytes:
        """构建进入休眠命令"""
        return self.build_command(0x01, 0x00, 0x00, 0x02)

    def build_get_result(self) -> bytes:
        """构建获取测量结果命令"""
        return self.build_command(0x03, 0x00, 0x00, 0x00)