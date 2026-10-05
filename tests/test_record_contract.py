"""Tests for the stdlib VRP validator shared by plugin hooks."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import PLUGIN_ROOT

HOOK_SCRIPTS = PLUGIN_ROOT / "hooks" / "scripts"
sys.path.insert(0, str(HOOK_SCRIPTS))

import _records  # noqa: E402


def _envelope(kind: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": kind,
        "plugin": "doc",
        "recorded_at": "2025-01-02T03:04:05Z",
        "sequence": 1,
        "event_id": "a" * 64,
        **fields,
    }


def _impression() -> str:
    return (
        "The first observation is grounded in the current artifact. "
        "The second explains what works for the intended reader. "
        "The third identifies a remaining concern and the next action. " * 4
    )


def test_record_contracts_accept_complete_records() -> None:
    decision = _envelope(
        "decision",
        id="source-choice",
        stage="brief",
        question="Which source best supports the interface claim?",
        principles=["Claims must be traceable to inspectable evidence."],
        options=[
            {"name": "direct", "pros": ["specific"], "cons": ["narrow"]},
            {"name": "overview", "pros": ["broad"], "cons": ["less precise"]},
        ],
        chosen="direct",
        rationale="A direct source supports a checkable statement. " * 5,
        evidence=[{"reference": "source.md"}],
        assumptions=[],
        unknowns=[],
        risks=["The source may become stale."],
        revisit_when="Revisit if a newer source contradicts this one.",
        decided_by="agent",
    )
    impression = _envelope(
        "stage_impression",
        stage="outline",
        artifacts=[{"path": "outline.md", "sha256": "b" * 64}],
        impression=_impression(),
    )
    vision = _envelope(
        "vision_review",
        image_path="figures/system.png",
        image_sha256="c" * 64,
        model="vision-capable-model",
        checklist="figure-review",
        findings=[{"category": "label", "severity": "info", "note": "Readable."}],
        impression=_impression(),
    )

    assert _records.record_errors("decision", decision) == []
    assert _records.record_errors("stage_impression", impression) == []
    assert _records.record_errors("vision_review", vision) == []
    assert _records.record_errors("decision", None) == ["record must be a JSON object"]


def test_record_contracts_report_invalid_fields() -> None:
    decision = _envelope(
        "wrong-kind",
        schema_version=2,
        plugin="",
        recorded_at="2025-01-02T03:04:05",
        sequence="1",
        event_id="invalid",
        id="Bad Id",
        stage="",
        question="",
        principles=[],
        options=[
            None,
            {"name": "same", "pros": [], "cons": []},
            {"name": "same", "pros": [], "cons": []},
        ],
        chosen="missing",
        rationale="short",
        evidence=[{"path": "source.md", "sha256": "F" * 64}, "not-an-object"],
        assumptions=None,
        unknowns=[""],
        risks=[],
        revisit_when="",
        decided_by="unknown",
    )
    errors = _records.decision_errors(decision)
    assert any("schema_version" in error for error in errors)
    assert any("recorded_at" in error for error in errors)
    assert any("option names must be unique" in error for error in errors)
    assert any("evidence[1] must be an object" in error for error in errors)
    assert any("decided_by" in error for error in errors)

    stage = _envelope(
        "stage_impression",
        stage="Not a slug",
        artifacts=[None],
        impression="Too short.",
    )
    assert any(
        "stage must be a lowercase slug" in error
        for error in _records.stage_impression_errors(stage)
    )

    vision = _envelope(
        "vision_review",
        image_path="figure.png",
        image_sha256="bad",
        model="",
        checklist="Bad checklist",
        findings=[None, {}],
        impression="Same sentence. Same sentence. Same sentence. " * 12,
    )
    vision_errors = _records.vision_review_errors(vision)
    assert any("image_sha256" in error for error in vision_errors)
    assert any("findings[0] must be an object" in error for error in vision_errors)
    assert any("repeats the same sentence" in error for error in vision_errors)


def test_record_validation_helpers_cover_time_and_impression_edges() -> None:
    assert _records.parse_time("2025-01-02T03:04:05Z") is not None
    assert _records.parse_time("2025-01-02T03:04:05") is None
    assert _records.parse_time("not-a-timestamp") is None
    assert _records.parse_time(None) is None
    assert _records.sentence_count("One. Two! 三。") == 3
    assert _records.sentences("One. Two!") == ["One.", "Two!"]
    assert _records.impression_errors(None)
    assert _records.impression_errors("Short. Short. Short.")
    assert any(
        "repeats the same sentence" in error
        for error in _records.impression_errors("Repeated. " * 3 + " " * 400)
    )


def test_tree_hash_jsonl_policy_and_artifact_helpers(tmp_path: Path) -> None:
    source = tmp_path / "one.txt"
    source.write_text("one", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "two.txt").write_text("two", encoding="utf-8")
    skipped = tmp_path / ".git"
    skipped.mkdir()
    (skipped / "ignored.txt").write_text("ignored", encoding="utf-8")
    (tmp_path / "linked.txt").symlink_to(source)
    expected = hashlib.sha256(
        (
            "nested/two.txt\0"
            + hashlib.sha256((nested / "two.txt").read_bytes()).hexdigest()
            + "\n"
            + "one.txt\0"
            + hashlib.sha256(source.read_bytes()).hexdigest()
            + "\n"
        ).encode()
    ).hexdigest()
    assert _records.tree_sha256(tmp_path) == expected
    assert (
        _records.tree_sha256(source) == hashlib.sha256(source.read_bytes()).hexdigest()
    )

    log = tmp_path / "records.jsonl"
    log.write_text('{"kind":"decision"}\n\nnot-json\n[]\n', encoding="utf-8")
    rows, malformed = _records.load_jsonl(log)
    assert rows == [{"kind": "decision"}]
    assert malformed == 2
    assert _records.load_jsonl(tmp_path / "missing.jsonl") == ([], 0)

    policy = _records.load_policy(PLUGIN_ROOT)
    assert policy["plugin"] == "doc"
    assert _records.matches("doc-work/a.md", ["doc-work/*.md"])
    assert not _records.matches("README.md", ["doc-work/*.md"])

    artifacts = tmp_path / "doc-work"
    artifacts.mkdir()
    (artifacts / "kept.md").write_text("kept", encoding="utf-8")
    (artifacts / "ignored.md").write_text("ignored", encoding="utf-8")
    records = tmp_path / "observations/doc"
    records.mkdir(parents=True)
    (records / "decisions.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.md").write_text("ignored", encoding="utf-8")
    (tmp_path / "doc-work" / "link.md").symlink_to(source)
    custom_policy = {
        "records_dir": "observations/doc",
        "artifact_globs": ["**/*.md"],
        "ignore_globs": ["doc-work/ignored.md"],
    }
    assert _records.changed_artifacts(tmp_path, custom_policy, 0) == [
        "doc-work/kept.md"
    ]
    assert _records.covers(".", "doc-work/kept.md")
    assert _records.covers("doc-work", "doc-work/kept.md")
    assert not _records.covers("doc-work/other.md", "doc-work/kept.md")


def test_load_policy_rejects_invalid_configuration(tmp_path: Path) -> None:
    policy_dir = tmp_path / "hooks"
    policy_dir.mkdir()
    policy_path = policy_dir / "records-policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "plugin": "doc",
                "records_dir": "observations/doc",
                "artifact_globs": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="artifact_globs"):
        _records.load_policy(tmp_path)
