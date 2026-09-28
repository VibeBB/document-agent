"""Tests for skills/doc-lint/scripts/doc_lint.py (brief contract + document lint)."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from conftest import BRIEF_REL, LINT_SCRIPT


def _brief(root: Path) -> dict[str, object]:
    return json.loads((root / BRIEF_REL).read_text(encoding="utf-8"))


def _save(root: Path, brief: dict[str, object]) -> None:
    (root / BRIEF_REL).write_text(json.dumps(brief), encoding="utf-8")


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--brief", str(BRIEF_REL), *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def _problems(doc_lint: ModuleType, root: Path) -> list[str]:
    report = doc_lint.build_report(root / BRIEF_REL, root)
    out: list[str] = list(report["brief_problems"])
    for doc in report["documents"]:
        out.extend(f"{doc['path']}: {p}" for p in doc["problems"])
    return out


def _edit(root: Path, rel: str, old: str, new: str) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_example_passes_and_report_is_deterministic(workspace: Path) -> None:
    first = _run(workspace)
    assert first.returncode == 0, first.stdout + first.stderr
    report_path = workspace / BRIEF_REL.with_name("doc-lint.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["verdict"] == "pass"
    assert report["mode"] == "full"
    assert report["unanswered_inquiries"] == 1
    assert report["open_questions"] == 1
    assert {d["kind"] for d in report["documents"]} == {
        "readme",
        "user_manual",
        "technical_reference",
    }
    snapshot = report_path.read_bytes()
    assert _run(workspace).returncode == 0
    assert report_path.read_bytes() == snapshot


def test_brief_only_writes_nothing(workspace: Path) -> None:
    (workspace / "README.md").unlink()
    result = _run(workspace, "--brief-only")
    assert result.returncode == 0
    assert not (workspace / BRIEF_REL.with_name("doc-lint.json")).exists()


def test_failing_lint_still_writes_report(workspace: Path) -> None:
    (workspace / "docs" / "user-manual.md").unlink()
    result = _run(workspace)
    assert result.returncode == 1
    assert "missing: target document does not exist" in result.stdout
    report = json.loads(
        (workspace / BRIEF_REL.with_name("doc-lint.json")).read_text(encoding="utf-8")
    )
    assert report["verdict"] == "fail"


def test_unreadable_brief_exits_2_and_writes_nothing(workspace: Path) -> None:
    (workspace / BRIEF_REL).write_text("{not json", encoding="utf-8")
    result = _run(workspace)
    assert result.returncode == 2
    assert "not valid UTF-8 JSON" in result.stderr
    assert not (workspace / BRIEF_REL.with_name("doc-lint.json")).exists()


def test_missing_root_exits_2(workspace: Path) -> None:
    assert _run(workspace, "--root", "nowhere").returncode == 2


def _mutated(doc_lint: ModuleType, workspace: Path, mutate: object) -> list[str]:
    brief = _brief(workspace)
    assert callable(mutate)
    mutate(brief)
    problems, _targets = doc_lint.validate_brief(brief)
    return problems


def _set_product(key: str, value: object):
    def mutate(brief: dict[str, object]) -> None:
        product = brief["product"]
        assert isinstance(product, dict)
        product[key] = value

    return mutate


def _pop_product(key: str):
    def mutate(brief: dict[str, object]) -> None:
        product = brief["product"]
        assert isinstance(product, dict)
        product.pop(key)

    return mutate


def _set(key: str, value: object):
    def mutate(brief: dict[str, object]) -> None:
        brief[key] = copy.deepcopy(value)

    return mutate


def _set_item(key: str, index: int, field: str, value: object):
    def mutate(brief: dict[str, object]) -> None:
        items = brief[key]
        assert isinstance(items, list)
        item = items[index]
        assert isinstance(item, dict)
        item[field] = value

    return mutate


def _pop_item(key: str, index: int, field: str):
    def mutate(brief: dict[str, object]) -> None:
        items = brief[key]
        assert isinstance(items, list)
        item = items[index]
        assert isinstance(item, dict)
        item.pop(field)

    return mutate


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_set("extra", 1), "extra: unknown top-level key"),
        (_set("artifact_kind", "song"), 'artifact_kind: must be "doc_brief"'),
        (_set("schema_version", "9"), "schema_version: must be"),
        (_set("language", "fr"), "language: must be"),
        (_set_product("name", ""), "product.name"),
        (_set_product("tagline", "x" * 141), "product.tagline"),
        (_set_product("audience", []), "product.audience"),
        (_set_product("mood", "happy"), "product.mood: unknown key"),
        (_pop_product("vision_source"), "vision and vision_source go together"),
        (_set_product("vision_source", "S1"), "must reference a user_interview"),
        (_set("sources", []), "sources: must be a non-empty list"),
        (_set_item("sources", 0, "kind", "rumor"), "sources[0].kind"),
        (_set_item("sources", 1, "id", "S1"), "sources[1].id: duplicate S1"),
        (_pop_item("sources", 1, "agent"), "sources[1].agent: must be one of"),
        (_set_item("sources", 0, "agent", "wire"), "only allowed for sibling"),
        (_set("facts", []), "facts: must be a non-empty list"),
        (_set_item("facts", 0, "sources", []), "every fact needs at least one"),
        (_set_item("facts", 0, "sources", ["S9"]), "unknown source 'S9'"),
        (_set_item("facts", 1, "id", "F1"), "facts[1].id: duplicate F1"),
        (_set_item("targets", 0, "path", "../README.md"), "relative path inside"),
        (_set_item("targets", 0, "path", "/abs/README.md"), "relative path inside"),
        (_set_item("targets", 0, "path", "README.txt"), "must end with .md"),
        (_set_item("targets", 1, "kind", "readme"), "targets[1].kind: duplicate"),
        (_set_item("targets", 1, "path", "README.md"), "targets[1].path: duplicate"),
        (_set_item("targets", 0, "kind", "quality_plan"), "planned quality-document"),
        (_set_item("targets", 0, "kind", "brochure"), "targets[0].kind: must be"),
        (_set("targets", []), "targets: must be a list of 1..3"),
        (_set_item("inquiries", 0, "to", "oracle"), "inquiries[0].to"),
        (_pop_item("inquiries", 0, "answer"), "answer: required when"),
        (
            _set_item("inquiries", 0, "source", "S2"),
            "must be a sibling source from mech",
        ),
        (_set_item("inquiries", 1, "source", "S3"), "user answers need user_interview"),
        (_set_item("inquiries", 2, "answer", "x"), "only allowed when answered"),
        (_set_item("inquiries", 2, "status", "maybe"), "inquiries[2].status"),
        (_set("open_questions", "none"), "open_questions: must be a list"),
    ],
)
def test_brief_rejections(
    doc_lint: ModuleType, workspace: Path, mutate: object, expected: str
) -> None:
    problems = _mutated(doc_lint, workspace, mutate)
    assert any(expected in p for p in problems), problems


def test_brief_must_be_object(doc_lint: ModuleType) -> None:
    problems, targets = doc_lint.validate_brief([])
    assert problems == ["brief: top level must be a JSON object"]
    assert targets == []


def test_example_brief_valid(doc_lint: ModuleType, workspace: Path) -> None:
    problems, targets = doc_lint.validate_brief(_brief(workspace))
    assert problems == []
    assert [t.kind for t in targets] == ["readme", "user_manual", "technical_reference"]


@pytest.mark.parametrize(
    ("rel", "old", "new", "expected"),
    [
        ("README.md", "## Quick start", "## Try it", "no Quick start section"),
        (
            "README.md",
            "```mermaid\nflowchart LR",
            "```text\nflowchart LR",
            "no diagram (mermaid block or image) before the Quick start",
        ),
        (
            "README.md",
            "## What is Tomo Timer?",
            "Intro",
            "product explanation (an H2 section) must come before",
        ),
        (
            "README.md",
            "2. Turn the knob until the ring shows the minutes you want.\n"
            "3. Press the knob. The ring starts counting down.\n"
            "4. When it chimes, press the knob to stop the glow.",
            "Then turn and press the knob.",
            "Quick start needs >=2 numbered steps",
        ),
        (
            "README.md",
            "4. When it chimes, press the knob to stop the glow.",
            "\n".join(f"{n}. Step {n}." for n in range(4, 10)),
            "Quick start has 9 steps (max 7)",
        ),
        (
            "README.md",
            "[User manual](docs/user-manual.md)",
            "User manual",
            "must link to the user_manual",
        ),
        ("README.md", "flowchart LR", "flowchat LR", "unknown mermaid diagram type"),
        ("README.md", "# Tomo Timer\n", "Tomo Timer\n", "first heading must be"),
        ("README.md", "## Learn more", "# Learn more", "more than one H1"),
        ("README.md", "## Learn more", "## Learn more\n\nTBD", "placeholder text"),
        ("README.md", "## Learn more", "## Learn more\n\n未定です", "placeholder text"),
        (
            "README.md",
            "## Learn more",
            "## Learn more\n\n[spec](docs/missing.md)",
            "broken relative link",
        ),
        (
            "README.md",
            "## Learn more",
            "## Learn more\n\n[up](../outside.md)",
            "link leaves the root",
        ),
        ("README.md", "```\n\n**Who", "\n\n**Who", "unclosed code fence"),
        ("docs/user-manual.md", "## How to use", "## Operation", "no usage section"),
        (
            "docs/technical-reference.md",
            "## Architecture",
            "## Overview",
            "no architecture section",
        ),
        (
            "docs/technical-reference.md",
            "```mermaid",
            "```text",
            "architecture section has no diagram",
        ),
        (
            "docs/technical-reference.md",
            "## Interfaces",
            "## Parts",
            "no interface / spec section",
        ),
        (
            "docs/technical-reference.md",
            "## Development",
            "## Notes",
            "no development / test section",
        ),
    ],
)
def test_document_rejections(
    doc_lint: ModuleType,
    workspace: Path,
    rel: str,
    old: str,
    new: str,
    expected: str,
) -> None:
    _edit(workspace, rel, old, new)
    problems = _problems(doc_lint, workspace)
    assert any(expected in p for p in problems), problems


def test_troubleshooting_section_required(
    doc_lint: ModuleType, workspace: Path
) -> None:
    _edit(workspace, "docs/user-manual.md", "## Troubleshooting", "## Notes")
    problems = _problems(doc_lint, workspace)
    assert any("no troubleshooting / FAQ section" in p for p in problems), problems


def test_product_name_must_appear(doc_lint: ModuleType, workspace: Path) -> None:
    brief = _brief(workspace)
    product = brief["product"]
    assert isinstance(product, dict)
    product["name"] = "Hoshi Clock"
    _save(workspace, brief)
    problems = _problems(doc_lint, workspace)
    assert any("identity: product name 'Hoshi Clock'" in p for p in problems)


def test_placeholder_inside_code_fence_is_allowed(
    doc_lint: ModuleType, workspace: Path
) -> None:
    _edit(
        workspace,
        "docs/technical-reference.md",
        "## Development\n",
        "## Development\n\n```c\n// TODO: tune debounce\n```\n",
    )
    assert _problems(doc_lint, workspace) == []


def test_image_counts_as_readme_diagram(doc_lint: ModuleType, workspace: Path) -> None:
    (workspace / "docs" / "flow.svg").write_text("<svg/>", encoding="utf-8")
    text = (workspace / "README.md").read_text(encoding="utf-8")
    start = text.index("```mermaid")
    end = text.index("```", start + 3) + 3
    text = text[:start] + "![How Tomo Timer works](docs/flow.svg)" + text[end:]
    (workspace / "README.md").write_text(text, encoding="utf-8")
    assert _problems(doc_lint, workspace) == []


def test_non_utf8_document_rejected(doc_lint: ModuleType, workspace: Path) -> None:
    (workspace / "README.md").write_bytes("# Tomo Timer\n".encode("utf-16"))
    problems = _problems(doc_lint, workspace)
    assert "README.md: encoding: document is not valid UTF-8" in problems


JA_README = """# Tomo Timer

