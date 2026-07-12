# e:\Health_man\scripts\utils\circuit_breaker.py
"""三态熔断器

状态：
- CLOSED: 正常，请求通过
- OPEN: 熔断，拒绝请求
- HALF_OPEN: 探测，允许单个请求
"""
import enum
import time


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """三态熔断器

    Args:
        failure_threshold: 触发熔断的连续失败次数
        recovery_timeout: 熔断后冷却时间（秒）
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        """当前状态（含自动 HALF_OPEN 转换）"""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def can_call(self) -> bool:
        """是否允许调用"""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            return True
        return False  # OPEN

    def record_success(self) -> None:
        """记录成功"""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
