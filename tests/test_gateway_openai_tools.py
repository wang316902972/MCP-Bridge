from types import SimpleNamespace

import pytest
from mcp import types

import mcp_bridge.config as bridge_config
from mcp_bridge.config.final import GatewayConfig
from mcp_bridge.openai_clients import utils

pytestmark = pytest.mark.unit


class FakeClient:
    def __init__(self, name: str, tools: list[types.Tool]) -> None:
        self.name = name
        self._tools = tools

    async def list_tools(self):
        return types.ListToolsResult(tools=self._tools)

    async def call_tool(self, name: str, arguments: dict, timeout: int | None = None):
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


def make_openai_tool(name: str):
    return SimpleNamespace(
        type="function",
        function=SimpleNamespace(
            name=name,
            description="existing",
            parameters={"type": "object"},
        ),
    )


@pytest.fixture(autouse=True)
def patch_gateway_dependencies(monkeypatch):
    original_config = bridge_config.config
    bridge_config.config = SimpleNamespace(gateway=GatewayConfig())
    manager = FakeClientManager(
        {"search": FakeClient("search", [make_tool("search_web")])}
    )
    monkeypatch.setattr(utils, "_get_client_manager", lambda: manager)
    utils.ToolRegistry._snapshot = None
    yield manager
    bridge_config.config = original_config
    utils.ToolRegistry._snapshot = None


@pytest.mark.asyncio
async def test_chat_completion_add_tools_uses_gateway_registry():
    request = SimpleNamespace(tools=[])

    result = await utils.chat_completion_add_tools(request)

    assert [tool.function.name for tool in result.tools] == ["search_web"]


@pytest.mark.asyncio
async def test_chat_completion_add_tools_preserves_existing_tools_and_skips_duplicates():
    request = SimpleNamespace(tools=[make_openai_tool("search_web")])

    result = await utils.chat_completion_add_tools(request)

    assert [tool.function.name for tool in result.tools] == ["search_web"]


@pytest.mark.asyncio
async def test_chat_completion_add_tools_injects_router_tools_in_router_mode():
    bridge_config.config.gateway.tools.mode = "router"
    request = SimpleNamespace(tools=[])

    result = await utils.chat_completion_add_tools(request)

    assert [tool.function.name for tool in result.tools] == [
        "mcp_bridge_search_tools",
        "mcp_bridge_call_tool",
    ]
