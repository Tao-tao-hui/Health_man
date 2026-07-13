"""Layer C LLM 蒸馏配置模块

集中管理 CredentialManager 和 AuditLogger 的初始化参数，
避免各脚本重复构造 storage_dir 和 master_key。

使用方式：
    from scripts.llm.llm_config import get_credential_manager, get_audit_logger

    cm = get_credential_manager()
    cm.store("glm_api_key", "your-key-here")

    audit = get_audit_logger()
    audit.log(operation="init", target="C_llm_distilled", success=True)
"""
import hashlib
import os
from pathlib import Path

from scripts.utils.audit_logger import AuditLogger
from scripts.utils.credential_manager import CredentialManager

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 凭证存储目录（已加入 .gitignore，不入版本控制）
CREDENTIALS_DIR = PROJECT_ROOT / "data" / "credentials"

# 审计日志路径
AUDIT_LOG_PATH = (
    PROJECT_ROOT / "data" / "knowledge" / "chinese_reference" /
    "C_llm_distilled" / "_logs" / "llm_audit_log.jsonl"
)

# 提示词模板目录
PROMPT_TEMPLATES_DIR = (
    PROJECT_ROOT / "data" / "knowledge" / "chinese_reference" /
    "C_llm_distilled" / "_metadata" / "prompt_templates"
)

# 蒸馏数据输出目录
DISTILLED_DIR = (
    PROJECT_ROOT / "data" / "knowledge" / "chinese_reference" /
    "C_llm_distilled"
)


def _get_master_key() -> bytes:
    """获取主密钥

    优先从环境变量 HEALTH_MAN_MASTER_KEY 读取，
    若未设置则使用项目路径派生的开发密钥（仅用于本地开发）。
    """
    env_key = os.environ.get("HEALTH_MAN_MASTER_KEY")
    if env_key:
        return env_key.encode("utf-8")
    # 开发环境默认密钥：基于项目路径的确定性派生
    dev_seed = str(PROJECT_ROOT).encode("utf-8")
    return hashlib.sha256(dev_seed).digest()


def get_credential_manager() -> CredentialManager:
    """获取已配置的 CredentialManager 实例

    Returns:
        CredentialManager（storage_dir 和 master_key 已正确设置）
    """
    return CredentialManager(
        storage_dir=CREDENTIALS_DIR,
        master_key=_get_master_key(),
    )


def get_audit_logger() -> AuditLogger:
    """获取已配置的 AuditLogger 实例

    Returns:
        AuditLogger（日志路径指向 C_llm_distilled/_logs/）
    """
    return AuditLogger(log_path=AUDIT_LOG_PATH)


def get_prompt_templates_dir() -> Path:
    """获取提示词模板目录路径"""
    return PROMPT_TEMPLATES_DIR


def get_distilled_dir() -> Path:
    """获取蒸馏数据输出目录路径"""
    return DISTILLED_DIR
