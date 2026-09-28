"""Validate a doc brief and lint the documents it targets.

Usage:
    python3 doc_lint.py --brief doc-work/<slug>/doc-brief.json [--root DIR]
                        [--out PATH] [--brief-only] [--no-write]

The brief (doc-brief.json, schema 0.1 or 0.2) is the fact ledger for one
documentation run: product identity, the sources every fact came from, the
questions asked of sibling agents or the user, and the target documents.
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
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import cast

SCHEMA_VERSION = "0.1"
BRIEF_VERSIONS = ("0.1", "0.2")
LINTER = "doc_lint.py 0.2.0"
REPORT_NAME = "doc-lint.json"

PRODUCT_DOC_KINDS = ("readme", "user_manual", "technical_reference")
LAUNCH_KINDS = ("product_page", "press_release", "demo_script", "launch_plan")
TARGET_KINDS = PRODUCT_DOC_KINDS + LAUNCH_KINDS
NUMBER_GROUNDED_KINDS = frozenset({"product_page", "press_release"})
CHANNEL_KINDS = frozenset(
    {
        "product_page",
        "press",
        "social",
        "video",
        "email",
        "event",
        "crowdfunding",
        "store",
        "community",
    }
)
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
        "launch",
    }
)
LAUNCH_KEYS = frozenset({"audiences", "messages", "channels", "call_to_action"})
AUDIENCE_KEYS = frozenset({"id", "name", "insight", "facts"})
MESSAGE_KEYS = frozenset({"id", "text", "audiences", "facts", "targets"})
CHANNEL_KEYS = frozenset({"id", "kind", "audiences", "messages"})
CTA_KEYS = frozenset({"text", "facts"})
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

FEATURE_ALIASES = (
    "feature",
    "benefit",
    "why",
    "what you get",
    "特長",
    "特徴",
    "できること",
    "魅力",
)
CTA_ALIASES = (
    "get ",
    "get it",
    "buy",
    "order",
    "try",
    "sign up",
    "join",
    "where to",
    "availability",
    "購入",
    "予約",
    "申し込",
    "入手",
    "試す",
    "お求め",
)
ABOUT_ALIASES = ("about", "について", "概要")
CONTACT_ALIASES = ("contact", "media", "press inquir", "問い合わせ", "報道")
AUDIENCE_ALIASES = ("audience", "who it is for", "target", "ターゲット", "対象")
MESSAGE_ALIASES = ("message", "メッセージ", "訴求")
CHANNEL_ALIASES = ("channel", "チャネル", "チャンネル", "媒体")
CHECKLIST_ALIASES = (
    "checklist",
    "schedule",
    "timeline",
    "チェックリスト",
    "スケジュール",
)
TIME_COLUMN_ALIASES = ("time", "timecode", "秒", "時間", "タイム")
VISUAL_COLUMN_ALIASES = ("visual", "shot", "screen", "scene", "画面", "映像", "シーン")
AUDIO_COLUMN_ALIASES = (
    "narration",
    "voice",
    "audio",
    "sound",
    "caption",
    "ナレーション",
    "セリフ",
    "音声",
    "字幕",
)

MAX_QUICKSTART_STEPS = 7
MIN_CHECKLIST_ITEMS = 2
PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|FIXME|XXX)\b|lorem ipsum|<placeholder>|要確認|未定|（仮）",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s{0,3}(```+|~~~+)\s*([\w-]*)")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
ORDERED_ITEM_RE = re.compile(r"^(\d+)[.)]\s+\S")
LIST_MARKER_RE = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+(?:\[[ xX]\]\s+)?")
TASK_ITEM_RE = re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s+\S")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
NUMBER_RE = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)*")
SUPERLATIVE_RE = re.compile(
    r"\b(?:best|No\.\s?1|number one|world'?s first|first[- ]ever|unbeatable"
    r"|guaranteed?|perfect|revolutionary|unmatched)\b"
    r"|#1\b|世界初|日本初|業界初|世界一|日本一|最高|最強|最速|最安|唯一|完璧|絶対|保証",
    re.IGNORECASE,
)


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
    version = top.get("schema_version")
    if version not in BRIEF_VERSIONS:
        problems.append(f"schema_version: must be one of {list(BRIEF_VERSIONS)}")
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
    allowed_kinds = PRODUCT_DOC_KINDS if version == "0.1" else TARGET_KINDS
    if raw_targets is None or not 1 <= len(raw_targets) <= len(allowed_kinds):
        problems.append(f"targets: must be a list of 1..{len(allowed_kinds)} targets")
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
        if kind in LAUNCH_KINDS and version == "0.1":
            problems.append(
                f"{label}.kind: {kind} is a marketing/launch kind; it needs"
                ' schema_version "0.2"'
            )
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
    launch_kinds = [t.kind for t in targets if t.kind in LAUNCH_KINDS]
    if "launch" in top:
        if version == "0.1":
            problems.append('launch: needs schema_version "0.2"')
        elif not launch_kinds:
            problems.append("launch: only allowed with a marketing/launch target")
        else:
            _validate_launch(top.get("launch"), fact_ids, launch_kinds, problems)
    elif launch_kinds:
        problems.append(
            "launch: required with marketing/launch targets"
            f" ({', '.join(launch_kinds)})"
        )
    return problems, targets


def _check_ids(
    value: object, label: str, known: set[str], problems: list[str], lo: int = 1
) -> list[str]:
    items = _as_list(value)
    if items is None or len(items) < lo:
        problems.append(f"{label}: must be a list of at least {lo} ids")
        return []
    ids: list[str] = []
    for ref in items:
        if not isinstance(ref, str) or ref not in known:
            problems.append(f"{label}: unknown id {ref!r}")
        else:
            ids.append(ref)
    return ids


def _validate_launch(
    raw: object, fact_ids: set[str], launch_kinds: list[str], problems: list[str]
) -> None:
    launch = _as_dict(raw)
    if launch is None:
        problems.append("launch: must be an object")
        return
    for key in sorted(set(launch) - LAUNCH_KEYS):
        problems.append(f"launch.{key}: unknown key")

    audience_ids: set[str] = set()
    raw_audiences = _as_list(launch.get("audiences"))
    if raw_audiences is None or not 1 <= len(raw_audiences) <= 6:
        problems.append("launch.audiences: must be a list of 1..6 audiences")
        raw_audiences = []
    for i, item in enumerate(raw_audiences):
        label = f"launch.audiences[{i}]"
        aud = _as_dict(item)
        if aud is None:
            problems.append(f"{label}: must be an object")
            continue
        for key in sorted(set(aud) - AUDIENCE_KEYS):
            problems.append(f"{label}.{key}: unknown key")
        aid = aud.get("id")
        if not isinstance(aid, str) or not re.fullmatch(r"A\d+", aid):
            problems.append(f"{label}.id: must match A<number>")
        elif aid in audience_ids:
            problems.append(f"{label}.id: duplicate {aid}")
        else:
            audience_ids.add(aid)
        if not _is_str(aud.get("name"), 1, 120):
            problems.append(f"{label}.name: must be a string of 1..120 chars")
        if not _is_str(aud.get("insight"), 1, 400):
            problems.append(f"{label}.insight: must be a string of 1..400 chars")
        _check_ids(aud.get("facts"), f"{label}.facts", fact_ids, problems)

    message_ids: set[str] = set()
    raw_messages = _as_list(launch.get("messages"))
    if raw_messages is None or not 1 <= len(raw_messages) <= 12:
        problems.append("launch.messages: must be a list of 1..12 messages")
        raw_messages = []
    for i, item in enumerate(raw_messages):
        label = f"launch.messages[{i}]"
        msg = _as_dict(item)
        if msg is None:
            problems.append(f"{label}: must be an object")
            continue
        for key in sorted(set(msg) - MESSAGE_KEYS):
            problems.append(f"{label}.{key}: unknown key")
        mid = msg.get("id")
        if not isinstance(mid, str) or not re.fullmatch(r"M\d+", mid):
            problems.append(f"{label}.id: must match M<number>")
        elif mid in message_ids:
            problems.append(f"{label}.id: duplicate {mid}")
        else:
            message_ids.add(mid)
        if not _is_str(msg.get("text"), 1, 200):
            problems.append(f"{label}.text: must be a string of 1..200 chars")
        _check_ids(msg.get("audiences"), f"{label}.audiences", audience_ids, problems)
        _check_ids(msg.get("facts"), f"{label}.facts", fact_ids, problems)
        _check_ids(msg.get("targets"), f"{label}.targets", set(launch_kinds), problems)

    raw_channels = _as_list(launch.get("channels", []))
    if raw_channels is None or len(raw_channels) > 12:
        problems.append("launch.channels: must be a list of 0..12 channels")
        raw_channels = []
    channel_ids: set[str] = set()
    for i, item in enumerate(raw_channels):
        label = f"launch.channels[{i}]"
        ch = _as_dict(item)
        if ch is None:
            problems.append(f"{label}: must be an object")
            continue
        for key in sorted(set(ch) - CHANNEL_KEYS):
            problems.append(f"{label}.{key}: unknown key")
        cid = ch.get("id")
        if not isinstance(cid, str) or not re.fullmatch(r"C\d+", cid):
            problems.append(f"{label}.id: must match C<number>")
        elif cid in channel_ids:
            problems.append(f"{label}.id: duplicate {cid}")
        else:
            channel_ids.add(cid)
        kind = ch.get("kind")
        if not isinstance(kind, str) or kind not in CHANNEL_KINDS:
            problems.append(f"{label}.kind: must be one of {sorted(CHANNEL_KINDS)}")
        _check_ids(ch.get("audiences"), f"{label}.audiences", audience_ids, problems)
        _check_ids(ch.get("messages"), f"{label}.messages", message_ids, problems)

    cta = _as_dict(launch.get("call_to_action"))
    if cta is None:
        problems.append("launch.call_to_action: must be an object")
        return
    for key in sorted(set(cta) - CTA_KEYS):
        problems.append(f"launch.call_to_action.{key}: unknown key")
    if not _is_str(cta.get("text"), 1, 120):
        problems.append("launch.call_to_action.text: must be a string of 1..120 chars")
    _check_ids(cta.get("facts"), "launch.call_to_action.facts", fact_ids, problems)


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


@dataclass
class BriefContext:
    """Brief values the per-kind document rules check against."""

    product_name: str = ""
    tagline: str = ""
    fact_texts: list[str] = field(default_factory=list[str])
    audiences: list[str] = field(default_factory=list[str])
    messages: list[tuple[str, list[str]]] = field(
        default_factory=list[tuple[str, list[str]]]
    )
    call_to_action: str = ""


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _contains(text: str, phrase: str) -> bool:
    return _normalize(phrase) in _normalize(text)


def _claim_text(line: str, product_name: str) -> str:
    """Prose of one line with markup that is not a claim removed."""
    line = LINK_TARGET_RE.sub("]", INLINE_CODE_RE.sub("", line))
    line = LIST_MARKER_RE.sub("", line)
    if product_name:
        line = re.sub(re.escape(product_name), " ", line, flags=re.IGNORECASE)
    return line


def _claim_problems(doc: ParsedDoc, kind: str, ctx: BriefContext) -> list[str]:
    problems: list[str] = []
    facts = " ".join(ctx.fact_texts)
    fact_numbers = set(NUMBER_RE.findall(facts))
    for lineno, line in doc.prose:
        text = _claim_text(line, ctx.product_name)
        for m in SUPERLATIVE_RE.finditer(text):
            if not _contains(facts, m.group(0)):
                problems.append(
                    f"line {lineno}: unsourced superlative {m.group(0)!r}"
                    " (only allowed when a fact says it)"
                )
        if kind not in NUMBER_GROUNDED_KINDS or TABLE_SEPARATOR_RE.match(line):
            continue
        for number in NUMBER_RE.findall(text):
            if number not in fact_numbers:
                problems.append(f"line {lineno}: number {number} is not in any fact")
    return problems


def _table_headers(doc: ParsedDoc) -> list[list[str]]:
    headers: list[list[str]] = []
    prose = doc.prose
    for (_n, line), (_m, nxt) in zip(prose, prose[1:], strict=False):
        if line.lstrip().startswith("|") and TABLE_SEPARATOR_RE.match(nxt):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            headers.append(cells)
    return headers


def _section_lines(doc: ParsedDoc, span: tuple[int, int]) -> list[str]:
    return [ln for lineno, ln in doc.prose if span[0] < lineno < span[1]]


def _launch_problems(
    doc: ParsedDoc, text: str, target: Target, ctx: BriefContext, diagrams: list[int]
) -> list[str]:
    kind = target.kind
    problems = _claim_problems(doc, kind, ctx)
    for message, kinds in ctx.messages:
        if kind in kinds and not _contains(text, message):
            problems.append(f"{kind}: key message not used verbatim: {message!r}")
    if kind == "product_page":
        if ctx.tagline and not _contains(text, ctx.tagline):
            problems.append("product_page: the tagline does not appear")
        if not diagrams:
            problems.append("product_page: no product image or diagram")
        if _section(doc, FEATURE_ALIASES) is None:
            problems.append("product_page: no features / benefits section (H2/H3)")
        cta = _section(doc, CTA_ALIASES)
        if cta is None:
            problems.append("product_page: no call-to-action section (H2/H3)")
        elif ctx.call_to_action and not _contains(
            "\n".join(_section_lines(doc, cta)), ctx.call_to_action
        ):
            problems.append(
                "product_page: the call-to-action section does not use"
                " launch.call_to_action.text"
            )
    elif kind == "press_release":
        lead = next(
            (
                ln
                for _lineno, ln in doc.prose
                if ln.strip() and not HEADING_RE.match(ln)
            ),
            "",
        )
        if ctx.product_name and not _contains(lead, ctx.product_name):
            problems.append(
                "press_release: the lead paragraph (first line after the"
                " headline) must name the product"
            )
        if _section(doc, ABOUT_ALIASES) is None:
            problems.append("press_release: no About section (H2/H3)")
        if _section(doc, CONTACT_ALIASES) is None:
            problems.append("press_release: no media contact section (H2/H3)")
    elif kind == "demo_script":
        ok = any(
            any(_matches(c, TIME_COLUMN_ALIASES) for c in header)
            and any(_matches(c, VISUAL_COLUMN_ALIASES) for c in header)
            and any(_matches(c, AUDIO_COLUMN_ALIASES) for c in header)
            for header in _table_headers(doc)
        )
        if not ok:
            problems.append(
                "demo_script: no shot table with time, visual, and"
                " narration / audio columns"
            )
    elif kind == "launch_plan":
        for aliases, name in (
            (AUDIENCE_ALIASES, "audience"),
            (MESSAGE_ALIASES, "message"),
            (CHANNEL_ALIASES, "channel"),
        ):
            if _section(doc, aliases) is None:
                problems.append(f"launch_plan: no {name} section (H2/H3)")
        checklist = _section(doc, CHECKLIST_ALIASES)
        if checklist is None:
            problems.append("launch_plan: no checklist / schedule section (H2/H3)")
        else:
            items = [
                ln for ln in _section_lines(doc, checklist) if TASK_ITEM_RE.match(ln)
            ]
            if len(items) < MIN_CHECKLIST_ITEMS:
                problems.append(
                    f"launch_plan: checklist needs >={MIN_CHECKLIST_ITEMS}"
                    " task items (- [ ] ...)"
                )
        for audience in ctx.audiences:
            if not _contains(text, audience):
                problems.append(f"launch_plan: audience {audience!r} never appears")
    return problems


def lint_document(
    target: Target,
    root: Path,
    product_name: str,
    all_targets: list[Target],
    ctx: BriefContext | None = None,
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


def build_report(
    brief_path: Path, root: Path, brief_only: bool = False
) -> dict[str, object]:
    brief, brief_digest = load_brief(brief_path)
    brief_problems, targets = validate_brief(brief)
    top = _as_dict(brief) or {}
    product = _as_dict(top.get("product")) or {}
    name = product.get("name")
    product_name = name.strip() if isinstance(name, str) else ""
    ctx = brief_context(top, product_name)
    documents: list[dict[str, object]] = []
    if not brief_only:
        for target in targets:
            problems, digest = lint_document(target, root, product_name, targets, ctx)
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
