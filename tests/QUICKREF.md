# MCP-Bridge 测试快速参考

## 🚀 快速命令

```bash
# 安装依赖
pip install -r tests/requirements.txt

# 启动服务
make run-docker

# 运行所有测试
make test

# 快速测试 (跳过外部服务)
make test-fast

# 生成覆盖率报告
make test-coverage
```

## 📋 测试文件

| 文件 | 描述 | 测试数 |
|------|------|--------|
| `test_duckduckgo_mcp.py` | DuckDuckGo MCP 测试 | 11 |
| `test_mcp_bridge_api.py` | MCP-Bridge API 测试 | 13 |
| `test_sse_bridge.py` | SSE Bridge 测试 | 9 |
| `test_openai_compatibility.py` | OpenAI 兼容性测试 | 12 |

## 🏷️ 测试标记

```bash
pytest tests/ -m integration          # 集成测试
pytest tests/ -m "not external"       # 跳过外部服务
pytest tests/ -m duckduckgo           # DuckDuckGo 测试
```

## 🔧 环境变量

```bash
export MCP_BRIDGE_URL="http://localhost:8000"
export DUCKDUCKGO_MCP_URL="http://localhost:8080"
export TEST_API_KEY="your-api-key"
export SKIP_EXTERNAL_TESTS="false"
```

## 📊 测试覆盖

### DuckDuckGo MCP
- ✅ MCP 初始化
- ✅ 工具列表 (3 个工具)
- ✅ 工具调用 (web_search, news_search, instant_answer)
- ✅ 错误处理
- ✅ 参数验证

### MCP-Bridge API
- ✅ 健康检查
- ✅ OpenAPI schema
- ✅ MCP 工具/资源/提示列表
- ✅ 工具调用
- ✅ 并发测试
- ✅ 错误处理

### SSE Bridge
- ✅ SSE 连接
- ✅ SSE 握手
- ✅ JSON-RPC over SSE
- ✅ SSE 认证
- ✅ mcp-cli 兼容性

### OpenAI 兼容性
- ✅ Chat Completions
- ✅ 流式响应
- ✅ 工具调用
- ✅ 响应格式验证
- ✅ OpenAI 客户端兼容

## 🛠️ Fixtures

```python
http_client              # MCP-Bridge HTTP 客户端
ddg_mcp_client          # DuckDuckGo MCP 客户端
auth_headers            # 认证请求头
jsonrpc_headers         # JSON-RPC 请求头
jsonrpc_request         # JSON-RPC 请求模板
sample_search_query     # 示例搜索查询
```

## 📝 示例测试

```python
@pytest.mark.asyncio
async def test_example(http_client, jsonrpc_headers):
    request_data = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }

    response = await http_client.post(
        "/v1/mcp/",
        headers=jsonrpc_headers,
        json=request_data
    )

    assert response.status_code == 200
    data = response.json()
    assert "result" in data
```

## 🐛 调试

```bash
# 详细输出
pytest tests/ -vv -s

# 只运行失败的测试
pytest tests/ --lf

# 停在第一个失败
pytest tests/ -x

# 运行特定测试
pytest tests/test_duckduckgo_mcp.py::TestDuckDuckGoMCPServer::test_mcp_initialize -v
```

## 📚 更多信息

- 完整文档: `tests/README.md`
- 测试总结: `tests/TESTING_SUMMARY.md`
- 项目 README: `README.md`
- DuckDuckGo 集成: `DUCKDUCKGO_INTEGRATION.md`
