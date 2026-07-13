"""测试 LLM 配置模块"""
from pathlib import Path

from scripts.llm.llm_config import (
    AUDIT_LOG_PATH,
    CREDENTIALS_DIR,
    DISTILLED_DIR,
    PROMPT_TEMPLATES_DIR,
    get_audit_logger,
    get_credential_manager,
    get_distilled_dir,
    get_prompt_templates_dir,
)


def test_get_credential_manager_returns_valid_instance():
    """get_credential_manager 必须返回可用的 CredentialManager"""
    cm = get_credential_manager()
    # 存储后能正确读取
    cm.store("test_key", "test_value_12345")
    assert cm.retrieve("test_key") == "test_value_12345"
    # 清理测试数据
    cm.delete("test_key")


def test_get_credential_manager_creates_storage_dir():
    """CredentialManager 存储目录必须存在"""
    cm = get_credential_manager()
    assert Path(cm.storage_dir).exists()


def test_get_audit_logger_returns_valid_instance():
    """get_audit_logger 必须返回可用的 AuditLogger"""
    logger = get_audit_logger()
    assert logger.log_path == AUDIT_LOG_PATH


def test_get_prompt_templates_dir_returns_existing_path():
    """提示词模板目录必须存在"""
    templates_dir = get_prompt_templates_dir()
    assert templates_dir.exists()
    # 应包含 extract_reference_range.txt
    assert (templates_dir / "extract_reference_range.txt").exists()


def test_get_distilled_dir_returns_existing_path():
    """蒸馏数据输出目录必须存在"""
    distilled_dir = get_distilled_dir()
    assert distilled_dir.exists()
