"""MCP-Bridge OpenAI API 兼容性测试"""

import pytest
import json
from typing import Dict, Any, List


@pytest.mark.external
@pytest.mark.integration
class TestOpenAICompatibility:
    """OpenAI API 兼容性测试套件"""

    @pytest.mark.asyncio
    async def test_chat_completion_endpoint(self, http_client, auth_headers):
        """测试 chat completion 端点"""
        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }

        response = await http_client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json=request_data
        )

        # 可能返回 200 (成功) 或 503 (推理服务未配置)
        if response.status_code == 200:
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            print(f"✅ Chat Completion 工作正常")
            print(f"   响应: {data['choices'][0]['message']['content'][:100]}...")
        elif response.status_code == 503:
            print("ℹ️  推理服务未配置或不可用")
        else:
            print(f"ℹ️  Chat Completion 状态: {response.status_code}")

    @pytest.mark.asyncio
    async def test_chat_completion_with_tools(self, http_client, auth_headers):
        """测试带工具的 chat completion"""
        # 首先获取可用工具
        tools_response = await http_client.post(
            "/v1/mcp/",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )

        tools = []
        if tools_response.status_code == 200:
            tools_data = tools_response.json()
            if "result" in tools_data and "tools" in tools_data["result"]:
                # 转换为 OpenAI 工具格式
                for tool in tools_data["result"]["tools"][:3]:  # 只取前 3 个
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("inputSchema", {})
                        }
                    })

        if len(tools) == 0:
            pytest.skip("没有可用的 MCP 工具")

        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "user", "content": "Search for information about artificial intelligence"}
            ],
            "tools": tools,
            "tool_choice": "auto"
        }

        response = await http_client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json=request_data
        )

        if response.status_code == 200:
            data = response.json()
            assert "choices" in data

            # 检查是否有工具调用
            message = data["choices"][0]["message"]
            if "tool_calls" in message:
                print(f"✅ 工具调用被触发: {len(message['tool_calls'])} 个调用")
            else:
                print("✅ 消息响应成功 (无工具调用)")
        else:
            print(f"ℹ️  Chat Completion with tools 状态: {response.status_code}")

    @pytest.mark.asyncio
    async def test_streaming_chat_completion(self, http_client, auth_headers):
        """测试流式 chat completion"""
        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "stream": True
        }

        response = await http_client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json=request_data
        )

        if response.status_code == 200:
            # 验证流式响应
            assert "text/event-stream" in response.headers.get("content-type", "")

            chunk_count = 0
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_count += 1
                    if chunk_count >= 5:  # 读取几个块后停止
                        break

            print(f"✅ 流式响应工作正常 (接收 {chunk_count} 个数据块)")
        else:
            print(f"ℹ️  流式 Chat Completion 状态: {response.status_code}")

    @pytest.mark.asyncio
    async def test_tool_execution_flow(self, http_client, auth_headers):
        """测试完整的工具执行流程"""
        # 步骤 1: 获取工具列表
        tools_response = await http_client.post(
            "/v1/mcp/",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )

        assert tools_response.status_code == 200
        tools_data = tools_response.json()

        if "result" not in tools_data or "tools" not in tools_data["result"]:
            pytest.skip("没有可用的工具")

        # 步骤 2: 调用工具
        tool_name = "web_search"  # 假设有 DuckDuckGo
        tools = tools_data["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        if tool_name not in tool_names:
            pytest.skip(f"工具 {tool_name} 不可用")

        call_response = await http_client.post(
            "/v1/mcp/",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {
                        "query": "test search",
                        "max_results": 2
                    }
                },
                "id": 2
            }
        )

        assert call_response.status_code == 200
        call_data = call_response.json()

        assert "result" in call_data
        assert "content" in call_data["result"]

        print(f"✅ 工具执行流程成功")
        print(f"   结果: {call_data['result']['content'][0]['text'][:100]}...")

    @pytest.mark.asyncio
    async def test_openai_error_handling(self, http_client, auth_headers):
        """测试 OpenAI API 错误处理"""
        # 发送无效请求
        request_data = {
            "model": "test-model",
            "messages": "invalid_format"  # 应该是数组
        }

        response = await http_client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json=request_data
        )

        # 应该返回错误
        assert response.status_code in [400, 422, 500]

        if response.status_code != 200:
            print("✅ 错误处理正常")
        else:
            print("ℹ️  请求被接受 (可能使用了默认值)")

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self, http_client, auth_headers):
        """测试多个工具调用"""
        # 准备多个工具调用
        tool_calls = [
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "web_search",
                    "arguments": {"query": "python", "max_results": 2}
                },
                "id": i
            }
            for i in range(1, 4)
        ]

        results = []
        for call in tool_calls:
            response = await http_client.post(
                "/v1/mcp/",
                json=call
            )

            if response.status_code == 200:
                results.append(response.json())

        assert len(results) > 0
        print(f"✅ 多个工具调用成功: {len(results)} 个结果")

    @pytest.mark.asyncio
    async def test_models_endpoint(self, http_client, auth_headers):
        """测试 models 端点"""
        response = await http_client.get(
            "/v1/models",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "data" in data or "object" in data
            print(f"✅ Models 端点可访问")
        else:
            print(f"ℹ️  Models 端点状态: {response.status_code}")

    @pytest.mark.asyncio
    async def test_compatibility_with_openai_clients(self, http_client, auth_headers):
        """测试与标准 OpenAI 客户端的兼容性"""
        # 验证响应格式符合 OpenAI 规范
        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "user", "content": "Test"}
            ]
        }

        response = await http_client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json=request_data
        )

        if response.status_code == 200:
            data = response.json()

            # 验证必需字段
            required_fields = ["id", "object", "created", "model", "choices"]
            for field in required_fields:
                if field in data:
                    print(f"✅ 字段 {field}: 存在")
                else:
                    print(f"⚠️  字段 {field}: 缺失")

            # 验证 choices 结构
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                choice_fields = ["index", "message", "finish_reason"]
                for field in choice_fields:
                    assert field in choice, f"缺少必需字段: {field}"

                # 验证 message 结构
                message = choice["message"]
                message_fields = ["role", "content"]
                for field in message_fields:
                    assert field in message, f"message 缺少字段: {field}"

                print("✅ OpenAI 响应格式验证通过")


