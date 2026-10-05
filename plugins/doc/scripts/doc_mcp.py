"""Minimal newline-delimited JSON-RPC MCP server using only the standard library."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from doc_records import (
    record_decision,
    record_impression,
    record_vision_review,
    records_summary,
)

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads(
    (PLUGIN_ROOT / ".plugin" / "plugin.json").read_text(encoding="utf-8")
)["version"]
RECORD_SCHEMAS = json.loads(
    (PLUGIN_ROOT / "scripts" / "records-schemas.json").read_text(encoding="utf-8")
)


def _object(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _string(minimum: int = 1) -> dict[str, Any]:
    return {"type": "string", "minLength": minimum}


RECORD_SCHEMAS["vision_review"]["anyOf"] = [
    {"required": ["image_path"]},
    {"required": ["source_event_id"]},
]
TOOLS: list[dict[str, Any]] = [
    {
        "name": "doc_record_decision",
        "description": "Append a hash-bound design decision.",
        "inputSchema": RECORD_SCHEMAS["decision"],
    },
    {
        "name": "doc_record_impression",
        "description": "Append a stage impression bound to artifacts.",
        "inputSchema": RECORD_SCHEMAS["impression"],
    },
    {
        "name": "doc_record_vision_review",
        "description": "Append an image review bound to an image or existing event.",
        "inputSchema": RECORD_SCHEMAS["vision_review"],
    },
    {
        "name": "doc_records_status",
        "description": "Summarize record counts and the last Stop-hook verdict.",
        "inputSchema": _object({}, []),
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "doc_ux_inbox",
        "description": "List and validate liaison requests targeting doc.",
        "inputSchema": _object({}, []),
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "doc_ux_respond",
        "description": "Write a liaison response.",
        "inputSchema": _object({"response": _object({}, [])}, ["response"]),
    },
    {
        "name": "doc_lint",
        "description": "Run the deterministic doc linter.",
        "inputSchema": _object(
            {
                "brief": _string(),
                "mode": {"type": "string", "enum": ["full", "brief_only"]},
            },
            ["brief"],
        ),
    },
    {
        "name": "doc_figures",
        "description": "Inventory figures referenced by brief target documents.",
        "inputSchema": _object({"brief": _string()}, ["brief"]),
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "doc_figure",
        "description": "Describe figure metadata.",
        "inputSchema": _object({"path": _string()}, ["path"]),
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "doc_view_figure",
        "description": "Return a supported image inline for visual inspection.",
        "inputSchema": _object({"path": _string()}, ["path"]),
        "annotations": {"readOnlyHint": True},
    },
]


def _call(
    name: str, args: dict[str, Any], tool_call_id: object = None
) -> dict[str, Any]:
    handlers: dict[str, Callable[..., dict[str, Any]]] = {
        "doc_record_decision": record_decision,
        "doc_record_impression": record_impression,
        "doc_record_vision_review": record_vision_review,
        "doc_records_status": lambda: records_summary(),
    }
    if name in handlers:
        if name in {
            "doc_record_decision",
            "doc_record_impression",
            "doc_record_vision_review",
        }:
            return handlers[name](args)
        return handlers[name]()
    if name == "doc_lint":
        from doc_figures import lint

        return lint(args["brief"], args.get("mode", "full"))
    if name in {"doc_figures", "doc_figure", "doc_view_figure"}:
        from doc_figures import figure_metadata, figures, view_figure

        if name == "doc_figures":
            return figures(args["brief"])
        if name == "doc_figure":
            return figure_metadata(args["path"])
        result = view_figure(args["path"], tool_call_id=tool_call_id)
        image = result.pop("image", None)
        text = result.pop("text", None)
        content: list[dict[str, Any]] = []
        if image:
            content.append(
                {"type": "image", "mimeType": image["mime_type"], "data": image["data"]}
            )
        if isinstance(text, str):
            content.append({"type": "text", "text": text})
        if content:
            result["content"] = content
        return result
    if name in {"doc_ux_inbox", "doc_ux_respond"}:
        import doc_slp

        return (
            doc_slp.ux_inbox()
            if name == "doc_ux_inbox"
            else doc_slp.ux_respond(args["response"])
        )
    raise ValueError(f"unknown tool: {name}")


def _result(value: dict[str, Any], *, error: bool = False) -> dict[str, Any]:
    content = value.get("content")
    if not isinstance(content, list):
        content = [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]
    structured = {key: item for key, item in value.items() if key != "content"}
    return {"content": content, "structuredContent": structured, "isError": error}


def _handle(message: object) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "invalid request"},
        }
    request = message
    method = request.get("method")
    request_id = request.get("id")
    if not isinstance(method, str):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32600, "message": "method is required"},
        }
    if method.startswith("notifications/"):
        return None
    if method == "initialize":
        params = request.get("params")
        protocol = (
            params.get("protocolVersion", "2024-11-05")
            if isinstance(params, dict)
            else "2024-11-05"
        )
        value: object = {
            "protocolVersion": protocol,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "doc", "version": VERSION},
        }
    elif method == "ping":
        value = {}
    elif method == "tools/list":
        value = {"tools": TOOLS}
    elif method == "tools/call":
        params = request.get("params")
        try:
            if not isinstance(params, dict) or not isinstance(params.get("name"), str):
                raise ValueError("params.name is required")
            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                raise ValueError("params.arguments must be an object")
            result = _call(params["name"], arguments, tool_call_id=request_id)
            wrapped = _result(result, error=result.get("ok") is False)
        except (KeyError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            wrapped = _result({"ok": False, "errors": [str(exc)]}, error=True)
        value = wrapped
    elif method in {"resources/list", "resources/templates/list", "prompts/list"}:
        value = (
            {"resources": []}
            if method == "resources/list"
            else {"templates": []}
            if method == "resources/templates/list"
            else {"prompts": []}
        )
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"unknown method: {method}"},
        }
    if request_id is None:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "result": value}


def serve() -> int:
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response = _handle(message)
            if response is not None:
                sys.stdout.write(
                    json.dumps(response, ensure_ascii=False, separators=(",", ":"))
                    + "\n"
                )
                sys.stdout.flush()
        except (json.JSONDecodeError, OSError) as exc:
            print(f"doc MCP server: {exc}", file=sys.stderr)
    return 0
