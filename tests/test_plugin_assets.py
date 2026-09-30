"""Consistency checks for the doc plugin assets (manifest, frontmatter, links)."""

import importlib.util
import json
import re
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, REPO_ROOT

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"(?ms)^(```+|~~~+).*?^\1[ \t]*$")
INLINE_CODE_PATTERN = re.compile(r"(`+)(?:(?!\1).)+?\1", re.S)
AGENT_NAMES = {"doc-writer", "doc-liaison", "doc-review", "doc-launch"}
SKILL_NAMES = {
    "doc-craft",
    "doc-lint",
    "doc-inquiry",
    "doc-brief-rules",
    "doc-launch-craft",
}
COMMAND_NAMES = {"write", "interview", "doctor", "launch"}


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    assert m, f"{path} has no YAML frontmatter"
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if re.match(r"^\s", line) or not line.strip():
            continue
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def test_plugin_json() -> None:
    manifest = json.loads(
        (PLUGIN_ROOT / ".plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    for key in ("name", "version", "description", "author", "license"):
        assert manifest.get(key), f"plugin.json missing {key}"
    assert manifest["name"] == "doc"
    assert manifest["license"] == "BSD-3-Clause"
    assert manifest["entry_command"] in COMMAND_NAMES


def test_agent_files() -> None:
    names: set[str] = set()
    for path in sorted(PLUGIN_ROOT.glob("agents/*.md")):
        fm = _frontmatter(path)
        assert fm.get("name") == path.stem
        assert "<example>" in fm.get("description", "")
        assert fm.get("model") in {"vibebb-author", "vibebb-review"}
        names.add(fm["name"])
    assert names == AGENT_NAMES


def test_review_agent_is_read_only() -> None:
    text = (PLUGIN_ROOT / "agents" / "doc-review.md").read_text(encoding="utf-8")
    head = FRONTMATTER_RE.match(text)
    assert head
    assert "  - file_editor\n" in head.group(1).split("hooks:")[0]
    normalized = " ".join(text.split())
    assert (
        "Read-only: you run read commands (`cat`, `ls`, `git --no-pager diff`, "
        "the linter with `--no-write`) and use `file_editor` only with `view`; nothing "
        "else." in normalized
    )
    assert _frontmatter(PLUGIN_ROOT / "agents" / "doc-review.md")["model"] == (
        "vibebb-review"
    )


def test_skill_files() -> None:
    names: set[str] = set()
    for path in sorted(PLUGIN_ROOT.glob("skills/*/SKILL.md")):
        fm = _frontmatter(path)
        assert fm.get("name") == path.parent.name
        assert fm.get("description")
        names.add(fm["name"])
    assert names == SKILL_NAMES


def test_brief_rule_is_path_triggered() -> None:
    head = (PLUGIN_ROOT / "skills" / "doc-brief-rules" / "SKILL.md").read_text(
        encoding="utf-8"
    )[:600]
    assert "paths:" in head
    assert "triggers:" not in head


def test_command_files() -> None:
    names = {p.stem for p in PLUGIN_ROOT.glob("commands/*.md")}
    assert names == COMMAND_NAMES
    for name in names:
        assert _frontmatter(PLUGIN_ROOT / "commands" / f"{name}.md").get("description")


def test_write_command_contract_lines() -> None:
    text = (PLUGIN_ROOT / "commands" / "write.md").read_text(encoding="utf-8")
    for expected in (
        'subagent_type="doc-liaison"',
        'subagent_type="doc-writer"',
        "Path: task sub-agent",
        "Path: fallback (no task)",
        "/doc:interview",
        "without a tool call",
        "Resume:",
        "--no-write",
        "Open questions:",
    ):
        assert expected in text, expected


def test_interview_command_ends_turn_and_records_verbatim() -> None:
    text = (PLUGIN_ROOT / "commands" / "interview.md").read_text(encoding="utf-8")
    for expected in ("without a tool call", "verbatim", "interview.md", "skip"):
        assert expected in text, expected


def test_agents_name_their_stage_files() -> None:
    writer = (PLUGIN_ROOT / "agents" / "doc-writer.md").read_text(encoding="utf-8")
    for expected in ("doc-brief.json", "outline.md", "review.md", "--brief-only"):
        assert expected in writer, expected
    liaison = (PLUGIN_ROOT / "agents" / "doc-liaison.md").read_text(encoding="utf-8")
    for expected in ("survey.md", "inquiries.md", "to: user"):
        assert expected in liaison, expected


def test_inquiry_skill_covers_every_sibling() -> None:
    text = (PLUGIN_ROOT / "skills" / "doc-inquiry" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    for sibling in ("wire", "mech", "circuit", "ux", "bard", "user"):
        assert f"| {sibling} |" in text, sibling


def test_hooks_json_matches_agent_frontmatter() -> None:
    hooks = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text("utf-8"))
    pre = {h["name"]: h["command"] for g in hooks["pre_tool_use"] for h in g["hooks"]}
    post = {h["name"]: h["command"] for g in hooks["post_tool_use"] for h in g["hooks"]}
    for path in PLUGIN_ROOT.glob("agents/*.md"):
        text = path.read_text(encoding="utf-8")
        for command in (*pre.values(), *post.values()):
            assert f"command: '{command}'" in text, path.name
    review = (PLUGIN_ROOT / "agents" / "doc-review.md").read_text(encoding="utf-8")
    assert "  - file_editor\n" in review


def _markdown_files() -> list[Path]:
    files = set(REPO_ROOT.glob("*.md"))
    files.update((REPO_ROOT / "docs").rglob("*.md"))
    files.update(PLUGIN_ROOT.rglob("*.md"))
    return sorted(p for p in files if p.is_file())


@pytest.mark.parametrize("path", _markdown_files(), ids=lambda p: p.name)
def test_relative_links_resolve(path: Path) -> None:
    text = FENCE_RE.sub("", path.read_text(encoding="utf-8"))
    text = INLINE_CODE_PATTERN.sub("", text)
    for target in LINK_RE.findall(text):
        if "://" in target or target.startswith("#") or target.startswith("mailto:"):
            continue
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith("<"):
            continue
        resolved = (path.parent / target).resolve()
        assert resolved.exists(), f"{path}: broken link {target}"


def test_sdk_plugin_load() -> None:
    pytest.importorskip("openhands.sdk.plugin")
    spec = importlib.util.spec_from_file_location(
        "check_plugin_load", REPO_ROOT / "scripts" / "check_plugin_load.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reasons = module.check_plugin(PLUGIN_ROOT)
    assert reasons == [], reasons
