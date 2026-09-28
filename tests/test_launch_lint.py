"""Tests for the schema 0.2 marketing/launch kinds of doc_lint.py."""

import copy
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from conftest import BRIEF_REL, PLUGIN_ROOT

LAUNCH_EXAMPLE = PLUGIN_ROOT / "skills" / "doc-lint" / "examples" / "desk-timer-launch"
PAGE = "docs/launch/product-page.md"
PRESS = "docs/launch/press-release.md"
DEMO = "docs/launch/demo-script.md"
PLAN = "docs/launch/launch-plan.md"


@pytest.fixture()
def launch_ws(tmp_path: Path) -> Path:
    root = tmp_path / "launch"
    shutil.copytree(LAUNCH_EXAMPLE, root)
    return root


def _brief(root: Path) -> dict[str, object]:
    return json.loads((root / BRIEF_REL).read_text(encoding="utf-8"))


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


def _launch(brief: dict[str, object]) -> dict[str, object]:
    launch = brief["launch"]
    assert isinstance(launch, dict)
    return launch


def test_launch_example_passes(doc_lint: ModuleType, launch_ws: Path) -> None:
    report = doc_lint.build_report(launch_ws / BRIEF_REL, launch_ws)
    assert report["verdict"] == "pass", _problems(doc_lint, launch_ws)
    assert [d["kind"] for d in report["documents"]] == [
        "product_page",
        "press_release",
        "demo_script",
        "launch_plan",
    ]


def test_launch_kinds_need_schema_0_2(doc_lint: ModuleType, launch_ws: Path) -> None:
    brief = _brief(launch_ws)
    brief["schema_version"] = "0.1"
    problems, _targets = doc_lint.validate_brief(brief)
    assert any('needs schema_version "0.2"' in p for p in problems), problems


def test_launch_block_required(doc_lint: ModuleType, launch_ws: Path) -> None:
    brief = _brief(launch_ws)
    brief.pop("launch")
    problems, _targets = doc_lint.validate_brief(brief)
    assert any("launch: required with marketing/launch targets" in p for p in problems)


def test_launch_block_needs_launch_target(
    doc_lint: ModuleType, launch_ws: Path
) -> None:
    brief = _brief(launch_ws)
    brief["targets"] = [{"kind": "readme", "path": "README.md"}]
    problems, _targets = doc_lint.validate_brief(brief)
    assert any("only allowed with a marketing/launch target" in p for p in problems)


def _step(node: object, key: str | int) -> object:
    if isinstance(key, int):
        assert isinstance(node, list)
        return node[key]
    assert isinstance(node, dict)
    return node[key]


def _mutate(path: list[str | int], value: object):
    def apply(brief: dict[str, object]) -> None:
        node: object = _launch(brief)
        for key in path[:-1]:
            node = _step(node, key)
        last = path[-1]
        if isinstance(last, int):
            assert isinstance(node, list)
            node[last] = copy.deepcopy(value)
        else:
            assert isinstance(node, dict)
            node[last] = copy.deepcopy(value)

    return apply


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_mutate(["extra"], 1), "launch.extra: unknown key"),
        (_mutate(["audiences"], []), "launch.audiences: must be a list of 1..6"),
        (_mutate(["audiences", 0, "facts"], []), "audiences[0].facts: must be"),
        (_mutate(["audiences", 0, "facts"], ["F99"]), "unknown id 'F99'"),
        (_mutate(["audiences", 1, "id"], "A1"), "audiences[1].id: duplicate A1"),
        (_mutate(["messages", 0, "facts"], []), "messages[0].facts: must be"),
        (_mutate(["messages", 0, "audiences"], ["A9"]), "unknown id 'A9'"),
        (_mutate(["messages", 0, "targets"], ["readme"]), "unknown id 'readme'"),
        (_mutate(["messages", 0, "id"], "X1"), "messages[0].id: must match M"),
        (_mutate(["channels", 0, "kind"], "billboard"), "channels[0].kind"),
        (_mutate(["channels", 0, "messages"], ["M9"]), "unknown id 'M9'"),
        (_mutate(["call_to_action", "facts"], []), "call_to_action.facts"),
        (_mutate(["call_to_action", "text"], ""), "call_to_action.text"),
    ],
)
def test_launch_brief_rejections(
    doc_lint: ModuleType, launch_ws: Path, mutate: object, expected: str
) -> None:
    brief = _brief(launch_ws)
    assert callable(mutate)
    mutate(brief)
    problems, _targets = doc_lint.validate_brief(brief)
    assert any(expected in p for p in problems), problems


