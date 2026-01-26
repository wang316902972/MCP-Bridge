#!/usr/bin/env python3
"""Simple test script for DuckDuckGo MCP server"""

import urllib.request
import json
import os

# Bypass proxy for localhost
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

def test_server():
    """Test MCP server endpoints"""
    url = "http://127.0.0.1:8888/mcp"

    # Test 1: tools/list
    print("Test 1: Testing tools/list endpoint...")
    data = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✅ Tools list response:")
            print(json.dumps(result, indent=2))

            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                print(f"\n✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool.get('description', 'No description')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test 2: initialize
    print("\n\nTest 2: Testing initialize endpoint...")
    data = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        },
        "id": 2
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✅ Initialize response:")
            print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    print("DuckDuckGo MCP Server Test")
    print("=" * 50)
    test_server()
