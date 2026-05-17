from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import mcp_bridge.config as bridge_config
from mcp_bridge.gateway import ToolRegistry
from mcp_bridge.mcp_clients.McpClientManager import ClientManager
from mcp.types import ListToolsResult, CallToolResult

router = APIRouter(prefix="/tools")


class ToolCallRequest(BaseModel):
    server: str = Field(..., description="MCP server name")
    tool: str = Field(..., description="Tool name on the MCP server")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )


@router.get("")
async def get_tools() -> dict[str, ListToolsResult]:
    """Get all tools from all MCP clients"""

    tools = {}

    for name, client in ClientManager.get_clients():
        tools[name] = await client.list_tools()

    return tools


@router.post("/call")
async def call_server_tool(request: ToolCallRequest) -> CallToolResult:
    """Call a tool by explicit server and tool name"""

    if bridge_config.config.gateway.tools.mode == "router":
        raise HTTPException(
            status_code=403,
            detail="Direct downstream tool calls are disabled in router mode",
        )

    result = await ToolRegistry.call_downstream_tool(
        ClientManager,
        request.server,
        request.tool,
        request.arguments,
    )
    return result


@router.post("/{tool_name}/call")
async def call_tool(tool_name: str, arguments: dict[str, Any] = {}) -> CallToolResult:
    """Call a tool through the configured gateway exposure mode"""

    result = await ToolRegistry.call_exposed_tool(ClientManager, tool_name, arguments)
    return result
