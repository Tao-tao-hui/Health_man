# e:\Health_man\tests\utils\test_retry.py
"""测试重试退避"""
import time
import pytest

from scripts.utils.retry import retry_with_backoff


def test_retry_succeeds_on_first_attempt():
    """首次成功不重试"""
    call_count = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def success_func():
        call_count["n"] += 1
        return "ok"

    result = success_func()
    assert result == "ok"
    assert call_count["n"] == 1


def test_retry_succeeds_after_failures():
    """前 N 次失败后成功"""
    call_count = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def flaky_func():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ValueError("fail")
        return "ok"

    result = flaky_func()
    assert result == "ok"
    assert call_count["n"] == 3


def test_retry_exhausted_raises():
    """重试耗尽后必须抛出最后异常"""
    @retry_with_backoff(max_retries=2, base_delay=0.01)
    def always_fail():
        raise ValueError("always fails")

    with pytest.raises(ValueError, match="always fails"):
        always_fail()
