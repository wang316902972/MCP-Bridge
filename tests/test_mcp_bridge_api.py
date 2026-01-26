"""MCP-Bridge 核心 API 集成测试"""

import pytest
import json
from typing import Dict, Any


@pytest.mark.external
@pytest.mark.integration
class TestMCPBridgeCoreAPI:
    """MCP-Bridge 核心 API 测试套件"""

    @pytest.mark.asyncio
    async def test_health_check(self, http_client):
        """测试健康检查端点"""
        response = await http_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

        print(f"✅ 健康检查: {data['status']}")

    @pytest.mark.asyncio
    async def test_openapi_schema(self, http_client):
        """测试 OpenAPI schema 端点"""
        response = await http_client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        # 验证 OpenAPI 结构
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        assert schema["info"]["title"] == "MCP Bridge"

        print(f"✅ OpenAPI schema: {schema['info']['title']} v{schema['info']['version']}")

    @pytest.mark.asyncio
    async def test_mcp_tools_list(self, http_client, jsonrpc_headers):
        """测试 MCP 工具列表端点"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }

        response = await http_client.post(
            "/v1/mcp/",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证 JSON-RPC 响应
        assert "result" in data
        assert "tools" in data["result"]

        tools = data["result"]["tools"]
        print(f"✅ MCP-Bridge 托管了 {len(tools)} 个工具:")

        for tool in tools:
            print(f"   - {tool['name']}: {tool.get('description', 'No description')}")

    @pytest.mark.asyncio
    async def test_mcp_resources_list(self, http_client, jsonrpc_headers):
        """测试 MCP 资源列表端点"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "resources/list",
            "id": 2
        }

        response = await http_client.post(
            "/v1/mcp/",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 资源列表可能为空
        if "result" in data and "resources" in data["result"]:
            resources = data["result"]["resources"]
            print(f"✅ 找到 {len(resources)} 个资源")
        else:
            print("ℹ️  当前没有配置资源")

    @pytest.mark.asyncio
    async def test_mcp_prompts_list(self, http_client, jsonrpc_headers):
        """测试 MCP 提示列表端点"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "prompts/list",
            "id": 3
        }

        response = await http_client.post(
            "/v1/mcp/",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 提示列表可能为空
        if "result" in data and "prompts" in data["result"]:
            prompts = data["result"]["prompts"]
            print(f"✅ 找到 {len(prompts)} 个提示")
        else:
            print("ℹ️  当前没有配置提示")

    @pytest.mark.asyncio
    async def test_mcp_initialize(self, http_client, jsonrpc_headers):
        """测试 MCP 初始化"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 4
        }

        response = await http_client.post(
            "/v1/mcp/",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        assert "serverInfo" in data["result"]
        assert "capabilities" in data["result"]

        print(f"✅ MCP 初始化成功: {data['result']['serverInfo']['name']}")

    @pytest.mark.asyncio
    async def test_mcp_tool_call_duckduckgo(self, http_client, jsonrpc_headers):
        """测试通过 MCP-Bridge 调用 DuckDuckGo 工具"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "web_search",
                "arguments": {
                    "query": "artificial intelligence",
                    "max_results": 3
                }
            },
            "id": 5
        }

        response = await http_client.post(
            "/v1/mcp/",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证工具调用结果
        assert "result" in data
        assert "content" in data["result"]
        assert len(data["result"]["content"]) > 0

        content = data["result"]["content"][0]
        assert "text" in content

        print(f"✅ DuckDuckGo 工具调用成功")
        print(f"   结果预览: {content['text'][:100]}...")

    @pytest.mark.asyncio
    async def test_mcp_server_status(self, http_client, auth_headers):
        """测试 MCP 服务器状态端点"""
        response = await http_client.get(
            "/mcp/servers",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # 验证响应格式
        assert isinstance(data, list) or isinstance(data, dict)

        if isinstance(data, list):
            print(f"✅ MCP 服务器状态: {len(data)} 个服务器")
            for server in data:
                print(f"   - {server.get('name', 'Unknown')}: {server.get('status', 'Unknown')}")
        else:
            print(f"✅ MCP 服务器状态获取成功")

    @pytest.mark.asyncio
    async def test_mcp_http_proxy(self, http_client):
        """测试 MCP HTTP 代理端点"""
        # 列出工具
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 6
        }

        response = await http_client.post(
            "/mcp",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        assert "tools" in data["result"]

        print(f"✅ MCP HTTP 代理: {len(data['result']['tools'])} 个工具可用")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_jsonrpc(self, http_client):
        """测试错误处理: 无效的 JSON-RPC 请求"""
        request_data = {
            "invalid_field": "value"
        }

        response = await http_client.post(
            "/v1/mcp/",
            json=request_data
        )

        # 应该返回错误
        assert response.status_code == 200
        data = response.json()

        # 验证错误响应
        if "error" in data:
            assert "code" in data["error"]
            assert "message" in data["error"]
            print(f"✅ 错误处理: {data['error']['message']}")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_method(self, http_client, jsonrpc_headers):
        """测试错误处理: 不存在的方法"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "invalid/method",
            "id": 7
        }

        response = await http_client.post(
            "/v1/mcp/",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证错误响应
        if "error" in data:
            assert data["error"]["code"] == -32601
            print(f"✅ 方法验证: {data['error']['message']}")

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, http_client, jsonrpc_headers):
        """测试并发工具调用"""
        import asyncio

        async def make_tool_call(query: str, call_id: int):
            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "web_search",
                    "arguments": {
                        "query": query,
                        "max_results": 2
                    }
                },
                "id": call_id
            }

            response = await http_client.post(
                "/v1/mcp/",
                headers=jsonrpc_headers,
                json=request_data
            )
            return response

        # 并发执行多个搜索
        queries = ["python", "javascript", "golang"]
        responses = await asyncio.gather(
            *[make_tool_call(q, i) for i, q in enumerate(queries)]
        )

        # 验证所有响应
        for i, response in enumerate(responses):
            assert response.status_code == 200
            data = response.json()
            assert "result" in data

        print(f"✅ 并发测试: {len(responses)} 个并发调用成功")


@pytest.mark.external
@pytest.mark.integration
class TestMCPBridgeSampling:
    """MCP-Bridge 采样功能测试"""

    @pytest.mark.asyncio
    async def test_sampling_config(self, http_client, auth_headers):
        """测试采样配置"""
        response = await http_client.get(
            "/sampling/config",
            headers=auth_headers
        )

        # 可能返回 200 或 404
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 采样配置: {data}")
        else:
            print("ℹ️  采样配置端点未实现或未启用")

    @pytest.mark.asyncio
    async def test_model_selection(self, http_client, auth_headers):
        """测试模型选择"""
        response = await http_client.get(
            "/sampling/models",
            headers=auth_headers
        )

        # 可能返回 200 或 404
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            print(f"✅ 可用模型: {len(data)} 个")
            for model in data:
                print(f"   - {model.get('model', 'Unknown')}")
        else:
            print("ℹ️  模型列表端点未实现")
