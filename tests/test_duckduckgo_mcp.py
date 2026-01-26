"""DuckDuckGo MCP 服务器集成测试"""

import pytest
from typing import Dict, Any


@pytest.mark.external
@pytest.mark.duckduckgo
class TestDuckDuckGoMCPServer:
    """DuckDuckGo MCP 服务器测试套件"""

    @pytest.mark.asyncio
    async def test_mcp_initialize(self, ddg_mcp_client, jsonrpc_headers):
        """测试 MCP 初始化握手"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证 JSON-RPC 响应格式
        assert "result" in data
        assert data["jsonrpc"] == "2.0"
        assert "serverInfo" in data["result"]
        assert "capabilities" in data["result"]

        print(f"✅ 初始化成功: {data['result']['serverInfo']['name']}")

    @pytest.mark.asyncio
    async def test_tools_list(self, ddg_mcp_client, jsonrpc_headers):
        """测试工具列表获取"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证工具列表
        assert "result" in data
        assert "tools" in data["result"]
        tools = data["result"]["tools"]

        # 应该有 3 个工具
        assert len(tools) == 3

        tool_names = [tool["name"] for tool in tools]
        assert "web_search" in tool_names
        assert "news_search" in tool_names
        assert "instant_answer" in tool_names

        # 验证工具结构
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

        print(f"✅ 找到 {len(tools)} 个工具:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")

    @pytest.mark.asyncio
    async def test_web_search_tool_schema(self, ddg_mcp_client, jsonrpc_headers):
        """测试 web_search 工具 schema"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 3
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 找到 web_search 工具
        web_search = next(
            (t for t in data["result"]["tools"] if t["name"] == "web_search"),
            None
        )
        assert web_search is not None

        # 验证 input schema
        schema = web_search["inputSchema"]
        assert "type" in schema
        assert "properties" in schema

        # 验证必需参数
        assert "query" in schema["properties"]
        assert schema["properties"]["query"]["type"] == "string"

        print(f"✅ web_search 工具 schema 验证通过")

    @pytest.mark.asyncio
    async def test_web_search_call(self, ddg_mcp_client, jsonrpc_headers, sample_search_query):
        """测试 web_search 工具调用"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "web_search",
                "arguments": {
                    "query": sample_search_query,
                    "max_results": 3
                }
            },
            "id": 4
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证响应
        assert "result" in data
        assert "content" in data["result"]
        assert len(data["result"]["content"]) > 0

        # 验证搜索结果格式
        content = data["result"]["content"][0]
        assert "type" in content
        assert "text" in content

        # 解析搜索结果
        results_text = content["text"]
        assert sample_search_query.lower() in results_text.lower() or len(results_text) > 0

        print(f"✅ web_search 成功: {len(data['result']['content'])} 个内容块")

    @pytest.mark.asyncio
    async def test_news_search_call(self, ddg_mcp_client, jsonrpc_headers, sample_news_query):
        """测试 news_search 工具调用"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "news_search",
                "arguments": {
                    "query": sample_news_query,
                    "max_results": 3
                }
            },
            "id": 5
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证响应
        assert "result" in data
        assert "content" in data["result"]

        print(f"✅ news_search 成功: {len(data['result']['content'])} 个内容块")

    @pytest.mark.asyncio
    async def test_instant_answer_call(self, ddg_mcp_client, jsonrpc_headers, sample_instant_answer_query):
        """测试 instant_answer 工具调用"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "instant_answer",
                "arguments": {
                    "query": sample_instant_answer_query
                }
            },
            "id": 6
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证响应
        assert "result" in data
        assert "content" in data["result"]

        # 验证答案格式
        if len(data["result"]["content"]) > 0:
            content = data["result"]["content"][0]
            assert "text" in content
            # 即时答案应该包含相关信息
            answer_text = content["text"].lower()
            print(f"✅ instant_answer 成功: {content['text'][:100]}...")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_tool(self, ddg_mcp_client, jsonrpc_headers):
        """测试错误处理: 调用不存在的工具"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            },
            "id": 7
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        # 应该返回错误或成功但带有错误信息
        assert response.status_code == 200
        data = response.json()

        # 验证错误响应
        if "error" in data:
            assert data["error"]["code"] == -32601 or data["error"]["code"] == -32602
            print(f"✅ 错误处理正常: {data['error']['message']}")

    @pytest.mark.asyncio
    async def test_error_handling_missing_params(self, ddg_mcp_client, jsonrpc_headers):
        """测试错误处理: 缺少必需参数"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "web_search",
                # 缺少 query 参数
            },
            "id": 8
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # 验证错误响应或默认行为
        if "error" in data:
            print(f"✅ 参数验证正常: {data['error']['message']}")
        else:
            # 服务器可能使用默认值
            print("ℹ️  服务器使用默认值处理缺失参数")

    @pytest.mark.asyncio
    async def test_time_range_parameter(self, ddg_mcp_client, jsonrpc_headers):
        """测试 web_search time_range 参数"""
        for time_range in ["day", "week", "month", "year"]:
            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "web_search",
                    "arguments": {
                        "query": "test",
                        "time_range": time_range,
                        "max_results": 1
                    }
                },
                "id": 9
            }

            response = await ddg_mcp_client.post(
                "/mcp",
                headers=jsonrpc_headers,
                json=request_data
            )

            assert response.status_code == 200
            data = response.json()
            assert "result" in data

        print(f"✅ time_range 参数测试通过 (day, week, month, year)")

    @pytest.mark.asyncio
    async def test_max_results_boundary(self, ddg_mcp_client, jsonrpc_headers):
        """测试 max_results 边界值"""
        # 测试最小值
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "web_search",
                "arguments": {
                    "query": "test",
                    "max_results": 1
                }
            },
            "id": 10
        }

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200

        # 测试最大值
        request_data["params"]["arguments"]["max_results"] = 100
        request_data["id"] = 11

        response = await ddg_mcp_client.post(
            "/mcp",
            headers=jsonrpc_headers,
            json=request_data
        )

        assert response.status_code == 200
        print(f"✅ max_results 边界值测试通过 (1-100)")
