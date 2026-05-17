from typing import Optional
from loguru import logger
from lmos_openai_types import CreateChatCompletionRequest
import mcp.types
import json

from mcp_bridge.gateway import ToolRegistry
from mcp_bridge.tool_mappers import mcp2openai


def _get_client_manager():
    from mcp_bridge.mcp_clients.McpClientManager import ClientManager

    return ClientManager


async def chat_completion_add_tools(request: CreateChatCompletionRequest):
    ClientManager = _get_client_manager()
    if request.tools is None:
        request.tools = []

    tools = await ToolRegistry.list_exposed_tools(ClientManager)
    logger.info(f"🔧 Loaded {len(tools)} exposed gateway tools")
    existing_names = {tool.function.name for tool in request.tools}
    mcp_tool_names = set()
    for tool in tools:
        tool_obj = mcp2openai(tool)
        if tool_obj.function.name in existing_names:
            logger.warning(
                f"Skipping duplicate OpenAI tool name: {tool_obj.function.name}"
            )
            continue
        request.tools.append(tool_obj)
        existing_names.add(tool_obj.function.name)
        mcp_tool_names.add(tool_obj.function.name)
        logger.debug(f"   - {tool_obj.function.name}: {tool_obj.function.description}")

    setattr(request, "_mcp_bridge_tool_names", mcp_tool_names)
    logger.info(f"✅ Total tools available: {len(request.tools)}")
    return request


def is_mcp_bridge_tool(
    request: CreateChatCompletionRequest, tool_call_name: str
) -> bool:
    tool_names = getattr(request, "_mcp_bridge_tool_names", None)
    return isinstance(tool_names, set) and tool_call_name in tool_names


async def call_tool(
    tool_call_name: str, tool_call_json: str, timeout: Optional[int] = None
) -> Optional[mcp.types.CallToolResult]:
    ClientManager = _get_client_manager()
    if tool_call_name == "" or tool_call_name is None:
        logger.error("tool call name is empty")
        return None

    if tool_call_json is None:
        logger.error("tool call json is empty")
        return None

    try:
        tool_call_args = json.loads(tool_call_json)
    except json.JSONDecodeError:
        logger.error(f"failed to decode json for {tool_call_name}")
        return None

    return await ToolRegistry.call_exposed_tool(
        ClientManager,
        tool_call_name,
        tool_call_args,
        timeout,
    )
