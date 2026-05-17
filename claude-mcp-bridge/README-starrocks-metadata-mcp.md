# StarRocks Metadata MCP Server 使用文档

## 概述

**StarRocks Metadata MCP Server** 是一个基于 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 的远程元数据查询服务，提供对 StarRocks / Doris / MySQL 数据库的元数据查询能力，包括列出数据库、列出表、查看表结构、查看分区、搜索表、获取表属性等功能。

### 架构

```
Claude Code / Claude Desktop
    │  stdio (JSON-RPC 2.0)
    ▼
mcp-bridge-starrocks-metadata.py   ← 本地 Bridge 脚本（stdio → HTTP 代理）
    │  HTTP POST
    ▼
http://192.168.136.224:8008/mcp    ← 远程 MCP Server（FastAPI + JSON-RPC 2.0）
    │
    ▼
StarRocks / Doris / MySQL 数据库
```

- **Bridge 脚本**（`mcp-bridge-starrocks-metadata.py`）：将 MCP 标准 stdio 协议转发为 HTTP 请求，部署在客户端本地。
- **远程 MCP Server**（`syncschema` 服务）：运行在 `192.168.136.224:8008`，提供 `/mcp` 端点处理 JSON-RPC 2.0 请求。

---

## 快速开始

### 1. 前置条件

- Python 3.8+
- `curl` 命令可用
- 网络可达 `192.168.136.224:8008`

### 2. 在 Claude Code 中配置

编辑 Claude Code 的 MCP 配置文件（通常在 `~/.claude/settings.json` 或项目 `.mcp.json`）：

```json
{
  "mcpServers": {
    "starrocks-metadata": {
      "command": "python3",
      "args": ["/usr/local/src/MCP-Bridge/claude-mcp-bridge/mcp-bridge-starrocks-metadata.py"],
      "env": {
        "MCP_BRIDGE_URL": "http://192.168.136.224:8008/mcp",
        "MCP_TIMEOUT": "30"
      }
    }
  }
}
```

### 3. 在 Claude Desktop 中配置

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "starrocks-metadata": {
      "command": "python3",
      "args": ["/path/to/mcp-bridge-starrocks-metadata.py"],
      "env": {
        "MCP_BRIDGE_URL": "http://192.168.136.224:8008/mcp",
        "MCP_TIMEOUT": "30"
      }
    }
  }
}
```

### 4. 验证连接

配置完成后，在 Claude 中询问：

> 帮我列出所有数据库

Claude 会自动调用 `starrocks_list_databases` 工具返回数据库列表。

---

## 环境变量

Bridge 脚本支持以下环境变量：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MCP_BRIDGE_URL` | `http://192.168.136.224:8008/mcp` | 远程 MCP Server 的 HTTP 端点地址 |
| `MCP_TIMEOUT` | `30` | HTTP 请求超时时间（秒） |

---

## 可用工具（Tools）

### 1. `starrocks_list_databases` — 列出数据库

列出所有可访问的数据库。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `dbtype` | string | 否 | `doris` | 数据库类型：`mysql` 或 `doris` |

**使用示例：**

> 列出所有 doris 数据库

> 帮我查看 mysql 下有哪些数据库（dbtype 传 mysql）

---

### 2. `starrocks_list_tables` — 列出表

列出指定数据库中的表，支持表类型和数据层级过滤。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `database` | string | **是** | — | 数据库名称 |
| `dbtype` | string | 否 | `doris` | 数据库类型：`mysql` 或 `doris` |
| `table_type` | string | 否 | — | 表类型过滤 |
| `layer` | string | 否 | — | 数据层级过滤（`ods`、`dwd`、`dws`、`ads`、`dim`） |
| `limit` | integer | 否 | `50` | 返回数量限制 |

**使用示例：**

> 列出 nd_game_ads_biz 数据库的所有表

> 列出 nd_game_ads_biz 数据库中 dws 层的表，最多返回 100 个

---

### 3. `starrocks_describe_table` — 获取表结构

获取指定表的详细结构信息，包括列定义、分区信息、分桶策略等。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `table` | string | **是** | — | 表名称 |
| `database` | string | 否 | 配置默认库 | 数据库名称 |
| `dbtype` | string | 否 | `doris` | 数据库类型：`mysql` 或 `doris` |

**使用示例：**

> 查看 ads_game_user_summary 表的结构

> 描述一下 nd_game_ads_biz 库里 dws_order_detail 表的字段

---

### 4. `starrocks_list_partitions` — 列出分区信息

列出指定表的分区详情。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `table` | string | **是** | — | 表名称 |
| `database` | string | 否 | 配置默认库 | 数据库名称 |
| `dbtype` | string | 否 | `doris` | 数据库类型：`mysql` 或 `doris` |

**使用示例：**

> 查看 dws_order_detail 表的分区情况

---

### 5. `starrocks_search_tables` — 搜索表

