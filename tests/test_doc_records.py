"""Tests for document-agent VRP writers and their MCP boundary."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/doc/scripts"
sys.path.insert(0, str(SCRIPTS))

import doc_mcp  # noqa: E402
import doc_records  # noqa: E402


def decision(path: str = "source.md") -> dict[str, Any]:
    return {
        "id": "fact-choice",
        "stage": "brief",
        "question": "Which source describes the interface?",
        "principles": ["Use claims that can be traced to an inspectable source."],
        "options": [
            {"name": "source-a", "pros": ["direct"], "cons": ["narrow"]},
            {"name": "source-b", "pros": ["broad"], "cons": ["indirect"]},
        ],
        "chosen": "source-a",
        "rationale": (
            "A direct source gives readers a checkable statement. "
            "The narrower scope reduces the chance that the brief implies "
            "unsupported compatibility or behavior. This choice also makes "
            "the claim easier to refresh when a version or interface "
            "changes, while preserving a clear trail for future reviewers."
        ),
        "evidence": [{"path": path}],
        "risks": ["The source may become stale."],
        "revisit_when": (
            "Revisit if the source changes or conflicts with a newer artifact."
        ),
    }


def test_decision_is_hash_bound_and_append_only(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("source evidence\n", encoding="utf-8")
    first = doc_records.record_decision(decision(), tmp_path)["record"]
    second = doc_records.record_decision(decision(), tmp_path)["record"]
    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert (
        first["evidence"][0]["sha256"]
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )
    log = tmp_path / "observations/doc/decisions.jsonl"
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2
    assert doc_records.records_summary(tmp_path)["counts"]["decision"] == 2


def test_unknown_keys_and_unsafe_paths_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("evidence", encoding="utf-8")
    payload = decision()
    payload["surprise"] = True
    with pytest.raises(ValueError, match="unknown key"):
        doc_records.record_decision(payload, tmp_path)
    payload = decision("../outside")
    with pytest.raises(ValueError, match=".."):
        doc_records.record_decision(payload, tmp_path)


def test_symlink_evidence_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "real.md").write_text("evidence", encoding="utf-8")
    (tmp_path / "linked.md").symlink_to(tmp_path / "real.md")
    with pytest.raises(ValueError, match="symlink"):
        doc_records.record_decision(decision("linked.md"), tmp_path)


def test_impression_binds_the_current_artifact_tree(tmp_path: Path) -> None:
    artifact = tmp_path / "stage.md"
    artifact.write_text("Draft the reader journey.\n", encoding="utf-8")
    text = (
        "The outline makes the reader's first question visible and ties the answer to "
        "the supplied interface evidence. The sequence keeps unsupported "
        "product claims out while explaining the immediate next action. "
        "The open concern is whether the source remains current; refresh it "
        "before a release or whenever the interface changes. This account is "
        "grounded in the current artifact and should be revisited if the "
        "product behavior or audience changes."
    )
    result = doc_records.record_impression(
        {"stage": "outline", "artifacts": ["stage.md"], "impression": text}, tmp_path
    )
    assert (
        result["record"]["artifacts"][0]["sha256"]
        == hashlib.sha256(artifact.read_bytes()).hexdigest()
    )


def test_vision_review_must_reference_a_real_event(tmp_path: Path) -> None:
    payload = {
        "source_event_id": "a" * 64,
        "model": "vision-model",
        "checklist": "doc-figure",
        "findings": [],
        "impression": "A distinct first sentence. A second useful observation. "
        "A third concrete "
        "next step. "
        + "The figure communicates its relationship to the surrounding text. "
        * 9,
    }
    with pytest.raises(ValueError, match="unknown source_event_id"):
        doc_records.record_vision_review(payload, tmp_path)


def test_vision_review_binds_an_image_and_existing_event(tmp_path: Path) -> None:
    image = tmp_path / "figure.png"
    image.write_bytes(b"png fixture")
    event_id = "b" * 64
    event_log = tmp_path / "observations/doc/vision-tool-events.jsonl"
    event_log.parent.mkdir(parents=True)
    event_log.write_text(json.dumps({"event_id": event_id}) + "\n", encoding="utf-8")
    payload = {
        "image_path": "figure.png",
        "source_event_id": event_id,
        "model": "vision-model",
        "checklist": "doc-figure",
        "findings": [],
        "impression": "The diagram shows a readable flow. Its labels match the nearby "
        "description. The next review should compare it after the interface changes. "
        + "The visual hierarchy supports the intended reading order. "
        * 8,
    }
    record = doc_records.record_vision_review(payload, tmp_path)["record"]
    assert record["image_sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert record["source_event_id"] == event_id


def test_record_schemas_match_writer_input_keys() -> None:
    schemas = {tool["name"]: tool["inputSchema"] for tool in doc_mcp.TOOLS}
    assert (
        set(schemas["doc_record_decision"]["properties"]) == doc_records.DECISION_KEYS
    )
    assert (
        set(schemas["doc_record_impression"]["properties"])
        == doc_records.IMPRESSION_KEYS
    )
    assert (
        set(schemas["doc_record_vision_review"]["properties"])
        == doc_records.VISION_REVIEW_KEYS
    )


def test_real_mcp_client_lists_and_calls_record_status(tmp_path: Path) -> None:
    pytest.importorskip("mcp.client.stdio")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def exercise() -> None:
        env = {**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)}
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(SCRIPTS / "doc_tool.py"), "mcp_server"],
            env=env,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert "doc_record_decision" in names
                assert "doc_view_figure" in names
                result = await session.call_tool("doc_records_status", {})
                assert not result.isError
                assert result.structuredContent["ok"] is True

    asyncio.run(exercise())
