"""Strict standard-library writers for document-agent VRP records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePath
from typing import Any, cast

HOOKS = Path(__file__).resolve().parents[1] / "hooks" / "scripts"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

import _records  # noqa: E402

PLUGIN = "doc"
RECORDS_DIR = Path("observations") / PLUGIN
LOG_FILES = dict(_records.LOG_FILES)
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
DECISION_KEYS = {
    "id",
    "stage",
    "question",
    "principles",
    "options",
    "chosen",
    "rationale",
    "evidence",
    "assumptions",
    "unknowns",
    "risks",
    "revisit_when",
    "decided_by",
}
IMPRESSION_KEYS = {"stage", "artifacts", "impression"}
VISION_REVIEW_KEYS = {
    "image_path",
    "source_event_id",
    "model",
    "checklist",
    "findings",
    "impression",
}


def workspace_root(root: Path | None = None) -> Path:
    return (
        root or Path(os.environ.get("OPENHANDS_PROJECT_DIR") or Path.cwd())
    ).resolve()


def _closed(
    value: object, required: set[str], optional: set[str], label: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} keys must be strings")
    obj = cast(dict[str, Any], value)
    unknown = sorted(set(obj) - required - optional)
    missing = sorted(required - set(obj))
    if unknown:
        raise ValueError(f"{label}: unknown key(s): {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{label}: missing key(s): {', '.join(missing)}")
    return obj


def _string(value: object, label: str, minimum: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f"{label} must be a string of at least {minimum} characters")
    return value


def _slug(value: object, label: str) -> str:
    text = _string(value, label)
    if not SLUG.fullmatch(text):
        raise ValueError(f"{label} must be a lowercase slug")
    return text


def _strings(value: object, label: str, minimum: int = 0) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{label} must be a list with at least {minimum} item(s)")
    out: list[str] = []
    for index, item in enumerate(cast(list[object], value)):
        out.append(_string(item, f"{label}[{index}]"))
    return out


def _workspace_path(value: object, root: Path) -> tuple[str, Path]:
    text = _string(value, "path")
    path = Path(text)
    if ".." in PurePath(text).parts:
        raise ValueError(f"path may not contain '..': {text}")
    candidate = path if path.is_absolute() else root / path
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        try:
            relative = candidate.resolve(strict=False).relative_to(root)
        except ValueError as exc:
            raise ValueError(f"path is outside the workspace: {text}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"path traverses a symlink: {text}")
    resolved = candidate.resolve()
    try:
        rel = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path is outside the workspace: {text}") from exc
    if not resolved.exists():
        raise ValueError(f"artifact does not exist: {text}")
    return rel or ".", resolved


def _sha(path: Path) -> str:
    return _records.tree_sha256(path)


def _append(kind: str, body: dict[str, Any], root: Path) -> dict[str, Any]:
    log = root / RECORDS_DIR / LOG_FILES[kind]
    log.parent.mkdir(parents=True, exist_ok=True)
    lines = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    sequence = sum(bool(line.strip()) for line in lines) + 1
    body = {key: value for key, value in body.items() if value is not None}
    identity = {"kind": kind, "sequence": sequence, **body}
    event_id = hashlib.sha256(
        json.dumps(
            identity, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    record = {
        "schema_version": _records.SCHEMA_VERSION,
        "kind": kind,
        "plugin": PLUGIN,
        "sequence": sequence,
        "event_id": event_id,
        "recorded_at": datetime.now(UTC).isoformat(),
        **body,
    }
    errors = _records.record_errors(kind, record)
    if errors:
        raise ValueError("; ".join(errors))
    with log.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
    return {
        "ok": True,
        "kind": kind,
        "path": log.relative_to(root).as_posix(),
        "record": record,
    }


def record_decision(value: object, root: Path | None = None) -> dict[str, Any]:
    base = workspace_root(root)
    required = {
        "id",
        "stage",
        "question",
        "principles",
        "options",
        "chosen",
        "rationale",
        "evidence",
        "risks",
        "revisit_when",
    }
    optional = {"assumptions", "unknowns", "decided_by"}
    data = _closed(value, required, optional, "decision")
    body: dict[str, Any] = {
        "id": _slug(data["id"], "id"),
        "stage": _slug(data["stage"], "stage"),
        "question": _string(data["question"], "question", _records.QUESTION_MIN_CHARS),
        "principles": _strings(data["principles"], "principles", 1),
        "options": [],
        "chosen": _string(data["chosen"], "chosen"),
        "rationale": _string(
            data["rationale"], "rationale", _records.RATIONALE_MIN_CHARS
        ),
        "assumptions": _strings(data.get("assumptions", []), "assumptions"),
        "unknowns": _strings(data.get("unknowns", []), "unknowns"),
        "risks": _strings(data["risks"], "risks", 1),
        "revisit_when": _string(data["revisit_when"], "revisit_when"),
        "decided_by": data.get("decided_by", "agent"),
    }
    if any(len(item) < _records.PRINCIPLE_MIN_CHARS for item in body["principles"]):
        raise ValueError(
            f"each principle needs at least {_records.PRINCIPLE_MIN_CHARS} characters"
        )
    options = data["options"]
    if not isinstance(options, list) or len(options) < 2:
        raise ValueError("options must contain at least two entries")
    for index, raw in enumerate(cast(list[object], options)):
        option = _closed(raw, {"name", "pros", "cons"}, set(), f"options[{index}]")
        body["options"].append(
            {
                "name": _string(option["name"], f"options[{index}].name"),
                "pros": _strings(option["pros"], f"options[{index}].pros", 1),
                "cons": _strings(option["cons"], f"options[{index}].cons", 1),
            }
        )
    names = [item["name"] for item in body["options"]]
    if len(set(names)) != len(names):
        raise ValueError("option names must be unique")
    if body["chosen"] not in names:
        raise ValueError("chosen must name one of the options")
    if (
        not isinstance(body["decided_by"], str)
        or body["decided_by"] not in _records.DECIDERS
    ):
        raise ValueError("decided_by must be 'agent' or 'user'")
    evidence = data["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("evidence must contain at least one entry")
    refs: list[dict[str, str]] = []
    for index, raw in enumerate(cast(list[object], evidence)):
        entry = _closed(raw, set(), {"path", "reference"}, f"evidence[{index}]")
        has_path = "path" in entry
        has_reference = "reference" in entry
        if has_path == has_reference:
            raise ValueError(
                f"evidence[{index}] needs exactly one of path or reference"
            )
        if has_path:
            relative, artifact = _workspace_path(entry["path"], base)
            refs.append({"path": relative, "sha256": _sha(artifact)})
        else:
            refs.append(
                {
                    "reference": _string(
                        entry["reference"], f"evidence[{index}].reference"
                    )
                }
            )
    body["evidence"] = refs
    return _append("decision", body, base)


def record_impression(value: object, root: Path | None = None) -> dict[str, Any]:
    base = workspace_root(root)
    data = _closed(value, {"stage", "artifacts", "impression"}, set(), "impression")
    artifacts = data["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("artifacts must contain at least one path")
    refs: list[dict[str, str]] = []
    for path in cast(list[object], artifacts):
        relative, artifact = _workspace_path(path, base)
        refs.append({"path": relative, "sha256": _sha(artifact)})
    body = {
        "stage": _slug(data["stage"], "stage"),
        "artifacts": refs,
        "impression": _string(data["impression"], "impression"),
    }
    return _append("stage_impression", body, base)


def _event_exists(event_id: str, root: Path) -> bool:
    for filename in (_records.VISION_EVENTS_FILE, _records.IMAGE_OBSERVATIONS_FILE):
        path = root / RECORDS_DIR / filename
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and record.get("event_id") == event_id:
                return True
    return False


def record_vision_review(value: object, root: Path | None = None) -> dict[str, Any]:
    base = workspace_root(root)
    data = _closed(
        value,
        {"model", "checklist", "impression"},
        {"image_path", "source_event_id", "findings"},
        "vision review",
    )
    if "image_path" not in data and "source_event_id" not in data:
        raise ValueError("provide image_path or source_event_id")
    findings: list[dict[str, str]] = []
    raw_findings = data.get("findings", [])
    if not isinstance(raw_findings, list):
        raise ValueError("findings must be a list")
    for index, raw in enumerate(cast(list[object], raw_findings)):
        finding = _closed(
            raw, {"category", "severity", "note"}, set(), f"findings[{index}]"
        )
        severity = finding["severity"]
        if not isinstance(severity, str) or severity not in _records.SEVERITIES:
            raise ValueError(
                f"findings[{index}].severity must be info, warning, or error"
            )
        findings.append(
            {
                "category": _string(finding["category"], f"findings[{index}].category"),
                "severity": severity,
                "note": _string(finding["note"], f"findings[{index}].note"),
            }
        )
    body: dict[str, Any] = {
        "model": _string(data["model"], "model"),
        "checklist": _slug(data["checklist"], "checklist"),
        "findings": findings,
        "impression": _string(data["impression"], "impression"),
        "image_sha256": None,
        "source_event_id": None,
        "image_path": None,
    }
    if "image_path" in data:
        relative, image = _workspace_path(data["image_path"], base)
        if not image.is_file():
            raise ValueError("image_path must identify a file")
        body["image_path"] = relative
        body["image_sha256"] = _records.sha256_file(image)
    if "source_event_id" in data:
        event_id = _string(data["source_event_id"], "source_event_id")
        if not SHA256.fullmatch(event_id):
            raise ValueError("source_event_id must be a lowercase sha256 event id")
        if not _event_exists(event_id, base):
            raise ValueError(f"unknown source_event_id: {event_id}")
        body["source_event_id"] = event_id
    return _append("vision_review", body, base)


def records_summary(root: Path | None = None) -> dict[str, Any]:
    base = workspace_root(root)
    directory = base / RECORDS_DIR
    counts: dict[str, int] = {}
    for kind, filename in LOG_FILES.items():
        path = directory / filename
        lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
        counts[kind] = sum(bool(line.strip()) for line in lines)
    status_path = directory / "records-status.json"
    status: object = None
    if status_path.is_file():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            status = {
                "verdict": "fail",
                "problems": ["records-status.json is malformed"],
            }
    sessions = directory / ".sessions"
    return {
        "ok": True,
        "records_dir": RECORDS_DIR.as_posix(),
        "counts": counts,
        "sessions": len(list(sessions.glob("*.json"))) if sessions.is_dir() else 0,
        "latest_status": status,
    }