@pytest.mark.parametrize(
    ("rel", "old", "new", "expected"),
    [
        (PAGE, "4,980 yen", "3,980 yen", "number 3,980 is not in any fact"),
        (PAGE, "- **Nothing", "- **The best timer.** \n- **Nothing", "superlative"),
        (PAGE, "## Why Tomo Timer", "## Details", "no features / benefits"),
        (PAGE, "## Pre-order", "## More", "no call-to-action section"),
        (
            PAGE,
            "Pre-order Tomo Timer from",
            "Reserve it from",
            "does not use launch.call_to_action.text",
        ),
        (PAGE, "A one-knob desk timer that", "A desk timer that", "tagline"),
        (PAGE, "```mermaid", "```text", "no product image or diagram"),
        (PAGE, "**Set a timer in one twist.**", "**Twist.**", "key message"),
        (
            PRESS,
            "Tomo Timer is a palm-sized desk timer you set without looking at a"
            " screen. Pre-orders open on 2026-11-02 at the Tomo Timer online shop",
            "A palm-sized desk timer you set without looking at a screen."
            " Pre-orders open on 2026-11-02 at our online shop",
            "lead paragraph",
        ),
        (PRESS, "## About Tomo Timer", "## Background", "no About section"),
        (PRESS, "## Media contact", "## Notes", "no media contact section"),
        (DEMO, "| Time | Visual | Narration |", "| Visual | Narration |", "shot"),
        (PLAN, "## Channels", "## Where", "no channel section"),
        (PLAN, "## Audience", "## People", "no audience section"),
        (
            PLAN,
            "- [ ] Send the press release on the pre-order day\n"
            "- [ ] Publish the demo video on the product page\n"
            "- [ ] Name a press contact (open question)\n",
            "",
            "checklist needs >=2 task items",
        ),
        (
            PLAN,
            "Students in focus sessions",
            "Students",
            "audience 'Students in focus sessions' never appears",
        ),
    ],
)
def test_launch_document_rejections(
    doc_lint: ModuleType,
    launch_ws: Path,
    rel: str,
    old: str,
    new: str,
    expected: str,
) -> None:
    _edit(launch_ws, rel, old, new)
    problems = _problems(doc_lint, launch_ws)
    assert any(expected in p for p in problems), problems


def test_superlative_allowed_when_a_fact_says_it(
    doc_lint: ModuleType, launch_ws: Path
) -> None:
    brief = _brief(launch_ws)
    facts = brief["facts"]
    assert isinstance(facts, list)
    facts.append(
        {"id": "F9", "text": "It won the Best Desk Gadget award.", "sources": ["S5"]}
    )
    (launch_ws / BRIEF_REL).write_text(json.dumps(brief), encoding="utf-8")
    _edit(
        launch_ws,
        PRESS,
        "## About Tomo Timer\n",
        "## About Tomo Timer\n\nIt won the Best Desk Gadget award.\n",
    )
    assert _problems(doc_lint, launch_ws) == []


def test_numbers_in_links_and_code_are_not_claims(
    doc_lint: ModuleType, launch_ws: Path
) -> None:
    _edit(
        launch_ws,
        PAGE,
        "## Pre-order\n",
        "## Pre-order\n\nSee [the demo script](demo-script.md) and `model-7`.\n",
    )
    assert _problems(doc_lint, launch_ws) == []


def test_readme_need_not_link_launch_documents(
    doc_lint: ModuleType, workspace: Path, launch_ws: Path
) -> None:
    brief = _brief(launch_ws)
    targets = brief["targets"]
    assert isinstance(targets, list)
    brief["targets"] = [{"kind": "readme", "path": "README.md"}, *targets]
    (launch_ws / BRIEF_REL).write_text(json.dumps(brief), encoding="utf-8")
    shutil.copy(workspace / "README.md", launch_ws / "README.md")
    (launch_ws / "docs" / "user-manual.md").write_text("# x\n", encoding="utf-8")
    (launch_ws / "docs" / "technical-reference.md").write_text(
        "# x\n", encoding="utf-8"
    )
    problems = [p for p in _problems(doc_lint, launch_ws) if p.startswith("README.md")]
    assert not any("must link to the product_page" in p for p in problems), problems
