"""Validate a doc brief and lint the documents it targets.

Usage:
    python3 doc_lint.py --brief doc-work/<slug>/doc-brief.json [--root DIR]
                        [--out PATH] [--brief-only] [--no-write]

The brief (doc-brief.json, schema 0.1) is the fact ledger for one
documentation run: product identity, the sources every fact came from, the
questions asked of sibling agents or the user, and the target documents.
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
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import cast

SCHEMA_VERSION = "0.1"
LINTER = "doc_lint.py 0.1.0"
REPORT_NAME = "doc-lint.json"

TARGET_KINDS = ("readme", "user_manual", "technical_reference")
PLANNED_KINDS = frozenset(
    {"quality_plan", "test_report", "risk_assessment", "inspection_record"}
)
SIBLINGS = ("wire", "mech", "circuit", "ux", "bard")
SOURCE_KINDS = frozenset(
    {
        "file",
        "git_log",
        "conversation",
        "user_interview",
        "sibling_agent",
        "sibling_artifact",
    }
)
INQUIRY_STATUSES = frozenset({"answered", "unanswered", "not_available"})
LANGUAGES = frozenset({"ja", "en"})

TOP_KEYS = frozenset(
    {
        "artifact_kind",
        "schema_version",
        "language",
        "product",
        "targets",
        "sources",
        "facts",
        "inquiries",
        "open_questions",
    }
)
PRODUCT_KEYS = frozenset(
    {
        "name",
        "tagline",
        "summary",
        "audience",
        "problem",
        "value",
        "vision",
        "vision_source",
    }
)

MERMAID_TYPES = frozenset(
    {
        "flowchart",
        "graph",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "erDiagram",
        "journey",
        "gantt",
        "pie",
        "mindmap",
        "timeline",
        "quadrantChart",
        "gitGraph",
        "requirementDiagram",
        "C4Context",
        "C4Container",
        "block-beta",
        "architecture-beta",
        "sankey-beta",
        "xychart-beta",
    }
)

QUICKSTART_ALIASES = (
    "quick start",
    "quickstart",
    "getting started",
    "クイックスタート",
    "はじめ",
)
USAGE_ALIASES = ("usage", "how to use", "using", "使い方", "操作", "使用方法")
TROUBLE_ALIASES = (
    "troubleshoot",
    "faq",
    "problem",
    "トラブル",
    "困った",
    "よくある質問",
    "故障",
)
ARCH_ALIASES = (
    "architecture",
    "system overview",
    "design",
    "アーキテクチャ",
    "構成",
    "設計",
)
INTERFACE_ALIASES = (
    "interface",
    "api",
    "cli",
    "protocol",
    "specification",
    "インターフェース",
    "インタフェース",
    "仕様",
    "プロトコル",
)
DEV_ALIASES = (
    "development",
    "build",
    "testing",
    "contributing",
    "開発",
    "ビルド",
    "テスト",
)

MAX_QUICKSTART_STEPS = 7
PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|FIXME|XXX)\b|lorem ipsum|<placeholder>|要確認|未定|（仮）",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s{0,3}(```+|~~~+)\s*([\w-]*)")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
ORDERED_ITEM_RE = re.compile(r"^(\d+)[.)]\s+\S")


class BriefError(Exception):
    """The brief file cannot be read at all."""


@dataclass
class Heading:
    level: int
    text: str
    line: int


@dataclass
class Fence:
    lang: str
    body: list[str]
    line: int


@dataclass
class ParsedDoc:
    headings: list[Heading] = field(default_factory=list)
    fences: list[Fence] = field(default_factory=list)
    prose: list[tuple[int, str]] = field(default_factory=list)
    unclosed_fence_line: int | None = None


@dataclass
class Target:
    kind: str
    path: str


def _is_str(value: object, lo: int = 1, hi: int = 4000) -> bool:
    return isinstance(value, str) and lo <= len(value.strip()) <= hi


def _as_dict(value: object) -> dict[str, object] | None:
    return cast(dict[str, object], value) if isinstance(value, dict) else None


def _as_list(value: object) -> list[object] | None:
    return cast(list[object], value) if isinstance(value, list) else None


def _safe_rel_path(value: str) -> bool:
    if not value or "\\" in value or value.startswith("/"):
        return False
    parts = PurePosixPath(value).parts
    return ".." not in parts and not re.match(r"^[A-Za-z]:", value)


def _check_str_list(
    value: object, label: str, lo: int, hi: int, problems: list[str]
) -> None:
    items = _as_list(value)
    if items is None or not lo <= len(items) <= hi:
        problems.append(f"{label}: must be a list of {lo}..{hi} strings")
        return
    for i, item in enumerate(items):
        if not _is_str(item, 1, 400):
            problems.append(f"{label}[{i}]: must be a non-empty string (<=400)")


def validate_brief(brief: object) -> tuple[list[str], list[Target]]:
    """Return (problems, targets). An empty problem list means valid."""
    problems: list[str] = []
    targets: list[Target] = []
    top = _as_dict(brief)
    if top is None:
        return ["brief: top level must be a JSON object"], targets
    for key in sorted(set(top) - TOP_KEYS):
        problems.append(f"{key}: unknown top-level key")
    if top.get("artifact_kind") != "doc_brief":
        problems.append('artifact_kind: must be "doc_brief"')
    if top.get("schema_version") != SCHEMA_VERSION:
        problems.append(f'schema_version: must be "{SCHEMA_VERSION}"')
    if top.get("language") not in LANGUAGES:
        problems.append('language: must be "ja" or "en"')

    sources: dict[str, str] = {}
    source_agents: dict[str, str] = {}
    raw_sources = _as_list(top.get("sources"))
    if raw_sources is None or not raw_sources:
        problems.append("sources: must be a non-empty list")
        raw_sources = []
    for i, raw in enumerate(raw_sources):
        src = _as_dict(raw)
        label = f"sources[{i}]"
        if src is None:
            problems.append(f"{label}: must be an object")
            continue
        sid = src.get("id")
        kind = src.get("kind")
        if not isinstance(sid, str) or not re.fullmatch(r"S\d+", sid):
            problems.append(f"{label}.id: must match S<number>")
            continue
        if sid in sources:
            problems.append(f"{label}.id: duplicate {sid}")
            continue
        if not isinstance(kind, str) or kind not in SOURCE_KINDS:
            problems.append(f"{label}.kind: must be one of {sorted(SOURCE_KINDS)}")
            continue
        if not _is_str(src.get("ref"), 1, 400):
            problems.append(f"{label}.ref: must be a non-empty string")
        agent = src.get("agent")
        if kind in ("sibling_agent", "sibling_artifact"):
            if agent not in SIBLINGS:
                problems.append(f"{label}.agent: must be one of {list(SIBLINGS)}")
            else:
                source_agents[sid] = cast(str, agent)
        elif agent is not None:
            problems.append(f"{label}.agent: only allowed for sibling sources")
        sources[sid] = kind

    product = _as_dict(top.get("product"))
    if product is None:
        problems.append("product: must be an object")
    else:
        for key in sorted(set(product) - PRODUCT_KEYS):
            problems.append(f"product.{key}: unknown key")
        if not _is_str(product.get("name"), 1, 80):
            problems.append("product.name: must be a string of 1..80 chars")
        if not _is_str(product.get("tagline"), 1, 140):
            problems.append("product.tagline: must be a string of 1..140 chars")
        if not _is_str(product.get("summary"), 1, 1200):
            problems.append("product.summary: must be a string of 1..1200 chars")
        if not _is_str(product.get("problem"), 1, 800):
            problems.append("product.problem: must be a string of 1..800 chars")
        _check_str_list(product.get("audience"), "product.audience", 1, 6, problems)
        _check_str_list(product.get("value"), "product.value", 1, 6, problems)
        has_vision = "vision" in product
        has_vision_source = "vision_source" in product
        if has_vision != has_vision_source:
            problems.append("product.vision: vision and vision_source go together")
        elif has_vision:
            if not _is_str(product.get("vision"), 1, 1200):
                problems.append("product.vision: must be a string of 1..1200 chars")
            vsrc = product.get("vision_source")
            if not isinstance(vsrc, str) or sources.get(vsrc) != "user_interview":
                problems.append(
                    "product.vision_source: must reference a user_interview source"
                    " (the maker's intent is never inferred)"
                )

    raw_targets = _as_list(top.get("targets"))
    if raw_targets is None or not 1 <= len(raw_targets) <= len(TARGET_KINDS):
        problems.append(f"targets: must be a list of 1..{len(TARGET_KINDS)} targets")
        raw_targets = []
    seen_kinds: set[str] = set()
    seen_paths: set[str] = set()
    for i, raw in enumerate(raw_targets):
        tgt = _as_dict(raw)
        label = f"targets[{i}]"
        if tgt is None:
            problems.append(f"{label}: must be an object")
            continue
        kind = tgt.get("kind")
        path = tgt.get("path")
        if isinstance(kind, str) and kind in PLANNED_KINDS:
            problems.append(
                f"{label}.kind: {kind} is a planned quality-document kind and is"
                " not supported by schema 0.1"
            )
            continue
        if not isinstance(kind, str) or kind not in TARGET_KINDS:
            problems.append(f"{label}.kind: must be one of {list(TARGET_KINDS)}")
            continue
        if not isinstance(path, str) or not _safe_rel_path(path):
            problems.append(f"{label}.path: must be a relative path inside the root")
            continue
        if not path.endswith(".md"):
            problems.append(f"{label}.path: must end with .md")
            continue
        if kind in seen_kinds:
            problems.append(f"{label}.kind: duplicate {kind}")
            continue
        if path in seen_paths:
            problems.append(f"{label}.path: duplicate {path}")
            continue
        seen_kinds.add(kind)
        seen_paths.add(path)
        targets.append(Target(kind, path))

    raw_facts = _as_list(top.get("facts"))
    if raw_facts is None or not raw_facts:
        problems.append("facts: must be a non-empty list")
        raw_facts = []
    fact_ids: set[str] = set()
    for i, raw in enumerate(raw_facts):
        fact = _as_dict(raw)
        label = f"facts[{i}]"
        if fact is None:
            problems.append(f"{label}: must be an object")
            continue
        fid = fact.get("id")
        if not isinstance(fid, str) or not re.fullmatch(r"F\d+", fid):
            problems.append(f"{label}.id: must match F<number>")
        elif fid in fact_ids:
            problems.append(f"{label}.id: duplicate {fid}")
        else:
            fact_ids.add(fid)
        if not _is_str(fact.get("text"), 1, 800):
            problems.append(f"{label}.text: must be a string of 1..800 chars")
        refs = _as_list(fact.get("sources"))
        if refs is None or not refs:
            problems.append(f"{label}.sources: every fact needs at least one source")
            continue
        for ref in refs:
            if not isinstance(ref, str) or ref not in sources:
                problems.append(f"{label}.sources: unknown source {ref!r}")

    raw_inquiries = _as_list(top.get("inquiries", []))
    if raw_inquiries is None:
        problems.append("inquiries: must be a list")
        raw_inquiries = []
    inquiry_ids: set[str] = set()
    for i, raw in enumerate(raw_inquiries):
        inq = _as_dict(raw)
        label = f"inquiries[{i}]"
        if inq is None:
            problems.append(f"{label}: must be an object")
            continue
        qid = inq.get("id")
        if not isinstance(qid, str) or not re.fullmatch(r"Q\d+", qid):
            problems.append(f"{label}.id: must match Q<number>")
        elif qid in inquiry_ids:
            problems.append(f"{label}.id: duplicate {qid}")
        else:
            inquiry_ids.add(qid)
        to = inq.get("to")
        if to not in (*SIBLINGS, "user"):
            problems.append(f'{label}.to: must be a sibling name or "user"')
            continue
        if not _is_str(inq.get("question"), 1, 800):
            problems.append(f"{label}.question: must be a non-empty string")
        status = inq.get("status")
        if not isinstance(status, str) or status not in INQUIRY_STATUSES:
            allowed = sorted(INQUIRY_STATUSES)
            problems.append(f"{label}.status: must be one of {allowed}")
            continue
        if status != "answered":
            if "answer" in inq or "source" in inq:
                problems.append(f"{label}: answer/source only allowed when answered")
            continue
        if not _is_str(inq.get("answer"), 1, 2000):
            problems.append(f"{label}.answer: required when status is answered")
        src = inq.get("source")
        if not isinstance(src, str) or src not in sources:
            problems.append(f"{label}.source: must reference a known source")
            continue
        if to == "user" and sources[src] != "user_interview":
            problems.append(f"{label}.source: user answers need user_interview")
        if to != "user" and source_agents.get(src) != to:
            problems.append(f"{label}.source: must be a sibling source from {to}")

    if "open_questions" in top:
        _check_str_list(top.get("open_questions"), "open_questions", 0, 50, problems)
    return problems, targets


def parse_markdown(text: str) -> ParsedDoc:
    doc = ParsedDoc()
    fence: Fence | None = None
    marker = ""
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = FENCE_RE.match(line)
        if fence is not None:
            if m and m.group(1)[0] == marker[0] and len(m.group(1)) >= len(marker):
                if not m.group(2):
                    doc.fences.append(fence)
                    fence = None
                    continue
            fence.body.append(line)
            continue
        if m:
            marker = m.group(1)
            fence = Fence(m.group(2), [], lineno)
            continue
        h = HEADING_RE.match(line)
        if h:
            doc.headings.append(Heading(len(h.group(1)), h.group(2).strip(), lineno))
        doc.prose.append((lineno, line))
    if fence is not None:
        doc.unclosed_fence_line = fence.line
    return doc


def _matches(text: str, aliases: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(alias in low for alias in aliases)


def _section(doc: ParsedDoc, aliases: tuple[str, ...]) -> tuple[int, int] | None:
    """Line span (start, end) of the first level-2/3 heading matching aliases."""
    for i, h in enumerate(doc.headings):
        if h.level in (2, 3) and _matches(h.text, aliases):
            end = 10**9
            for nxt in doc.headings[i + 1 :]:
                if nxt.level <= h.level:
                    end = nxt.line
                    break
            return h.line, end
    return None


def _mermaid_problems(doc: ParsedDoc) -> list[str]:
    problems: list[str] = []
    for f in doc.fences:
        if f.lang != "mermaid":
            continue
        body = [
            ln.strip()
            for ln in f.body
            if ln.strip() and not ln.strip().startswith("%%")
        ]
        if not body:
            problems.append(f"line {f.line}: empty mermaid block")
            continue
        head = body[0].split()[0]
        if head not in MERMAID_TYPES:
            problems.append(f"line {f.line}: unknown mermaid diagram type {head!r}")
    return problems


def _diagram_lines(doc: ParsedDoc, doc_path: Path) -> list[int]:
    lines = [f.line for f in doc.fences if f.lang == "mermaid"]
    for lineno, line in doc.prose:
        for m in IMAGE_RE.finditer(line):
            target = m.group(1)
            if target.startswith(("http://", "https://")):
                lines.append(lineno)
            elif (doc_path.parent / target.split("#")[0]).is_file():
                lines.append(lineno)
    return sorted(lines)


def _link_problems(doc: ParsedDoc, doc_path: Path, root: Path) -> list[str]:
    problems: list[str] = []
    for lineno, line in doc.prose:
        for m in LINK_RE.finditer(line):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            rel = target.split("#")[0]
            if not rel:
                continue
            resolved = (doc_path.parent / rel).resolve()
            if not resolved.is_relative_to(root.resolve()):
                problems.append(f"line {lineno}: link leaves the root: {target}")
            elif not resolved.exists():
                problems.append(f"line {lineno}: broken relative link: {target}")
    return problems


def _links_to(doc: ParsedDoc, doc_path: Path, other: Path) -> bool:
    for _lineno, line in doc.prose:
        for m in LINK_RE.finditer(line):
            rel = m.group(1).split("#")[0]
            if rel and (doc_path.parent / rel).resolve() == other.resolve():
                return True
    return False


def lint_document(
    target: Target, root: Path, product_name: str, all_targets: list[Target]
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
            if other.kind != "readme" and not _links_to(doc, path, root / other.path):
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


def build_report(
    brief_path: Path, root: Path, brief_only: bool = False
) -> dict[str, object]:
    brief, brief_digest = load_brief(brief_path)
    brief_problems, targets = validate_brief(brief)
    top = _as_dict(brief) or {}
    product = _as_dict(top.get("product")) or {}
    name = product.get("name")
    product_name = name.strip() if isinstance(name, str) else ""
    documents: list[dict[str, object]] = []
    if not brief_only:
        for target in targets:
            problems, digest = lint_document(target, root, product_name, targets)
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
