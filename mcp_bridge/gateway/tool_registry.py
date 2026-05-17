import fnmatch
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from mcp import types

import mcp_bridge.config as bridge_config
from mcp_bridge.config.final import GatewayToolsConfig, ToolExposureRule


@dataclass(frozen=True)
class ToolRef:
    server_name: str
    tool_name: str
    gateway_name: str
    tool: types.Tool
    exposed: bool = True
    collision_group: tuple[str, ...] = ()


@dataclass
class ToolRegistrySnapshot:
    tools_by_server: dict[str, list[ToolRef]] = field(default_factory=dict)
    tools_by_gateway_name: dict[str, ToolRef] = field(default_factory=dict)
    collisions: dict[str, list[ToolRef]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class ToolListContext:
    query: str | None = None


class GatewayToolRegistry:
    def __init__(self) -> None:
        self._snapshot: ToolRegistrySnapshot | None = None

    async def refresh(
        self, client_manager: Any, force: bool = False
    ) -> ToolRegistrySnapshot:
        tools_config = bridge_config.config.gateway.tools
        if not force and self._snapshot and not self._is_expired(tools_config):
            return self._snapshot

        raw_tools_by_name: dict[str, list[ToolRef]] = {}
        tools_by_server: dict[str, list[ToolRef]] = {}

        for server_name, client in client_manager.get_clients():
            if client is None:
                logger.error(f"Client '{server_name}' not found")
                continue

            try:
                result = await client.list_tools()
            except Exception as e:
                logger.error(f"Error listing tools for {server_name}: {e}")
                continue

            server_tools = []
            for tool in result.tools:
                exposed = self._matches_exposure_rules(
                    server_name, tool.name, tools_config
                )
                tool_ref = ToolRef(
                    server_name=server_name,
                    tool_name=tool.name,
                    gateway_name=self._gateway_name(
                        server_name, tool.name, tools_config
                    ),
                    tool=tool,
                    exposed=exposed,
                )
                server_tools.append(tool_ref)
                if exposed:
                    raw_tools_by_name.setdefault(tool.name, []).append(tool_ref)

            tools_by_server[server_name] = server_tools

        collisions = {
            name: refs for name, refs in raw_tools_by_name.items() if len(refs) > 1
        }
        exposed_refs = self._build_exposed_refs(
            tools_by_server, collisions, tools_config
        )
        tools_by_gateway_name = {
            tool_ref.gateway_name: tool_ref for tool_ref in exposed_refs
        }

        self._snapshot = ToolRegistrySnapshot(
            tools_by_server=tools_by_server,
            tools_by_gateway_name=tools_by_gateway_name,
            collisions=collisions,
        )
        self._log_collisions(collisions, tools_config)
        return self._snapshot

    async def inventory(self, client_manager: Any) -> dict[str, list[ToolRef]]:
        snapshot = await self.refresh(client_manager)
        return snapshot.tools_by_server

    async def list_exposed_tools(
        self,
        client_manager: Any,
        context: ToolListContext | None = None,
    ) -> list[types.Tool]:
        tools_config = bridge_config.config.gateway.tools
        if tools_config.mode == "router":
            return self._build_router_tools(tools_config)

        snapshot = await self.refresh(client_manager)
        refs = list(snapshot.tools_by_gateway_name.values())
        if tools_config.dynamic_filter.enabled:
            refs = self._filter_dynamic(
                refs, context, tools_config.dynamic_filter.max_tools
            )
            if tools_config.dynamic_filter.include_router_fallback:
                router_tools = self._build_router_tools(tools_config)
                router_tool_names = {tool.name for tool in router_tools}
                refs = [
                    ref for ref in refs if ref.gateway_name not in router_tool_names
                ]
                return [*self._tool_refs_to_tools(refs), *router_tools]

        return self._tool_refs_to_tools(refs)

    async def call_exposed_tool(
        self,
        client_manager: Any,
        name: str,
        arguments: dict[str, Any] | None,
        timeout: int | None = None,
    ) -> types.CallToolResult:
        tools_config = bridge_config.config.gateway.tools
        arguments = arguments or {}

        router_tools_exposed = tools_config.mode == "router" or (
            tools_config.dynamic_filter.enabled
            and tools_config.dynamic_filter.include_router_fallback
        )
        if router_tools_exposed:
            router_call_name = self._router_call_tool_name(tools_config)
            router_search_name = self._router_search_tool_name(tools_config)
            router_inventory_name = self._router_inventory_tool_name(tools_config)

            if name == router_search_name and tools_config.router.expose_search_tool:
                return await self.search_tools(
                    client_manager=client_manager,
                    query=arguments.get("query"),
                    server=arguments.get("server"),
                    limit=arguments.get("limit"),
                    include_schema=arguments.get("include_schema"),
                )

            if name == router_call_name and tools_config.router.expose_call_tool:
                server_name = arguments.get("server")
                tool_name = arguments.get("tool")
                tool_arguments = arguments.get("arguments", {})
                if not isinstance(server_name, str) or not server_name:
                    return self._error_result(
                        "Missing required string argument: server"
                    )
                if not isinstance(tool_name, str) or not tool_name:
                    return self._error_result("Missing required string argument: tool")
                if not isinstance(tool_arguments, dict):
                    return self._error_result("arguments must be an object")
                return await self.call_downstream_tool(
                    client_manager, server_name, tool_name, tool_arguments, timeout
                )

            if (
                name == router_inventory_name
                and tools_config.router.expose_inventory_tool
            ):
                return await self._inventory_result(client_manager)

        if tools_config.mode == "router":
            return self._error_result(f"Tool '{name}' is not exposed in router mode")

        snapshot = await self.refresh(client_manager)
        tool_ref = snapshot.tools_by_gateway_name.get(name)
        if tool_ref is None:
            if (
                tools_config.mode in {"flat", "filtered"}
                and tools_config.collision_strategy == "error"
            ):
                collision = snapshot.collisions.get(name)
                if collision:
                    candidates = ", ".join(ref.server_name for ref in collision)
                    return self._error_result(
                        f"Tool '{name}' is ambiguous. Candidate servers: {candidates}"
                    )
            return self._error_result(f"Tool '{name}' not found")

        return await self.call_downstream_tool(
            client_manager,
            tool_ref.server_name,
            tool_ref.tool_name,
            arguments,
            timeout,
        )

    async def search_tools(
        self,
        client_manager: Any,
        query: str | None = None,
        server: str | None = None,
        limit: int | None = None,
        include_schema: bool | None = None,
    ) -> types.CallToolResult:
        tools_config = bridge_config.config.gateway.tools
        if query is not None and not isinstance(query, str):
            return self._error_result("query must be a string")
        if server is not None and not isinstance(server, str):
            return self._error_result("server must be a string")
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            return self._error_result("limit must be a positive integer")
        if include_schema is not None and not isinstance(include_schema, bool):
            return self._error_result("include_schema must be a boolean")

        snapshot = await self.refresh(client_manager)
        result_limit = limit or tools_config.router.search_result_limit
        include_tool_schema = (
            tools_config.router.include_input_schema
            if include_schema is None
            else include_schema
        )
        query_text = query or ""

        candidates = []
        for server_name, refs in snapshot.tools_by_server.items():
            if server and server_name != server:
                continue
            for tool_ref in refs:
                if not tool_ref.exposed:
                    continue
                score = self._score_tool(tool_ref, query_text)
                if query_text and score <= 0:
                    continue
                candidates.append((score, tool_ref))

        candidates.sort(
            key=lambda item: (-item[0], item[1].server_name, item[1].tool_name)
        )
        tools = [
            self._tool_ref_metadata(tool_ref, include_tool_schema)
            for _, tool_ref in candidates[:result_limit]
        ]

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps({"tools": tools}, ensure_ascii=False),
                )
            ],
            isError=False,
        )

    async def call_downstream_tool(
        self,
        client_manager: Any,
        server: str,
        tool: str,
        arguments: dict[str, Any] | None,
        timeout: int | None = None,
        require_exposed: bool = True,
    ) -> types.CallToolResult:
        try:
            client = client_manager.get_client(server)
        except KeyError:
            return self._error_result(f"Server '{server}' not found")
        if client is None:
            return self._error_result(f"Server '{server}' not found")

        snapshot = await self.refresh(client_manager)
        known_tools = snapshot.tools_by_server.get(server, [])
        if require_exposed:
            exists = any(
                tool_ref.tool_name == tool and tool_ref.exposed
                for tool_ref in known_tools
            )
        else:
            exists = any(tool_ref.tool_name == tool for tool_ref in known_tools)
        if not exists:
            return self._error_result(f"Tool '{tool}' not found on server '{server}'")

        return await client.call_tool(tool, arguments or {}, timeout)

    def _is_expired(self, tools_config: GatewayToolsConfig) -> bool:
        if self._snapshot is None:
            return True
        return (
            time.monotonic() - self._snapshot.created_at
            > tools_config.cache_ttl_seconds
        )

    def _build_exposed_refs(
        self,
        tools_by_server: dict[str, list[ToolRef]],
        collisions: dict[str, list[ToolRef]],
        tools_config: GatewayToolsConfig,
    ) -> list[ToolRef]:
        exposed_refs: list[ToolRef] = []
        gateway_names: set[str] = set()

        for refs in tools_by_server.values():
            for tool_ref in refs:
                if not tool_ref.exposed:
                    continue

                collision_group = collisions.get(tool_ref.tool_name, [])
                gateway_name = tool_ref.gateway_name

                if tools_config.mode in {"flat", "filtered"} and collision_group:
                    if tools_config.collision_strategy == "error":
                        continue
                    if tools_config.collision_strategy == "first":
                        if collision_group[0] != tool_ref:
                            continue
                        gateway_name = tool_ref.tool_name
                    elif tools_config.collision_strategy == "namespace":
                        gateway_name = self._namespaced_name(
                            tool_ref.server_name, tool_ref.tool_name, tools_config
                        )

                elif tools_config.mode in {"namespaced"}:
                    gateway_name = self._namespaced_name(
                        tool_ref.server_name, tool_ref.tool_name, tools_config
                    )

                if gateway_name in gateway_names:
                    logger.warning(
                        f"Gateway tool name collision skipped: {gateway_name}"
                    )
                    continue

                gateway_names.add(gateway_name)
                exposed_refs.append(
                    ToolRef(
                        server_name=tool_ref.server_name,
                        tool_name=tool_ref.tool_name,
                        gateway_name=gateway_name,
                        tool=tool_ref.tool,
                        exposed=tool_ref.exposed,
                        collision_group=tuple(
                            ref.server_name for ref in collision_group
                        ),
                    )
                )

        return exposed_refs

    def _tool_refs_to_tools(self, tool_refs: list[ToolRef]) -> list[types.Tool]:
        tools = []
        for tool_ref in tool_refs:
            tools.append(
                types.Tool(
                    name=tool_ref.gateway_name,
                    description=tool_ref.tool.description,
                    inputSchema=tool_ref.tool.inputSchema,
                )
            )
        return tools

    def _build_router_tools(self, tools_config: GatewayToolsConfig) -> list[types.Tool]:
        tools = []
        if tools_config.router.expose_search_tool:
            tools.append(
                types.Tool(
                    name=self._router_search_tool_name(tools_config),
                    description="Search downstream MCP tools by query and optional server.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "server": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                            "include_schema": {"type": "boolean"},
                        },
                    },
                )
            )

        if tools_config.router.expose_call_tool:
            tools.append(
                types.Tool(
                    name=self._router_call_tool_name(tools_config),
                    description="Call a downstream MCP tool by server and tool name.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "server": {"type": "string"},
                            "tool": {"type": "string"},
                            "arguments": {"type": "object"},
                        },
                        "required": ["server", "tool"],
                    },
                )
            )

        if tools_config.router.expose_inventory_tool:
            tools.append(
                types.Tool(
                    name=self._router_inventory_tool_name(tools_config),
                    description="List downstream MCP servers and tool names.",
                    inputSchema={"type": "object", "properties": {}},
                )
            )

        return tools

    def _gateway_name(
        self,
        server_name: str,
        tool_name: str,
        tools_config: GatewayToolsConfig,
    ) -> str:
        if tools_config.mode == "namespaced":
            return self._namespaced_name(server_name, tool_name, tools_config)
        return tool_name

    def _namespaced_name(
        self,
        server_name: str,
        tool_name: str,
        tools_config: GatewayToolsConfig,
    ) -> str:
        name = tools_config.name_template.format(server=server_name, tool=tool_name)
        return self._sanitize_tool_name(name)

    def _sanitize_tool_name(self, name: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        if re.match(r"^[a-zA-Z_]", sanitized):
            return sanitized
        return f"tool_{sanitized}"

    def _matches_exposure_rules(
        self,
        server_name: str,
        tool_name: str,
        tools_config: GatewayToolsConfig,
    ) -> bool:
        included = any(
            self._matches_rule(server_name, tool_name, rule)
            for rule in tools_config.include
        )
        excluded = any(
            self._matches_rule(server_name, tool_name, rule)
            for rule in tools_config.exclude
        )
        return included and not excluded

    def _matches_rule(
        self,
        server_name: str,
        tool_name: str,
        rule: ToolExposureRule,
    ) -> bool:
        if not fnmatch.fnmatch(server_name, rule.server):
            return False
        return any(fnmatch.fnmatch(tool_name, pattern) for pattern in rule.tools)

    def _filter_dynamic(
        self,
        refs: list[ToolRef],
        context: ToolListContext | None,
        max_tools: int,
    ) -> list[ToolRef]:
        if not context or not context.query:
            return refs[:max_tools]
        scored = [(self._score_tool(ref, context.query), ref) for ref in refs]
        scored = [item for item in scored if item[0] > 0]
        scored.sort(key=lambda item: (-item[0], item[1].server_name, item[1].tool_name))
        return [ref for _, ref in scored[:max_tools]]

    def _score_tool(self, tool_ref: ToolRef, query: str) -> float:
        if not query:
            return 1.0
        haystack = " ".join(
            [
                tool_ref.server_name,
                tool_ref.tool_name,
                tool_ref.gateway_name,
                tool_ref.tool.description or "",
            ]
        ).lower()
        terms = [term for term in query.lower().split() if term]
        if not terms:
            return 1.0
        return float(sum(1 for term in terms if term in haystack))

    def _tool_ref_metadata(
        self, tool_ref: ToolRef, include_schema: bool
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "server": tool_ref.server_name,
            "tool": tool_ref.tool_name,
            "name": tool_ref.gateway_name,
            "description": tool_ref.tool.description,
        }
        if include_schema:
            metadata["inputSchema"] = tool_ref.tool.inputSchema
        return metadata

    async def _inventory_result(self, client_manager: Any) -> types.CallToolResult:
        snapshot = await self.refresh(client_manager)
        servers = {
            server_name: [ref.tool_name for ref in refs if ref.exposed]
            for server_name, refs in snapshot.tools_by_server.items()
        }
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps({"servers": servers}, ensure_ascii=False),
                )
            ],
            isError=False,
        )

    def _error_result(self, message: str) -> types.CallToolResult:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=message)],
            isError=True,
        )

    def _router_search_tool_name(self, tools_config: GatewayToolsConfig) -> str:
        return self._sanitize_tool_name(f"{tools_config.router.prefix}_search_tools")

    def _router_call_tool_name(self, tools_config: GatewayToolsConfig) -> str:
        return self._sanitize_tool_name(f"{tools_config.router.prefix}_call_tool")

    def _router_inventory_tool_name(self, tools_config: GatewayToolsConfig) -> str:
        return self._sanitize_tool_name(f"{tools_config.router.prefix}_inventory")

    def _log_collisions(
        self,
        collisions: dict[str, list[ToolRef]],
        tools_config: GatewayToolsConfig,
    ) -> None:
        for tool_name, refs in collisions.items():
            servers = ", ".join(ref.server_name for ref in refs)
            logger.warning(
                f"Tool name collision detected for '{tool_name}' on servers: {servers}. "
                f"strategy={tools_config.collision_strategy}"
            )


ToolRegistry = GatewayToolRegistry()
