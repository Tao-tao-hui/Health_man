# e:\Health_man\scripts\utils\rate_limiter.py
"""令牌桶限流器

原理：
- 桶容量为 capacity，初始满
- 每秒按 refill_rate 速率填充令牌
- 每次请求消耗 1 个令牌
- 令牌不足时拒绝请求
"""
import time


class TokenBucketLimiter:
    """令牌桶限流器

    Args:
        capacity: 桶容量（最大突发量）
        refill_rate: 令牌填充速率（个/秒）
    """

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()

    def acquire(self) -> bool:
        """尝试获取 1 个令牌

        Returns:
            True=获取成功；False=令牌不足
        """
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False
