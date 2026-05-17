# MCP-Bridge 测试快速参考

## 快速命令

```bash
pip install -r tests/requirements.txt

make test
make test-unit
make test-integration
make test-fast
make test-coverage

python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --fast
```

## 测试文件

| 文件 | 描述 |
|------|------|
| `test_gateway_tool_registry.py` | Gateway tool registry/router 单元测试 |
| `test_gateway_http_proxy.py` | HTTP JSON-RPC proxy gateway 测试 |
| `test_gateway_openai_tools.py` | OpenAI tool 注入测试 |
| `test_gateway_stream_chat_completion.py` | 流式 Chat Completion 工具调用测试 |
| `test_mcp_bridge_api.py` | MCP-Bridge API 集成测试 |
| `test_sse_bridge.py` | SSE Bridge 集成测试 |
| `test_openai_compatibility.py` | OpenAI 兼容性集成测试 |

## 测试标记

```bash
pytest tests/ -m unit
pytest tests/ -m integration
pytest tests/ -m "not external"
```

## 环境变量

```bash
export MCP_BRIDGE_URL="http://localhost:8000"
export TEST_API_KEY="your-api-key"
export SKIP_EXTERNAL_TESTS="false"
```

## 覆盖重点

### Gateway registry/router

- flat、filtered、namespaced、router 暴露模式
- first、error、namespace 冲突策略
- include/exclude 过滤
- router search/call/inventory 工具
- OpenAI tool 注入和流式工具调用处理

### MCP-Bridge API

- 健康检查
- OpenAPI schema
- MCP 工具/资源/提示列表
- MCP 初始化
- MCP HTTP 代理
- 管理端点
- JSON-RPC 错误处理

### SSE Bridge

- SSE 连接和握手
- JSON-RPC over SSE
- SSE 工具列表
- 认证、重连、错误处理

### OpenAI 兼容性

- Chat Completions
- 流式响应
- 工具调用
- 响应格式验证

## Fixtures

```python
http_client          # MCP-Bridge HTTP 客户端
auth_headers        # 认证请求头
jsonrpc_headers     # JSON-RPC 请求头
jsonrpc_request     # JSON-RPC 请求模板
sample_search_query # 示例搜索查询
```

## 调试命令

```bash
pytest tests/ -vv -s
pytest tests/ --lf
pytest tests/ -x
pytest tests/test_gateway_tool_registry.py -v
pytest tests/test_gateway_http_proxy.py -v
```

## 更多信息

- 完整文档: `tests/README.md`
- 测试总结: `tests/TESTING_SUMMARY.md`
- 项目 README: `README.md`
