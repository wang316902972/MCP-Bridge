# MCP-Bridge 测试套件总结

## 测试概览

MCP-Bridge 测试覆盖网关核心 API、SSE Bridge、OpenAI 兼容接口，以及 gateway tool registry/router 的单元测试。

## 测试模块

### Gateway tool registry/router 单元测试

相关文件：

- `test_gateway_tool_registry.py`
- `test_gateway_http_proxy.py`
- `test_gateway_openai_tools.py`
- `test_gateway_stream_chat_completion.py`

覆盖场景：

- flat 模式保留下游工具名并路由调用
- 重复工具名冲突检测
- `collision_strategy=first|error|namespace`
- filtered 模式 include/exclude 规则
- namespaced 模式工具名映射
- router 模式只暴露网关工具
- router search/call/inventory 行为
- router 参数类型校验
- HTTP JSON-RPC proxy 使用 gateway registry
- OpenAI tool 注入保留调用方工具并注入 MCP-Bridge 暴露工具
- Streaming Chat Completion 正确处理外部工具和 MCP 工具调用 ID

### MCP-Bridge 核心 API 测试 (`test_mcp_bridge_api.py`)

测试类：

- `TestMCPBridgeCoreAPI`
- `TestMCPBridgeSampling`

覆盖场景：

- 健康检查端点
- OpenAPI schema
- MCP 工具列表
- MCP 资源列表
- MCP 提示列表
- MCP 初始化
- MCP 服务器状态
- MCP HTTP 代理
- 无效 JSON-RPC 错误处理
- 无效方法错误处理
- 并发工具调用
- 采样配置
- 模型选择

### SSE Bridge 测试 (`test_sse_bridge.py`)

测试类：

- `TestSSEBridge`
- `TestMCPClientIntegration`

覆盖场景：

- SSE 端点连接
- SSE 握手协议
- SSE JSON-RPC 消息传输
- SSE 工具列表
- SSE 认证
- SSE 重连能力
- SSE 错误处理
- mcp-cli 兼容性
- Claude Desktop 兼容性

### OpenAI API 兼容性测试 (`test_openai_compatibility.py`)

测试类：

- `TestOpenAICompatibility`
- `TestToolIntegration`

覆盖场景：

- Chat Completions 端点
- 带工具的 Chat Completions
- 流式 Chat Completions
- 工具执行流程
- OpenAI 错误处理
- 多个工具调用
- Models 端点
- OpenAI 客户端兼容性
- 工具列表可访问
- 工具调用往返

## 测试基础设施

### 配置文件

1. `conftest.py`
   - `TestConfig`
   - `http_client`
   - `auth_headers`
   - `jsonrpc_headers`
   - 示例查询数据 fixtures

2. `pytest.ini`
   - 测试路径和文件匹配
   - 标记定义
   - 日志配置
   - 覆盖率配置

3. `requirements.txt`
   - pytest
   - pytest-asyncio
   - httpx

4. `run_tests.py`
   - 命令行参数解析
   - 测试分类和过滤
   - 覆盖率报告生成

5. `Makefile`
   - `make test`
   - `make test-unit`
   - `make test-integration`
   - `make test-fast`
   - `make test-coverage`

## 快速开始

### 安装依赖

```bash
pip install -r tests/requirements.txt
```

或使用 uv：

```bash
uv pip install -r tests/requirements.txt
```

### 运行测试

```bash
make test
make test-fast
make test-coverage

python tests/run_tests.py
python tests/run_tests.py --fast
python tests/run_tests.py --unit
python tests/run_tests.py --integration

pytest tests/ -v
pytest tests/ -m integration
pytest tests/ -m "not external"
```

## 测试标记系统

- `@pytest.mark.integration`: 集成测试，需要运行的服务
- `@pytest.mark.unit`: 单元测试，独立运行
- `@pytest.mark.external`: 需要外部服务的测试

## 环境变量

```bash
export MCP_BRIDGE_URL="http://localhost:8000"
export TEST_API_KEY="your-test-api-key"
export SKIP_EXTERNAL_TESTS="false"
```

## 测试覆盖的端点

### MCP 协议端点

- `POST /v1/mcp/`
- `POST /mcp`

### OpenAI 兼容端点

- `POST /v1/chat/completions`
- `GET /v1/models`

### SSE Bridge 端点

- `GET /mcp-server/sse`

### 管理端点

- `GET /health`
- `GET /openapi.json`
- `GET /mcp/servers`
- `GET /sampling/config`
- `GET /sampling/models`

## 后续可扩展测试

- 性能测试
- 安全测试
- 更多 MCP server 集成测试
- 端到端用户工作流测试
- 多步骤工具调用测试

## 总结

该测试套件提供：

- 网关工具暴露与路由的单元测试
- MCP-Bridge 主要 API 的集成测试
- SSE Bridge 和 OpenAI 兼容性测试
- 标记系统、共享 fixtures、运行脚本和 Makefile 快捷命令

创建日期: 2025-01-26
测试框架: pytest
