#!/usr/bin/env python3
"""
Mock MCP server for testing.
Implements basic MCP protocol for tool discovery and execution via stdio.
"""

import sys
import json
import time


def handle_initialize(params):
    """Handle initialization request."""
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "1.0",
            "serverInfo": {
                "name": "mock-mcp-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {}
            }
        }
    }


def handle_list_tools(params):
    """Return mock tool list."""
    return {
        "jsonrpc": "2.0",
        "result": {
            "tools": [
                {
                    "name": "test_tool",
                    "description": "A test tool",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "input": {"type": "string", "description": "Test input"}
                        },
                        "required": ["input"]
                    }
                },
                {
                    "name": "echo_tool",
                    "description": "Echoes back the input",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Message to echo"}
                        },
                        "required": ["message"]
                    }
                }
            ]
        }
    }


def handle_call_tool(params):
    """Execute mock tool."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if tool_name == "test_tool":
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Processed: {arguments.get('input', '')}"
                    }
                ]
            }
        }
    elif tool_name == "echo_tool":
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": arguments.get('message', '')
                    }
                ]
            }
        }
    elif tool_name == "crash_tool":
        # Simulate crash for crash recovery tests
        sys.exit(1)
    elif tool_name == "timeout_tool":
        # Simulate timeout
        time.sleep(60)
        return {"jsonrpc": "2.0", "result": {"content": []}}
    else:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Unknown tool: {tool_name}"
            }
        }


def handle_ping(params):
    """Handle ping for health checks."""
    return {
        "jsonrpc": "2.0",
        "result": {}
    }


def main():
    """Main server loop reading from stdin and writing to stdout."""
    # Send initialize notification
    init_notification = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    print(json.dumps(init_notification), flush=True)

    # Main request/response loop
    for line in sys.stdin:
        if not line.strip():
            continue

        try:
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")

            # Route to appropriate handler
            if method == "initialize":
                response = handle_initialize(params)
            elif method == "tools/list":
                response = handle_list_tools(params)
            elif method == "tools/call":
                response = handle_call_tool(params)
            elif method == "ping":
                response = handle_ping(params)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }

            # Add request ID to response
            if request_id is not None:
                response["id"] = request_id

            print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
