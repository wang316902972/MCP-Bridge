"""MCP HTTP JSON-RPC Proxy Router

提供 /v1/mcp 端点,接收HTTP POST JSON-RPC 2.0请求,
转发到后端MCP服务器,并返回JSON-RPC 2.0响应
"""

from fastapi import APIRouter, Request
from loguru import logger
from mcp import types
from mcp_bridge.gateway import ToolRegistry
from mcp_bridge.mcp_clients.McpClientManager import ClientManager
from mcp_bridge.mcp_http_proxy.models import (
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
)

router = APIRouter(prefix="/v1/mcp", tags=["MCP HTTP Proxy"])


class JSONRPCMethodNotFoundError(Exception):
    pass


@router.post("/")
async def handle_mcp_jsonrpc(request: Request) -> JSONRPCResponse:
    """处理 MCP JSON-RPC 2.0 请求

    接收JSON-RPC 2.0格式的HTTP POST请求,根据方法名路由到相应的MCP操作:

    支持的方法:
    - initialize: 初始化MCP会话
    - tools/list: 列出所有可用工具
    - tools/call: 调用指定工具
    - resources/list: 列出所有资源
    - prompts/list: 列出所有提示
    - notifications/initialized: 初始化完成通知

    请求格式:
    {
        "jsonrpc": "2.0",
        "method": "方法名",
        "params": {参数对象},
        "id": 请求ID
    }

    响应格式:
    {
        "jsonrpc": "2.0",
        "result": {结果对象},
        "id": 请求ID
    }
    """
    try:
        # 解析请求体
        request_data = await request.json()

        # 验证JSON-RPC 2.0基本格式
        if not isinstance(request_data, dict):
            return JSONRPCResponse(
                error=JSONRPCError(
                    code=-32600, message="Invalid Request", data="请求体必须是JSON对象"
                ),
                id=None,
            )

        # 创建JSONRPCRequest对象
        rpc_request = JSONRPCRequest(**request_data)

        # 验证jsonrpc版本
        if rpc_request.jsonrpc != "2.0":
            return JSONRPCResponse(
                error=JSONRPCError(
                    code=-32600, message="Invalid Request", data="只支持JSON-RPC 2.0"
                ),
                id=rpc_request.id,
            )

        # 路由到对应的处理器
        logger.info(f"📥 收到MCP JSON-RPC请求: {rpc_request.method}")

        try:
            result = await _dispatch_method(rpc_request.method, rpc_request.params)

            return JSONRPCResponse(result=result, id=rpc_request.id)

        except JSONRPCMethodNotFoundError as e:
            error_msg = str(e)
            logger.error(f"❌ MCP方法不存在: {rpc_request.method} - {error_msg}")

            return JSONRPCResponse(
                error=JSONRPCError(
                    code=-32601, message="Method not found", data=error_msg
                ),
                id=rpc_request.id,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 处理MCP请求失败: {rpc_request.method} - {error_msg}")

            return JSONRPCResponse(
                error=JSONRPCError(
                    code=-32603, message="Internal error", data=error_msg
                ),
                id=rpc_request.id,
            )

    except Exception as e:
        logger.error(f"❌ 解析请求失败: {e}")

        return JSONRPCResponse(
            error=JSONRPCError(code=-32700, message="Parse error", data=str(e)), id=None
        )


async def _dispatch_method(method: str, params: dict | None):
    """分发方法到对应的处理器"""

    if method == "initialize":
        return await _handle_initialize(params)

    elif method == "tools/list":
        return await _handle_tools_list(params)

    elif method == "tools/call":
        return await _handle_tools_call(params)

    elif method == "resources/list":
        return await _handle_resources_list()

    elif method == "prompts/list":
        return await _handle_prompts_list()

    elif method == "notifications/initialized":
        # 初始化通知,返回空结果
        return {}

    else:
        raise JSONRPCMethodNotFoundError(f"未知的方法: {method}")


async def _handle_initialize(params: dict | None):
    """处理initialize请求"""
    logger.info("🔄 处理initialize请求")

    # 返回服务器能力
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        "serverInfo": {"name": "MCP-Bridge", "version": "0.2.0"},
    }


async def _handle_tools_list(params: dict | None = None):
    """处理tools/list请求"""
    logger.info("🔧 列出可暴露工具")

    tools = await ToolRegistry.list_exposed_tools(ClientManager)
    logger.info(f"✅ 暴露 {len(tools)} 个工具")

    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }
            for tool in tools
        ]
    }


async def _handle_tools_call(params: dict | None):
    """处理tools/call请求"""
    if not params or "name" not in params:
        raise ValueError("缺少工具名称参数")

    tool_name = params["name"]
    arguments = params.get("arguments", {})

    logger.info(f"🔧 调用工具: {tool_name} 参数: {arguments}")

    result = await ToolRegistry.call_exposed_tool(ClientManager, tool_name, arguments)
    return serialize_call_tool_result(result)


def serialize_call_tool_result(result: types.CallToolResult) -> dict:
    content_list = []
    for content in result.content:
        if hasattr(content, "text"):
            content_list.append({"type": "text", "text": content.text})
        elif hasattr(content, "data"):
            content_list.append({"type": content.type, "data": content.data})
        else:
            content_list.append({"type": "text", "text": str(content)})

    return {
        "content": content_list,
        "isError": result.isError if hasattr(result, "isError") else False,
    }


async def _handle_resources_list():
    """处理resources/list请求"""
    logger.info("📚 列出所有资源")

    all_resources = []
    clients = ClientManager.get_clients()

    for name, client in clients:
        try:
            if not client.session:
                continue

            resources_result = await client.session.list_resources()
            all_resources.extend(resources_result.resources)

        except Exception as e:
            logger.error(f"❌ 获取 {name} 资源列表失败: {e}")

    logger.info(f"✅ 找到 {len(all_resources)} 个资源")

    return {
        "resources": [
            {
                "uri": str(resource.uri),
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mimeType,
            }
            for resource in all_resources
        ]
    }


async def _handle_prompts_list():
    """处理prompts/list请求"""
    logger.info("💬 列出所有提示")

    all_prompts = []
    clients = ClientManager.get_clients()

    for name, client in clients:
        try:
            if not client.session:
                continue

            prompts_result = await client.session.list_prompts()
            all_prompts.extend(prompts_result.prompts)

        except Exception as e:
            logger.error(f"❌ 获取 {name} 提示列表失败: {e}")

    logger.info(f"✅ 找到 {len(all_prompts)} 个提示")

    return {
        "prompts": [
            {
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments,
            }
            for prompt in all_prompts
        ]
    }
