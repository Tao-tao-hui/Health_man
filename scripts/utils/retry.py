# e:\Health_man\scripts\utils\retry.py
"""重试退避工具

提供指数退避重试装饰器，支持：
- 最大重试次数
- 基础延迟与指数倍数
- 可指定捕获的异常类型
"""
import functools
import logging
import random
import time
from typing import Callable, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """指数退避重试装饰器

    Args:
        max_retries: 最大重试次数（不含首次调用）
        base_delay: 基础延迟（秒），实际延迟 = base_delay * 2^attempt + jitter
        exceptions: 捕获的异常类型

    Returns:
        装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(
                            "重试 %s (attempt %d/%d): %s, 等待 %.2fs",
                            func.__name__, attempt + 1, max_retries, str(e), delay,
                        )
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
