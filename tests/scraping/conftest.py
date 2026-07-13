# tests/scraping/conftest.py
"""测试配置文件

为 scraping 模块提供共享的 pytest fixtures。
"""
import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（pytest-asyncio 需要）"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
