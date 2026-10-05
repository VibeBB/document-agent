"""Validate documentation brief contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import cast

__all__ = [
    "AUDIENCE_KEYS",
    "BRIEF_VERSIONS",
    "BriefError",
    "CHANNEL_KEYS",
    "CHANNEL_KINDS",
    "CTA_KEYS",
    "INQUIRY_STATUSES",
    "LANGUAGES",
    "LAUNCH_KEYS",
    "LAUNCH_KINDS",
    "MESSAGE_KEYS",
    "NUMBER_GROUNDED_KINDS",
    "PLANNED_KINDS",
    "PRODUCT_DOC_KINDS",
    "PRODUCT_KEYS",
    "SCHEMA_VERSION",
    "SISTERS",
    "SISTER_RECORD_FILES",
    "SOURCE_KINDS",
    "TARGET_KINDS",
    "TOP_KEYS",
    "Target",
    "_as_dict",
    "_as_list",
    "_check_ids",
    "_check_str_list",
    "_is_str",
    "_safe_rel_path",
    "_validate_launch",
    "validate_brief",
]

SCHEMA_VERSION = "0.1"

BRIEF_VERSIONS = ("0.1", "0.2")

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

SISTERS = (
    "bard",
    "circuit",
    "dashboard",
    "firmware",
    "fpga",
    "mech",
    "prodeng",
    "sim",
    "ux",
    "wire",
)

SISTER_SOURCE_KINDS = frozenset({"sister_agent", "sister_artifact", "sister_record"})

SISTER_RECORD_FILES = {
    "decisions.jsonl",
    "impressions.jsonl",
    "vision-reviews.jsonl",
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

SOURCE_KINDS = frozenset(
    {
        "file",
        "git_log",
        "conversation",
        "user_interview",
        "sister_agent",
        "sister_artifact",
        "sister_record",
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


class BriefError(Exception):
    """The brief file cannot be read at all."""


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
    if not value or "\x00" in value or "\\" in value or value.startswith("/"):
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
        allowed_keys = {"id", "kind", "ref"}
        if kind in SISTER_SOURCE_KINDS:
            allowed_keys.add("agent")
        if kind in {"file", "sister_artifact"}:
            allowed_keys.add("sha256")
        if kind == "sister_record":
            allowed_keys.add("event_id")
        for key in sorted(set(src) - allowed_keys):
            problems.append(f"{label}.{key}: unknown key")
        if kind in SISTER_SOURCE_KINDS:
            if agent not in SISTERS:
                problems.append(f"{label}.agent: must be one of {list(SISTERS)}")
            elif kind in {"sister_agent", "sister_artifact"}:
                source_agents[sid] = cast(str, agent)
        elif agent is not None:
            problems.append(f"{label}.agent: only allowed for sister sources")
        if kind == "sister_artifact" and "sha256" not in src:
            problems.append(f"{label}.sha256: required for sister_artifact sources")
        if kind in {"file", "sister_artifact"} and "sha256" in src:
            if not isinstance(src["sha256"], str) or not SHA256_RE.fullmatch(
                src["sha256"]
            ):
                problems.append(f"{label}.sha256: must be a lowercase hex sha256")
        if kind == "sister_record":
            event_id = src.get("event_id")
            if not isinstance(event_id, str) or not SHA256_RE.fullmatch(event_id):
                problems.append(f"{label}.event_id: must be a lowercase hex sha256")
            if (
                isinstance(agent, str)
                and isinstance(src.get("ref"), str)
                and src.get("ref")
                not in {f"observations/{agent}/{name}" for name in SISTER_RECORD_FILES}
            ):
                problems.append(
                    f"{label}.ref: must identify a record log under"
                    f" observations/{agent}/"
                )
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
    if any(kind == "sister_record" for kind in sources.values()) and not any(
        target.kind == "technical_reference" for target in targets
    ):
        problems.append("targets: sister_record sources require a technical_reference")

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
        if to not in (*SISTERS, "user"):
            problems.append(f'{label}.to: must be a sister name or "user"')
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
            problems.append(f"{label}.source: must be a sister source from {to}")

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
