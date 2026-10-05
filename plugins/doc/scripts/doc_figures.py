"""Inventory and inspect figures in documentation workspace targets."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import mimetypes
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlsplit

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
LINT_SCRIPTS = PLUGIN_ROOT / "skills" / "doc-lint" / "scripts"
if str(LINT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(LINT_SCRIPTS))
HOOK_SCRIPTS = PLUGIN_ROOT / "hooks" / "scripts"
if str(HOOK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(HOOK_SCRIPTS))

from _provenance import (  # type: ignore[reportMissingImports]  # noqa: E402
    actor,
    event_id,
    events_path,
    next_sequence,
)
from doc_brief import (  # type: ignore[reportMissingImports]  # noqa: E402
    Target,
    validate_brief,
)
from doc_lint import build_report  # type: ignore[reportMissingImports]  # noqa: E402

IMAGE_OBSERVATIONS = Path("observations/doc/image-observations.jsonl")
VISION_REVIEWS = Path("observations/doc/vision-reviews.jsonl")
VIEW_TOOL_NAME = "doc_view_figure"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SUPPORTED_MIMES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_MARKDOWN_IMAGE = re.compile(
    r"!\[([^\]]*)\]\(\s*(?:<([^>]+)>|([^\s)]+))"
    r"(?:\s+(['\"]).*?\4)?\s*\)"
)
_INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)*?\1")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _workspace_root(root: Path | None = None) -> Path:
    return (
        root or Path(os.environ.get("OPENHANDS_PROJECT_DIR") or Path.cwd())
    ).resolve()


def _inside_workspace(path: Path, root: Path, label: str) -> tuple[str, Path]:
    candidate = path if path.is_absolute() else root / path
    try:
        lexical_relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} is outside the workspace: {path}") from exc
    current = root
    for part in lexical_relative.parts:
        if part == "..":
            current = current.parent
            continue
        if part == ".":
            continue
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label} traverses a symlink: {path}")
    try:
        resolved = candidate.resolve(strict=False)
        relative = resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"{label} is outside the workspace: {path}") from exc
    return relative.as_posix(), resolved


def _brief_targets(brief: str | Path, root: Path) -> tuple[str, Path, list[Target]]:
    brief_rel, brief_path = _inside_workspace(Path(brief), root, "brief")
    if not brief_path.is_file():
        raise ValueError(f"brief does not exist: {brief_rel}")
    try:
        data: object = json.loads(brief_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"brief is not readable JSON: {brief_rel}") from exc
    problems, targets = validate_brief(data)
    if problems:
        raise ValueError("invalid brief: " + "; ".join(problems))
    return brief_rel, brief_path, targets


def _visible_lines(text: str) -> tuple[list[str], int]:
    lines = text.splitlines()
    visible: list[str] = []
    fence_char: str | None = None
    fence_size = 0
    mermaid_blocks = 0
    for line in lines:
        match = _FENCE.match(line)
        if match:
            marker, info = match.groups()
            if fence_char is None:
                fence_char = marker[0]
                fence_size = len(marker)
                if re.match(r"^\s*mermaid(?:\s|$)", info, re.IGNORECASE):
                    mermaid_blocks += 1
            elif marker[0] == fence_char and len(marker) >= fence_size:
                fence_char = None
                fence_size = 0
            visible.append("")
            continue
        if fence_char is not None:
            visible.append("")
            continue
        visible.append(_INLINE_CODE.sub(lambda m: " " * len(m.group()), line))
    return visible, mermaid_blocks


class _HTMLImages(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[tuple[int, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        values = dict(attrs)
        source = values.get("src")
        if source:
            self.images.append(
                (self.getpos()[0], html.unescape(values.get("alt") or ""), source)
            )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _image_reference(
    source: str, document: Path, root: Path
) -> tuple[str, Path | None]:
    clean = html.unescape(source.strip())
    parsed = urlsplit(clean)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return clean, None
    decoded = unquote(parsed.path)
    ref = (
        Path(decoded.lstrip("/"))
        if decoded.startswith("/")
        else document.parent / decoded
    )
    try:
        relative, path = _inside_workspace(ref, root, "image")
    except ValueError:
        return clean, None
    return relative, path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(cast(dict[str, Any], value))
    return records


def _review_ids(root: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    by_hash: dict[str, list[str]] = {}
    observation_hashes: dict[str, str] = {}
    for observation in _read_jsonl(root / IMAGE_OBSERVATIONS):
        event = observation.get("event_id")
        digest = observation.get("image_sha256")
        if isinstance(event, str) and isinstance(digest, str):
            observation_hashes[event] = digest
    for review in _read_jsonl(root / VISION_REVIEWS):
        event = review.get("event_id")
        digest = review.get("image_sha256")
        if not isinstance(digest, str):
            source_event = review.get("source_event_id")
            digest = (
                observation_hashes.get(source_event)
                if isinstance(source_event, str)
                else None
            )
        if isinstance(digest, str) and isinstance(event, str):
            by_hash.setdefault(digest, []).append(event)
    return by_hash, observation_hashes


def _mime(path: Path) -> str | None:
    return (
        SUPPORTED_MIMES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0]
    )


def _inventory_entry(
    document: Path,
    line: int,
    alt: str,
    source: str,
    root: Path,
    reviews: dict[str, list[str]],
) -> dict[str, object]:
    relative, image = _image_reference(source, document, root)
    exists = image is not None and image.is_file()
    digest = (
        hashlib.sha256(image.read_bytes()).hexdigest()
        if exists and image is not None
        else None
    )
    event_ids = reviews.get(digest, []) if digest else []
    try:
        document_rel = document.resolve().relative_to(root).as_posix()
    except (OSError, ValueError):
        document_rel = document.as_posix()
    mime_path = image if image is not None else Path(relative)
    return {
        "document": document_rel,
        "line": line,
        "alt": alt,
        "path": relative,
        "exists": exists,
        "sha256": digest,
        "mime": _mime(mime_path),
        "reviewed": bool(event_ids),
        "review_event_ids": sorted(event_ids),
    }


def figures(brief: str | Path, root: Path | None = None) -> dict[str, Any]:
    workspace = _workspace_root(root)
    brief_rel, _, targets = _brief_targets(brief, workspace)
    reviews, _ = _review_ids(workspace)
    documents: list[dict[str, object]] = []
    entries: list[dict[str, object]] = []
    for target in targets:
        relative, path = _inside_workspace(Path(target.path), workspace, "document")
        document_result: dict[str, object] = {
            "document": relative,
            "mermaid_blocks": 0,
        }
        if not path.is_file():
            document_result["error"] = "target document does not exist"
            documents.append(document_result)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            document_result["error"] = f"target document is unreadable: {exc}"
            documents.append(document_result)
            continue
        visible, mermaid_count = _visible_lines(text)
        document_result["mermaid_blocks"] = mermaid_count
        markdown_images: list[tuple[int, str, str]] = []
        for line_number, line in enumerate(visible, start=1):
            for match in _MARKDOWN_IMAGE.finditer(line):
                source = match.group(2) or match.group(3) or ""
                markdown_images.append((line_number, match.group(1), source))
        html_parser = _HTMLImages()
        html_parser.feed("\n".join(visible))
        for line_number, alt, source in markdown_images + html_parser.images:
            entries.append(
                _inventory_entry(path, line_number, alt, source, workspace, reviews)
            )
        documents.append(document_result)
    return {
        "ok": True,
        "brief": brief_rel,
        "documents": documents,
        "figures": entries,
    }


def figure_metadata(path: str | Path, root: Path | None = None) -> dict[str, Any]:
    workspace = _workspace_root(root)
    relative, image = _inside_workspace(Path(path), workspace, "image")
    if not image.is_file():
        return {"ok": False, "errors": [f"image does not exist: {relative}"]}
    return {
        "ok": True,
        "path": relative,
        "exists": True,
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "mime": _mime(image),
        "size_bytes": image.stat().st_size,
    }


def _append_image_observation(
    root: Path, image: Path, digest: str, tool_call_id: object
) -> str:
    payload: dict[str, Any] = {
        "working_dir": str(root),
        "tool_name": VIEW_TOOL_NAME,
    }
    if tool_call_id is not None:
        payload["tool_call_id"] = tool_call_id
    log = events_path(payload, "DOC_IMAGE_OBSERVATIONS", IMAGE_OBSERVATIONS)
    log.parent.mkdir(parents=True, exist_ok=True)
    sequence = next_sequence(log)
    identity = {
        "sequence": sequence,
        "tool_name": VIEW_TOOL_NAME,
        "image_path": str(image),
        "image_sha256": digest,
    }
    identifier = event_id(identity)
    record = {
        **identity,
        "event_id": identifier,
        "recorded_at": datetime.now(UTC).isoformat(),
        "session_id": None,
        "actor": actor(payload),
        "tool_call_id": tool_call_id,
    }
    with log.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        stream.write("\n")
    return identifier


def view_figure(
    path: str | Path,
    root: Path | None = None,
    *,
    tool_call_id: object = None,
) -> dict[str, Any]:
    workspace = _workspace_root(root)
    try:
        relative, image = _inside_workspace(Path(path), workspace, "image")
    except ValueError as exc:
        return {
            "ok": False,
            "errors": [str(exc)],
            "content": [{"type": "text", "text": str(exc)}],
        }
    if image.suffix.lower() == ".svg":
        message = (
            "SVG cannot be returned inline; ask the owning sister to render it to PNG "
            "and retry with that image."
        )
        return {
            "ok": False,
            "errors": [message],
            "content": [{"type": "text", "text": message}],
        }
    mime = SUPPORTED_MIMES.get(image.suffix.lower())
    if mime is None:
        message = "only PNG, JPEG, GIF, and WebP images can be viewed inline"
        return {
            "ok": False,
            "errors": [message],
            "content": [{"type": "text", "text": message}],
        }
    if not image.is_file():
        message = f"image does not exist: {relative}"
        return {
            "ok": False,
            "errors": [message],
            "content": [{"type": "text", "text": message}],
        }
    size = image.stat().st_size
    if size > MAX_IMAGE_BYTES:
        message = f"image exceeds the 5 MiB limit: {relative}"
        return {
            "ok": False,
            "errors": [message],
            "content": [{"type": "text", "text": message}],
        }
    data = image.read_bytes()
    valid_signature = {
        "image/png": data.startswith(_PNG_SIGNATURE),
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/gif": data.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }[mime]
    if not valid_signature:
        message = f"file content does not match its {mime} extension: {relative}"
        return {
            "ok": False,
            "errors": [message],
            "content": [{"type": "text", "text": message}],
        }
    digest = hashlib.sha256(data).hexdigest()
    try:
        identifier = _append_image_observation(workspace, image, digest, tool_call_id)
    except OSError as exc:
        message = f"could not record image observation: {exc}"
        return {
            "ok": False,
            "errors": [message],
            "content": [{"type": "text", "text": message}],
        }
    metadata = {
        "path": relative,
        "sha256": digest,
        "event_id": identifier,
        "next": "record doc_record_vision_review with source_event_id or image_path",
    }
    return {
        "ok": True,
        **metadata,
        "text": json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
        "image": {
            "mime_type": mime,
            "data": base64.b64encode(data).decode("ascii"),
        },
    }


def lint(brief: str, mode: str = "full") -> dict[str, Any]:
    root = _workspace_root()
    _, brief_path, _ = _brief_targets(brief, root)
    if mode not in {"full", "brief_only"}:
        raise ValueError("mode must be 'full' or 'brief_only'")
    if mode == "brief_only":
        return {"ok": True, "report": build_report(brief_path, root, brief_only=True)}
    script = LINT_SCRIPTS / "doc_lint.py"
    result = subprocess.run(
        [sys.executable, str(script), "--brief", str(brief_path), "--root", str(root)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode not in {0, 1}:
        return {
            "ok": False,
            "errors": [
                result.stderr.strip() or result.stdout.strip() or "doc-lint failed"
            ],
        }
    report_path = brief_path.with_name("doc-lint.json")
    try:
        report: object = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "errors": [f"doc-lint report unavailable: {exc}"]}
    if not isinstance(report, dict):
        return {"ok": False, "errors": ["doc-lint report is not a JSON object"]}
    return {"ok": True, "report": report}
