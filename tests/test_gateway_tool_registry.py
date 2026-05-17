import json
from types import SimpleNamespace

import pytest
from mcp import types

import mcp_bridge.config as bridge_config
from mcp_bridge.config.final import GatewayConfig, ToolExposureRule
from mcp_bridge.gateway.tool_registry import GatewayToolRegistry

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


def make_tool(name: str, description: str = "") -> types.Tool:
    return types.Tool(
        name=name,
        description=description or f"{name} description",
        inputSchema={"type": "object", "properties": {}},
    )


@pytest.fixture(autouse=True)
def reset_gateway_config():
    original_config = bridge_config.config
    bridge_config.config = SimpleNamespace(gateway=GatewayConfig())
    yield
    bridge_config.config = original_config


@pytest.mark.asyncio
async def test_flat_mode_preserves_tool_names_and_calls_unique_tool():
    registry = GatewayToolRegistry()
    search_client = FakeClient("search", [make_tool("search_web")])
    manager = FakeClientManager({"search": search_client})

    tools = await registry.list_exposed_tools(manager)
    assert [tool.name for tool in tools] == ["search_web"]

    result = await registry.call_exposed_tool(manager, "search_web", {"query": "mcp"})
    assert result.isError is False
    assert search_client.calls == [("search_web", {"query": "mcp"})]


@pytest.mark.asyncio
async def test_duplicate_tool_names_are_detected_and_first_strategy_preserves_first_match():
    registry = GatewayToolRegistry()
    first_client = FakeClient("first", [make_tool("lookup")])
    second_client = FakeClient("second", [make_tool("lookup")])
    manager = FakeClientManager({"first": first_client, "second": second_client})

    snapshot = await registry.refresh(manager)
    assert "lookup" in snapshot.collisions

    tools = await registry.list_exposed_tools(manager)
    assert [tool.name for tool in tools] == ["lookup"]

    result = await registry.call_exposed_tool(manager, "lookup", {})
    assert result.isError is False
    assert first_client.calls == [("lookup", {})]
    assert second_client.calls == []


@pytest.mark.asyncio
async def test_error_collision_strategy_rejects_ambiguous_flat_calls():
    bridge_config.config.gateway.tools.collision_strategy = "error"
    registry = GatewayToolRegistry()
    manager = FakeClientManager(
        {
            "first": FakeClient("first", [make_tool("lookup")]),
            "second": FakeClient("second", [make_tool("lookup")]),
        }
    )

    tools = await registry.list_exposed_tools(manager)
    assert tools == []

    result = await registry.call_exposed_tool(manager, "lookup", {})
    assert result.isError is True
    assert "ambiguous" in result.content[0].text


@pytest.mark.asyncio
async def test_namespace_collision_strategy_exposes_namespaced_tools():
    bridge_config.config.gateway.tools.collision_strategy = "namespace"
    registry = GatewayToolRegistry()
    first_client = FakeClient("first", [make_tool("lookup")])
    second_client = FakeClient("second", [make_tool("lookup")])
    manager = FakeClientManager({"first": first_client, "second": second_client})

    tools = await registry.list_exposed_tools(manager)
    assert [tool.name for tool in tools] == ["first__lookup", "second__lookup"]

    result = await registry.call_exposed_tool(manager, "second__lookup", {"id": 1})
    assert result.isError is False
    assert second_client.calls == [("lookup", {"id": 1})]


@pytest.mark.asyncio
async def test_filtered_mode_applies_exclude_rules():
    bridge_config.config.gateway.tools.mode = "filtered"
    bridge_config.config.gateway.tools.exclude = [
        ToolExposureRule(server="filesystem", tools=["delete_*"])
    ]
    registry = GatewayToolRegistry()
    manager = FakeClientManager(
        {
            "filesystem": FakeClient(
                "filesystem",
                [make_tool("read_file"), make_tool("delete_file")],
            )
        }
    )

    tools = await registry.list_exposed_tools(manager)
    assert [tool.name for tool in tools] == ["read_file"]