ひとひねりで休憩時間を知らせる卓上タイマー。

## Tomo Timer とは

つまみを回して分を選び、押すとリングが光って残り時間を示します。

```mermaid
flowchart LR
    A[つまみを回す] --> B[押して開始] --> C[時間になると光る]
```

## クイックスタート

1. USB-C 充電器につなぎます。
2. つまみを回して分を選びます。
3. つまみを押すと開始します。
"""

JA_MANUAL = """# Tomo Timer 取扱説明書

## 使い方

つまみを回して時間を選びます。

## トラブルシューティング

| 症状 | 対処 |
| --- | --- |
| 光らない | ケーブルを確認します |
"""


def test_japanese_headings_pass(doc_lint: ModuleType, workspace: Path) -> None:
    brief = _brief(workspace)
    brief["language"] = "ja"
    brief["targets"] = [
        {"kind": "readme", "path": "README.ja.md"},
        {"kind": "user_manual", "path": "docs/manual.ja.md"},
    ]
    _save(workspace, brief)
    readme = JA_README + "\n[取扱説明書](docs/manual.ja.md)\n"
    (workspace / "README.ja.md").write_text(readme, encoding="utf-8")
    (workspace / "docs" / "manual.ja.md").write_text(JA_MANUAL, encoding="utf-8")
    assert _problems(doc_lint, workspace) == []
