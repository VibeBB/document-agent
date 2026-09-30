"""Parse and lint Markdown target documents."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from doc_brief import (  # noqa: E402
    NUMBER_GROUNDED_KINDS,
    Target,
)

__all__ = [
    "ABOUT_ALIASES",
    "ARCH_ALIASES",
    "AUDIENCE_ALIASES",
    "AUDIO_COLUMN_ALIASES",
    "BriefContext",
    "CHANNEL_ALIASES",
    "CHECKLIST_ALIASES",
    "CONTACT_ALIASES",
    "CTA_ALIASES",
    "DEV_ALIASES",
    "FEATURE_ALIASES",
    "FENCE_RE",
    "Fence",
    "HEADING_RE",
    "Heading",
    "IMAGE_RE",
    "INLINE_CODE_RE",
    "INTERFACE_ALIASES",
    "LINK_RE",
    "LINK_TARGET_RE",
    "LIST_MARKER_RE",
    "MAX_QUICKSTART_STEPS",
    "MERMAID_TYPES",
    "MESSAGE_ALIASES",
    "MIN_CHECKLIST_ITEMS",
    "NUMBER_RE",
    "ORDERED_ITEM_RE",
    "PLACEHOLDER_RE",
    "ParsedDoc",
    "QUICKSTART_ALIASES",
    "SUPERLATIVE_RE",
    "TABLE_SEPARATOR_RE",
    "TASK_ITEM_RE",
    "TIME_COLUMN_ALIASES",
    "TROUBLE_ALIASES",
    "USAGE_ALIASES",
    "VISUAL_COLUMN_ALIASES",
    "_claim_problems",
    "_claim_text",
    "_contains",
    "_diagram_lines",
    "_launch_problems",
    "_link_problems",
    "_links_to",
    "_matches",
    "_mermaid_problems",
    "_normalize",
    "_section",
    "_section_lines",
    "_table_headers",
    "parse_markdown",
]

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
