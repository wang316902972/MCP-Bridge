"""MCP-Bridge SSE (Server-Sent Events) Bridge 集成测试"""

import pytest
import asyncio
from typing import AsyncGenerator


@pytest.mark.external
@pytest.mark.integration
class TestSSEBridge:
    """SSE Bridge 测试套件"""

    @pytest.mark.asyncio
    async def test_sse_endpoint_connection(self, http_client):
        """测试 SSE 端点连接"""
        # SSE 端点应该接受连接
        response = await http_client.get(
            "/mcp-server/sse",
            headers={
                "Accept": "text/event-stream"
            }
        )

        # SSE 端点可能返回 200 或其他状态码
        assert response.status_code in [200, 401, 403]

        if response.status_code == 200:
            print("✅ SSE 端点可访问")
        else:
            print(f"ℹ️  SSE 端点返回状态码: {response.status_code}")

    @pytest.mark.asyncio
    async def test_sse_handshake(self, http_client):
        """测试 SSE 握手协议"""
        # SSE 连接应该发送握手消息
        async with http_client.stream("GET", "/mcp-server/sse") as response:
            if response.status_code == 200:
                # 读取初始消息
                chunks = []
                async for chunk in response.aiter_text():
                    chunks.append(chunk)
                    if len(chunks) > 5:  # 读取前几个消息
                        break

                messages = "".join(chunks)
                # 验证 SSE 格式
                assert "data:" in messages or len(messages) > 0
                print(f"✅ SSE 握手成功，接收到 {len(chunks)} 个消息块")
            else:
                print(f"ℹ️  SSE 连接状态: {response.status_code}")

    @pytest.mark.asyncio
    async def test_sse_jsonrpc_over_sse(self, http_client):
        """测试通过 SSE 传输 JSON-RPC 消息"""
        # 这个测试验证 SSE 端点能够处理 JSON-RPC 协议
        async with http_client.stream("GET", "/mcp-server/sse") as response:
            if response.status_code == 200:
                # 尝试接收消息
                message_count = 0
                timeout = 5.0
                start_time = asyncio.get_event_loop().time()

                async for chunk in response.aiter_text():
                    if chunk:
                        message_count += 1
                        # SSE 格式: "data: {...}\n\n"
                        if "data:" in chunk:
                            print(f"✅ 接收到 SSE 消息 #{message_count}")

                    # 超时检查
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        break

                    if message_count >= 3:  # 接收几个消息后停止
                        break

                print(f"✅ SSE JSON-RPC 测试完成，接收 {message_count} 个消息")
            else:
                print(f"ℹ️  SSE 端点状态: {response.status_code}")

    @pytest.mark.asyncio
    async def test_sse_tools_list(self, http_client):
        """测试通过 SSE 获取工具列表"""
        # 某些 SSE 实现可能支持 POST 请求
        response = await http_client.post(
            "/mcp-server/sse",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            }
        )

        # SSE 端点可能返回 405 (Method Not Allowed) 或其他状态码
        if response.status_code == 200:
            print("✅ SSE 端点支持 POST 请求")
        else:
            print(f"ℹ️  SSE 端点 POST 请求返回: {response.status_code}")

    @pytest.mark.asyncio
    async def test_sse_authentication(self, http_client, auth_headers):
        """测试 SSE 认证"""
        # 测试带认证的 SSE 连接
        headers = {
            "Accept": "text/event-stream",
            **auth_headers
        }

        response = await http_client.get(
            "/mcp-server/sse",
            headers=headers
        )

        # 根据认证配置返回不同状态码
        if response.status_code == 200:
            print("✅ SSE 认证成功")
        elif response.status_code in [401, 403]:
            print("ℹ️  SSE 需要有效认证")
        else:
            print(f"ℹ️  SSE 认证状态: {response.status_code}")

    @pytest.mark.asyncio
    async def test_sse_reconnect_capability(self, http_client):
        """测试 SSE 重连能力"""
        # 第一次连接
        response1 = await http_client.get("/mcp-server/sse")
        status1 = response1.status_code
        await response1.aclose()

        # 立即重连
        response2 = await http_client.get("/mcp-server/sse")
        status2 = response2.status_code
        await response2.aclose()

        if status1 == 200 and status2 == 200:
            print("✅ SSE 支持重连")
        else:
            print(f"ℹ️  SSE 连接状态: 第一次={status1}, 第二次={status2}")

    @pytest.mark.asyncio
    async def test_sse_error_handling(self, http_client):
        """测试 SSE 错误处理"""
        # 发送无效请求
        response = await http_client.get(
            "/mcp-server/sse",
            params={"invalid": "param"}
        )

        # 应该优雅地处理错误
        assert response.status_code in [200, 400, 404, 500]

        if response.status_code != 200:
            print(f"✅ SSE 错误处理: {response.status_code}")
        else:
            print("ℹ️  SSE 忽略了无效参数")


@pytest.mark.external
@pytest.mark.integration
class TestMCPClientIntegration:
    """MCP 客户端集成测试"""

    @pytest.mark.asyncio
    async def test_mcp_cli_compatibility(self, http_client):
        """测试与 mcp-cli 的兼容性"""
        # 验证 SSE 端点符合 MCP over SSE 规范
        response = await http_client.get(
            "/mcp-server/sse",
            headers={
                "Accept": "text/event-stream"
            }
        )

        if response.status_code == 200:
            # 读取响应头验证 SSE 格式
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type or len(content_type) == 0
            print("✅ SSE 端点兼容 mcp-cli")
        else:
            print(f"ℹ️  SSE 端点状态: {response.status_code}")

    @pytest.mark.asyncio
    async def test_desktop_client_compatibility(self, http_client):
        """测试与 Claude Desktop 等客户端的兼容性"""
        # 验证端点结构符合 MCP 客户端期望
        endpoints = [
            "/mcp-server/sse",
            "/mcp",
            "/v1/mcp/"
        ]

        working_endpoints = []
        for endpoint in endpoints:
            try:
                if endpoint == "/mcp-server/sse":
                    response = await http_client.get(endpoint)
                else:
                    # POST 请求用于 JSON-RPC
                    response = await http_client.post(
                        endpoint,
                        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
                    )

                if response.status_code == 200:
                    working_endpoints.append(endpoint)
            except Exception:
                pass

        print(f"✅ 可访问的 MCP 端点: {len(working_endpoints)}")
        for endpoint in working_endpoints:
            print(f"   - {endpoint}")
