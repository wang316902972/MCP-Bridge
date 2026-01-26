#!/usr/bin/env python3
"""DuckDuckGo MCP Server - HTTP JSON-RPC 2.0

This server implements the Model Context Protocol (MCP) over HTTP JSON-RPC 2.0,
providing DuckDuckGo search capabilities as MCP tools.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import json
import uvicorn

try:
    from duckduckgo_search import DDGS
except ImportError:
    print("ERROR: duckduckgo-search not installed. Run: pip install duckduckgo-search")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="DuckDuckGo MCP Server",
    description="MCP server providing DuckDuckGo search capabilities",
    version="1.0.0"
)


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 Request Model"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: int


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 Response Model"""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: int


def get_tools_definition() -> List[Dict[str, Any]]:
    """Return MCP tools definition

    Returns:
        List of tool definitions with name, description, and input schema
    """
    return [
        {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo. Returns relevant web pages with titles, URLs, and snippets.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of results to return (1-100)"
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["day", "week", "month", "year"],
                        "default": None,
                        "description": "Filter results by time period"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "news_search",
            "description": "Search news articles using DuckDuckGo. Returns recent news articles with metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of results to return (1-100)"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "instant_answer",
            "description": "Get instant answers from DuckDuckGo. Useful for quick facts, calculations, definitions, etc.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query for instant answer"
                    }
                },
                "required": ["query"]
            }
        }
    ]


async def call_web_search(ddgs: DDGS, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute web search using DuckDuckGo

    Args:
        ddgs: DuckDuckGo search instance
        arguments: Search arguments (query, max_results, time_range)

    Returns:
        List of search results with title, url, and snippet
    """
    query = arguments["query"]
    max_results = arguments.get("max_results", 10)
    time_range = arguments.get("time_range")

    # Validate max_results
    if not 1 <= max_results <= 100:
        max_results = min(100, max(1, max_results))

    logger.info(f"🔍 Web search: query='{query}', max_results={max_results}, time_range={time_range}")

    try:
        search_results = ddgs.text(
            query,
            max_results=max_results,
            timelimit=time_range or None
        )

        results = []
        for r in search_results:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("body", "")
            })

        logger.info(f"✅ Web search returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"❌ Web search error: {e}")
        raise


async def call_news_search(ddgs: DDGS, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute news search using DuckDuckGo

    Args:
        ddgs: DuckDuckGo search instance
        arguments: Search arguments (query, max_results)

    Returns:
        List of news results with title, url, snippet, date, and source
    """
    query = arguments["query"]
    max_results = arguments.get("max_results", 10)

    # Validate max_results
    if not 1 <= max_results <= 100:
        max_results = min(100, max(1, max_results))

    logger.info(f"📰 News search: query='{query}', max_results={max_results}")

    try:
        search_results = ddgs.news(query, max_results=max_results)

        results = []
        for r in search_results:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("body", ""),
                "date": r.get("date", ""),
                "source": r.get("source", "")
            })

        logger.info(f"✅ News search returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"❌ News search error: {e}")
        raise


async def call_instant_answer(ddgs: DDGS, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute instant answer search using DuckDuckGo

    Args:
        ddgs: DuckDuckGo search instance
        arguments: Search arguments (query)

    Returns:
        List of instant answers with text, url, and type
    """
    query = arguments["query"]

    logger.info(f"⚡ Instant answer: query='{query}'")

    try:
        # Use chat() for instant answers (new API for ddgs package)
        answer_results = ddgs.chat(query, model="default")

        results = [{
            "text": answer_results,
            "url": "",
            "type": "answer"
        }]

        logger.info(f"✅ Instant answer returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"❌ Instant answer error: {e}")
        # Fallback to regular web search for first result
        try:
            search_results = list(ddgs.text(query, max_results=1))
            if search_results:
                results = [{
                    "text": search_results[0].get("body", ""),
                    "url": search_results[0].get("link", ""),
                    "type": "fallback"
                }]
                logger.info(f"✅ Fallback to web search successful")
                return results
        except Exception as fallback_error:
            logger.error(f"❌ Fallback search also failed: {fallback_error}")
        raise


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments

    Returns:
        MCP tool call result with content
    """
    ddgs = DDGS()

    try:
        if tool_name == "web_search":
            results = await call_web_search(ddgs, arguments)

        elif tool_name == "news_search":
            results = await call_news_search(ddgs, arguments)

        elif tool_name == "instant_answer":
            results = await call_instant_answer(ddgs, arguments)

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Format results as MCP content
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(results, ensure_ascii=False, indent=2)
                }
            ]
        }

    except Exception as e:
        logger.error(f"❌ Tool execution error: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error executing {tool_name}: {str(e)}"
                }
            ],
            "isError": True
        }


@app.post("/mcp")
async def handle_mcp(request: JSONRPCRequest) -> JSONRPCResponse:
    """Handle MCP JSON-RPC 2.0 requests

    Supports the following MCP methods:
    - initialize: Initialize MCP session
    - tools/list: List available tools
    - tools/call: Execute a tool
    - notifications/initialized: Session initialized notification

    Args:
        request: JSON-RPC 2.0 request

    Returns:
        JSON-RPC 2.0 response
    """
    try:
        logger.info(f"📥 Received MCP request: {request.method}")

        # Handle initialize
        if request.method == "initialize":
            logger.info("🔄 Initializing MCP session")
            return JSONRPCResponse(
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "duckduckgo-mcp",
                        "version": "1.0.0"
                    }
                },
                id=request.id
            )

        # Handle tools/list
        elif request.method == "tools/list":
            logger.info("🔧 Listing tools")
            tools = get_tools_definition()
            logger.info(f"✅ Returning {len(tools)} tools")
            return JSONRPCResponse(
                result={"tools": tools},
                id=request.id
            )

        # Handle tools/call
        elif request.method == "tools/call":
            if not request.params:
                raise ValueError("Missing params in tools/call request")

            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})

            if not tool_name:
                raise ValueError("Missing tool name in params")

            logger.info(f"🔧 Calling tool: {tool_name} with arguments: {arguments}")

            result = await execute_tool(tool_name, arguments)

            return JSONRPCResponse(
                result=result,
                id=request.id
            )

        # Handle notifications/initialized
        elif request.method == "notifications/initialized":
            logger.info("✅ MCP session initialized")
            return JSONRPCResponse(
                result={},
                id=request.id
            )

        # Unknown method
        else:
            logger.error(f"❌ Unknown method: {request.method}")
            return JSONRPCResponse(
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                },
                id=request.id
            )

    except Exception as e:
        logger.error(f"❌ Error handling MCP request: {e}", exc_info=True)
        return JSONRPCResponse(
            error={
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            id=request.id
        )


@app.get("/")
async def root():
    """Root endpoint - server info"""
    return {
        "name": "DuckDuckGo MCP Server",
        "version": "1.0.0",
        "description": "MCP server providing DuckDuckGo search capabilities",
        "endpoints": {
            "mcp": "/mcp (POST)",
            "docs": "/docs (Swagger UI)"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "duckduckgo-mcp"
    }


if __name__ == "__main__":
    import sys
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="DuckDuckGo MCP Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )
