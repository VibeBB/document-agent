"""Sister Liaison Protocol v2 — the document side of the liaison loop.

UX-creator writes `liaison/<id>.ux-request.json` in the workspace; doc answers
with `liaison/<id>.ux-response.json` beside it. This module is a strict local
mirror of the v2 schemas: it imports no UX code, rejects unknown keys at every
level, and hashes every input and artifact it reports. A `done` response is
refused unless the deterministic doc linter already passed for every Markdown
artifact it claims.

Python standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any, cast

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
HOOK_SCRIPTS = PLUGIN_ROOT / "hooks" / "scripts"
if str(HOOK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(HOOK_SCRIPTS))

import _records  # type: ignore[reportMissingImports]  # noqa: E402
from report_doc_status import (  # type: ignore[reportMissingImports]  # noqa: E402
    lint_state,
)

PLUGIN = "doc"
SYSTEM = "ux-creator"
SCHEMA_VERSION = 2
LIAISON_DIR = Path("liaison")
REQUEST_SUFFIX = ".ux-request.json"
RESPONSE_SUFFIX = ".ux-response.json"
WORK_DIR = Path("doc-work")
LINT_REPORT_GATE = "doc-lint"
TARGET_AGENTS = (
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
STAGES = (
    "requirements",
    "design",
    "manufacturing_handoff",
    "build",
    "evaluation",
    "revision",
)
RISKS = ("low", "high")
STATUSES = (
    "accepted",
    "in_progress",
    "done",
    "rejected",
    "deferred",
    "needs_info",
)
TERMINAL_STATUSES = ("done", "rejected", "deferred")
VERDICTS = ("pass", "fail", "unknown")
REASON_MIN_CHARS = 20
PURPOSE_MIN_CHARS = 20
RATIONALE_MIN_CHARS = 20
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUEST_KEYS = {
    "schema_version",
    "system",
    "id",
    "target_agent",
    "stage",
    "risk",
    "purpose",
    "rationale",
    "requested_changes",
    "inputs",
    "expected_deliverables",
    "acceptance",
    "depends_on",
    "created_at",
}
RESPONSE_KEYS = {
    "schema_version",
    "system",
    "request",
    "responder",
    "status",
    "reason",
    "input_hashes",
    "artifacts",
    "gate_verdicts",
    "decision_refs",
    "impression_refs",
    "questions_for_user",
    "responded_at",
}
RESPOND_KEYS = {
    "request",
    "status",
    "reason",
    "artifacts",
    "gate_verdicts",
    "decision_refs",
    "impression_refs",
    "questions_for_user",
}
RESPOND_REQUIRED = RESPOND_KEYS - {"reason"}


class LiaisonError(ValueError):
    """The payload or request cannot be used as written."""


def workspace_root(root: Path | None = None) -> Path:
    return (
        root or Path(os.environ.get("OPENHANDS_PROJECT_DIR") or Path.cwd())
    ).resolve()


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LiaisonError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise LiaisonError(f"{label} keys must be strings")
    return cast(dict[str, Any], value)


def _closed(
    value: object, allowed: set[str], required: set[str], label: str
) -> dict[str, Any]:
    obj = _object(value, label)
    unknown = sorted(set(obj) - allowed)
    missing = sorted(required - set(obj))
    if unknown:
        raise LiaisonError(f"{label}: unknown key(s): {', '.join(unknown)}")
    if missing:
        raise LiaisonError(f"{label}: missing key(s): {', '.join(missing)}")
    return obj


def _text(value: object, label: str, minimum: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise LiaisonError(f"{label} must be a string of at least {minimum} characters")
    return value


def _enum(value: object, allowed: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise LiaisonError(f"{label} must be one of {', '.join(allowed)}")
    return value


def _slug(value: object, label: str) -> str:
    text = _text(value, label)
    if not SLUG.fullmatch(text):
        raise LiaisonError(f"{label} must be a lowercase slug: {text}")
    return text


def _timestamp(value: object, label: str) -> str:
    text = _text(value, label)
    try:
        moment = datetime.fromisoformat(text)
    except ValueError as exc:
        raise LiaisonError(f"{label} must be an ISO-8601 timestamp") from exc
    if moment.tzinfo is None:
        raise LiaisonError(f"{label} must carry a timezone offset")
    return text


def _text_list(
    value: object, label: str, minimum: int = 0, chars: int = 1
) -> list[str]:
    if not isinstance(value, list):
        raise LiaisonError(f"{label} must be a list")
    items = [
        _text(item, f"{label}[{index}]", chars)
        for index, item in enumerate(cast(list[object], value))
    ]
    if len(items) < minimum:
        raise LiaisonError(
            f"{label} needs at least {minimum} entr{'y' if minimum == 1 else 'ies'}"
        )
    return items


def _relative(
    value: object, label: str, root: Path, *, require_exists: bool = True
) -> tuple[str, Path]:
    root = root.resolve()
    text = _text(value, label)
    if (
        PurePath(text).is_absolute()
        or PureWindowsPath(text).is_absolute()
        or ".." in PurePath(text).parts
        or "\\" in text
        or "\x00" in text
        or not PurePath(text).parts
    ):
        raise LiaisonError(f"{label} must be a relative workspace path: {text}")
    target = root / text
    current = root
    for part in PurePath(text).parts:
        current = current / part
        if current.is_symlink():
            raise LiaisonError(f"{label} traverses a symlink: {text}")
    try:
        target.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise LiaisonError(f"{label} is outside the workspace: {text}") from exc
    if require_exists and not target.exists():
        raise LiaisonError(f"{label} does not exist: {text}")
    return PurePath(text).as_posix(), target


def validate_request(
    value: object, stem: str | None = None, root: Path | None = None
) -> dict[str, Any]:
    data = _closed(value, REQUEST_KEYS, REQUEST_KEYS, "request")
    if data["schema_version"] != SCHEMA_VERSION:
        raise LiaisonError(f"request.schema_version must be {SCHEMA_VERSION}")
    if data["system"] != SYSTEM:
        raise LiaisonError(f"request.system must be {SYSTEM!r}")
    identifier = _slug(data["id"], "request.id")
    if stem is not None and identifier != stem:
        raise LiaisonError(
            f"request.id must equal the file stem: {identifier} != {stem}"
        )
    risk = _enum(data["risk"], RISKS, "request.risk")
    request: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "system": SYSTEM,
        "id": identifier,
        "target_agent": _enum(
            data["target_agent"], TARGET_AGENTS, "request.target_agent"
        ),
        "stage": _enum(data["stage"], STAGES, "request.stage"),
        "risk": risk,
        "purpose": _text(data["purpose"], "request.purpose", PURPOSE_MIN_CHARS),
        "rationale": _text(
            data["rationale"],
            "request.rationale",
            RATIONALE_MIN_CHARS if risk == "high" else 0,
        ),
        "requested_changes": _text_list(
            data["requested_changes"], "request.requested_changes", 1
        ),
        "expected_deliverables": _text_list(
            data["expected_deliverables"], "request.expected_deliverables", 1
        ),
        "acceptance": _text_list(data["acceptance"], "request.acceptance", 1),
        "depends_on": [
            _slug(item, f"request.depends_on[{index}]")
            for index, item in enumerate(
                _text_list(data["depends_on"], "request.depends_on")
            )
        ],
        "created_at": _timestamp(data["created_at"], "request.created_at"),
    }
    inputs = data["inputs"]
    if not isinstance(inputs, list):
        raise LiaisonError("request.inputs must be a list")
    declared: list[dict[str, str]] = []
    for index, raw in enumerate(cast(list[object], inputs)):
        item = _closed(
            raw, {"path", "sha256"}, {"path", "sha256"}, f"request.inputs[{index}]"
        )
        path = _text(item["path"], f"request.inputs[{index}].path")
        if root is not None:
            path, _ = _relative(
                path, f"request.inputs[{index}].path", root, require_exists=False
            )
        elif (
            PurePath(path).is_absolute()
            or PureWindowsPath(path).is_absolute()
            or ".." in PurePath(path).parts
            or "\\" in path
            or "\x00" in path
            or not PurePath(path).parts
        ):
            raise LiaisonError(
                f"request.inputs[{index}].path must be a relative workspace path: "
                f"{path}"
            )
        digest = _text(item["sha256"], f"request.inputs[{index}].sha256")
        if not SHA256.fullmatch(digest):
            raise LiaisonError(
                f"request.inputs[{index}].sha256 must be a lowercase sha256"
            )
        declared.append({"path": PurePath(path).as_posix(), "sha256": digest})
    if len({entry["path"] for entry in declared}) != len(declared):
        raise LiaisonError("request.inputs may not contain duplicate paths")
    if identifier in request["depends_on"]:
        raise LiaisonError("request.depends_on may not include its own id")
    if len(set(request["depends_on"])) != len(request["depends_on"]):
        raise LiaisonError("request.depends_on may not contain duplicate ids")
    request["inputs"] = declared
    return request


def validate_response(value: object, root: Path) -> dict[str, Any]:
    data = _closed(value, RESPONSE_KEYS, RESPONSE_KEYS, "response")
    if data["schema_version"] != SCHEMA_VERSION:
        raise LiaisonError(f"response.schema_version must be {SCHEMA_VERSION}")
    if data["system"] != SYSTEM:
        raise LiaisonError(f"response.system must be {SYSTEM!r}")
    responder = _enum(data["responder"], TARGET_AGENTS, "response.responder")
    status = _enum(data["status"], STATUSES, "response.status")
    hashes = _object(data["input_hashes"], "response.input_hashes")
    normalized_hashes: dict[str, str] = {}
    for key, digest in hashes.items():
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise LiaisonError(
                f"response.input_hashes[{key}] must be a lowercase sha256"
            )
        relative, _ = _relative(
            key, "response.input_hashes path", root, require_exists=False
        )
        if relative in normalized_hashes:
            raise LiaisonError("response.input_hashes may not contain duplicate paths")
        normalized_hashes[relative] = digest
    artifacts: list[dict[str, str]] = []
    raw_artifacts = data["artifacts"]
    if not isinstance(raw_artifacts, list):
        raise LiaisonError("response.artifacts must be a list")
    for index, raw in enumerate(cast(list[object], raw_artifacts)):
        item = _closed(
            raw, {"path", "sha256"}, {"path", "sha256"}, f"response.artifacts[{index}]"
        )
        digest = _text(item["sha256"], f"response.artifacts[{index}].sha256")
        if not SHA256.fullmatch(digest):
            raise LiaisonError(
                f"response.artifacts[{index}].sha256 must be a lowercase sha256"
            )
        relative, target = _relative(
            item["path"], f"response.artifacts[{index}].path", root
        )
        if any(artifact["path"] == relative for artifact in artifacts):
            raise LiaisonError("response.artifacts may not contain duplicate paths")
        artifacts.append(
            {
                "path": relative,
                "sha256": digest,
            }
        )
        if _records.tree_sha256(target) != digest:
            raise LiaisonError(
                f"response.artifacts[{index}] sha256 does not match current artifact: "
                f"{relative}"
            )
    verdicts: list[dict[str, str]] = []
    raw_verdicts = data["gate_verdicts"]
    if not isinstance(raw_verdicts, list):
        raise LiaisonError("response.gate_verdicts must be a list")
    for index, raw in enumerate(cast(list[object], raw_verdicts)):
        item = _closed(
            raw,
            {"gate", "verdict"},
            {"gate", "verdict"},
            f"response.gate_verdicts[{index}]",
        )
        verdicts.append(
            {
                "gate": _text(item["gate"], f"response.gate_verdicts[{index}].gate"),
                "verdict": _enum(
                    item["verdict"],
                    VERDICTS,
                    f"response.gate_verdicts[{index}].verdict",
                ),
            }
        )
    if status == "done" and any(item["verdict"] != "pass" for item in verdicts):
        raise LiaisonError("response.done requires every gate verdict to pass")
    decision_refs = _text_list(data["decision_refs"], "response.decision_refs")
    impression_refs = _text_list(data["impression_refs"], "response.impression_refs")
    for label, references in (
        ("response.decision_refs", decision_refs),
        ("response.impression_refs", impression_refs),
    ):
        if any(not SHA256.fullmatch(reference) for reference in references):
            raise LiaisonError(f"{label} entries must be lowercase sha256 event ids")
    known_decisions = _event_ids(root, (_records.LOG_FILES["decision"],), responder)
    known_impressions = _event_ids(
        root,
        (
            _records.LOG_FILES["stage_impression"],
            _records.LOG_FILES["vision_review"],
        ),
        responder,
    )
    if set(decision_refs) - known_decisions:
        raise LiaisonError("response.decision_refs include unknown VRP event ids")
    if set(impression_refs) - known_impressions:
        raise LiaisonError("response.impression_refs include unknown VRP event ids")
    questions = _text_list(data["questions_for_user"], "response.questions_for_user")
    if status == "needs_info" and not questions:
        raise LiaisonError("response.needs_info requires questions_for_user")
    return {
        "schema_version": SCHEMA_VERSION,
        "system": SYSTEM,
        "request": _slug(data["request"], "response.request"),
        "responder": responder,
        "status": status,
        "reason": _text(
            data["reason"],
            "response.reason",
            0 if status in {"accepted", "in_progress"} else REASON_MIN_CHARS,
        ),
        "input_hashes": {
            key: normalized_hashes[key] for key in sorted(normalized_hashes)
        },
        "artifacts": artifacts,
        "gate_verdicts": verdicts,
        "decision_refs": decision_refs,
        "impression_refs": impression_refs,
        "questions_for_user": questions,
        "responded_at": _timestamp(data["responded_at"], "response.responded_at"),
    }


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _current_hash(root: Path, relative: str) -> str | None:
    try:
        _, target = _relative(relative, "input", root)
        return _records.tree_sha256(target)
    except (OSError, LiaisonError):
        return None


def _responses(
    root: Path,
    requests: dict[str, dict[str, Any]],
    doc_request_ids: set[str] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    valid: dict[str, dict[str, Any]] = {}
    malformed: list[dict[str, Any]] = []
    doc_request_ids = {
        identifier
        for identifier, request in requests.items()
        if request["target_agent"] == PLUGIN
    } | (doc_request_ids or set())
    for path in sorted((root / LIAISON_DIR).glob(f"*{RESPONSE_SUFFIX}")):
        relative = path.relative_to(root).as_posix()
        stem = path.name[: -len(RESPONSE_SUFFIX)]
        try:
            if path.is_symlink():
                raise LiaisonError("response file may not be a symlink")
            response = validate_response(_read_json(path), root)
            if response["request"] != stem:
                raise LiaisonError(
                    f"response.request must equal the file stem: "
                    f"{response['request']} != {stem}"
                )
            request = requests.get(response["request"])
            if request is None:
                raise LiaisonError(
                    f"response has no matching request: {response['request']}"
                )
            if response["responder"] != request["target_agent"]:
                raise LiaisonError(
                    f"response.responder must match request.target_agent: "
                    f"{request['target_agent']}"
                )
            if response["status"] == "done" and request["target_agent"] == PLUGIN:
                problems = _done_problems(
                    root,
                    response["artifacts"],
                    response["gate_verdicts"],
                    response["decision_refs"],
                    response["impression_refs"],
                )
                if problems:
                    raise LiaisonError("; ".join(problems))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, LiaisonError) as exc:
            raw: object = None
            if not path.is_symlink():
                try:
                    raw = _read_json(path)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    pass
            responder = raw.get("responder") if isinstance(raw, dict) else None
            request_id = raw.get("request") if isinstance(raw, dict) else None
            if (
                responder == PLUGIN
                or request_id in doc_request_ids
                or stem in doc_request_ids
            ):
                malformed.append({"path": relative, "errors": [str(exc)]})
            continue
        valid[response["request"]] = response
    return valid, malformed


def _stale_inputs(
    root: Path, request: dict[str, Any], response: dict[str, Any] | None
) -> list[str]:
    stale: list[str] = []
    current_hashes: dict[str, str] = {}
    for entry in cast(list[dict[str, str]], request["inputs"]):
        relative = entry["path"]
        current = _current_hash(root, relative)
        if current is None or current != entry["sha256"]:
            stale.append(relative)
            continue
        current_hashes[relative] = current
        if response is not None:
            seen = cast(dict[str, str], response["input_hashes"]).get(relative)
            if seen != current:
                stale.append(relative)
    if response is not None:
        response_hashes = cast(dict[str, str], response["input_hashes"])
        stale.extend(sorted(set(response_hashes) - set(current_hashes)))
    return sorted(set(stale))


def _blocked_by(
    root: Path,
    request: dict[str, Any],
    requests: dict[str, dict[str, Any]],
    responses: dict[str, dict[str, Any]],
) -> list[str]:
    blocked: list[str] = []
    for dependency in cast(list[str], request["depends_on"]):
        answer = responses.get(dependency)
        dependency_request = requests.get(dependency)
        if (
            answer is None
            or dependency_request is None
            or answer["status"] not in TERMINAL_STATUSES
            or _stale_inputs(root, dependency_request, answer)
        ):
            blocked.append(dependency)
    return blocked


def ux_inbox(root: Path | None = None) -> dict[str, Any]:
    workspace = workspace_root(root)
    directory = workspace / LIAISON_DIR
    malformed: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    parsed: list[dict[str, Any]] = []
    all_requests: dict[str, dict[str, Any]] = {}
    doc_request_ids: set[str] = set()
    if directory.is_symlink():
        return {
            "ok": True,
            "requests": [],
            "malformed": [
                {
                    "path": LIAISON_DIR.as_posix(),
                    "errors": ["liaison directory is a symlink"],
                }
            ],
            "counts": {},
        }
    for path in (
        sorted(directory.glob(f"*{REQUEST_SUFFIX}")) if directory.is_dir() else []
    ):
        relative = path.relative_to(workspace).as_posix()
        stem = path.name[: -len(REQUEST_SUFFIX)]
        try:
            if path.is_symlink():
                raise LiaisonError("request file may not be a symlink")
            request = validate_request(_read_json(path), stem, workspace)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, LiaisonError) as exc:
            raw: object = None
            if not path.is_symlink():
                try:
                    raw = _read_json(path)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    raw = None
            target = raw.get("target_agent") if isinstance(raw, dict) else None
            if target is None or target == PLUGIN:
                malformed.append({"path": relative, "errors": [str(exc)]})
                doc_request_ids.add(stem)
            continue
        all_requests[request["id"]] = request
        if request["target_agent"] != PLUGIN:
            continue
        doc_request_ids.add(request["id"])
        parsed.append(request)
    responses, malformed_responses = _responses(
        workspace, all_requests, doc_request_ids
    )
    malformed.extend(malformed_responses)
    for request in parsed:
        response = responses.get(request["id"])
        stale = _stale_inputs(workspace, request, response)
        blocked = _blocked_by(workspace, request, all_requests, responses)
        if stale:
            state = "stale"
        elif response is not None:
            state = "answered"
        elif blocked:
            state = "blocked"
        else:
            state = "new"
        requests.append(
            {
                "id": request["id"],
                "path": (LIAISON_DIR / f"{request['id']}{REQUEST_SUFFIX}").as_posix(),
                "state": state,
                "stage": request["stage"],
                "risk": request["risk"],
                "purpose": request["purpose"],
                "expected_deliverables": request["expected_deliverables"],
                "acceptance": request["acceptance"],
                "depends_on": request["depends_on"],
                "response_status": response["status"] if response else None,
                "stale_inputs": stale,
                "blocked_by": blocked,
            }
        )
    counts: dict[str, int] = {}
    for entry in requests:
        state = cast(str, entry["state"])
        counts[state] = counts.get(state, 0) + 1
    return {
        "ok": True,
        "requests": requests,
        "malformed": sorted(malformed, key=lambda item: cast(str, item["path"])),
        "counts": counts,
    }


def _event_ids(root: Path, filenames: tuple[str, ...], agent: str = PLUGIN) -> set[str]:
    found: set[str] = set()
    for filename in filenames:
        path = root / "observations" / agent / filename
        parents = (root / "observations", root / "observations" / agent)
        if any(parent.is_symlink() for parent in parents) or path.is_symlink():
            continue
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and isinstance(record.get("event_id"), str):
                found.add(cast(str, record["event_id"]))
    return found


def _linted_documents(root: Path) -> set[str]:
    """Markdown paths covered by a fresh, passing doc-lint report."""
    covered: set[str] = set()
    work = root / WORK_DIR
    if work.is_symlink() or not work.is_dir():
        return covered
    for directory in sorted(work.iterdir()):
        if directory.is_symlink() or not directory.is_dir():
            continue
        brief = directory / "doc-brief.json"
        report_path = directory / "doc-lint.json"
        if (
            brief.is_symlink()
            or report_path.is_symlink()
            or not brief.is_file()
            or not report_path.is_file()
        ):
            continue
        try:
            report = _read_json(report_path)
            if not isinstance(report, dict):
                continue
            documents = report.get("documents")
            if not isinstance(documents, list):
                continue
            safe_paths = {
                relative
                for entry in documents
                if isinstance(entry, dict) and isinstance(entry.get("path"), str)
                for relative, target in [
                    _relative(entry["path"], "doc-lint path", root)
                ]
                if target.is_file() and target.suffix.lower() == ".md"
            }
            if lint_state(brief, root) != "pass":
                continue
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        covered.update(safe_paths)
    return covered


def _done_problems(
    root: Path,
    artifacts: list[dict[str, str]],
    verdicts: list[dict[str, str]],
    decision_refs: list[str],
    impression_refs: list[str],
) -> list[str]:
    problems: list[str] = []
    if not artifacts:
        problems.append("done needs at least one artifact")
    if not decision_refs:
        problems.append("done needs at least one decision_ref")
    if not impression_refs:
        problems.append("done needs at least one impression_ref")
    if not verdicts:
        problems.append("done needs at least one gate verdict")
    failing = [entry["gate"] for entry in verdicts if entry["verdict"] != "pass"]
    if failing:
        problems.append(
            "done needs every gate to pass; not passing: " + ", ".join(sorted(failing))
        )
    lint_gates = [entry for entry in verdicts if entry["gate"] == LINT_REPORT_GATE]
    if not any(entry["verdict"] == "pass" for entry in lint_gates):
        problems.append(f"done needs a passing {LINT_REPORT_GATE!r} gate verdict")
    else:
        covered = _linted_documents(root)
        markdown: set[str] = set()
        for entry in artifacts:
            target = root / entry["path"]
            if target.is_file() and target.suffix.lower() == ".md":
                markdown.add(entry["path"])
            elif target.is_dir():
                markdown.update(
                    path.relative_to(root).as_posix()
                    for path in target.rglob("*")
                    if path.is_file()
                    and not path.is_symlink()
                    and path.suffix.lower() == ".md"
                )
        unlisted = sorted(markdown - covered)
        if unlisted:
            problems.append(
                "these Markdown artifacts are not in a fresh passing doc-lint report: "
                + ", ".join(unlisted)
            )
    return problems


def ux_respond(payload: object, root: Path | None = None) -> dict[str, Any]:
    workspace = workspace_root(root)
    data = _closed(payload, RESPOND_KEYS, RESPOND_REQUIRED, "response input")
    identifier = _slug(data["request"], "request")
    status = _enum(data["status"], STATUSES, "status")
    request_rel = (LIAISON_DIR / f"{identifier}{REQUEST_SUFFIX}").as_posix()
    _, request_path = _relative(request_rel, "request", workspace, require_exists=False)
    if not request_path.is_file():
        raise LiaisonError(f"unknown request: {identifier}")
    request = validate_request(_read_json(request_path), identifier, workspace)
    if request["target_agent"] != PLUGIN:
        raise LiaisonError(
            f"request {identifier} targets {request['target_agent']}, not {PLUGIN}"
        )

    raw_artifacts = data["artifacts"]
    if not isinstance(raw_artifacts, list):
        raise LiaisonError("artifacts must be a list of workspace paths")
    artifacts: list[dict[str, str]] = []
    for index, raw in enumerate(cast(list[object], raw_artifacts)):
        relative, target = _relative(raw, f"artifacts[{index}]", workspace)
        if any(artifact["path"] == relative for artifact in artifacts):
            raise LiaisonError("artifacts may not contain duplicate paths")
        artifacts.append({"path": relative, "sha256": _records.tree_sha256(target)})
    verdicts: list[dict[str, str]] = []
    raw_verdicts = data["gate_verdicts"]
    if not isinstance(raw_verdicts, list):
        raise LiaisonError("gate_verdicts must be a list")
    for index, raw in enumerate(cast(list[object], raw_verdicts)):
        item = _closed(
            raw, {"gate", "verdict"}, {"gate", "verdict"}, f"gate_verdicts[{index}]"
        )
        verdicts.append(
            {
                "gate": _text(item["gate"], f"gate_verdicts[{index}].gate"),
                "verdict": _enum(
                    item["verdict"], VERDICTS, f"gate_verdicts[{index}].verdict"
                ),
            }
        )
    decision_refs = _text_list(data["decision_refs"], "decision_refs")
    impression_refs = _text_list(data["impression_refs"], "impression_refs")
    questions = _text_list(data["questions_for_user"], "questions_for_user")
    reason = _text(
        data.get("reason", ""),
        "reason",
        0 if status in {"accepted", "in_progress"} else REASON_MIN_CHARS,
    )

    known_decisions = _event_ids(workspace, (_records.LOG_FILES["decision"],))
    unknown_decisions = sorted(set(decision_refs) - known_decisions)
    known_impressions = _event_ids(
        workspace,
        (
            _records.LOG_FILES["stage_impression"],
            _records.LOG_FILES["vision_review"],
        ),
    )
    unknown_impressions = sorted(set(impression_refs) - known_impressions)

    problems: list[str] = []
    if unknown_decisions:
        problems.append(
            "decision_refs not found in observations/doc/decisions.jsonl: "
            + ", ".join(unknown_decisions)
        )
    if unknown_impressions:
        problems.append(
            "impression_refs not found in impressions.jsonl or vision-reviews.jsonl: "
            + ", ".join(unknown_impressions)
        )
    if status == "needs_info" and not questions:
        problems.append("needs_info needs at least one question_for_user")

    input_hashes: dict[str, str] = {}
    missing_inputs: list[str] = []
    stale_inputs: list[str] = []
    for entry in cast(list[dict[str, str]], request["inputs"]):
        relative = entry["path"]
        current = _current_hash(workspace, relative)
        if current is None:
            missing_inputs.append(relative)
            continue
        input_hashes[relative] = current
        if current != entry["sha256"]:
            stale_inputs.append(relative)
    if missing_inputs and status not in {"needs_info", "rejected"}:
        problems.append(
            "these request inputs are missing; answer needs_info or rejected: "
            + ", ".join(sorted(missing_inputs))
        )
    if stale_inputs and status == "done":
        problems.append(
            "these request inputs changed since the request; done is refused: "
            + ", ".join(sorted(stale_inputs))
        )
    if status == "done":
        problems.extend(
            _done_problems(
                workspace, artifacts, verdicts, decision_refs, impression_refs
            )
        )
    if problems:
        return {
            "ok": False,
            "errors": problems,
            "suggestion": "answer with needs_info or rejected and a reason instead",
        }

    response = {
        "schema_version": SCHEMA_VERSION,
        "system": SYSTEM,
        "request": identifier,
        "responder": PLUGIN,
        "status": status,
        "reason": reason,
        "input_hashes": {key: input_hashes[key] for key in sorted(input_hashes)},
        "artifacts": artifacts,
        "gate_verdicts": verdicts,
        "decision_refs": decision_refs,
        "impression_refs": impression_refs,
        "questions_for_user": questions,
        "responded_at": datetime.now().astimezone().isoformat(),
    }
    validate_response(response, workspace)
    response_rel = (LIAISON_DIR / f"{identifier}{RESPONSE_SUFFIX}").as_posix()
    _, path = _relative(response_rel, "response path", workspace, require_exists=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(
                json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "ok": True,
        "path": path.relative_to(workspace).as_posix(),
        "response": response,
        "stale_inputs": sorted(stale_inputs),
    }
