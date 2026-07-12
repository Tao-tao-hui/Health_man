"""测试凭证管理器"""
import pytest
from pathlib import Path

from scripts.utils.credential_manager import CredentialManager


def test_store_and_retrieve_credential(tmp_path):
    """存储后必须能正确读取"""
    mgr = CredentialManager(storage_dir=tmp_path, master_key=b"test-key-32bytes-padding!!!")
    mgr.store("GLM_API_KEY", "sk-abc123")
    retrieved = mgr.retrieve("GLM_API_KEY")
    assert retrieved == "sk-abc123"


def test_retrieve_nonexistent_returns_none(tmp_path):
    """读取不存在的凭证必须返回 None"""
    mgr = CredentialManager(storage_dir=tmp_path, master_key=b"test-key-32bytes-padding!!!")
    assert mgr.retrieve("NONEXISTENT") is None


def test_list_credentials(tmp_path):
    """必须能列出所有存储的凭证名"""
    mgr = CredentialManager(storage_dir=tmp_path, master_key=b"test-key-32bytes-padding!!!")
    mgr.store("GLM_API_KEY", "key1")
    mgr.store("QWEN_API_KEY", "key2")
    names = mgr.list_keys()
    assert "GLM_API_KEY" in names
    assert "QWEN_API_KEY" in names


def test_delete_credential(tmp_path):
    """删除后不可再读取"""
    mgr = CredentialManager(storage_dir=tmp_path, master_key=b"test-key-32bytes-padding!!!")
    mgr.store("TEMP_KEY", "temp")
    mgr.delete("TEMP_KEY")
    assert mgr.retrieve("TEMP_KEY") is None