通过关键词搜索表，支持按数据库、表类型和数据层级过滤。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `keyword` | string | **是** | — | 搜索关键词 |
| `database` | string | 否 | 全部数据库 | 限定搜索范围 |
| `dbtype` | string | 否 | `doris` | 数据库类型：`mysql` 或 `doris` |
| `table_type` | string | 否 | — | 表类型过滤 |
| `layer` | string | 否 | — | 数据层级过滤 |
| `limit` | integer | 否 | `50` | 返回数量限制 |

**使用示例：**

> 搜索包含 "order" 关键词的表

> 在 nd_game_ads_biz 库中搜索 dws 层包含 "user" 的表

---

### 6. `starrocks_get_table_properties` — 获取表属性

获取表的属性配置，包括副本数、存储介质、排序键等。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `table` | string | **是** | — | 表名称 |
| `database` | string | 否 | 配置默认库 | 数据库名称 |
| `dbtype` | string | 否 | `doris` | 数据库类型：`mysql` 或 `doris` |

**使用示例：**

> 查看 ads_game_user_summary 表的属性配置

---

## dbtype 参数说明

所有工具都支持 `dbtype` 参数来切换目标数据库实例：

| dbtype 值 | 连接目标 | 说明 |
|-----------|----------|------|
| `doris`（默认） | StarRocks / Doris 集群 | 端口 9030，使用 `DORIS_*` / `STARROCKS_*` 环境变量配置 |
| `mysql` | MySQL 数据库 | 端口 3306，使用 `MYSQL_*` 环境变量配置 |

---

## REST API 端点（直接 HTTP 调用）

除了 MCP 协议，远程服务还提供 REST API：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 服务信息 |
| `GET` | `/health` | 健康检查 |
| `GET` | `/docs` | Swagger API 文档 |
| `GET` | `/cache/stats` | 缓存统计 |
| `POST` | `/cache/clear` | 清除缓存 |
| `POST` | `/api/sync` | 同步元数据到知识库 |
| `POST` | `/api/metadata` | 查询元数据 |
| `POST` | `/mcp` | MCP JSON-RPC 2.0 端点 |

### 直接调用 MCP 端点示例

```bash
# 列出工具
curl -s -X POST http://192.168.136.224:8008/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# 列出数据库
curl -s -X POST http://192.168.136.224:8008/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"starrocks_list_databases","arguments":{"dbtype":"doris"}},"id":2}'

# 搜索表
curl -s -X POST http://192.168.136.224:8008/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"starrocks_search_tables","arguments":{"keyword":"order","dbtype":"doris"}},"id":3}'

# 获取表结构
curl -s -X POST http://192.168.136.224:8008/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"starrocks_describe_table","arguments":{"table":"ads_game_user_summary","dbtype":"doris"}},"id":4}'
```

---

## 服务端部署

远程 MCP Server（`syncschema` 项目）通过 Docker Compose 部署：

```bash
cd /usr/local/src/syncschema

# 复制并编辑环境变量
cp .env.example .env
# 编辑 .env 填入实际数据库连接信息

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 验证服务
curl http://192.168.136.224:8008/health
```

### 服务端环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DORIS_HOST` | Doris/StarRocks 主机 | `longzhou-doris1.lz.dscc.99.com` |
| `DORIS_PORT` | Doris/StarRocks 端口 | `9030` |
| `DORIS_USER` | 用户名 | `test_user01` |
| `DORIS_PASSWORD` | 密码 | `your_password` |
| `DORIS_DATABASE` | 默认数据库 | `nd_game_ads_biz` |
| `MYSQL_HOST` | MySQL 主机 | `172.24.140.110` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户 | `root` |
| `MYSQL_PASSWORD` | MySQL 密码 | `your_password` |
| `KB_API_URL` | 知识库 API 地址 | `http://192.168.136.224:8003` |
| `API_HOST` | 服务监听地址 | `0.0.0.0` |
| `API_PORT` | 服务监听端口 | `8008` |

---

## 故障排查

### 1. Bridge 脚本无响应

```bash
# 测试远程服务是否可达
curl -s http://192.168.136.224:8008/health

# 手动测试 MCP 端点
curl -s -X POST http://192.168.136.224:8008/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### 2. 连接超时

增大超时时间：

```json
{
  "env": {
    "MCP_TIMEOUT": "60"
  }
}
```

### 3. 数据库连接失败

检查远程服务日志：

```bash
docker-compose -f /usr/local/src/syncschema/docker-compose.yml logs -f
```

### 4. 缓存问题

元数据查询结果默认缓存 5 分钟，如需实时数据：

```bash
# 清除缓存
curl -X POST http://192.168.136.224:8008/cache/clear

# 查看缓存统计
curl http://192.168.136.224:8008/cache/stats
```

---

## 相关项目

| 项目 | 路径 | 说明 |
|------|------|------|
| MCP Bridge 脚本 | `/usr/local/src/MCP-Bridge/claude-mcp-bridge/` | 本地 stdio → HTTP 代理 |
| syncschema 服务 | `/usr/local/src/syncschema/` | 远程 MCP Server + REST API |
| Lineage MCP | `mcp-bridge-starrocks-lineage.py` | 血缘关系查询（端口 8007） |
| Knowledge Base MCP | `mcp-bridge-knowledge-base.py` | 知识库查询 |
