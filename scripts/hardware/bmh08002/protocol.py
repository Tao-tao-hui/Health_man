"""BMH08002血氧模块通信协议基类

支持UART和IIC两种通信方式
"""


class BMH08002Protocol:
    """
    BMH08002血氧模块通信协议基类

    定义通用的协议常量和校验方法
    """

    HEAD = 0x55
    CMD_DATA = 0xB0
    CMD_COMMAND = 0xB1
    TAIL = 0xAA

    def calculate_checksum(self, data: bytes) -> int:
        """计算校验和"""
        return sum(data) & 0xFF