@pytest.mark.asyncio
async def test_router_mode_exposes_only_router_tools_and_dispatches_explicit_call():
    bridge_config.config.gateway.tools.mode = "router"
    registry = GatewayToolRegistry()
    client = FakeClient("search", [make_tool("search_web", "web search")])
    manager = FakeClientManager({"search": client})

    tools = await registry.list_exposed_tools(manager)
    assert [tool.name for tool in tools] == [
        "mcp_bridge_search_tools",
        "mcp_bridge_call_tool",
    ]

    direct_result = await registry.call_exposed_tool(manager, "search_web", {})
    assert direct_result.isError is True

    search_result = await registry.call_exposed_tool(
        manager,
        "mcp_bridge_search_tools",
        {"query": "web", "include_schema": False},
    )
    payload = json.loads(search_result.content[0].text)
    assert payload["tools"][0]["server"] == "search"
    assert payload["tools"][0]["tool"] == "search_web"
    assert "inputSchema" not in payload["tools"][0]

    call_result = await registry.call_exposed_tool(
        manager,
        "mcp_bridge_call_tool",
        {"server": "search", "tool": "search_web", "arguments": {"query": "mcp"}},
    )
    assert call_result.isError is False
    assert client.calls == [("search_web", {"query": "mcp"})]


@pytest.mark.asyncio
async def test_router_call_tool_is_not_callable_when_not_exposed():
    bridge_config.config.gateway.tools.collision_strategy = "error"
    registry = GatewayToolRegistry()
    first_client = FakeClient("first", [make_tool("lookup")])
    second_client = FakeClient("second", [make_tool("lookup")])
    manager = FakeClientManager({"first": first_client, "second": second_client})

    result = await registry.call_exposed_tool(
        manager,
        "mcp_bridge_call_tool",
        {"server": "first", "tool": "lookup", "arguments": {"id": 1}},
    )

    assert result.isError is True
    assert first_client.calls == []
    assert second_client.calls == []


@pytest.mark.asyncio
async def test_downstream_tool_named_like_router_tool_is_callable_in_flat_mode():
    registry = GatewayToolRegistry()
    client = FakeClient("gateway", [make_tool("mcp_bridge_call_tool")])
    manager = FakeClientManager({"gateway": client})

    result = await registry.call_exposed_tool(
        manager, "mcp_bridge_call_tool", {"value": 1}
    )

    assert result.isError is False
    assert client.calls == [("mcp_bridge_call_tool", {"value": 1})]


@pytest.mark.asyncio
async def test_dynamic_router_fallback_hides_colliding_downstream_tool_name():
    bridge_config.config.gateway.tools.dynamic_filter.enabled = True
    registry = GatewayToolRegistry()
    client = FakeClient("gateway", [make_tool("mcp_bridge_call_tool")])
    manager = FakeClientManager({"gateway": client})

    tools = await registry.list_exposed_tools(manager)

    assert [tool.name for tool in tools] == [
        "mcp_bridge_search_tools",
        "mcp_bridge_call_tool",
    ]


@pytest.mark.asyncio
async def test_router_search_rejects_invalid_argument_types():
    bridge_config.config.gateway.tools.mode = "router"
    registry = GatewayToolRegistry()
    manager = FakeClientManager(
        {"search": FakeClient("search", [make_tool("search_web")])}
    )

    result = await registry.call_exposed_tool(
        manager,
        "mcp_bridge_search_tools",
        {"query": [], "limit": "5", "include_schema": "true"},
    )

    assert result.isError is True


@pytest.mark.asyncio
async def test_router_inventory_only_lists_exposed_tools():
    bridge_config.config.gateway.tools.mode = "router"
    bridge_config.config.gateway.tools.router.expose_inventory_tool = True
    bridge_config.config.gateway.tools.exclude = [
        ToolExposureRule(server="filesystem", tools=["delete_*"])
    ]
    registry = GatewayToolRegistry()
    manager = FakeClientManager(
        {
            "filesystem": FakeClient(
                "filesystem",
                [make_tool("read_file"), make_tool("delete_file")],
            )
        }
    )

    result = await registry.call_exposed_tool(manager, "mcp_bridge_inventory", {})
    payload = json.loads(result.content[0].text)

    assert payload == {"servers": {"filesystem": ["read_file"]}}
