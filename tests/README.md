# MCP-Bridge 测试套件

全面的 MCP-Bridge 集成测试套件，覆盖所有网关和 API 端点。

## 📋 测试覆盖范围

### 1. DuckDuckGo MCP 网关测试 (`test_duckduckgo_mcp.py`)

测试 DuckDuckGo MCP 服务器的完整功能:

- ✅ MCP 初始化握手
- ✅ 工具列表获取 (3 个工具)
- ✅ 工具 schema 验证
- ✅ web_search 工具调用
- ✅ news_search 工具调用
- ✅ instant_answer 工具调用
- ✅ 错误处理 (无效工具、缺失参数)
- ✅ 参数验证 (time_range, max_results)
- ✅ 边界值测试

### 2. MCP-Bridge 核心 API 测试 (`test_mcp_bridge_api.py`)

测试 MCP-Bridge 的核心 API 功能:

- ✅ 健康检查端点
- ✅ OpenAPI schema
- ✅ MCP 工具列表
- ✅ MCP 资源列表
- ✅ MCP 提示列表
- ✅ MCP 初始化
- ✅ MCP 工具调用 (通过网关)
- ✅ MCP 服务器状态
- ✅ MCP HTTP 代理
- ✅ 错误处理
- ✅ 并发工具调用
- ✅ 采样配置

### 3. SSE Bridge 测试 (`test_sse_bridge.py`)

测试 Server-Sent Events 桥接功能:

- ✅ SSE 端点连接
- ✅ SSE 握手协议
- ✅ SSE JSON-RPC 消息传输
- ✅ SSE 工具列表
- ✅ SSE 认证
- ✅ SSE 重连能力
- ✅ SSE 错误处理
- ✅ mcp-cli 兼容性
- ✅ Claude Desktop 兼容性

### 4. OpenAI API 兼容性测试 (`test_openai_compatibility.py`)

测试与 OpenAI API 的兼容性:

- ✅ Chat Completions 端点
- ✅ 带工具的 Chat Completions
- ✅ 流式 Chat Completions
- ✅ 工具执行流程
- ✅ 错误处理
- ✅ 多个工具调用
- ✅ Models 端点
- ✅ OpenAI 客户端兼容性
- ✅ 响应格式验证
- ✅ DuckDuckGo 工具集成
- ✅ 工具调用往返

## 🚀 快速开始

### 安装依赖

```bash
# 安装测试依赖
pip install -r tests/requirements.txt

# 或使用 uv
uv pip install -r tests/requirements.txt
```

### 配置环境变量

```bash
# MCP-Bridge 服务地址 (默认: http://localhost:8000)
export MCP_BRIDGE_URL="http://localhost:8000"

# DuckDuckGo MCP 服务地址 (默认: http://localhost:8080)
export DUCKDUCKGO_MCP_URL="http://localhost:8080"

# 测试 API Key (如果启用了认证)
export TEST_API_KEY="your-test-api-key"

# 跳过需要外部服务的测试
export SKIP_EXTERNAL_TESTS="false"
```

### 运行测试

#### 使用测试脚本 (推荐)

```bash
# 运行所有测试
python tests/run_tests.py

# 只运行集成测试
python tests/run_tests.py --integration

# 只运行 DuckDuckGo 测试
python tests/run_tests.py --duckduckgo

# 快速测试 (跳过外部服务)
python tests/run_tests.py --fast

# 生成覆盖率报告
python tests/run_tests.py --coverage

# 详细输出
python tests/run_tests.py --verbose
```

#### 使用 pytest 直接运行

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_duckduckgo_mcp.py -v

# 运行特定测试类
pytest tests/test_duckduckgo_mcp.py::TestDuckDuckGoMCPServer -v

# 运行特定测试方法
pytest tests/test_duckduckgo_mcp.py::TestDuckDuckGoMCPServer::test_mcp_initialize -v

# 使用标记过滤
pytest tests/ -m integration          # 只运行集成测试
pytest tests/ -m "not external"       # 跳过外部服务测试
pytest tests/ -m duckduckgo           # 只运行 DuckDuckGo 测试

# 生成覆盖率报告
pytest tests/ --cov=mcp_bridge --cov-report=html

