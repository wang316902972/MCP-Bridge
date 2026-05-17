#!/usr/bin/env python3
"""
MCP-Bridge stdio client for Knowledge-Base (Remote HTTP MCP Server)
Proxy MCP stdio protocol to remote HTTP endpoint (192.168.136.224:8003)
"""
import sys
import json
import subprocess
import os

# Configuration
MCP_BRIDGE_URL = os.environ.get("MCP_BRIDGE_URL", "http://192.168.136.224:8003/v1/mcp")
TIMEOUT = int(os.environ.get("MCP_TIMEOUT", "30"))


def send_request(payload: dict) -> dict:
    """Send JSON-RPC request to MCP-Bridge HTTP endpoint"""
    try:
        cmd = [
            "curl", "-s", "-X", "POST",
            MCP_BRIDGE_URL,
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            "--max-time", str(TIMEOUT)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if not result.stdout.strip():
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Empty response from server"},
                "id": payload.get("id")
            }

        response = json.loads(result.stdout)

        # Remove "error": null if present (Claude Code doesn't like it)
        if "error" in response and response["error"] is None:
            del response["error"]

        return response

    except subprocess.CalledProcessError as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"HTTP error: {e.stderr}"},
            "id": payload.get("id")
        }
    except json.JSONDecodeError as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
            "id": payload.get("id")
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": payload.get("id")
        }


def transform_arguments(arguments: dict) -> dict:
    """
    Transform arguments to be compatible with the remote MCP server.
    - Accept both 'query' and 'question' parameters
    - Convert 'question' to 'query' if needed (server expects 'query')
    """
    if arguments is None:
        return arguments

    # If 'question' is provided but 'query' is not, rename 'question' to 'query'
    # (Server expects 'query', but users may provide 'question')
    if "question" in arguments and "query" not in arguments:
        arguments["query"] = arguments.pop("question")

    return arguments


def main():
    """Main stdio loop - reads from stdin, writes to stdout"""
    req_id_counter = 0

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)

            # Validate JSON-RPC
            if request.get("jsonrpc") != "2.0":
                continue

            # Transform arguments for tools/call method
            if request.get("method") == "tools/call":
                params = request.get("params", {})
                arguments = params.get("arguments", {})
                transformed_args = transform_arguments(arguments)
                params["arguments"] = transformed_args
                request["params"] = params

            req_id = request.get("id", req_id_counter)
            if isinstance(req_id, int):
                req_id_counter = req_id + 1

            # Forward request to MCP-Bridge
            response = send_request(request)
            print(json.dumps(response), flush=True)

        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }
            print(json.dumps(error_resp), flush=True)
        except Exception as e:
            error_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": req_id_counter
            }
            print(json.dumps(error_resp), flush=True)


if __name__ == "__main__":
    main()
