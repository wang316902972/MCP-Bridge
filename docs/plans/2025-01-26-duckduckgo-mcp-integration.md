# DuckDuckGo MCP集成实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 完成DuckDuckGo MCP服务器与MCP-Bridge网关的集成，实现通过OpenAI API接口访问DuckDuckGo搜索功能

**架构:** 使用HTTP JSON-RPC 2.0协议将DuckDuckGo MCP服务器连接到MCP-Bridge网关，网关将MCP工具转换为OpenAI兼容的工具调用格式

**技术栈:** FastAPI, Docker, JSON-RPC 2.0, DuckDuckGo Search API, MCP Protocol

---

## 当前状态

✅ **已完成:**
- DuckDuckGo MCP服务器实现 (`duckduckgo_mcp_server/`)
- MCP-Bridge配置文件 (`config.json`)
- Docker Compose配置 (`compose.yml`)

⚠️ **待验证:**
- MCP-Bridge与DuckDuckGo服务器的连接
- 工具列表的可用性
- 完整的搜索功能测试

---

## Task 1: 验证DuckDuckGo MCP服务器状态

**文件:** 无（验证任务）

**Step 1: 检查DuckDuckGo服务器健康状态**

验证服务器是否在 `http://192.168.136.224:8005/mcp` 正常运行

```bash
curl -X POST http://192.168.136.224:8005/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python3 -m json.tool
```

**预期输出:**
```json
{
    "result": {
        "tools": [
            {
                "name": "web_search",
                "description": "Search the web using DuckDuckGo..."
            },
            {
                "name": "news_search",
                "description": "Search news articles..."
            },
            {
                "name": "instant_answer",
                "description": "Get instant answers..."
            }
        ]
    }
}
```

**Step 2: 测试web_search功能**

```bash
curl -X POST http://192.168.136.224:8005/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "artificial intelligence",
        "max_results": 3
      }
    },
    "id": 2
  }' | python3 -m json.tool
```

**预期输出:** 包含搜索结果的JSON响应，有title, url, snippet字段

**Step 3: 确认服务器可用性**

如果以上测试成功，DuckDuckGo服务器已就绪，继续Task 2

---

## Task 2: 启动MCP-Bridge网关

**文件:** `compose.yml`

**Step 1: 检查Docker服务状态**

```bash
docker ps -a | grep mcp-bridge
```

**预期输出:** 可能显示已存在的容器或无输出

**Step 2: 停止并清理旧容器（如果存在）**

```bash
docker compose -f compose.yml down
```

**预期输出:** 容器已停止并移除

**Step 3: 启动MCP-Bridge服务**

```bash
docker compose -f compose.yml up -d --build
```

**预期输出:**
```
[+] Running 2/2
 ✔ Network mcp-bridge          Built                                                                                                                                                 0.0s
 ✔ Container mcp-bridge         Started
```

**Step 4: 查看服务日志**

```bash
docker logs -f mcp-bridge --tail 50
```

**预期输出:** 服务正常启动，无严重错误日志

按 `Ctrl+C` 退出日志查看

**Step 5: 验证容器状态**

```bash
docker ps | grep mcp-bridge
```

**预期输出:** 容器状态为 `Up X seconds`

**Step 6: 提交检查点**

```bash
# 记录当前状态
docker logs mcp-bridge > logs/mcp-bridge-startup.log 2>&1
echo "✅ MCP-Bridge started at $(date)" >> logs/deployment.log
```

---

## Task 3: 验证MCP-Bridge配置加载

**文件:** `config.json`

**Step 1: 检查配置文件挂载**

```bash
docker exec mcp-bridge cat /mcp_bridge/config.json | python3 -m json.tool | head -20
```

**预期输出:** 显示config.json内容，包含duckduckgo服务器配置

**Step 2: 测试MCP-Bridge健康检查**

```bash
curl -s http://localhost:8004/health | python3 -m json.tool
```

**预期输出:** `{"status": "healthy"}` 或类似健康状态

**Step 3: 通过MCP-Bridge列出可用工具**

```bash
curl -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python3 -m json.tool
```

**预期输出:**
```json
{
    "result": {
        "tools": [
            {
                "name": "web_search",
                "description": "Search the web using DuckDuckGo..."
            },
            {
                "name": "news_search",
                "description": "Search news articles..."
            },
            {
                "name": "instant_answer",
                "description": "Get instant answers..."
            }
        ]
    }
}
```