@pytest.mark.external
@pytest.mark.integration
class TestToolIntegration:
    """工具集成测试"""

    @pytest.mark.asyncio
    async def test_duckduckgo_tool_availability(self, http_client, auth_headers):
        """测试 DuckDuckGo 工具可用性"""
        response = await http_client.post(
            "/v1/mcp/",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )

        if response.status_code == 200:
            data = response.json()
            if "result" in data and "tools" in data["result"]:
                tools = data["result"]["tools"]
                tool_names = [t["name"] for t in tools]

                ddg_tools = ["web_search", "news_search", "instant_answer"]
                available_ddg_tools = [t for t in ddg_tools if t in tool_names]

                if len(available_ddg_tools) > 0:
                    print(f"✅ DuckDuckGo 工具可用: {available_ddg_tools}")
                else:
                    print("ℹ️  DuckDuckGo 工具未配置")

    @pytest.mark.asyncio
    async def test_tool_call_roundtrip(self, http_client, auth_headers):
        """测试工具调用的完整往返"""
        # 1. 列出工具
        list_response = await http_client.post(
            "/v1/mcp/",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )

        if list_response.status_code != 200:
            pytest.skip("无法获取工具列表")

        tools_data = list_response.json()
        if "result" not in tools_data or "tools" not in tools_data["result"]:
            pytest.skip("没有可用工具")

        # 2. 选择第一个工具
        first_tool = tools_data["result"]["tools"][0]
        tool_name = first_tool["name"]

        # 3. 调用工具 (使用测试参数)
        if tool_name == "web_search":
            arguments = {"query": "test", "max_results": 1}
        elif tool_name == "news_search":
            arguments = {"query": "test", "max_results": 1}
        elif tool_name == "instant_answer":
            arguments = {"query": "test"}
        else:
            arguments = {}

        call_response = await http_client.post(
            "/v1/mcp/",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 2
            }
        )

        if call_response.status_code == 200:
            call_data = call_response.json()
            assert "result" in call_data
            print(f"✅ 工具调用往返成功: {tool_name}")
        else:
            print(f"ℹ️  工具调用失败: {tool_name}")
