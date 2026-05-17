import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from mcp import types

import mcp_bridge.config as bridge_config
from mcp_bridge.config.final import GatewayConfig
from mcp_bridge.mcpManagement import tools as management_tools

http_proxy_router = importlib.import_module("mcp_bridge.mcp_http_proxy.router")

pytestmark = pytest.mark.unit


class FakeClient:
    def __init__(self, name: str, tools: list[types.Tool]) -> None:
        self.name = name
        self._tools = tools
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        return types.ListToolsResult(tools=self._tools)

    async def call_tool(self, name: str, arguments: dict, timeout: int | None = None):
        self.calls.append((name, arguments))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"{self.name}:{name}")],
            isError=False,
        )


class FakeClientManager:
    def __init__(self, clients: dict[str, FakeClient]) -> None:
        self.clients = clients

    def get_clients(self):
        return list(self.clients.items())

    def get_client(self, server_name: str):
        return self.clients[server_name]


def make_tool(name: str) -> types.Tool:
    return types.Tool(name=name, description=name, inputSchema={"type": "object"})


@pytest.fixture(autouse=True)
def patch_gateway_dependencies(monkeypatch):
    original_config = bridge_config.config
    bridge_config.config = SimpleNamespace(gateway=GatewayConfig())
    manager = FakeClientManager(
        {"search": FakeClient("search", [make_tool("search_web")])}
    )
    monkeypatch.setattr(http_proxy_router, "ClientManager", manager)
    monkeypatch.setattr(management_tools, "ClientManager", manager)
    http_proxy_router.ToolRegistry._snapshot = None
    management_tools.ToolRegistry._snapshot = None
    yield manager
    bridge_config.config = original_config
    http_proxy_router.ToolRegistry._snapshot = None
    management_tools.ToolRegistry._snapshot = None


@pytest.mark.asyncio
async def test_tools_list_uses_gateway_registry(patch_gateway_dependencies):
    response = await http_proxy_router._handle_tools_list()
    assert response == {
        "tools": [
            {
                "name": "search_web",
                "description": "search_web",
                "inputSchema": {"type": "object"},
            }
        ]
    }


@pytest.mark.asyncio
async def test_tools_call_uses_gateway_registry(patch_gateway_dependencies):
    response = await http_proxy_router._handle_tools_call(
        {"name": "search_web", "arguments": {"query": "mcp"}}
    )

    assert response == {
        "content": [{"type": "text", "text": "search:search_web"}],
        "isError": False,
    }
    client = patch_gateway_dependencies.clients["search"]
    assert client.calls == [("search_web", {"query": "mcp"})]


@pytest.mark.asyncio
async def test_tools_list_returns_router_tools_in_router_mode(
    patch_gateway_dependencies,
):
    bridge_config.config.gateway.tools.mode = "router"
    http_proxy_router.ToolRegistry._snapshot = None

    response = await http_proxy_router._handle_tools_list()
    assert [tool["name"] for tool in response["tools"]] == [
        "mcp_bridge_search_tools",
        "mcp_bridge_call_tool",
    ]


@pytest.mark.asyncio
async def test_management_direct_call_is_forbidden_in_router_mode(
    patch_gateway_dependencies,
):
    bridge_config.config.gateway.tools.mode = "router"

    with pytest.raises(HTTPException) as exc_info:
        await management_tools.call_server_tool(
            management_tools.ToolCallRequest(
                server="search",
                tool="search_web",
                arguments={"query": "mcp"},
            )
        )

    assert exc_info.value.status_code == 403
