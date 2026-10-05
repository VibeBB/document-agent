#!/usr/bin/env python3
"""Command-line entry point for document-agent records, liaison, figures, and MCP."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import doc_records  # noqa: E402


def _payload(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _record(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "status":
        return doc_records.records_summary()
    payload = _payload(args.json_file)
    handlers: dict[str, Callable[[object], dict[str, Any]]] = {
        "decision": doc_records.record_decision,
        "impression": doc_records.record_impression,
        "vision-review": doc_records.record_vision_review,
    }
    return handlers[args.action](payload)


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "record":
        return _record(args)
    if args.command == "mcp_server":
        import doc_mcp

        return {"ok": bool(doc_mcp.serve())}
    if args.command == "ux":
        import doc_slp

        if args.action == "inbox":
            return doc_slp.ux_inbox()
        return doc_slp.ux_respond(_payload(args.json_file))
    if args.command == "figures":
        import doc_figures

        return doc_figures.figures(args.brief)
    if args.command == "figure":
        import doc_figures

        return doc_figures.figure_metadata(args.path)
    raise ValueError(f"unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doc_tool.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    record = subparsers.add_parser("record")
    record_sub = record.add_subparsers(dest="action", required=True)
    for action in ("decision", "impression", "vision-review"):
        command = record_sub.add_parser(action)
        command.add_argument("--json", dest="json_file", required=True)
    record_sub.add_parser("status")
    ux = subparsers.add_parser("ux")
    ux_sub = ux.add_subparsers(dest="action", required=True)
    ux_sub.add_parser("inbox")
    respond = ux_sub.add_parser("respond")
    respond.add_argument("--json", dest="json_file", required=True)
    figures = subparsers.add_parser("figures")
    figures.add_argument("--brief", required=True)
    figure = subparsers.add_parser("figure")
    figure.add_argument("--path", required=True)
    subparsers.add_parser("mcp_server")
    args = parser.parse_args(argv)
    try:
        if args.command == "mcp_server":
            import doc_mcp

            return doc_mcp.serve()
        result = _dispatch(args)
        _print(result)
        return 2 if result.get("ok") is False else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _print({"ok": False, "errors": [str(exc)]})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
