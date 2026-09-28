#!/usr/bin/env python3
"""Report documentation-run status when an agent stops.

Reads the stop-hook event on stdin and scans `doc-work/*/doc-brief.json`
under the working directory. Each brief is reported as:

- linted=pass   doc-lint.json passes and still matches the brief and every
                target document (sha256)
- linted=stale  a report exists but the brief or a document changed since
- linted=fail   the latest report failed
- linted=false  no report yet

Anything but a fresh pass is surfaced so the agent reruns doc_lint.py or
states the verdict before finishing. Unanswered inquiries and open questions
are surfaced too, so they reach the user instead of being silently dropped.

Python standard library only. Unreadable briefs or reports fail closed.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import cast

BRIEF_NAME = "doc-brief.json"
REPORT_NAME = "doc-lint.json"
REPORT_KIND = "doc_lint_report"
WORK_DIR = "doc-work"


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _read_object(path: Path) -> dict[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return cast(dict[str, object], value)


def _list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def lint_state(brief: Path, root: Path) -> str:
    report_path = brief.with_name(REPORT_NAME)
    if not report_path.is_file():
        return "false"
    report = _read_object(report_path)
    if report.get("artifact_kind") != REPORT_KIND:
        raise ValueError(f"{report_path}: unexpected artifact_kind")
    if _dict(report.get("brief")).get("sha256") != _sha256(brief):
        return "stale"
    for raw in _list(report.get("documents")):
        doc = _dict(raw)
        path = doc.get("path")
        if not isinstance(path, str) or doc.get("sha256") != _sha256(root / path):
            return "stale"
    if report.get("mode") != "full" or report.get("verdict") != "pass":
        return "fail"
    return "pass"


def pending_questions(brief: dict[str, object]) -> tuple[int, int]:
    unanswered = sum(
        1
        for raw in _list(brief.get("inquiries"))
        if _dict(raw).get("status") != "answered"
    )
    return unanswered, len(_list(brief.get("open_questions")))


def main() -> int:
    try:
        event = _dict(json.load(sys.stdin))
        working = event.get("working_dir")
        root = Path(working if isinstance(working, str) and working else os.getcwd())
        root = root.resolve()
        work = root / WORK_DIR
        briefs = sorted(work.glob(f"*/{BRIEF_NAME}")) if work.is_dir() else []
        lines: list[str] = []
        todo: list[str] = []
        for brief_path in briefs:
            brief = _read_object(brief_path)
            state = lint_state(brief_path, root)
            unanswered, open_q = pending_questions(brief)
            rel = brief_path.relative_to(root).as_posix()
            lines.append(
                f"{rel}: linted={state} unanswered_inquiries={unanswered}"
                f" open_questions={open_q}"
            )
            if state != "pass":
                todo.append(rel)
        if todo:
            lines.append(
                "Before finishing, rerun doc_lint.py (or state the failing verdict"
                " explicitly) for: " + ", ".join(todo)
            )
        if any("unanswered_inquiries=0 open_questions=0" not in ln for ln in lines):
            lines.append(
                "List unanswered inquiries and open questions in the final"
                " report so the user can answer them."
            )
        if not lines:
            lines.append(f"No doc briefs under {work} (no documentation run).")
        print(json.dumps({"decision": "allow", "additionalContext": "\n".join(lines)}))
        return 0
    except Exception as exc:  # noqa: BLE001 - report and fail closed
        print(f"report_doc_status: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
