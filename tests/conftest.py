"""MCP-Bridge 测试配置和共享 fixtures"""

import asyncio
import json
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

# 跳过本地代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'


class TestConfig:
    """测试配置"""

    # MCP-Bridge 服务地址
    MCP_BRIDGE_URL = os.getenv("MCP_BRIDGE_URL", "http://localhost:8004")

    # DuckDuckGo MCP 服务地址
    DUCKDUCKGO_MCP_URL = os.getenv("DUCKDUCKGO_MCP_URL", "http://localhost:8005")

    # 测试 API Key (如果启用了认证)
    API_KEY = os.getenv("TEST_API_KEY", "test-api-key")

    # 测试超时时间
    TIMEOUT = 10.0

    # 是否跳过需要外部服务的测试
    SKIP_EXTERNAL = os.getenv("SKIP_EXTERNAL_TESTS", "false").lower() == "true"


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """提供测试配置"""
    return TestConfig


@pytest_asyncio.fixture
async def http_client(test_config: TestConfig) -> AsyncGenerator[AsyncClient, None]:
    """提供异步 HTTP 客户端"""
    async with AsyncClient(base_url=test_config.MCP_BRIDGE_URL, timeout=test_config.TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def ddg_mcp_client(test_config: TestConfig) -> AsyncGenerator[AsyncClient, None]:
    """提供 DuckDuckGo MCP 客户端"""
    async with AsyncClient(base_url=test_config.DUCKDUCKGO_MCP_URL, timeout=test_config.TIMEOUT) as client:
        yield client


@pytest.fixture
def auth_headers(test_config: TestConfig) -> Dict[str, str]:
    """提供认证头"""
    return {"Authorization": f"Bearer {test_config.API_KEY}"}


@pytest.fixture
def jsonrpc_headers() -> Dict[str, str]:
    """提供 JSON-RPC 请求头"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


@pytest.fixture
def jsonrpc_request() -> Dict[str, Any]:
    """基础 JSON-RPC 请求模板"""
    return {
        "jsonrpc": "2.0",
        "id": 1
    }


@pytest.fixture
def sample_search_query() -> str:
    """示例搜索查询"""
    return "artificial intelligence"


@pytest.fixture
def sample_news_query() -> str:
    """示例新闻查询"""
    return "technology news"


@pytest.fixture
def sample_instant_answer_query() -> str:
    """示例即时答案查询"""
    return "capital of France"


def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "unit: 单元测试标记"
    )
    config.addinivalue_line(
        "markers", "external: 需要外部服务的测试"
    )
    config.addinivalue_line(
        "markers", "duckduckgo: DuckDuckGo MCP 相关测试"
    )
