"""凭证管理器

职责：
- API Key 的加密存储与读取
- 列举与删除凭证
- 不在内存中长时间保留明文

存储格式：
- 每个凭证一个文件：{storage_dir}/{name}.enc
- 文件内容：base64(nonce + ciphertext)
"""
import json
from pathlib import Path

from scripts.utils.crypto import CryptoUtils


class CredentialManager:
    """凭证管理器

    Args:
        storage_dir: 凭证存储目录
        master_key: 主密钥
    """

    def __init__(self, storage_dir: Path, master_key: bytes):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.crypto = CryptoUtils(master_key)

    def store(self, name: str, value: str) -> None:
        """存储凭证（加密）"""
        file_path = self.storage_dir / f"{name}.enc"
        encrypted = self.crypto.encrypt(value.encode("utf-8"))
        with open(file_path, "wb") as f:
            f.write(encrypted)

    def retrieve(self, name: str) -> str | None:
        """读取凭证（解密）"""
        file_path = self.storage_dir / f"{name}.enc"
        if not file_path.exists():
            return None
        with open(file_path, "rb") as f:
            encrypted = f.read()
        decrypted = self.crypto.decrypt(encrypted)
        return decrypted.decode("utf-8")

    def list_keys(self) -> list[str]:
        """列出所有凭证名"""
        return [
            f.stem
            for f in self.storage_dir.glob("*.enc")
        ]

    def delete(self, name: str) -> None:
        """删除凭证"""
        file_path = self.storage_dir / f"{name}.enc"
        if file_path.exists():
            file_path.unlink()