**Step 4: 验证日志中的连接信息**

```bash
docker logs mcp-bridge 2>&1 | grep -i "duckduckgo\|mcp.*server"
```

**预期输出:** 显示DuckDuckGo服务器连接成功的日志

**Step 5: 提交检查点**

```bash
echo "✅ Configuration verified at $(date)" >> logs/deployment.log
```

---

## Task 4: 端到端功能测试

**文件:** 测试脚本

**Step 1: 测试web_search工具**

```bash
curl -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "Python programming",
        "max_results": 3
      }
    },
    "id": 2
  }' | python3 -m json.tool
```

**预期输出:**
```json
{
    "result": {
        "content": [
            {
                "type": "text",
                "text": "{\"results\": [{\"title\": \"...\", \"url\": \"...\", \"body\": \"...\"}]}"
            }
        ]
    }
}
```

**Step 2: 测试news_search工具**

```bash
curl -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "news_search",
      "arguments": {
        "query": "technology",
        "max_results": 3
      }
    },
    "id": 3
  }' | python3 -m json.tool
```

**预期输出:** 包含新闻搜索结果的JSON响应

**Step 3: 测试instant_answer工具**

```bash
curl -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "instant_answer",
      "arguments": {
        "query": "capital of France"
      }
    },
    "id": 4
  }' | python3 -m json.tool
```

**预期输出:** 包含"Paris"的快速答案

**Step 4: 创建测试脚本**

创建: `tests/test_duckduckgo_integration.sh`

```bash
#!/bin/bash
set -e

echo "Testing DuckDuckGo MCP Integration..."

# Test 1: List tools
echo "Test 1: Listing tools..."
curl -s -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
  | python3 -m json.tool \
  | grep -q "web_search" && echo "✅ web_search found" || echo "❌ web_search not found"

# Test 2: Web search
echo "Test 2: Testing web_search..."
RESULT=$(curl -s -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "test",
        "max_results": 1
      }
    },
    "id": 2
  }')
echo "$RESULT" | python3 -m json.tool | grep -q "results" && echo "✅ web_search working" || echo "❌ web_search failed"

# Test 3: News search
echo "Test 3: Testing news_search..."
curl -s -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "news_search",
      "arguments": {
        "query": "tech",
        "max_results": 1
      }
    },
    "id": 3
  }' | python3 -m json.tool | grep -q "content" && echo "✅ news_search working" || echo "❌ news_search failed"

# Test 4: Instant answer
echo "Test 4: Testing instant_answer..."
curl -s -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "instant_answer",
      "arguments": {
        "query": "2+2"
      }
    },
    "id": 4
  }' | python3 -m json.tool | grep -q "content" && echo "✅ instant_answer working" || echo "❌ instant_answer failed"

echo "All tests completed!"
```

**Step 5: 运行测试脚本**

```bash
chmod +x tests/test_duckduckgo_integration.sh
bash tests/test_duckduckgo_integration.sh
```

**预期输出:** 所有测试显示 ✅

**Step 6: 提交测试结果**

```bash
echo "✅ E2E tests passed at $(date)" >> logs/deployment.log
```

---

## Task 5: OpenAI API兼容性测试

**文件:** 测试脚本

**Step 1: 测试OpenAI格式工具列表**

```bash
curl -s http://localhost:8004/v1/tools | python3 -m json.tool
```

**预期输出:** OpenAI格式的工具列表

**Step 2: 使用OpenAI客户端测试（可选）**

如果安装了OpenAI Python客户端:

创建: `tests/test_openai_client.py`

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8004/v1",
    api_key="test"
)

# List tools
tools = client.tools.list()
print("Available tools:", [tool.name for tool in.tools.data])

# Simple chat completion with tools
response = client.chat.completions.create(
    model="gpt-4",  # 替换为实际模型
    messages=[
        {"role": "user", "content": "Search for recent AI news"}
    ],
    tools=tools.data
)

print("Response:", response.choices[0].message)
```

**Step 3: 运行Python测试**

```bash
python3 tests/test_openai_client.py
```

**预期输出:** 显示可用工具和模型响应

---

## Task 6: 文档更新

**文件:** `README.md`, `docs/duckduckgo-integration.md`

**Step 1: 创建集成文档**

创建: `docs/duckduckgo-integration.md`

```markdown
# DuckDuckGo MCP集成指南

