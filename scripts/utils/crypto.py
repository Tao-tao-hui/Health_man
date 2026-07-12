"""加密工具

基于 AES-256-GCM 算法，提供对称加密与解密。
用于保护 API Key 等敏感配置。
"""
import os
import base64
import hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoUtils:
    """AES-256-GCM 加密工具

    Args:
        master_key: 主密钥（任意长度，内部派生为 32 字节）
    """

    def __init__(self, master_key: bytes):
        # 派生 32 字节密钥（AES-256）
        self._key = hashlib.sha256(master_key).digest()

    def encrypt(self, plaintext: bytes) -> bytes:
        """加密

        Args:
            plaintext: 原始字节

        Returns:
            base64 编码的 nonce + ciphertext
        """
        nonce = os.urandom(12)  # 96-bit nonce
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return base64.b64encode(nonce + ciphertext)

    def decrypt(self, encoded_data: bytes) -> bytes:
        """解密

        Args:
            encoded_data: encrypt() 返回的 base64 数据

        Returns:
            原始字节

        Raises:
            Exception: 解密失败
        """
        raw = base64.b64decode(encoded_data)
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None)
