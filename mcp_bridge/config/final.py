from typing import Annotated, Literal, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field

from mcp.client.stdio import StdioServerParameters
from mcpx.client.transports.docker import DockerMCPServer


class InferenceServer(BaseModel):
    base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL of the inference server",
    )
    api_key: str = Field(
        default="unauthenticated", description="API key for the inference server"
    )


class Logging(BaseModel):
    log_level: Literal["INFO", "DEBUG"] = Field("INFO", description="default log level")
    log_server_pings: bool = Field(False, description="log server pings")


class SamplingModel(BaseModel):
    model: Annotated[str, Field(description="Name of the sampling model")]

    intelligence: Annotated[
        float, Field(description="Intelligence of the sampling model")
    ] = 0.5
    cost: Annotated[float, Field(description="Cost of the sampling model")] = 0.5
    speed: Annotated[float, Field(description="Speed of the sampling model")] = 0.5


class Sampling(BaseModel):
    timeout: Annotated[int, Field(description="Timeout for sampling requests")] = 10
    models: Annotated[
        list[SamplingModel], Field(description="List of sampling models")
    ] = []


class SSEMCPServer(BaseModel):
    # TODO: expand this once I find a good definition for this
    url: str = Field(description="URL of the MCP server")


class HTTPMCPServer(BaseModel):
    """HTTP MCP Server - 使用HTTP POST和JSON-RPC 2.0协议"""

    url: str = Field(description="URL of the MCP server (HTTP POST endpoint)")
    protocol: Literal["http"] = Field(default="http", description="Protocol type")


MCPServer = Annotated[
    Union[StdioServerParameters, SSEMCPServer, HTTPMCPServer, DockerMCPServer],
    Field(description="MCP server configuration"),
]


class Network(BaseModel):
    host: str = Field("0.0.0.0", description="Host of the network")
    port: int = Field(8000, description="Port of the network")


class Cors(BaseModel):
    enabled: bool = Field(True, description="Enable CORS")
    allow_origins: list[str] = Field(["*"], description="Allowed origins")
    allow_credentials: bool = Field(True, description="Allow credentials")
    allow_methods: list[str] = Field(["*"], description="Allowed methods")
    allow_headers: list[str] = Field(["*"], description="Allowed headers")


class ApiKey(BaseModel):
    key: str = Field(..., description="API key")
    permissions: Literal["all"] = Field(
        "all", description="API key permissions"
    )  # TODO: Add support for other permissions


class Auth(BaseModel):
    enabled: bool = Field(False, description="Enable authentication")
    api_keys: list[ApiKey] = Field([], description="API keys")


class ToolExposureRule(BaseModel):
    server: str = Field("*", description="Server name pattern")
    tools: list[str] = Field(
        default_factory=lambda: ["*"], description="Tool name patterns"
    )


class RouterToolsConfig(BaseModel):
    prefix: str = Field("mcp_bridge", description="Prefix for gateway router tools")
    expose_search_tool: bool = Field(True, description="Expose the gateway search tool")
    expose_call_tool: bool = Field(True, description="Expose the gateway call tool")
    expose_inventory_tool: bool = Field(
        False, description="Expose the gateway inventory tool"
    )
    search_result_limit: int = Field(
        20, ge=1, description="Maximum search results returned by router tools"
    )
    include_input_schema: bool = Field(
        True, description="Include input schemas in search results"
    )


class DynamicToolFilterConfig(BaseModel):
    enabled: bool = Field(False, description="Enable context-based tool filtering")
    max_tools: int = Field(
        20, ge=1, description="Maximum tools exposed after dynamic filtering"
    )
    include_router_fallback: bool = Field(
        True, description="Include router tools after dynamic filtering"
    )


class GatewayToolsConfig(BaseModel):
    mode: Literal["flat", "filtered", "namespaced", "router"] = Field(
        "flat", description="Tool exposure mode"
    )
    collision_strategy: Literal["first", "error", "namespace"] = Field(
        "first", description="How duplicate downstream tool names are handled"
    )
    name_template: str = Field(
        "{server}__{tool}", description="Template for namespaced tools"
    )
    cache_ttl_seconds: int = Field(
        60, ge=0, description="Tool registry cache TTL in seconds"
    )
    include: list[ToolExposureRule] = Field(
        default_factory=lambda: [ToolExposureRule()],
        description="Tool exposure include rules",
    )
    exclude: list[ToolExposureRule] = Field(
        default_factory=list, description="Tool exposure exclude rules"
    )
    router: RouterToolsConfig = Field(
        default_factory=lambda: RouterToolsConfig.model_construct(),
        description="Gateway router tool configuration",
    )
    dynamic_filter: DynamicToolFilterConfig = Field(
        default_factory=lambda: DynamicToolFilterConfig.model_construct(),
        description="Dynamic tool filtering configuration",
    )