## 概述

DuckDuckGo MCP服务器提供隐私保护的搜索功能，通过MCP-Bridge网关以OpenAI API兼容格式暴露。

## 架构

```
OpenAI客户端 → MCP-Bridge (:8004) → DuckDuckGo MCP (:8005/mcp)
```

## 可用工具

### 1. web_search
网页搜索，支持时间范围过滤

**参数:**
- `query` (string): 搜索查询
- `max_results` (int, 可选): 返回结果数 (1-100)
- `time_range` (string, 可选): day|week|month|year

### 2. news_search
新闻文章搜索

**参数:**
- `query` (string): 搜索查询
- `max_results` (int, 可选): 返回结果数 (1-100)

### 3. instant_answer
快速答案，适合事实查询

**参数:**
- `query` (string): 查询内容

## 使用示例

### 通过cURL

\`\`\`bash
# 列出工具
curl -X POST http://localhost:8004/v1/mcp/ \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# 执行搜索
curl -X POST http://localhost:8004/v1/mcp/ \\
  -H "Content-Type: application/json" \\
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "web_search",
      "arguments": {"query": "AI news", "max_results": 5}
    },
    "id": 2
  }'
\`\`\`

### 通过OpenAI Python客户端

\`\`\`python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8004/v1",
    api_key="your-key"
)

# 获取工具
tools = client.tools.list()

# 使用工具进行对话
response = client.chat.completions.create(
    model="your-model",
    messages=[{"role": "user", "content": "Search for Python tutorials"}],
    tools=tools.data
)
\`\`\`

## 部署

\`\`\`bash
# 启动服务
docker compose -f compose.yml up -d

# 验证
curl http://localhost:8004/health
\`\`\`

## 配置

配置文件: `config.json`

\`\`\`json
{
  "mcp_servers": {
    "duckduckgo": {
      "url": "http://192.168.136.224:8005/mcp"
    }
  }
}
\`\`\`
```

**Step 2: 更新主README**

修改: `README.md` (在适当位置添加)

```markdown
## 集成的MCP服务器

- **DuckDuckGo**: 隐私保护的网页和新闻搜索
  - 文档: [DuckDuckGo集成指南](docs/duckduckgo-integration.md)
  - 工具: web_search, news_search, instant_answer
```

**Step 3: 提交文档**

```bash
git add README.md docs/duckduckgo-integration.md
git commit -m "docs: add DuckDuckGo MCP integration documentation"
```

---

## Task 7: 性能和错误处理测试

**文件:** 测试脚本

**Step 1: 测试并发请求**

创建: `tests/test_concurrent.sh`

```bash
#!/bin/bash
echo "Testing concurrent requests..."

for i in {1..10}; do
  curl -s -X POST http://localhost:8004/v1/mcp/ \
    -H "Content-Type: application/json" \
    -d '{
      "jsonrpc":"2.0",
      "method":"tools/call",
      "params": {
        "name": "web_search",
        "arguments": {"query": "test '$i'", "max_results": 1}
      },
      "id": '$i'
    }' > /tmp/result_$i.json &
done

wait

echo "Completed 10 concurrent requests"
grep -l "results" /tmp/result_*.json | wc -l
```

**Step 2: 运行并发测试**

```bash
bash tests/test_concurrent.sh
```

**预期输出:** 10个请求全部成功

**Step 3: 测试错误处理**

```bash
# 测试无效工具名
curl -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "invalid_tool",
      "arguments": {}
    },
    "id": 1
  }' | python3 -m json.tool
```

**预期输出:** JSON-RPC错误响应

```bash
# 测试缺少必需参数
curl -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params": {
      "name": "web_search",
      "arguments": {}
    },
    "id": 2
  }' | python3 -m json.tool
```

**预期输出:** 参数验证错误

**Step 4: 查看错误日志**

```bash
docker logs mcp-bridge 2>&1 | grep -i error | tail -20
```

**Step 5: 提交测试结果**

```bash
echo "✅ Performance and error handling tests passed at $(date)" >> logs/deployment.log
```

---

## Task 8: 部署验证和监控

**文件:** 监控脚本

**Step 1: 创建监控脚本**

