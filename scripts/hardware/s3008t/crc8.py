"""S3008T CRC-8校验算法实现

多项式: x^8 + x^2 + x + 1 (0x07)
初值: 0x00
"""


def calculate_crc8(data: bytes) -> int:
    """
    CRC-8校验计算

    Args:
        data: 需要计算CRC的数据

    Returns:
        CRC-8校验值(0~255)
    """
    crc = 0x00
    polynomial = 0x07

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFF

    return crc