# 并行运行测试
pytest tests/ -n auto
```

## 📊 测试组织结构

```
tests/
├── __init__.py                 # 测试包初始化
├── conftest.py                 # pytest 配置和共享 fixtures
├── requirements.txt            # 测试依赖
├── run_tests.py               # 测试运行脚本
├── README.md                  # 本文档
├── test_duckduckgo_mcp.py     # DuckDuckGo MCP 测试
├── test_mcp_bridge_api.py     # MCP-Bridge API 测试
├── test_sse_bridge.py         # SSE Bridge 测试
└── test_openai_compatibility.py # OpenAI 兼容性测试
```

## 🏷️ 测试标记

测试使用 pytest 标记进行分类:

- `@pytest.mark.integration`: 集成测试 (需要运行的服务)
- `@pytest.mark.unit`: 单元测试 (独立测试)
- `@pytest.mark.external`: 需要外部服务的测试
- `@pytest.mark.duckduckgo`: DuckDuckGo 相关测试

## 🔧 Fixtures

测试套件提供以下共享 fixtures:

### 客户端 Fixtures

- `http_client`: MCP-Bridge HTTP 客户端
- `ddg_mcp_client`: DuckDuckGo MCP HTTP 客户端

### 配置 Fixtures

- `test_config`: 测试配置对象
- `auth_headers`: 认证请求头
- `jsonrpc_headers`: JSON-RPC 请求头
- `jsonrpc_request`: JSON-RPC 请求模板

### 数据 Fixtures

- `sample_search_query`: 示例搜索查询 ("artificial intelligence")
- `sample_news_query`: 示例新闻查询 ("technology news")
- `sample_instant_answer_query`: 示例即时答案查询 ("capital of France")

## 📝 编写新测试

### 添加新测试文件

```python
# tests/test_new_feature.py

import pytest

@pytest.mark.external
@pytest.mark.integration
class TestNewFeature:
    """新功能测试套件"""

    @pytest.mark.asyncio
    async def test_new_endpoint(self, http_client, auth_headers):
        """测试新端点"""
        response = await http_client.get(
            "/new-endpoint",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # 添加断言...

        print("✅ 测试通过")
```

### 使用 Fixtures

```python
@pytest.mark.asyncio
async def test_with_fixtures(
    http_client,
    auth_headers,
    jsonrpc_request,
    sample_search_query
):
    """使用多个 fixtures"""
    request_data = {
        **jsonrpc_request,
        "method": "tools/call",
        "params": {
            "name": "web_search",
            "arguments": {"query": sample_search_query}
        }
    }

    response = await http_client.post(
        "/v1/mcp/",
        headers=auth_headers,
        json=request_data
    )

    assert response.status_code == 200
```

## 🐛 调试测试

### 详细输出

```bash
# 打印详细输出
pytest tests/ -vv -s

# 打印特定测试的输出
pytest tests/test_duckduckgo_mcp.py::TestDuckDuckGoMCPServer::test_mcp_initialize -vv -s
```

### 只运行失败的测试

```bash
# 第一次运行
pytest tests/ --failed

# 之后只运行失败的
pytest tests/ --lf
```

### 停在第一个失败处

```bash
pytest tests/ -x
```

## 📈 持续集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mcp-bridge:
        image: mcp-bridge:latest
        ports:
          - 8000:8000

      duckduckgo-mcp:
        image: duckduckgo-mcp:latest
        ports:
          - 8080:8080

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r tests/requirements.txt

      - name: Run tests
        run: |
          python tests/run_tests.py --integration
```

## 🎯 测试最佳实践

1. **使用标记**: 始终使用适当的标记 (`@pytest.mark.*`)
2. **异步测试**: 所有 HTTP 客户端测试应该是异步的
3. **fixtures 复用**: 使用共享 fixtures 避免重复代码
4. **清晰的输出**: 使用 `print` 语句提供清晰的测试反馈
5. **错误处理**: 测试正常和错误情况
6. **独立性**: 每个测试应该独立运行
7. **清理资源**: 使用 `async with` 确保资源清理

## 🔍 故障排除

### 常见问题

**Q: 测试失败，显示连接被拒绝**

A: 确保 MCP-Bridge 和相关服务正在运行:
```bash
docker compose -f docker-compose.duckduckgo.yml up -d
```

**Q: DuckDuckGo 测试超时**

A: 检查 DuckDuckGo MCP 服务是否运行:
```bash
curl http://localhost:8080/mcp
```

**Q: 认证测试失败**

A: 设置正确的 API Key:
```bash
export TEST_API_KEY="your-actual-api-key"
```

**Q: 如何跳过外部服务测试?**

A: 使用 `--fast` 标志或设置环境变量:
```bash
export SKIP_EXTERNAL_TESTS=true
```

## 📚 相关文档

- [DuckDuckGo 集成文档](../DUCKDUCKGO_INTEGRATION.md)
- [项目 README](../README.md)
- [MCP 协议规范](https://spec.modelcontextprotocol.io/)
- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)

## 🤝 贡献

欢迎贡献新的测试! 请遵循以下准则:

1. 将测试放在适当的文件中
2. 使用清晰的测试名称和描述
3. 添加适当的标记
4. 提供打印输出以便调试
5. 更新此文档

## 📄 许可证

MIT License - 与主项目相同
