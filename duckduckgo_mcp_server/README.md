# DuckDuckGo MCP Server

A Model Context Protocol (MCP) server that provides DuckDuckGo search capabilities over HTTP JSON-RPC 2.0.

## Overview

This server implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to expose DuckDuckGo search functionality as standardized tools. It can be integrated with MCP-compatible clients and gateways like MCP-Bridge.

## Features

- **Three Search Tools**:
  - `web_search`: General web search with time range filtering
  - `news_search`: News-specific search
  - `instant_answer`: Quick answers (calculations, definitions, facts)

- **MCP Protocol Compliant**: Implements JSON-RPC 2.0 over HTTP
- **FastAPI-based**: High-performance async Python web framework
- **Docker Ready**: Containerized deployment with health checks
- **Privacy-Focused**: Uses DuckDuckGo which doesn't track users

## Installation

### Method 1: Docker (Recommended)

```bash
# Build the Docker image
docker build -t duckduckgo-mcp .

# Run the server
docker run -p 8080:8080 duckduckgo-mcp
```

### Method 2: Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python server.py
```

The server will start on `http://0.0.0.0:8080`

## MCP Tools

### 1. web_search

Search the web using DuckDuckGo.

**Parameters**:
- `query` (string, required): Search query string
- `max_results` (integer, optional): Maximum number of results (1-100, default: 10)
- `time_range` (string, optional): Filter by time period (`day`, `week`, `month`, `year`)

**Example Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "web_search",
    "arguments": {
      "query": "artificial intelligence latest developments",
      "max_results": 5,
      "time_range": "week"
    }
  },
  "id": 1
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[\n  {\n    \"title\": \"AI News\",\n    \"url\": \"https://example.com\",\n    \"snippet\": \"Latest AI developments...\"\n  }\n]"
      }
    ]
  },
  "id": 1
}
```

### 2. news_search

Search news articles using DuckDuckGo.

**Parameters**:
- `query` (string, required): Search query string
- `max_results` (integer, optional): Maximum number of results (1-100, default: 10)

**Example Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "news_search",
    "arguments": {
      "query": "technology news",
      "max_results": 5
    }
  },
  "id": 2
}
```

### 3. instant_answer

Get instant answers from DuckDuckGo.

**Parameters**:
- `query` (string, required): Query for instant answer

**Example Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "instant_answer",
    "arguments": {
      "query": "capital of France"
    }
  },
  "id": 3
}
```

## API Endpoints

### POST /mcp

Main MCP JSON-RPC 2.0 endpoint.

**Supported Methods**:
- `initialize`: Initialize MCP session
- `tools/list`: List available tools
- `tools/call`: Execute a tool
- `notifications/initialized`: Session initialized notification

### GET /

Server information and API documentation.

## Testing

### Manual Testing with curl

```bash
# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Initialize session
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {"tools": {}},
      "clientInfo": {"name": "test", "version": "1.0.0"}
    },
    "id": 2
  }'

# Execute web search
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "DuckDuckGo privacy",
        "max_results": 3
      }
    },
    "id": 3
  }'
```

### Automated Testing

```bash
# Run test script
python test_server.py
```

## Integration with MCP-Bridge

### 1. Add to config.json

```json
{
  "mcp_servers": {
    "duckduckgo": {
      "url": "http://duckduckgo-mcp:8080/mcp"
    }
  }
}
```

### 2. Update docker-compose.yml

```yaml
services:
  duckduckgo-mcp:
    build: ./duckduckgo_mcp_server
    ports:
      - "8080:8080"
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/mcp')"]
      interval: 30s
      timeout: 10s
      retries: 3

  mcp-bridge:
    # ... existing configuration ...
    depends_on:
      - duckduckgo-mcp
```

### 3. Test Integration

```bash
# Start services
docker-compose up -d

# Test through MCP-Bridge proxy
curl -X POST http://localhost:8004/v1/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Configuration

### Environment Variables

- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8080`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Proxy Configuration

If running behind a proxy, configure environment variables:

```bash
export http_proxy=http://proxy-server:port
export https_proxy=http://proxy-server:port
export NO_PROXY=localhost,127.0.0.1
```

## Development

### Project Structure

```
duckduckgo_mcp_server/
├── server.py              # Main MCP server implementation
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker image configuration
├── test_server.py        # Test script
└── README.md             # This file
```

### Adding New Tools

1. Define tool schema in `get_tools_definition()`
2. Implement tool logic in `execute_tool()`
3. Add input validation and error handling
4. Update tests and documentation

## Performance Considerations

- **Rate Limiting**: DuckDuckGo doesn't have official rate limits, but be respectful
- **Caching**: Consider implementing caching for frequent searches
- **Timeout**: Default timeout is 30 seconds per request
- **Async Operations**: All I/O operations are async for better performance

## Troubleshooting

### Common Issues

**Issue**: "Network unreachable" errors
**Solution**: Configure proxy settings or use `NO_PROXY` for localhost

**Issue**: Port already in use
**Solution**: Change port with `--port` flag or stop conflicting service

**Issue**: No search results
**Solution**: Check network connectivity and DuckDuckGo service status

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python server.py
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:
- Check the logs: `/tmp/ddg_server.log` or Docker logs
- Review test output: `python test_server.py`
- Consult MCP specification: https://modelcontextprotocol.io/

## Acknowledgments

- [DuckDuckGo](https://duckduckgo.com/) for the search API
- [Model Context Protocol](https://modelcontextprotocol.io/) for the protocol specification
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
