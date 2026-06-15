"""MCP stdio server for PhysicalAgent cerebrum tools.

The server intentionally has no third-party MCP dependency.  Claude Code and
Codex talk to stdio MCP servers with newline-delimited JSON-RPC messages, and
this module implements the small subset needed by tool calls.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from physical_agent.driver_client import SocketDriverClient
from physical_agent.tools import frontend

SERVER_NAME = "physical_agent"
PROTOCOL_VERSION = "2025-06-18"


def _tool_specs() -> list[dict[str, Any]]:
    tools = []
    for tool in frontend.get_tools_spec():
        tools.append(
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "inputSchema": tool.get("input_schema", {"type": "object"}),
            }
        )
    return tools


def _tool_result_to_mcp(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"content": [{"type": "text", "text": str(result)}]}

    result_for_text = dict(result)
    image = result_for_text.pop("_image_bytes", None)
    image_cam = result_for_text.pop("_image_cam_bytes", None)

    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": json.dumps(result_for_text, indent=2, default=str),
        }
    ]

    def add_png(data: bytes | None) -> None:
        if not data:
            return
        content.append(
            {
                "type": "image",
                "data": base64.b64encode(data).decode("ascii"),
                "mimeType": "image/png",
            }
        )

    add_png(image)
    add_png(image_cam)
    return {"content": content, "isError": bool(result_for_text.get("error"))}


class StdioJsonRpc:
    """Minimal newline-delimited JSON-RPC transport over stdio."""

    def __init__(self) -> None:
        """Bind the transport to process stdin/stdout."""
        self._stdin = sys.stdin.buffer
        self._stdout = sys.stdout.buffer

    def read_message(self) -> dict[str, Any] | None:
        """Read one newline-delimited JSON-RPC message from stdin."""
        while True:
            line = self._stdin.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                continue
            return json.loads(line.decode("utf-8"))

    def write_message(self, message: dict[str, Any]) -> None:
        """Write one newline-delimited JSON-RPC message to stdout."""
        payload = json.dumps(message, separators=(",", ":"), default=str).encode("utf-8")
        self._stdout.write(payload + b"\n")
        self._stdout.flush()


def _response(request: dict[str, Any], result: Any) -> dict[str, Any] | None:
    if "id" not in request:
        return None
    return {"jsonrpc": "2.0", "id": request["id"], "result": result}


def _error_response(
    request: dict[str, Any],
    code: int,
    message: str,
    data: Any | None = None,
) -> dict[str, Any] | None:
    if "id" not in request:
        return None
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request["id"], "error": error}


def _handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    params = request.get("params") or {}

    if method == "initialize":
        return _response(
            request,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": "0.1.0"},
            },
        )

    if method == "tools/list":
        return _response(request, {"tools": _tool_specs()})

    if method == "ping":
        return _response(request, {})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return _error_response(request, -32602, "tools/call requires string name")
        if not isinstance(arguments, dict):
            return _error_response(
                request,
                -32602,
                "tools/call arguments must be an object",
            )
        result = frontend.execute_tool(name, arguments)
        return _response(request, _tool_result_to_mcp(result))

    if method in {"notifications/initialized", "$/cancelRequest"}:
        return None

    return _error_response(request, -32601, f"unknown method: {method}")


def serve() -> int:
    """Run the MCP request loop until stdin closes."""
    rpc = StdioJsonRpc()
    while True:
        request = rpc.read_message()
        if request is None:
            return 0
        try:
            response = _handle_request(request)
        except Exception as e:
            response = _error_response(
                request,
                -32603,
                str(e),
                traceback.format_exc(),
            )
        if response is not None:
            rpc.write_message(response)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and serve the PhysicalAgent MCP tools."""
    ap = argparse.ArgumentParser(description="PhysicalAgent MCP server")
    ap.add_argument("--workdir", required=True, help="driver workdir")
    ap.add_argument("--repo-root", default="", help="repository root")
    ap.add_argument(
        "--transport",
        default="file",
        choices=["file", "socket"],
        help="driver transport used by MCP tools",
    )
    ap.add_argument("--transport-host", default="127.0.0.1", help="socket host")
    ap.add_argument("--transport-port", type=int, default=0, help="socket port")
    args = ap.parse_args(argv)

    if args.repo_root:
        os.chdir(args.repo_root)
        if str(Path(args.repo_root)) not in sys.path:
            sys.path.insert(0, str(Path(args.repo_root)))
    frontend.set_workdir(args.workdir)
    if args.transport == "socket":
        if args.transport_port <= 0:
            raise ValueError("--transport socket requires --transport-port")
        frontend.set_driver_client(
            SocketDriverClient(args.transport_host, args.transport_port)
        )
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