class GatewayConfig(BaseModel):
    tools: GatewayToolsConfig = Field(
        default_factory=lambda: GatewayToolsConfig.model_construct(),
        description="Gateway tool exposure configuration",
    )


class GitNexusWebhookConfig(BaseModel):
    enabled: bool = Field(False, description="Enable GitNexus GitLab webhook")
    secret_token: str = Field(
        "", description="GitLab webhook secret token from X-Gitlab-Token"
    )
    project_tokens: dict[str, str] = Field(
        default_factory=dict,
        description="Map GitLab project path/name/remote URL to webhook secret tokens",
    )
    branches: list[str] = Field(
        default_factory=lambda: ["main", "master"],
        description="Branch names that trigger GitNexus analysis",
    )
    repo_paths: dict[str, str] = Field(
        default_factory=dict,
        description="Map GitLab project path/name/remote URL to local repo paths",
    )
    registry_file: str = Field(
        "~/.gitnexus/registry.json",
        description="GitNexus registry used to resolve project remote URLs",
    )
    command: str = Field("gitnexus", description="GitNexus CLI command")
    extra_args: list[str] = Field(
        default_factory=list,
        description="Additional arguments passed before the repo path",
    )
    sync_before_analyze: bool = Field(
        True,
        description="Fetch and fast-forward the local repository before analysis",
    )
    timeout_seconds: int = Field(
        1800, ge=1, description="Maximum runtime for gitnexus analyze"
    )


class GitNexusConfig(BaseModel):
    webhook: GitNexusWebhookConfig = Field(
        default_factory=lambda: GitNexusWebhookConfig.model_construct(),
        description="GitNexus integration configuration",
    )


class Security(BaseModel):
    CORS: Cors = Field(
        default_factory=lambda: Cors.model_construct(), description="CORS configuration"
    )
    auth: Auth = Field(
        default_factory=lambda: Auth.model_construct(),
        description="Authentication configuration",
    )


class Telemetry(BaseModel):
    """Telemetry configuration

    open-telemetry is entirely local to your own infrastructure and does not send any data to any external service unless you configure it to do so

    defaults to false since we cannot assume you are actually running an open telemetry collector on your machine.
    """

    enabled: bool = Field(False, description="Enable telemetry")
    service_name: str = Field(default="MCP Bridge", description="Name of the service")
    otel_endpoint: str = Field(
        default="http://jaeger:4318/v1/traces",
        description="Endpoint for the OTEL exporter",
    )


class Settings(BaseSettings):
    inference_server: InferenceServer = Field(
        default_factory=lambda: InferenceServer.model_construct(),
        description="Inference server configuration",
    )

    mcp_servers: dict[str, MCPServer] = Field(
        default_factory=dict, description="MCP servers configuration"
    )

    sampling: Sampling = Field(
        default_factory=lambda: Sampling.model_construct(),
        description="sampling config",
    )

    logging: Logging = Field(
        default_factory=lambda: Logging.model_construct(),
        description="logging config",
    )

    network: Network = Field(
        default_factory=lambda: Network.model_construct(),
        description="network config",
    )

    security: Security = Field(
        default_factory=lambda: Security.model_construct(),
        description="security config",
    )

    telemetry: Telemetry = Field(
        default_factory=lambda: Telemetry.model_construct(),
        description="telemetry config",
    )

    gateway: GatewayConfig = Field(
        default_factory=lambda: GatewayConfig.model_construct(),
        description="Gateway configuration",
    )

    gitnexus: GitNexusConfig = Field(
        default_factory=lambda: GitNexusConfig.model_construct(),
        description="GitNexus integration configuration",
    )

    model_config = SettingsConfigDict(
        env_prefix="MCP_BRIDGE__",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        cli_parse_args=False,
        cli_avoid_json=True,
        extra="ignore",
    )
