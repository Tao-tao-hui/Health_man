# e:\Health_man\tests\utils\test_circuit_breaker.py
"""测试熔断器"""
import pytest

from scripts.utils.circuit_breaker import CircuitBreaker, CircuitState


def test_initial_state_is_closed():
    """初始状态必须为 CLOSED"""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    assert cb.state == CircuitState.CLOSED


def test_opens_after_threshold():
    """达到失败阈值后必须 OPEN"""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_blocks_calls_when_open():
    """OPEN 状态必须阻止调用"""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_call() is False


def test_half_open_after_timeout():
    """超时后必须 HALF_OPEN"""
    import time
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.15)
    assert cb.can_call() is True  # HALF_OPEN 允许探测
