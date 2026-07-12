"""测试加密工具"""
from scripts.utils.crypto import CryptoUtils


def test_encrypt_decrypt_roundtrip():
    """加密后解密必须得到原文"""
    crypto = CryptoUtils(master_key=b"test-master-key-32bytes-padding!")
    plaintext = b"sensitive api key value"
    ciphertext = crypto.encrypt(plaintext)
    assert ciphertext != plaintext
    decrypted = crypto.decrypt(ciphertext)
    assert decrypted == plaintext


def test_encrypt_returns_different_ciphertext():
    """相同明文每次加密结果必须不同（含随机 nonce）"""
    crypto = CryptoUtils(master_key=b"test-master-key-32bytes-padding!")
    plaintext = b"same value"
    c1 = crypto.encrypt(plaintext)
    c2 = crypto.encrypt(plaintext)
    assert c1 != c2  # 因 nonce 不同


def test_decrypt_invalid_data_raises_error():
    """解密无效数据必须抛出异常"""
    crypto = CryptoUtils(master_key=b"test-master-key-32bytes-padding!")
    import pytest
    with pytest.raises(Exception):
        crypto.decrypt(b"invalid ciphertext")
