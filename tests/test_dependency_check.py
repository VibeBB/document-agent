"""Tests for scripts/check_dependency_updates.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_dependency_updates.py"


@pytest.fixture(scope="session")
def dep_check() -> Any:
    spec = importlib.util.spec_from_file_location("check_dependency_updates", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_dependency_updates"] = module
    spec.loader.exec_module(module)
    return module


def test_project_dependencies_parsed(dep_check: Any) -> None:
    deps = dep_check.dependency_names(dep_check.project_data(REPO_ROOT))
    assert "openhands-sdk" in deps
    assert "openhands-tools" in deps
    assert "pytest" in deps
    assert "ruff" in deps


def test_lock_versions_cover_direct_deps(dep_check: Any) -> None:
    versions = dep_check.lock_versions(REPO_ROOT)
    deps = dep_check.dependency_names(dep_check.project_data(REPO_ROOT))
    missing = [name for name in deps if name not in versions]
    assert missing == []
    assert versions["openhands-sdk"] == "1.52.0"
    assert versions["pytest"] == "9.1.1"


def test_uv_pin_parsed(dep_check: Any) -> None:
    assert dep_check.uv_version_pin(REPO_ROOT) == "==0.12.23"


def test_workflow_files_have_expected_suffixes(dep_check: Any) -> None:
    files = dep_check.workflow_files(REPO_ROOT)
    assert all(f.suffix in {".yml", ".yaml"} for f in files)


def test_render_markdown_groups_by_surface(dep_check: Any) -> None:
    statuses = [
        dep_check.DependencyStatus(
            "pypi", "pydantic", "2.13.5", "2.13.5", "pyproject.toml", False
        ),
        dep_check.DependencyStatus(
            "pypi", "mcp", "1.30.0", "2.2.0", "pyproject.toml", True
        ),
        dep_check.DependencyStatus(
            "github-actions",
            "actions/checkout",
            "v7.0.1",
            "v7.0.1",
            ".github/workflows/ci.yml",
            False,
        ),
    ]
    markdown = dep_check.render_markdown(statuses)
    assert "## PyPI (direct dependencies)" in markdown
    assert "## GitHub Actions" in markdown
    assert "Docker" not in markdown
    assert "| mcp | 1.30.0 | 2.2.0 | update available | pyproject.toml |" in markdown
    assert "| pydantic | 2.13.5 | 2.13.5 | up to date | pyproject.toml |" in markdown
    assert "update candidates: 1" in markdown


def test_action_statuses_strip_subpath_actions(
    dep_check: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow = tmp_path / "lint.yml"
    sha = "2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2"
    workflow.write_text(
        f"- uses: github/codeql-action/upload-sarif@{sha} # v4.38.2\n"
        "- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dep_check, "workflow_files", lambda _root: [workflow])
    urls: list[str] = []

    def tags(url: str) -> list[str]:
        urls.append(url)
        return []

    statuses = dep_check.check_github_actions(tmp_path, list_remote_tags=tags)
    assert {s.name for s in statuses} == {
        "github/codeql-action",
        "actions/checkout",
    }
    assert set(urls) == {
        "https://github.com/github/codeql-action",
        "https://github.com/actions/checkout",
    }


def test_every_sha_pinned_workflow_action_is_tracked(dep_check: Any) -> None:
    statuses = dep_check.check_github_actions(REPO_ROOT, list_remote_tags=lambda _u: [])
    tracked = {s.name for s in statuses if s.surface == "github-actions"}
    pinned = set()
    for workflow in dep_check.workflow_files(REPO_ROOT):
        for uses_path, _sha, _comment in dep_check._ACTION.findall(
            workflow.read_text(encoding="utf-8")
        ):
            pinned.add(dep_check._action_repo(uses_path))
    assert pinned <= tracked
    assert "github/codeql-action" in tracked


def test_workflow_downloads_track_wheel_tarball_and_trivy(
    dep_check: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow = tmp_path / "lint.yml"
    workflow.write_text(
        "- name: actionlint\n"
        "  run: |\n"
        '    curl "https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz"\n'
        "- name: wheel\n"
        "  run: |\n"
        '    wheel="zizmor-1.30.1-py3-none-manylinux_2_28_x86_64.whl"\n'
        '    curl "https://files.pythonhosted.org/packages/ab/cd/$wheel"\n'
        "- uses: aquasecurity/trivy-action@2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2\n"
        "  with:\n"
        "    version: 0.58.0\n"
        "- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dep_check, "workflow_files", lambda _root: [workflow])

    def fetch_json(_url: str) -> Any:
        return {"info": {"version": "9.9.9"}}

    def tags(url: str) -> list[str]:
        return {
            "https://github.com/rhysd/actionlint": ["v1.7.12"],
            "https://github.com/aquasecurity/trivy": ["v0.58.0"],
        }.get(url, [])

    statuses = dep_check.check_workflow_downloads(
        tmp_path, fetch_json=fetch_json, list_remote_tags=tags
    )
    assert {(s.name, s.current) for s in statuses} == {
        ("zizmor", "1.30.1"),
        ("rhysd/actionlint", "v1.7.12"),
        ("aquasecurity/trivy", "0.58.0"),
    }
    assert all(s.surface == "direct-download" for s in statuses)


def test_workflow_downloads_cover_repo_pins(dep_check: Any) -> None:
    def fetch_json(_url: str) -> Any:
        return {"info": {"version": "9.9.9"}}

    statuses = dep_check.check_workflow_downloads(
        REPO_ROOT, fetch_json=fetch_json, list_remote_tags=lambda _u: ["v9.9.9"]
    )
    rows = {(s.name, s.current) for s in statuses}
    assert ("zizmor", "1.30.1") in rows
    assert ("rhysd/actionlint", "v1.7.12") in rows


def test_uvx_statuses_deduplicated_on_name_and_pin(
    dep_check: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow = tmp_path / "lint.yml"
    workflow.write_text(
        "- run: uvx zizmor@1.30.1 --format sarif .\n"
        "- run: uvx zizmor@1.30.1 --format plain .\n"
        "- run: uvx zizmor@1.29.0 --format plain .\n"
        "- run: uvx ruff@0.1.0 check .\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dep_check, "workflow_files", lambda _root: [workflow])
    monkeypatch.setattr(
        dep_check, "_default_fetch_json", lambda _url: {"info": {"version": "9.9.9"}}
    )
    statuses = dep_check.check_github_actions(tmp_path, list_remote_tags=lambda _u: [])
    uvx = [(s.name, s.current) for s in statuses if s.surface == "pypi-uvx"]
    assert uvx == [("zizmor", "1.30.1"), ("zizmor", "1.29.0"), ("ruff", "0.1.0")]


def test_apply_deferrals_marks_matching_outdated(
    dep_check: Any, tmp_path: Path
) -> None:
    deferrals_path = tmp_path / "scripts" / "dependency_update_deferrals.json"
    deferrals_path.parent.mkdir(parents=True)
    deferrals_path.write_text(
        json.dumps(
            {
                "deferrals": [
                    {
                        "surface": "pypi",
                        "name": "mcp",
                        "latest": "2.2.0",
                        "review_by": "2999-01-01",
                        "reason": "test",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    deferrals = dep_check.load_deferrals(tmp_path)
    statuses = dep_check.apply_deferrals(
        [
            dep_check.DependencyStatus(
                "pypi", "mcp", "1.30.0", "2.2.0", "pyproject.toml", True
            )
        ],
        deferrals,
        date(2026, 9, 23),
    )
    assert statuses[0].deferred is True
    assert statuses[0].outdated is False
    assert "test" in statuses[0].note


def test_fetch_failures_are_unknown_and_counted(
    dep_check: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def failed_json(url: str) -> Any:
        raise OSError(url)

    def failed_tags(url: str) -> list[str]:
        raise OSError(url)

    monkeypatch.setattr(dep_check, "_default_fetch_json", failed_json)
    statuses = [
        *dep_check.check_pypi(REPO_ROOT, fetch_json=failed_json),
        *dep_check.check_uv_pin(REPO_ROOT, fetch_json=failed_json),
        *dep_check.check_github_actions(REPO_ROOT, list_remote_tags=failed_tags),
    ]
    unknown = [status for status in statuses if status.fetch_failed]

    assert unknown
    assert all(not status.outdated for status in unknown)
    assert {"pypi", "uv-pin", "github-actions"} <= {
        status.surface for status in unknown
    }

    monkeypatch.setattr(dep_check, "check_dependency_updates", lambda _root: unknown)
    monkeypatch.setattr(dep_check, "load_deferrals", lambda _root: [])
    report_path = tmp_path / "report.json"
    assert (
        dep_check.main(["--repo-root", str(REPO_ROOT), "--json", str(report_path)]) == 0
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknown_count"] == len(unknown)
    assert report["outdated_count"] == 0
    assert "| unknown |" in capsys.readouterr().out
