"""Tests for the document side of Sister Liaison Protocol v2."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import BRIEF_REL, LINT_SCRIPT, PLUGIN_ROOT

SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import doc_records  # noqa: E402
import doc_slp  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_payload(
    identifier: str,
    *,
    target: str = "doc",
    inputs: list[dict[str, str]] | None = None,
    depends_on: list[str] | None = None,
    risk: str = "low",
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "system": "ux-creator",
        "id": identifier,
        "target_agent": target,
        "stage": "design",
        "risk": risk,
        "purpose": "Document the kettle control panel for first-time owners.",
        "rationale": (
            "The panel labels changed and the manual now contradicts the device."
        ),
        "requested_changes": ["Rewrite the control panel section."],
        "inputs": inputs or [],
        "expected_deliverables": ["docs/user-manual.md"],
        "acceptance": ["Every label in the manual matches the panel."],
        "depends_on": depends_on or [],
        "created_at": "2025-01-02T03:04:05+00:00",
    }


def write_request(root: Path, identifier: str, **kwargs: Any) -> Path:
    path = root / "liaison" / f"{identifier}.ux-request.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request_payload(identifier, **kwargs)), encoding="utf-8")
    return path


def response_input(request: str, status: str, **kwargs: Any) -> dict[str, Any]:
    return {
        "request": request,
        "status": status,
        "artifacts": [],
        "gate_verdicts": [],
        "decision_refs": [],
        "impression_refs": [],
        "questions_for_user": [],
        **kwargs,
    }


def _input(root: Path, relative: str, text: str) -> dict[str, str]:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return {"path": relative, "sha256": _sha(target)}


def _records(root: Path) -> tuple[str, str]:
    source = root / "source.md"
    source.write_text("panel labels\n", encoding="utf-8")
    decision = doc_records.record_decision(
        {
            "id": "panel-source",
            "stage": "brief",
            "question": "Which source names the panel labels?",
            "principles": ["Use claims that can be traced to an inspectable source."],
            "options": [
                {"name": "device", "pros": ["direct"], "cons": ["needs hardware"]},
                {"name": "firmware", "pros": ["textual"], "cons": ["may lag"]},
            ],
            "chosen": "device",
            "rationale": (
                "The device itself is the label a reader sees, so the manual should "
                "follow it rather than an intermediate artifact. Firmware strings can "
                "lag the silk-screen and would make the manual disagree with the "
                "object in the reader's hand, which is the failure we are fixing."
            ),
            "evidence": [{"path": "source.md"}],
            "risks": ["A later revision may change the silk-screen."],
            "revisit_when": "Revisit when the panel artwork changes.",
        },
        root,
    )["record"]
    impression = doc_records.record_impression(
        {
            "stage": "outline",
            "artifacts": ["source.md"],
            "impression": (
                "The outline puts the panel walkthrough before the troubleshooting "
                "list, which matches the order a new owner meets the device. The "
                "labels are quoted from the panel itself so a reader can check each "
                "one by looking down at the kettle. My worry is that the artwork may "
                "be revised before print, so the section should be refreshed whenever "
                "the panel changes. Next step is to lint the manual and answer the "
                "liaison request with the resulting verdict."
            ),
        },
        root,
    )["record"]
    return decision["event_id"], impression["event_id"]


def test_inbox_lists_only_doc_requests_with_state_precedence(tmp_path: Path) -> None:
    write_request(tmp_path, "for-wire", target="wire")
    write_request(tmp_path, "fresh")
    write_request(tmp_path, "waiting", depends_on=["fresh"])
    changing = _input(tmp_path, "notes.md", "first\n")
    write_request(tmp_path, "drifted", inputs=[changing])
    (tmp_path / "notes.md").write_text("second\n", encoding="utf-8")
    doc_slp.ux_respond(response_input("drifted", "accepted"), tmp_path)
    answered = write_request(tmp_path, "closed")
    assert answered.is_file()
    doc_slp.ux_respond(response_input("closed", "accepted"), tmp_path)

    inbox = doc_slp.ux_inbox(tmp_path)
    states = {entry["id"]: entry["state"] for entry in inbox["requests"]}
    assert states == {
        "fresh": "new",
        "waiting": "blocked",
        "drifted": "stale",
        "closed": "answered",
    }
    waiting = next(e for e in inbox["requests"] if e["id"] == "waiting")
    assert waiting["blocked_by"] == ["fresh"]
    drifted = next(e for e in inbox["requests"] if e["id"] == "drifted")
    assert drifted["stale_inputs"] == ["notes.md"]
    assert inbox["counts"]["new"] == 1
    assert inbox["malformed"] == []


def test_response_input_hash_must_match_current_request_inputs(tmp_path: Path) -> None:
    source = _input(tmp_path, "source.md", "v1\n")
    write_request(tmp_path, "hash-check", inputs=[source])
    doc_slp.ux_respond(response_input("hash-check", "accepted"), tmp_path)
    response_path = tmp_path / "liaison/hash-check.ux-response.json"
    response = json.loads(response_path.read_text(encoding="utf-8"))
    response["input_hashes"]["source.md"] = "f" * 64
    response_path.write_text(json.dumps(response), encoding="utf-8")

    inbox = doc_slp.ux_inbox(tmp_path)
    entry = inbox["requests"][0]
    assert entry["state"] == "stale"
    assert entry["stale_inputs"] == ["source.md"]


def test_missing_inputs_only_allow_needs_info_or_rejected(tmp_path: Path) -> None:
    write_request(
        tmp_path,
        "missing-input",
        inputs=[{"path": "gone.md", "sha256": "a" * 64}],
    )
    refused = doc_slp.ux_respond(response_input("missing-input", "accepted"), tmp_path)
    assert refused["ok"] is False
    assert any("inputs are missing" in error for error in refused["errors"])

    response = doc_slp.ux_respond(
        response_input(
            "missing-input",
            "needs_info",
            reason="The source file named in the request is missing.",
            questions_for_user=["Can you restore the source file?"],
        ),
        tmp_path,
    )["response"]
    assert response["input_hashes"] == {}


def test_dependency_accepts_a_terminal_sister_response(tmp_path: Path) -> None:
    write_request(tmp_path, "upstream", target="wire")
    write_request(tmp_path, "consumer", depends_on=["upstream"])
    source = _input(tmp_path, "wire-input.md", "v1\n")
    write_request(tmp_path, "stale-upstream", target="wire", inputs=[source])
    write_request(tmp_path, "waiting", depends_on=["stale-upstream"])
    write_request(tmp_path, "failed-upstream", target="wire")
    write_request(tmp_path, "failed-waiting", depends_on=["failed-upstream"])
    event_id = "a" * 64
    log = tmp_path / "observations/wire/decisions.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text(json.dumps({"event_id": event_id}) + "\n", encoding="utf-8")
    response = {
        "schema_version": 2,
        "system": "ux-creator",
        "request": "upstream",
        "responder": "wire",
        "status": "done",
        "reason": "The sister finished this request.",
        "input_hashes": {},
        "artifacts": [],
        "gate_verdicts": [],
        "decision_refs": [event_id],
        "impression_refs": [],
        "questions_for_user": [],
        "responded_at": "2026-01-01T00:00:00+00:00",
    }
    (tmp_path / "liaison/upstream.ux-response.json").write_text(
        json.dumps(response), encoding="utf-8"
    )
    stale_response = dict(response, request="stale-upstream")
    (tmp_path / "liaison/stale-upstream.ux-response.json").write_text(
        json.dumps(stale_response), encoding="utf-8"
    )
    failed_response = dict(
        response,
        request="failed-upstream",
        gate_verdicts=[{"gate": "safety", "verdict": "fail"}],
    )
    (tmp_path / "liaison/failed-upstream.ux-response.json").write_text(
        json.dumps(failed_response), encoding="utf-8"
    )

    inbox = doc_slp.ux_inbox(tmp_path)
    entries = {entry["id"]: entry for entry in inbox["requests"]}
    assert entries["consumer"]["state"] == "new"
    assert entries["consumer"]["blocked_by"] == []
    assert entries["waiting"]["state"] == "blocked"
    assert entries["waiting"]["blocked_by"] == ["stale-upstream"]
    assert entries["failed-waiting"]["state"] == "blocked"
    assert entries["failed-waiting"]["blocked_by"] == ["failed-upstream"]


def test_malformed_requests_for_doc_are_reported(tmp_path: Path) -> None:
    liaison = tmp_path / "liaison"
    liaison.mkdir()
    (liaison / "broken.ux-request.json").write_text("{oops", encoding="utf-8")
    payload = request_payload("surprising")
    payload["surprise"] = True
    (liaison / "surprising.ux-request.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    naive = request_payload("naive")
    naive["created_at"] = "2025-01-02T03:04:05"
    (liaison / "naive.ux-request.json").write_text(json.dumps(naive), encoding="utf-8")
    other = request_payload("elsewhere", target="mech")
    other.pop("acceptance")
    (liaison / "elsewhere.ux-request.json").write_text(
        json.dumps(other), encoding="utf-8"
    )

    inbox = doc_slp.ux_inbox(tmp_path)
    reported = {Path(item["path"]).name for item in inbox["malformed"]}
    assert reported == {
        "broken.ux-request.json",
        "surprising.ux-request.json",
        "naive.ux-request.json",
    }
    assert inbox["requests"] == []


def test_malformed_doc_responses_are_reported_without_other_sisters(
    tmp_path: Path,
) -> None:
    write_request(tmp_path, "doc-request")
    write_request(tmp_path, "wire-request", target="wire")
    liaison = tmp_path / "liaison"
    (liaison / "doc-request.ux-response.json").write_text("{oops", encoding="utf-8")
    (liaison / "wire-request.ux-response.json").write_text("{oops", encoding="utf-8")

    inbox = doc_slp.ux_inbox(tmp_path)
    assert [Path(item["path"]).name for item in inbox["malformed"]] == [
        "doc-request.ux-response.json"
    ]


def test_request_enum_matches_family_brief() -> None:
    assert doc_slp.TARGET_AGENTS == (
        "bard",
        "circuit",
        "dashboard",
        "doc",
        "firmware",
        "fpga",
        "mech",
        "prodeng",
        "sim",
        "wire",
    )


def test_malformed_response_for_unparseable_doc_request_is_reported(
    tmp_path: Path,
) -> None:
    liaison = tmp_path / "liaison"
    liaison.mkdir()
    (liaison / "broken.ux-request.json").write_text("{oops", encoding="utf-8")
    (liaison / "broken.ux-response.json").write_text("{oops", encoding="utf-8")

    inbox = doc_slp.ux_inbox(tmp_path)
    assert {Path(item["path"]).name for item in inbox["malformed"]} == {
        "broken.ux-request.json",
        "broken.ux-response.json",
    }


def test_symlinked_liaison_inputs_and_artifacts_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("inside\n", encoding="utf-8")
    (tmp_path / "alias.md").symlink_to(source)
    write_request(
        tmp_path,
        "linked-input",
        inputs=[{"path": "alias.md", "sha256": _sha(source)}],
    )
    inbox = doc_slp.ux_inbox(tmp_path)
    assert "symlink" in inbox["malformed"][0]["errors"][0]

    write_request(tmp_path, "linked-artifact")
    with pytest.raises(doc_slp.LiaisonError, match="symlink"):
        doc_slp.ux_respond(
            {
                **response_input("linked-artifact", "accepted"),
                "artifacts": ["alias.md"],
            },
            tmp_path,
        )


def test_request_and_response_schemas_reject_invalid_enums_and_nested_keys(
    tmp_path: Path,
) -> None:
    payload = request_payload("panel")
    payload["stage"] = "unknown"
    with pytest.raises(doc_slp.LiaisonError, match="request.stage"):
        doc_slp.validate_request(payload)
    payload = request_payload("panel")
    payload["target_agent"] = "ux"
    with pytest.raises(doc_slp.LiaisonError, match="request.target_agent"):
        doc_slp.validate_request(payload)
    payload = request_payload("panel")
    payload["risk"] = "critical"
    with pytest.raises(doc_slp.LiaisonError, match="request.risk"):
        doc_slp.validate_request(payload)
    payload = request_payload("panel", risk="high")
    payload["rationale"] = "short"
    with pytest.raises(doc_slp.LiaisonError, match="request.rationale"):
        doc_slp.validate_request(payload)
    payload = request_payload("panel", inputs=[{"path": "x", "sha256": "A" * 64}])
    with pytest.raises(doc_slp.LiaisonError, match="lowercase sha256"):
        doc_slp.validate_request(payload)
    payload = request_payload("panel", inputs=[{"path": "x", "sha256": "0" * 64}])
    payload["inputs"][0]["extra"] = "rejected"
    with pytest.raises(doc_slp.LiaisonError, match="unknown key"):
        doc_slp.validate_request(payload)

    write_request(tmp_path, "panel")
    response = doc_slp.ux_respond(response_input("panel", "accepted"), tmp_path)[
        "response"
    ]
    response["gate_verdicts"] = [{"gate": "lint", "verdict": "pass", "extra": True}]
    with pytest.raises(doc_slp.LiaisonError, match="unknown key"):
        doc_slp.validate_response(response, tmp_path)
    response["gate_verdicts"] = [{"gate": "lint", "verdict": "maybe"}]
    with pytest.raises(doc_slp.LiaisonError, match="response.gate_verdicts"):
        doc_slp.validate_response(response, tmp_path)
    response["gate_verdicts"] = []
    response["status"] = "unknown"
    with pytest.raises(doc_slp.LiaisonError, match="response.status"):
        doc_slp.validate_response(response, tmp_path)


def test_request_id_must_match_the_file_stem(tmp_path: Path) -> None:
    liaison = tmp_path / "liaison"
    liaison.mkdir()
    (liaison / "named.ux-request.json").write_text(
        json.dumps(request_payload("other")), encoding="utf-8"
    )
    inbox = doc_slp.ux_inbox(tmp_path)
    assert "file stem" in inbox["malformed"][0]["errors"][0]


def test_response_hashes_inputs_and_artifacts_and_overwrites(tmp_path: Path) -> None:
    source = _input(tmp_path, "panel.md", "labels\n")
    write_request(tmp_path, "panel", inputs=[source])
    artifact = tmp_path / "doc-work/panel/outline.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Outline\n", encoding="utf-8")
    first = doc_slp.ux_respond(
        {
            **response_input("panel", "in_progress"),
            "artifacts": ["doc-work/panel/outline.md"],
        },
        tmp_path,
    )
    assert first["ok"] is True
    written = json.loads(
        (tmp_path / "liaison/panel.ux-response.json").read_text(encoding="utf-8")
    )
    assert written["responder"] == "doc"
    assert written["input_hashes"] == {"panel.md": source["sha256"]}
    assert written["artifacts"][0]["sha256"] == _sha(artifact)
    doc_slp.validate_response(written, tmp_path)

    artifact.write_text("# Outline\n\nMore.\n", encoding="utf-8")
    with pytest.raises(doc_slp.LiaisonError, match="sha256 does not match"):
        doc_slp.validate_response(written, tmp_path)
    second = doc_slp.ux_respond(
        {
            **response_input(
                "panel",
                "needs_info",
                questions_for_user=["Which panel revision ships first?"],
            ),
            "reason": "The panel artwork revision is not stated anywhere.",
        },
        tmp_path,
    )
    assert second["ok"] is True
    reread = json.loads(
        (tmp_path / "liaison/panel.ux-response.json").read_text(encoding="utf-8")
    )
    assert reread["status"] == "needs_info"
    assert list((tmp_path / "liaison").glob(".*tmp")) == []


def test_unknown_request_and_unknown_refs_are_refused(tmp_path: Path) -> None:
    with pytest.raises(doc_slp.LiaisonError, match="unknown request"):
        doc_slp.ux_respond(response_input("missing", "accepted"), tmp_path)
    write_request(tmp_path, "panel")
    with pytest.raises(doc_slp.LiaisonError, match="unknown key"):
        doc_slp.ux_respond(
            {**response_input("panel", "accepted"), "mood": "sunny"}, tmp_path
        )
    result = doc_slp.ux_respond(
        response_input(
            "panel",
            "in_progress",
            decision_refs=["c" * 64],
            impression_refs=["d" * 64],
        ),
        tmp_path,
    )
    assert result["ok"] is False
    assert any("decision_refs" in error for error in result["errors"])
    assert any("impression_refs" in error for error in result["errors"])
    assert not (tmp_path / "liaison/panel.ux-response.json").exists()


def test_needs_info_requires_a_question(tmp_path: Path) -> None:
    write_request(tmp_path, "panel")
    result = doc_slp.ux_respond(
        response_input(
            "panel",
            "needs_info",
            reason="The panel revision is not recorded in the workspace.",
        ),
        tmp_path,
    )
    assert result["ok"] is False
    assert any("question_for_user" in error for error in result["errors"])


def test_done_requires_passing_gates_and_a_fresh_lint_report(workspace: Path) -> None:
    decision_ref, impression_ref = _records(workspace)
    write_request(workspace, "manual")
    base = response_input(
        "manual",
        "done",
        reason="The manual now matches the panel labels on the device.",
        artifacts=["docs/user-manual.md"],
        decision_refs=[decision_ref],
        impression_refs=[impression_ref],
        gate_verdicts=[{"gate": "doc-lint", "verdict": "pass"}],
    )
    unlinted = doc_slp.ux_respond(dict(base), workspace)
    assert unlinted["ok"] is False
    assert any("doc-lint report" in error for error in unlinted["errors"])

    subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--brief", str(BRIEF_REL)],
        cwd=workspace,
        check=True,
        capture_output=True,
    )
    extra = workspace / "docs/unlisted.md"
    extra.write_text("# Unlisted\n", encoding="utf-8")
    unlisted = dict(
        base,
        artifacts=["docs/user-manual.md", "docs/unlisted.md"],
    )
    refused = doc_slp.ux_respond(unlisted, workspace)
    assert refused["ok"] is False
    assert any("docs/unlisted.md" in error for error in refused["errors"])
    extra.unlink()
    for verdict in ("fail", "unknown"):
        failing = dict(base, gate_verdicts=[{"gate": "doc-lint", "verdict": verdict}])
        refused = doc_slp.ux_respond(failing, workspace)
        assert refused["ok"] is False
        assert any("every gate to pass" in error for error in refused["errors"])
    no_lint_gate = dict(base, gate_verdicts=[{"gate": "safety", "verdict": "pass"}])
    refused = doc_slp.ux_respond(no_lint_gate, workspace)
    assert refused["ok"] is False
    assert any(
        "passing 'doc-lint' gate verdict" in error for error in refused["errors"]
    )

    done = doc_slp.ux_respond(dict(base), workspace)
    assert done["ok"] is True, done
    assert done["response"]["status"] == "done"

    manual = workspace / "docs/user-manual.md"
    manual.write_text(
        manual.read_text(encoding="utf-8") + "\nMore.\n", encoding="utf-8"
    )
    stale = doc_slp.ux_respond(dict(base), workspace)
    assert stale["ok"] is False
    assert any("doc-lint report" in error for error in stale["errors"])


def test_done_needs_records_and_an_artifact(workspace: Path) -> None:
    write_request(workspace, "manual")
    result = doc_slp.ux_respond(
        response_input(
            "manual",
            "done",
            reason="The manual is finished and matches the device panel.",
        ),
        workspace,
    )
    assert result["ok"] is False
    joined = " ".join(result["errors"])
    assert "at least one artifact" in joined
    assert "decision_ref" in joined
    assert "impression_ref" in joined


def test_cli_inbox_and_respond_round_trip(tmp_path: Path) -> None:
    write_request(tmp_path, "panel")
    env = {**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)}
    inbox = subprocess.run(
        [sys.executable, str(SCRIPTS / "doc_tool.py"), "ux", "inbox"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert inbox.returncode == 0, inbox.stderr
    assert json.loads(inbox.stdout)["requests"][0]["state"] == "new"

    payload = tmp_path / "answer.json"
    payload.write_text(
        json.dumps(response_input("panel", "accepted")), encoding="utf-8"
    )
    respond = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "doc_tool.py"),
            "ux",
            "respond",
            "--json",
            str(payload),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert respond.returncode == 0, respond.stderr
    assert json.loads(respond.stdout)["path"] == "liaison/panel.ux-response.json"


def test_cli_respond_returns_failure_exit_for_refused_done(tmp_path: Path) -> None:
    write_request(tmp_path, "panel")
    payload = tmp_path / "answer.json"
    payload.write_text(
        json.dumps(
            response_input(
                "panel",
                "done",
                reason="The manual is finished and matches the device panel.",
            )
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "doc_tool.py"),
            "ux",
            "respond",
            "--json",
            str(payload),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)},
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["ok"] is False


def test_mcp_inbox_and_respond_round_trip(tmp_path: Path) -> None:
    pytest.importorskip("mcp.client.stdio")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    write_request(tmp_path, "panel")
    env = {**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)}

    async def exercise() -> None:
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
                assert "doc_ux_inbox" in names
                assert "doc_ux_respond" in names
                inbox = await session.call_tool("doc_ux_inbox", {})
                assert inbox.structuredContent is not None
                assert inbox.structuredContent["requests"][0]["state"] == "new"
                answered = await session.call_tool(
                    "doc_ux_respond",
                    response_input("panel", "accepted"),
                )
                assert not answered.isError
                assert answered.structuredContent is not None
                assert answered.structuredContent["ok"] is True

    asyncio.run(exercise())


def test_doctor_reports_unanswered_liaison_requests(tmp_path: Path) -> None:
    write_request(tmp_path, "panel")
    result = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "hooks/scripts/doc_doctor.py")],
        input="{}",
        capture_output=True,
        text=True,
        env={**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)["additionalContext"]
    assert "requests for doc=1 unanswered=1" in context
