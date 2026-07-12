"""GLM-4-Flash 模型适配器

智谱 AI GLM-4-Flash 实现：完全免费、128K 上下文、OpenAI 兼容协议。
复用 Phase 1-2 的安全工具链：TokenBucketLimiter + CircuitBreaker + retry_with_backoff + AuditLogger。
"""
import logging
import time
from typing import Any

import requests

from scripts.llm.model_adapter import ModelAdapter
from scripts.utils.audit_logger import AuditLogger
from scripts.utils.circuit_breaker import CircuitBreaker
from scripts.utils.rate_limiter import TokenBucketLimiter
from scripts.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# GLM-4-Flash 默认配置
GLM_DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
GLM_MODEL_ID = "glm-4-flash"
GLM_CONTEXT_LENGTH = 128000


class GlmAdapter(ModelAdapter):
    """GLM-4-Flash 模型适配器

    Args:
        api_key: GLM API 密钥
        base_url: API 基础 URL
        max_tokens: 单次响应最大 token 数
        temperature: 采样温度（0.1 保证稳定性）
        timeout: API 超时秒数
        rate_limiter: 令牌桶限流器（可选）
        circuit_breaker: 熔断器（可选）
        audit_logger: 审计日志器（可选）
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = GLM_DEFAULT_BASE_URL,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        timeout: int = 60,
        rate_limiter: TokenBucketLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        audit_logger: AuditLogger | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.audit_logger = audit_logger

    def chat(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        """调用 GLM-4-Flash 进行对话

        Returns:
            含 content, tokens_used, model_id, latency_ms 的字典
        """
        # 限流检查
        if self.rate_limiter and not self.rate_limiter.acquire():
            raise RuntimeError("Rate limit exceeded: token bucket empty")

        # 熔断检查
        if self.circuit_breaker and not self.circuit_breaker.can_call():
            raise RuntimeError("Circuit breaker is OPEN: model unavailable")

        start_time = time.monotonic()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        def _do_request() -> dict[str, Any]:
            """实际的 API 请求（供 retry_with_backoff 包装）"""
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": GLM_MODEL_ID,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
            resp = requests.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()

        # 带重试的 API 调用
        # retry_with_backoff 是装饰器工厂，需先构建装饰器再应用到 _do_request 上后调用
        try:
            data = retry_with_backoff(
                max_retries=2, base_delay=5.0,
                exceptions=(requests.RequestException,),
            )(_do_request)()
        except Exception as e:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            if self.audit_logger:
                self.audit_logger.log(
                    operation="llm_call", target=GLM_MODEL_ID,
                    success=False, error=str(e),
                )
            raise

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # 解析响应
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)

        # 记录成功
        if self.circuit_breaker:
            self.circuit_breaker.record_success()
        if self.audit_logger:
            self.audit_logger.log(
                operation="llm_call", target=GLM_MODEL_ID,
                success=True, tokens_used=tokens_used,
                latency_ms=latency_ms,
            )

        logger.info("GLM 调用成功: %d tokens, %dms", tokens_used, latency_ms)
        return {
            "content": content,
            "tokens_used": tokens_used,
            "model_id": GLM_MODEL_ID,
            "latency_ms": latency_ms,
        }

    def health_check(self) -> bool:
        """检查 GLM-4-Flash 是否可用"""
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": GLM_MODEL_ID,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }
            resp = requests.post(
                url, json=payload, headers=headers, timeout=10
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_model_info(self) -> dict[str, Any]:
        """返回 GLM-4-Flash 模型信息"""
        return {
            "model_id": GLM_MODEL_ID,
            "provider": "zhipu",
            "context_length": GLM_CONTEXT_LENGTH,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
