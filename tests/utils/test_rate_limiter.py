# e:\Health_man\tests\utils\test_rate_limiter.py
"""测试令牌桶限流器"""
import time

from scripts.utils.rate_limiter import TokenBucketLimiter


def test_first_request_allowed():
    """首次请求必须允许"""
    limiter = TokenBucketLimiter(capacity=5, refill_rate=1.0)
    assert limiter.acquire() is True


def test_capacity_exhausted():
    """超过容量后必须拒绝"""
    limiter = TokenBucketLimiter(capacity=2, refill_rate=0.0)
    assert limiter.acquire() is True
    assert limiter.acquire() is True
    assert limiter.acquire() is False


def test_refill_over_time():
    """令牌必须随时间填充"""
    limiter = TokenBucketLimiter(capacity=2, refill_rate=100.0)  # 每秒 100 个
    # 耗尽
    limiter.acquire()
    limiter.acquire()
    assert limiter.acquire() is False
    # 等待填充
    time.sleep(0.05)
    assert limiter.acquire() is True
