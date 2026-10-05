"""Validate a doc brief and lint the documents it targets.

Usage:
    python3 doc_lint.py --brief doc-work/<slug>/doc-brief.json [--root DIR]
                        [--out PATH] [--brief-only] [--no-write]

The brief (doc-brief.json, schema 0.1 or 0.2) is the fact ledger for one
documentation run: product identity, the sources every fact came from, the
questions asked of sister agents or the user, and the target documents.
Schema 0.2 adds the marketing/launch kinds and the `launch` block that ties
every audience, message, and call to action to facts.
Target paths are resolved against --root (default: current directory, i.e.
the workspace root).

Exit codes:
    0  brief valid and every target document passes
    1  brief invalid or at least one document fails (report still written)
    2  usage error or unreadable brief (nothing written)

The report (default: doc-lint.json next to the brief) is deterministic: no
timestamps, sorted keys, sha256 of the brief and every target, so a Stop hook
can tell whether it is still fresh. Only this script may write it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import cast

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
_HOOKS_DIR = str(Path(__file__).resolve().parents[3] / "hooks" / "scripts")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

import _records  # type: ignore[reportMissingImports]  # noqa: E402
from doc_brief import (  # noqa: E402
    AUDIENCE_KEYS,
    BRIEF_VERSIONS,
    CHANNEL_KEYS,
    CHANNEL_KINDS,
    CTA_KEYS,
    INQUIRY_STATUSES,
    LANGUAGES,
    LAUNCH_KEYS,
    LAUNCH_KINDS,
    MESSAGE_KEYS,
    NUMBER_GROUNDED_KINDS,
    PLANNED_KINDS,
    PRODUCT_DOC_KINDS,
    PRODUCT_KEYS,
    SCHEMA_VERSION,
    SISTERS,
    SOURCE_KINDS,
    TARGET_KINDS,
    TOP_KEYS,
    BriefError,
    Target,
    _as_dict,
    _as_list,
    _check_ids,
    _check_str_list,
    _is_str,
    _safe_rel_path,
    _validate_launch,
    validate_brief,
)
from doc_markdown import (  # noqa: E402
    ABOUT_ALIASES,
    ARCH_ALIASES,
    AUDIENCE_ALIASES,
    AUDIO_COLUMN_ALIASES,
    CHANNEL_ALIASES,
    CHECKLIST_ALIASES,
    CONTACT_ALIASES,
    CTA_ALIASES,
    DEV_ALIASES,
    FEATURE_ALIASES,
    FENCE_RE,
    HEADING_RE,
    IMAGE_RE,
    INLINE_CODE_RE,
    INTERFACE_ALIASES,
    LINK_RE,
    LINK_TARGET_RE,
    LIST_MARKER_RE,
    MAX_QUICKSTART_STEPS,
    MERMAID_TYPES,
    MESSAGE_ALIASES,
    MIN_CHECKLIST_ITEMS,
    NUMBER_RE,
    ORDERED_ITEM_RE,
    PLACEHOLDER_RE,
    QUICKSTART_ALIASES,
    RATIONALE_ALIASES,
    SUPERLATIVE_RE,
    TABLE_SEPARATOR_RE,
    TASK_ITEM_RE,
    TIME_COLUMN_ALIASES,
    TROUBLE_ALIASES,
    USAGE_ALIASES,
    VISUAL_COLUMN_ALIASES,
    BriefContext,
    Fence,
    Heading,
    ParsedDoc,
    _claim_problems,
    _claim_text,
    _contains,
    _diagram_lines,
    _launch_problems,
    _link_problems,
    _links_to,
    _matches,
    _mermaid_problems,
    _normalize,
    _section,
    _section_lines,
    _table_headers,
    parse_markdown,
)

__all__ = [
    "ABOUT_ALIASES",
    "ARCH_ALIASES",
    "AUDIENCE_ALIASES",
    "AUDIENCE_KEYS",
    "AUDIO_COLUMN_ALIASES",
    "BRIEF_VERSIONS",
    "BriefContext",
    "BriefError",
    "CHANNEL_ALIASES",
    "CHANNEL_KEYS",
    "CHANNEL_KINDS",
    "CHECKLIST_ALIASES",
    "CONTACT_ALIASES",
    "CTA_ALIASES",
    "CTA_KEYS",
    "DEV_ALIASES",
    "FEATURE_ALIASES",
    "FENCE_RE",
    "Fence",
    "HEADING_RE",
    "Heading",
    "IMAGE_RE",
    "INLINE_CODE_RE",
    "INQUIRY_STATUSES",
    "INTERFACE_ALIASES",
    "LANGUAGES",
    "LAUNCH_KEYS",
    "LAUNCH_KINDS",
    "LINK_RE",
    "LINK_TARGET_RE",
    "LINTER",
    "LIST_MARKER_RE",
    "MAX_QUICKSTART_STEPS",
    "MERMAID_TYPES",
    "MESSAGE_ALIASES",
    "MESSAGE_KEYS",
    "MIN_CHECKLIST_ITEMS",
    "NUMBER_GROUNDED_KINDS",
    "NUMBER_RE",
    "ORDERED_ITEM_RE",
    "PLACEHOLDER_RE",
    "PLANNED_KINDS",
    "PRODUCT_DOC_KINDS",
    "PRODUCT_KEYS",
    "ParsedDoc",
    "QUICKSTART_ALIASES",
    "RATIONALE_ALIASES",
    "REPORT_NAME",
    "SCHEMA_VERSION",
    "SISTERS",
    "SOURCE_KINDS",
    "SUPERLATIVE_RE",
    "TABLE_SEPARATOR_RE",
    "TARGET_KINDS",
    "TASK_ITEM_RE",
    "TIME_COLUMN_ALIASES",
    "TOP_KEYS",
    "TROUBLE_ALIASES",
    "Target",
    "USAGE_ALIASES",
    "VISUAL_COLUMN_ALIASES",
    "_as_dict",
    "_as_list",
    "_check_ids",
    "_check_str_list",
    "_claim_problems",
    "_claim_text",
    "_contains",
    "_diagram_lines",
    "_is_str",
    "_launch_problems",
    "_link_problems",
    "_links_to",
    "_matches",
    "_mermaid_problems",
    "_normalize",
    "_safe_rel_path",
    "_section",
    "_section_lines",
    "_strings",
    "_table_headers",
    "_validate_launch",
    "brief_context",
    "build_report",
    "lint_document",
    "load_brief",
    "main",
    "parse_markdown",
    "validate_brief",
]

LINTER = "doc_lint.py 0.2.0"

REPORT_NAME = "doc-lint.json"


def lint_document(
    target: Target,
    root: Path,
    product_name: str,
    all_targets: list[Target],
    ctx: BriefContext | None = None,
    *,
    require_rationale: bool = False,
) -> tuple[list[str], str | None]:
    """Return (problems, sha256-or-None) for one target document."""
    path = root / target.path
    if not path.is_file():
        return ["missing: target document does not exist"], None
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ["encoding: document is not valid UTF-8"], digest
    if not text.strip():
        return ["empty: document has no content"], digest
    doc = parse_markdown(text)
    problems: list[str] = []
    if doc.unclosed_fence_line is not None:
        problems.append(f"line {doc.unclosed_fence_line}: unclosed code fence")
    if not doc.headings or doc.headings[0].level != 1:
        problems.append("structure: the first heading must be a single H1 title")
    if sum(1 for h in doc.headings if h.level == 1) > 1:
        problems.append("structure: more than one H1 heading")
    for lineno, line in doc.prose:
        if PLACEHOLDER_RE.search(line):
            problems.append(f"line {lineno}: placeholder text left in document")
    if product_name and product_name.lower() not in text.lower():
        problems.append(f"identity: product name {product_name!r} never appears")
    problems.extend(_mermaid_problems(doc))
    problems.extend(_link_problems(doc, path, root))
    diagrams = _diagram_lines(doc, path)

    if target.kind == "readme":
        quick = _section(doc, QUICKSTART_ALIASES)
        if quick is None:
            problems.append("readme: no Quick start section (H2/H3)")
        else:
            start, end = quick
            before = [h for h in doc.headings if h.level == 2 and h.line < start]
            if not before:
                problems.append(
                    "readme: the product explanation (an H2 section) must come"
                    " before the Quick start"
                )
            if not any(line < start for line in diagrams):
                problems.append(
                    "readme: no diagram (mermaid block or image) before the Quick start"
                )
            steps = [
                ln
                for lineno, ln in doc.prose
                if start < lineno < end and ORDERED_ITEM_RE.match(ln)
            ]
            if len(steps) < 2:
                problems.append("readme: Quick start needs >=2 numbered steps")
            elif len(steps) > MAX_QUICKSTART_STEPS:
                problems.append(
                    f"readme: Quick start has {len(steps)} steps"
                    f" (max {MAX_QUICKSTART_STEPS}); move detail to the user manual"
                )
        for other in all_targets:
            if (
                other.kind in PRODUCT_DOC_KINDS
                and other.kind != "readme"
                and not (_links_to(doc, path, root / other.path))
            ):
                problems.append(f"readme: must link to the {other.kind} ({other.path})")
    elif target.kind == "user_manual":
        if _section(doc, USAGE_ALIASES) is None:
            problems.append("user_manual: no usage section (H2/H3)")
        if _section(doc, TROUBLE_ALIASES) is None:
            problems.append("user_manual: no troubleshooting / FAQ section (H2/H3)")
    elif target.kind == "technical_reference":
        arch = _section(doc, ARCH_ALIASES)
        if arch is None:
            problems.append("technical_reference: no architecture section (H2/H3)")
        elif not any(arch[0] < line < arch[1] for line in diagrams):
            problems.append("technical_reference: architecture section has no diagram")
        if _section(doc, INTERFACE_ALIASES) is None:
            problems.append("technical_reference: no interface / spec section")
        if _section(doc, DEV_ALIASES) is None:
            problems.append("technical_reference: no development / test section")
        if require_rationale and _section(doc, RATIONALE_ALIASES) is None:
            problems.append("technical_reference: no design-rationale section")
    elif target.kind in LAUNCH_KINDS:
        context = ctx or BriefContext(product_name=product_name)
        problems.extend(_launch_problems(doc, text, target, context, diagrams))
    return problems, digest


def load_brief(path: Path) -> tuple[object, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BriefError(f"{path}: cannot read brief ({exc.strerror})") from exc
    try:
        return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BriefError(f"{path}: brief is not valid UTF-8 JSON ({exc})") from exc


def _strings(value: object, key: str) -> list[str]:
    out: list[str] = []
    for item in _as_list(value) or []:
        entry = _as_dict(item)
        text = entry.get(key) if entry is not None else None
        if isinstance(text, str) and text.strip():
            out.append(text.strip())
    return out


def brief_context(top: dict[str, object], product_name: str) -> BriefContext:
    product = _as_dict(top.get("product")) or {}
    tagline = product.get("tagline")
    launch = _as_dict(top.get("launch")) or {}
    messages: list[tuple[str, list[str]]] = []
    for item in _as_list(launch.get("messages")) or []:
        msg = _as_dict(item)
        if msg is None:
            continue
        text = msg.get("text")
        kinds = [k for k in _as_list(msg.get("targets")) or [] if isinstance(k, str)]
        if isinstance(text, str) and text.strip():
            messages.append((text.strip(), kinds))
    cta = _as_dict(launch.get("call_to_action")) or {}
    cta_text = cta.get("text")
    return BriefContext(
        product_name=product_name,
        tagline=tagline.strip() if isinstance(tagline, str) else "",
        fact_texts=_strings(top.get("facts"), "text"),
        audiences=_strings(launch.get("audiences"), "name"),
        messages=messages,
        call_to_action=cta_text.strip() if isinstance(cta_text, str) else "",
    )


def _source_target(root: Path, ref: str) -> tuple[Path | None, str | None]:
    if not _safe_rel_path(ref):
        return None, "ref must be a relative workspace path"
    base = root.resolve()
    relative = Path(*PurePosixPath(ref).parts)
    current = base
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return None, "ref traverses a symlink"
    try:
        target = current.resolve(strict=True)
        target.relative_to(base)
    except FileNotFoundError:
        return None, "ref does not exist"
    except (OSError, ValueError):
        return None, "ref is outside the workspace"
    return target, None


def _source_problems(root: Path, brief: dict[str, object]) -> list[str]:
    problems: list[str] = []
    for raw in _as_list(brief.get("sources")) or []:
        source = _as_dict(raw)
        if source is None:
            continue
        source_id = source.get("id")
        label = f"source {source_id}" if isinstance(source_id, str) else "source"
        kind = source.get("kind")
        ref = source.get("ref")
        if not isinstance(ref, str):
            continue
        if kind == "file" and isinstance(source.get("sha256"), str):
            ref = ref.partition("#")[0]
        if kind not in {"file", "sister_artifact", "sister_record"}:
            continue
        target, path_error = _source_target(root, ref)
        if path_error is not None or target is None:
            problems.append(f"{label} {path_error}: {ref}")
            continue
        if kind == "sister_record":
            if not target.is_file():
                problems.append(f"{label} record log is not a file: {ref}")
                continue
            event_id = source.get("event_id")
            agent = source.get("agent")
            found = False
            wrong_plugin = False
            try:
                lines = target.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                problems.append(f"{label} record log cannot be read: {ref}")
                continue
            for line in lines:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or record.get("event_id") != event_id:
                    continue
                if record.get("plugin") == agent:
                    found = True
                    break
                wrong_plugin = True
            if not found:
                if wrong_plugin:
                    problems.append(
                        f"{label} event {event_id} plugin does not match {agent}"
                    )
                else:
                    problems.append(f"{label} event {event_id} not found in {ref}")
            continue
        if kind == "sister_artifact" and not (target.is_file() or target.is_dir()):
            problems.append(f"{label} is not a file or directory: {ref}")
            continue
        digest = source.get("sha256")
        if not isinstance(digest, str):
            continue
        if not (target.is_file() or target.is_dir()):
            problems.append(f"{label} is not a file or directory: {ref}")
            continue
        if _records.tree_sha256(target) != digest:
            problems.append(f"{label} changed since the brief was written")
    return problems


def build_report(
    brief_path: Path, root: Path, brief_only: bool = False
) -> dict[str, object]:
    brief, brief_digest = load_brief(brief_path)
    brief_problems, targets = validate_brief(brief)
    top = _as_dict(brief) or {}
    brief_problems.extend(_source_problems(root, top))
    product = _as_dict(top.get("product")) or {}
    name = product.get("name")
    product_name = name.strip() if isinstance(name, str) else ""
    ctx = brief_context(top, product_name)
    require_rationale = any(
        (_as_dict(raw) or {}).get("kind") == "sister_record"
        for raw in _as_list(top.get("sources")) or []
    )
    documents: list[dict[str, object]] = []
    if not brief_only:
        for target in targets:
            problems, digest = lint_document(
                target,
                root,
                product_name,
                targets,
                ctx,
                require_rationale=require_rationale,
            )
            documents.append(
                {
                    "kind": target.kind,
                    "path": target.path,
                    "sha256": digest,
                    "problems": problems,
                }
            )
    inquiries = _as_list(top.get("inquiries")) or []
    unanswered = sum(
        1
        for raw in inquiries
        if (inq := _as_dict(raw)) is not None and inq.get("status") != "answered"
    )
    open_questions = _as_list(top.get("open_questions")) or []
    failed = bool(brief_problems) or any(d["problems"] for d in documents)
    return {
        "artifact_kind": "doc_lint_report",
        "schema_version": SCHEMA_VERSION,
        "linter": LINTER,
        "mode": "brief_only" if brief_only else "full",
        "verdict": "fail" if failed else "pass",
        "brief": {"path": brief_path.as_posix(), "sha256": brief_digest},
        "brief_problems": brief_problems,
        "documents": documents,
        "unanswered_inquiries": unanswered,
        "open_questions": len(open_questions),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a doc brief and lint the documents it targets."
    )
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--brief-only", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    brief_path = cast(Path, args.brief)
    root = cast(Path, args.root)
    if not root.is_dir():
        print(f"doc-lint: root {root} is not a directory", file=sys.stderr)
        return 2
    try:
        report = build_report(brief_path, root, brief_only=bool(args.brief_only))
    except BriefError as exc:
        print(f"doc-lint: {exc}", file=sys.stderr)
        return 2
    out = cast(Path | None, args.out) or brief_path.with_name(REPORT_NAME)
    if not args.no_write and not args.brief_only:
        out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    for problem in cast(list[str], report["brief_problems"]):
        print(f"brief: {problem}")
    for d in cast(list[dict[str, object]], report["documents"]):
        for problem in cast(list[str], d["problems"]):
            print(f"{d['path']}: {problem}")
    print(
        f"doc-lint: {report['verdict']}"
        f" (unanswered inquiries: {report['unanswered_inquiries']},"
        f" open questions: {report['open_questions']})"
    )
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
