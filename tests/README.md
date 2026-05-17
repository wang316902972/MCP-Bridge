# MCP-Bridge 测试套件

MCP-Bridge 测试覆盖网关 API、SSE Bridge、OpenAI 兼容接口，以及 gateway tool registry/router 单元测试。

## 测试覆盖范围

### MCP-Bridge 核心 API 测试 (`test_mcp_bridge_api.py`)

- 健康检查端点
- OpenAPI schema
- MCP 工具、资源、提示列表
- MCP 初始化
- MCP 服务器状态
- MCP HTTP 代理
- JSON-RPC 错误处理
- 并发工具调用
- 采样配置

### SSE Bridge 测试 (`test_sse_bridge.py`)

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

- Chat Completions 端点
- 带工具的 Chat Completions
- 流式 Chat Completions
- 工具执行流程
- 错误处理
- 多个工具调用
- Models 端点
- OpenAI 客户端兼容性
- 工具调用往返

### Gateway registry/router 单元测试

- `test_gateway_tool_registry.py`
- `test_gateway_http_proxy.py`
- `test_gateway_openai_tools.py`
- `test_gateway_stream_chat_completion.py`

覆盖 flat、filtered、namespaced、router 暴露模式，冲突策略，HTTP JSON-RPC 代理，OpenAI tool 注入，以及流式工具调用处理。

## 快速开始

### 安装依赖

```bash
pip install -r tests/requirements.txt
```

或使用 uv：

```bash
uv pip install -r tests/requirements.txt
```

### 配置环境变量

```bash
export MCP_BRIDGE_URL="http://localhost:8000"
export TEST_API_KEY="your-test-api-key"
export SKIP_EXTERNAL_TESTS="false"
```

### 运行测试

使用测试脚本：

```bash
python tests/run_tests.py
python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --fast
python tests/run_tests.py --coverage
python tests/run_tests.py --verbose
```

直接使用 pytest：

```bash
pytest tests/ -v
pytest tests/ -m integration
pytest tests/ -m "not external"
pytest tests/test_gateway_tool_registry.py -v
pytest tests/test_gateway_http_proxy.py -v
```

## 测试组织结构

```text
tests/
├── __init__.py
├── conftest.py
├── requirements.txt
├── run_tests.py
├── README.md
├── test_gateway_http_proxy.py
├── test_gateway_openai_tools.py
├── test_gateway_stream_chat_completion.py
├── test_gateway_tool_registry.py
├── test_mcp_bridge_api.py
├── test_openai_compatibility.py
└── test_sse_bridge.py
```

## 测试标记

- `@pytest.mark.integration`: 集成测试，需要运行的服务
- `@pytest.mark.unit`: 单元测试，独立运行
- `@pytest.mark.external`: 需要外部服务的测试

## Fixtures

- `http_client`: MCP-Bridge HTTP 客户端
- `test_config`: 测试配置对象
- `auth_headers`: 认证请求头
- `jsonrpc_headers`: JSON-RPC 请求头
- `jsonrpc_request`: JSON-RPC 请求模板
- `sample_search_query`: 示例搜索查询
- `sample_news_query`: 示例新闻查询

## 编写新测试

```python
import pytest

@pytest.mark.external
@pytest.mark.integration
class TestNewFeature:
    @pytest.mark.asyncio
    async def test_new_endpoint(self, http_client, auth_headers):
        response = await http_client.get("/new-endpoint", headers=auth_headers)
        assert response.status_code == 200
```

## 调试测试

```bash
pytest tests/ -vv -s
pytest tests/ --lf
pytest tests/ -x
pytest tests/test_gateway_tool_registry.py::test_flat_mode_preserves_tool_names_and_calls_unique_tool -v
```

## 故障排除

如果外部集成测试连接失败，请确认 MCP-Bridge 服务正在运行，并检查 `MCP_BRIDGE_URL` 是否指向正确地址。

如需跳过外部服务测试：

```bash
python tests/run_tests.py --fast
pytest tests/ -m "not external"
```

## 相关文档

- [项目 README](../README.md)
- [MCP 协议规范](https://spec.modelcontextprotocol.io/)
- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