创建: `scripts/monitor-bridge.sh`

```bash
#!/bin/bash

echo "MCP-Bridge Monitoring Script"
echo "=============================="

while true; do
  clear
  echo "Time: $(date)"
  echo ""

  # Container status
  echo "📦 Container Status:"
  docker ps | grep mcp-bridge
  echo ""

  # Health check
  echo "🏥 Health Check:"
  curl -s http://localhost:8004/health | python3 -m json.tool 2>/dev/null || echo "❌ Health check failed"
  echo ""

  # Available tools
  echo "🔧 Available Tools:"
  curl -s -X POST http://localhost:8004/v1/mcp/ \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
    | python3 -m json.tool 2>/dev/null | grep -A 1 '"name"' | head -6
  echo ""

  # Recent logs
  echo "📋 Recent Logs (last 5):"
  docker logs --tail 5 mcp-bridge 2>&1
  echo ""

  sleep 5
done
```

**Step 2: 启动监控（可选）**

```bash
chmod +x scripts/monitor-bridge.sh
bash scripts/monitor-bridge.sh
```

按 `Ctrl+C` 停止监控

**Step 3: 创建部署检查清单**

创建: `docs/deployment-checklist.md`

```markdown
# DuckDuckGo MCP部署检查清单

## 部署前检查

- [ ] DuckDuckGo MCP服务器运行在 http://192.168.136.224:8005/mcp
- [ ] config.json已配置正确的服务器URL
- [ ] Docker和Docker Compose已安装
- [ ] 端口8004未被占用

## 部署步骤

- [ ] 运行 `docker compose -f compose.yml up -d --build`
- [ ] 验证容器状态: `docker ps | grep mcp-bridge`
- [ ] 检查日志: `docker logs mcp-bridge`

## 功能验证

- [ ] 健康检查: `curl http://localhost:8004/health`
- [ ] 工具列表: `curl -X POST http://localhost:8004/v1/mcp/ -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'`
- [ ] web_search测试
- [ ] news_search测试
- [ ] instant_answer测试

## 性能测试

- [ ] 并发请求测试
- [ ] 错误处理测试
- [ ] 响应时间检查

## 监控设置

- [ ] 配置日志收集
- [ ] 设置健康检查监控
- [ ] 配置告警（可选）

## 文档

- [ ] 集成文档已更新
- [ ] README已更新
- [ ] 部署检查清单已创建
```

**Step 4: 运行检查清单**

```bash
cat docs/deployment-checklist.md
```

**Step 5: 最终验证**

```bash
# 完整的端到端测试
bash tests/test_duckduckgo_integration.sh

# 检查所有服务状态
docker compose -f compose.yml ps

# 查看最终日志
docker logs mcp-bridge --tail 50
```

**Step 6: 提交完成标记**

```bash
echo "✅ Deployment completed and verified at $(date)" >> logs/deployment.log
git add .
git commit -m "feat: complete DuckDuckGo MCP integration and verification"
```

---

## 成功标准

集成完成需满足:

1. ✅ DuckDuckGo MCP服务器可访问
2. ✅ MCP-Bridge成功启动并加载配置
3. ✅ 三个搜索工具都可正常工作
4. ✅ 通过OpenAI API格式可以访问工具
5. ✅ 并发请求处理正常
6. ✅ 错误处理工作正常
7. ✅ 文档完整更新
8. ✅ 测试脚本可重复执行

## 故障排除

### DuckDuckGo服务器无法连接

检查:
```bash
curl http://192.168.136.224:8005/mcp -X POST -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

如果失败，检查:
- DuckDuckGo服务器是否运行
- 网络连接是否正常
- 防火墙规则

### MCP-Bridge无法加载配置

检查:
```bash
docker exec mcp-bridge cat /mcp_bridge/config.json
```

验证JSON格式和配置路径

### 工具调用失败

查看日志:
```bash
docker logs mcp-bridge -f
```

查找错误信息并参考MCP协议文档

---

**计划完成并保存至 `docs/plans/2025-01-26-duckduckgo-mcp-integration.md`**

## 执行选项

**方案1: 子代理驱动（当前会话）** - 我在每个任务间调度新的子代理，审查结果，快速迭代

**方案2: 并行会话（独立）** - 在worktree中打开新会话，使用executing-plans批量执行并设置检查点

**选择哪个方案？**
