"""Tests for figure inventory, image viewing, and review binding."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/doc/scripts"
HOOKS = ROOT / "plugins/doc/hooks/scripts"
EXAMPLE_BRIEF = ROOT / (
    "plugins/doc/skills/doc-lint/examples/desk-timer/doc-work/desk-timer/doc-brief.json"
)
sys.path.insert(0, str(SCRIPTS))

import doc_figures  # noqa: E402
import doc_records  # noqa: E402


@pytest.mark.parametrize("producer", [False, True])
def test_native_figure_view_preserves_verified_producer_ancestry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, producer: bool
) -> None:
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("OPENHANDS_SESSION_ID", raising=False)
    monkeypatch.delenv("OPENHANDS_CONVERSATION_ID", raising=False)
    source = tmp_path / "original.png"
    source.write_bytes(_png())
    image = tmp_path / "detail.png"
    image.write_bytes(_png() + b"derived fixture")
    parent = {
        "path": str(source),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "owner_plugin": "ux",
        "origin": "renderer",
    }
    claim = {
        "path": str(image),
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "owner_plugin": "ux",
        "origin": "derived",
        "operation": "crop",
        "parents": [parent],
    }
    if producer:
        assert doc_figures.capture_image_delivery(
            {
                "tool_name": "ux_image_detail",
                "tool_response": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "inline_images": [
                                        {
                                            "path": str(image),
                                            "sha256": claim["sha256"],
                                            "attached": True,
                                            "identity_status": "bound",
                                            "image_identity": claim,
                                        }
                                    ]
                                }
                            ),
                        },
                        {
                            "type": "image",
                            "data": base64.b64encode(image.read_bytes()).decode(),
                            "mimeType": "image/png",
                        },
                    ]
                },
            },
            tmp_path,
            tmp_path / "observations/ux/image-observations.jsonl",
        )
    import doc_mcp

    request = {
        "jsonrpc": "2.0",
        "id": "view-detail",
        "method": "tools/call",
        "params": {
            "name": "doc_view_figure",
            "arguments": {"path": "detail.png", "session_id": "reader"},
        },
    }
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request) + "\n"))
    monkeypatch.setattr(sys, "stdout", output)
    assert doc_mcp.serve() == 0
    result = json.loads(output.getvalue())["result"]["structuredContent"]
    assert result["ok"]
    row = json.loads(
        (tmp_path / "observations/doc/image-observations.jsonl").read_text(
            encoding="utf-8"
        )
    )
    assert row["image_sha256"] == claim["sha256"]
    assert row["image_identity"] == (claim if producer else None)
    assert row["identity_status"] == ("bound" if producer else "unknown")


def test_figure_view_returns_its_own_event_after_an_interleaved_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = tmp_path / "first.png"
    image.write_bytes(_png())
    other = tmp_path / "other.png"
    other.write_bytes(_png() + b"other image")
    capture = doc_figures.capture_image_delivery
    expected: list[str] = []

    def interleave(
        payload: dict[str, object],
        root: Path,
        log: Path,
        event_ids: list[str] | None = None,
    ) -> bool:
        result = capture(payload, root, log, event_ids)
        assert event_ids is not None
        expected.extend(event_ids)
        assert capture(
            {
                "tool_name": "file_editor",
                "session_id": "other-session",
                "tool_input": {"command": "view", "path": str(other)},
                "tool_response": {
                    "content": [
                        {
                            "type": "image",
                            "mimeType": "image/png",
                            "data": base64.b64encode(other.read_bytes()).decode(),
                        }
                    ]
                },
            },
            root,
            log,
        )
        return result

    monkeypatch.setattr(doc_figures, "capture_image_delivery", interleave)
    result = doc_figures.view_figure("first.png", tmp_path, session_id="reader")
    assert result["event_id"] == expected[0]


def _png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = binascii.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00\x10\x40\x80\xff"))
        + chunk(b"IEND", b"")
    )


def _workspace(tmp_path: Path, *, markdown: str | None = None) -> tuple[Path, Path]:
    brief = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))
    brief["targets"] = [
        {"kind": "readme", "path": "doc-work/desk-timer/README.md"},
        {
            "kind": "technical_reference",
            "path": "doc-work/desk-timer/technical-reference.md",
        },
    ]
    work = tmp_path / "doc-work/desk-timer"
    work.mkdir(parents=True)
    brief_path = work / "doc-brief.json"
    brief_path.write_text(json.dumps(brief), encoding="utf-8")
    (work / "technical-reference.md").write_text(
        "# Technical reference\n\n## Design rationale\n\nA source-backed choice.\n",
        encoding="utf-8",
    )
    document = work / "README.md"
    document.write_text(
        markdown
        or (
            "# Timer\n"
            "![Timer top](figures/timer.png)\n"
            '<img src="figures/missing.png" alt="Status panel">\n'
            "```mermaid\nflowchart TD\n  A --> B\n```\n"
        ),
        encoding="utf-8",
    )
    image = work / "figures/timer.png"
    image.parent.mkdir()
    image.write_bytes(_png())
    return brief_path, image


def _append_jsonl(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value) + "\n")


def test_inventory_reports_missing_images_html_and_mermaid(tmp_path: Path) -> None:
    brief, image = _workspace(tmp_path)
    inventory = doc_figures.figures(brief, tmp_path)
    assert inventory["ok"] is True
    assert inventory["documents"] == [
        {"document": "doc-work/desk-timer/README.md", "mermaid_blocks": 1},
        {
            "document": "doc-work/desk-timer/technical-reference.md",
            "mermaid_blocks": 0,
        },
    ]
    figure, missing = inventory["figures"]
    assert figure["path"] == "doc-work/desk-timer/figures/timer.png"
    assert figure["exists"] is True
    assert figure["sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert figure["mime"] == "image/png"
    assert figure["reviewed"] is False
    assert missing["line"] == 3
    assert missing["alt"] == "Status panel"
    assert missing["exists"] is False
    assert missing["reviewed"] is False


def test_inventory_rebinds_reviews_when_image_hash_changes(tmp_path: Path) -> None:
    brief, image = _workspace(tmp_path)
    first_hash = hashlib.sha256(image.read_bytes()).hexdigest()
    review_log = tmp_path / "observations/doc/vision-reviews.jsonl"
    _append_jsonl(
        review_log,
        {"event_id": "review-first", "image_sha256": first_hash},
    )
    entry = doc_figures.figures(brief, tmp_path)["figures"][0]
    assert entry["reviewed"] is True
    assert entry["review_event_ids"] == ["review-first"]

    image.write_bytes(_png() + b"changed")
    changed = doc_figures.figures(brief, tmp_path)["figures"][0]
    assert changed["reviewed"] is False
    assert changed["review_event_ids"] == []

    new_hash = hashlib.sha256(image.read_bytes()).hexdigest()
    observation_log = tmp_path / "observations/doc/image-observations.jsonl"
    _append_jsonl(
        observation_log,
        {"event_id": "view-current", "image_sha256": new_hash},
    )
    with review_log.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {"event_id": "review-current", "source_event_id": "view-current"}
            )
        )
        stream.write("\n")
    rebound = doc_figures.figures(brief, tmp_path)["figures"][0]
    assert rebound["reviewed"] is True
    assert rebound["review_event_ids"] == ["review-current"]


def test_view_observation_blocks_stop_until_review_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = tmp_path / "photo.png"
    image.write_bytes(_png())
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("DOC_IMAGE_OBSERVATIONS", raising=False)
    env = {**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)}
    event = {"session_id": "view-session", "working_dir": str(tmp_path)}
    started = subprocess.run(
        [sys.executable, str(HOOKS / "require_records.py"), "session-start"],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert started.returncode == 0

    result = doc_figures.view_figure("photo.png", tmp_path, tool_call_id="mcp-call-3")
    assert result["ok"] is True
    observation = json.loads(
        (tmp_path / "observations/doc/image-observations.jsonl").read_text("utf-8")
    )
    assert observation["tool_name"] == "doc_view_figure"
    assert observation["event_id"] == result["event_id"]
    assert observation["tool_call_id"] == "mcp-call-3"
    assert result["sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()

    stop = [sys.executable, str(HOOKS / "require_records.py"), "stop"]
    missing_review = subprocess.run(
        stop,
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert missing_review.returncode != 0

    impression = (
        "The figure makes the status relationship visible to a first-time reader. "
        "Its labels match the nearby explanation and the image shows the intended "
        "flow in a way that is easy to scan. The main uncertainty is whether the final "
        "interface keeps these names and colors. Recheck the image after "
        "implementation changes, update its nearby caption, and keep the observation "
        "tied to this image hash so a replacement receives a new review. The contrast "
        "is legible at normal size."
    )
    doc_records.record_vision_review(
        {
            "source_event_id": result["event_id"],
            "image_path": "photo.png",
            "model": "test-model",
            "checklist": "figure-reader",
            "findings": [],
            "impression": impression,
            "facets": {
                "observed": [
                    "the status flow is drawn left to right",
                    "the labels sit beside each state",
                ],
                "works": ["labels match the caption"],
                "concerns": [
                    {
                        "id": "c1",
                        "text": "final interface may rename the states",
                        "severity": "info",
                        "about": "self",
                        "anchor": "status",
                    }
                ],
                "feelings": {
                    "maker": "can keep the figure tied to its hash",
                    "user": "scans the flow at a glance",
                },
                "next_actions": ["recheck the image after interface changes"],
            },
            "claims": [
                {
                    "text": "the figure shows the status flow",
                    "anchor": "status",
                    "artifact": "photo.png",
                }
            ],
            "lookback": [
                {"claim": 0, "verdict": "confirmed", "note": "second look shows it"}
            ],
            "confidence": "medium",
        },
        tmp_path,
    )
    covered = subprocess.run(
        stop,
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert covered.returncode == 0


def test_view_rejects_svg_oversize_and_workspace_escape(tmp_path: Path) -> None:
    svg = tmp_path / "figure.svg"
    svg.write_text("<svg/>", encoding="utf-8")
    result = doc_figures.view_figure(svg, tmp_path)
    assert result["ok"] is False
    assert "render it to PNG" in result["errors"][0]

    oversized = tmp_path / "large.png"
    oversized.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024))
    result = doc_figures.view_figure(oversized, tmp_path)
    assert result["ok"] is False
    assert "5 MiB" in result["errors"][0]

    result = doc_figures.view_figure("../outside.png", tmp_path)
    assert result["ok"] is False
    assert "outside the workspace" in result["errors"][0]


def test_view_rejects_symlink_and_mismatched_image_content(tmp_path: Path) -> None:
    actual = tmp_path / "actual.png"
    actual.write_bytes(_png())
    link = tmp_path / "linked.png"
    link.symlink_to(actual)
    result = doc_figures.view_figure(link, tmp_path)
    assert result["ok"] is False
    assert "symlink" in result["errors"][0]

    malformed = tmp_path / "malformed.png"
    malformed.write_bytes(b"<svg/>")
    result = doc_figures.view_figure(malformed, tmp_path)
    assert result["ok"] is False
    assert "does not match" in result["errors"][0]


def test_view_accepts_jpeg_gif_and_webp_signatures(tmp_path: Path) -> None:
    images = {
        "photo.jpg": (b"\xff\xd8\xff\x00", "image/jpeg"),
        "animation.gif": (b"GIF89a\x00", "image/gif"),
        "render.webp": (b"RIFF\x04\x00\x00\x00WEBP", "image/webp"),
    }
    for name, (data, mime) in images.items():
        (tmp_path / name).write_bytes(data)
        result = doc_figures.view_figure(name, tmp_path)
        assert result["ok"] is True
        assert result["image"]["mime_type"] == mime


def test_status_hook_reports_unreviewed_figures_advisorially(
    tmp_path: Path,
) -> None:
    brief, _ = _workspace(tmp_path)
    result = subprocess.run(
        [sys.executable, str(HOOKS / "report_doc_status.py")],
        input=json.dumps({"working_dir": str(tmp_path)}),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)},
    )
    assert result.returncode == 0
    status = json.loads(result.stdout)
    assert status["decision"] == "allow"
    assert (
        f"{brief.relative_to(tmp_path).as_posix()}: figures not vision-reviewed: 2"
        in status["additionalContext"]
    )


def test_mcp_view_figure_returns_inline_image_and_records_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp.client.stdio")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import TextContent

    image = tmp_path / "figure.png"
    image.write_bytes(_png())
    monkeypatch.delenv("DOC_IMAGE_OBSERVATIONS", raising=False)

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
                result = await session.call_tool(
                    "doc_view_figure", {"path": "figure.png"}
                )
                assert not result.is_error
                assert [item.type for item in result.content] == ["image", "text"]
                assert isinstance(result.content[1], TextContent)
                metadata = json.loads(result.content[1].text)
                assert (
                    metadata["sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()
                )
                assert "event_id" in metadata
                observation = json.loads(
                    (tmp_path / "observations/doc/image-observations.jsonl").read_text(
                        "utf-8"
                    )
                )
                assert observation["event_id"] == metadata["event_id"]

    asyncio.run(exercise())


@pytest.mark.parametrize("explicit", [True, False])
def test_figure_observation_keeps_native_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool
) -> None:
    (tmp_path / "photo.png").write_bytes(_png())
    monkeypatch.delenv("DOC_IMAGE_OBSERVATIONS", raising=False)
    monkeypatch.delenv("OPENHANDS_SESSION_ID", raising=False)
    context = {"session_id": "child"} if explicit else {}
    if not explicit:
        monkeypatch.setenv("OPENHANDS_SESSION_ID", "child")
    assert doc_figures.view_figure("photo.png", tmp_path, **context)["ok"]
    log = tmp_path / "observations/doc/image-observations.jsonl"
    observation = json.loads(log.read_text(encoding="utf-8"))
    assert observation["session_id"] == "child"
