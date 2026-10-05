"""Tests for the doc plugin hook scripts."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import BRIEF_REL, EXAMPLE, LINT_SCRIPT, PLUGIN_ROOT

SCRIPTS = PLUGIN_ROOT / "hooks" / "scripts"
STATUS_SCRIPT = SCRIPTS / "report_doc_status.py"
DOCTOR_SCRIPT = SCRIPTS / "doc_doctor.py"
PROTECT_SCRIPT = SCRIPTS / "protect_lint_report.py"
SAFETY_RAIL_SCRIPT = SCRIPTS / "safety_rail.py"
ENSURE_PROFILES_SCRIPT = SCRIPTS / "ensure_llm_profiles.py"
REQUIRE_RECORDS_SCRIPT = SCRIPTS / "require_records.py"


def _run(
    script: Path, payload: object, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _status(root: Path) -> str:
    result = _run(STATUS_SCRIPT, {"working_dir": str(root)})
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["decision"] == "allow"
    return payload["additionalContext"]


def _lint(root: Path) -> None:
    subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--brief", str(BRIEF_REL)],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_status_without_doc_work(tmp_path: Path) -> None:
    assert "No doc briefs" in _status(tmp_path)


def test_require_records_session_marker_and_stop_status(tmp_path: Path) -> None:
    policy = PLUGIN_ROOT / "hooks" / "records-policy.json"
    env = {**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)}
    start = subprocess.run(
        [sys.executable, str(REQUIRE_RECORDS_SCRIPT), "session-start"],
        input=json.dumps({"session_id": "test-session", "working_dir": str(tmp_path)}),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert start.returncode == 0, start.stderr
    marker = tmp_path / "observations/doc/.sessions/test-session.json"
    assert marker.is_file()
    stop = subprocess.run(
        [sys.executable, str(REQUIRE_RECORDS_SCRIPT), "stop"],
        input=json.dumps({"session_id": "test-session", "working_dir": str(tmp_path)}),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert stop.returncode == 0, stop.stderr
    status = json.loads(
        (tmp_path / "observations/doc/records-status.json").read_text("utf-8")
    )
    assert status["verdict"] == "pass"
    assert policy.is_file()


def test_require_records_denial_is_bounded(tmp_path: Path) -> None:
    env = {**os.environ, "OPENHANDS_PROJECT_DIR": str(tmp_path)}
    start = subprocess.run(
        [sys.executable, str(REQUIRE_RECORDS_SCRIPT), "session-start"],
        input=json.dumps({"session_id": "bounded", "working_dir": str(tmp_path)}),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert start.returncode == 0
    artifact = tmp_path / "doc-work/example/README.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Changed output\n", encoding="utf-8")
    command = [sys.executable, str(REQUIRE_RECORDS_SCRIPT), "stop"]
    payload = json.dumps({"session_id": "bounded", "working_dir": str(tmp_path)})
    for _ in range(2):
        denied = subprocess.run(
            command, input=payload, text=True, capture_output=True, env=env, check=False
        )
        assert denied.returncode != 0
    allowed = subprocess.run(
        command, input=payload, text=True, capture_output=True, env=env, check=False
    )
    assert allowed.returncode == 0
    status = json.loads(
        (tmp_path / "observations/doc/records-status.json").read_text("utf-8")
    )
    assert status["verdict"] == "fail"


def test_protected_record_status_and_session_paths() -> None:
    spec = importlib.util.spec_from_file_location("protect_lint_report", PROTECT_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module._is_protected("observations/doc/records-status.json")
    assert module._is_protected("observations/doc/.sessions/session.json")


def test_status_unlinted_then_pass_then_stale(workspace: Path) -> None:
    context = _status(workspace)
    assert "doc-work/desk-timer/doc-brief.json: linted=false" in context
    assert "Before finishing, rerun doc_lint.py" in context
    assert "unanswered_inquiries=1 open_questions=1" in context
    assert "List unanswered inquiries and open questions" in context

    _lint(workspace)
    context = _status(workspace)
    assert "linted=pass" in context
    assert "Before finishing" not in context

    readme = workspace / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nMore.\n", "utf-8")
    assert "linted=stale" in _status(workspace)


def test_status_brief_change_is_stale(workspace: Path) -> None:
    _lint(workspace)
    brief = workspace / BRIEF_REL
    brief.write_text(brief.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert "linted=stale" in _status(workspace)


def test_status_failed_report(workspace: Path) -> None:
    (workspace / "docs" / "user-manual.md").unlink()
    subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--brief", str(BRIEF_REL)],
        cwd=workspace,
        check=False,
        capture_output=True,
    )
    assert "linted=fail" in _status(workspace)


def test_status_no_questions_no_reminder(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    shutil.copytree(EXAMPLE, root)
    brief_path = root / BRIEF_REL
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["inquiries"] = brief["inquiries"][:2]
    brief["open_questions"] = []
    brief_path.write_text(json.dumps(brief), encoding="utf-8")
    _lint(root)
    context = _status(root)
    assert "linted=pass unanswered_inquiries=0 open_questions=0" in context
    assert "List unanswered" not in context


def test_status_malformed_brief_fails_closed(workspace: Path) -> None:
    (workspace / BRIEF_REL).write_text("{", encoding="utf-8")
    result = _run(STATUS_SCRIPT, {"working_dir": str(workspace)})
    assert result.returncode == 1
    assert "report_doc_status" in result.stderr


def test_status_foreign_report_fails_closed(workspace: Path) -> None:
    (workspace / BRIEF_REL.with_name("doc-lint.json")).write_text(
        json.dumps({"artifact_kind": "song"}), encoding="utf-8"
    )
    result = _run(STATUS_SCRIPT, {"working_dir": str(workspace)})
    assert result.returncode == 1
    assert "unexpected artifact_kind" in result.stderr


def _doctor(env: dict[str, str]) -> str:
    result = _run(DOCTOR_SCRIPT, {}, env={**env, "PATH": os.environ.get("PATH", "")})
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["decision"] == "allow"
    return payload["additionalContext"]


def test_doctor_resolves_root_and_reports_sisters(tmp_path: Path) -> None:
    sister = tmp_path / "project" / "plugins" / "mech" / ".plugin"
    sister.mkdir(parents=True)
    (sister / "plugin.json").write_text("{}", encoding="utf-8")
    context = _doctor(
        {
            "DOC_PLUGIN_ROOT": str(PLUGIN_ROOT),
            "OPENHANDS_PROJECT_DIR": str(tmp_path / "project"),
            "HOME": str(tmp_path),
        }
    )
    assert f"plugin layout ok at {PLUGIN_ROOT}" in context
    assert "mech=installed" in context
    assert "wire=missing" in context
    for sister in (
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
    ):
        assert f"{sister}=" in context
    assert "no sister plugins found" not in context


def test_doctor_unresolved_root_is_advisory(tmp_path: Path) -> None:
    context = _doctor({"OPENHANDS_PROJECT_DIR": str(tmp_path), "HOME": str(tmp_path)})
    assert "plugin root unresolved" in context
    assert "no sister plugins found" in context


def _editor(command: str, path: str, **extra: str) -> dict[str, object]:
    return {
        "tool_name": "file_editor",
        "tool_input": {"command": command, "path": path, **extra},
    }


def _terminal(command: str) -> dict[str, object]:
    return {"tool_name": "terminal", "tool_input": {"command": command}}


def test_protect_lint_report_denies_writes() -> None:
    for payload in (
        _editor("create", "doc-work/x/doc-lint.json", file_text="{}"),
        _editor("str_replace", "/w/doc-work/x/doc-lint.json", old_str="a", new_str="b"),
        _editor("create", "observations/doc/image-observations.jsonl", file_text=""),
        _editor(
            "str_replace",
            "/w/observations/doc/vision-tool-events.jsonl",
            old_str="a",
            new_str="b",
        ),
        _editor("create", "intake/attachments/manifest.jsonl", file_text=""),
        _terminal("echo '{}' > doc-work/x/doc-lint.json"),
        _terminal("cp other.json doc-work/x/doc-lint.json"),
        _terminal("sed -i s/fail/pass/ doc-work/x/doc-lint.json"),
        _terminal("rm doc-work/x/doc-lint.json"),
        _terminal("echo record >> observations/doc/image-observations.jsonl"),
        _terminal("cp manifest.jsonl intake/attachments/manifest.jsonl"),
        {
            "tool_name": "apply_patch",
            "tool_input": {"patch": "*** Update File: doc-work/x/doc-lint.json"},
        },
        {
            "tool_name": "apply_patch",
            "tool_input": {
                "patch": "*** Update File: observations/doc/image-observations.jsonl"
            },
        },
        {
            "tool_name": "apply_patch",
            "tool_input": {
                "patch": "*** Update File: intake/attachments/manifest.jsonl"
            },
        },
    ):
        assert _run(PROTECT_SCRIPT, payload).returncode == 2, payload


def test_protect_lint_report_allows_reads_and_documents() -> None:
    for payload in (
        _editor("view", "doc-work/x/doc-lint.json"),
        _editor("view", "observations/doc/image-observations.jsonl"),
        _editor("create", "README.md", file_text="see doc-lint.json"),
        _editor("create", "README.md", file_text="see observations/doc/notes.jsonl"),
        _editor("create", "doc-work/x/doc-brief.json", file_text="{}"),
        _terminal("cat doc-work/x/doc-lint.json"),
        _terminal("cat observations/doc/image-observations.jsonl"),
        _terminal(f"python3 {LINT_SCRIPT} --brief doc-work/x/doc-brief.json"),
        _terminal("grep verdict doc-work/x/doc-lint.json"),
    ):
        assert _run(PROTECT_SCRIPT, payload).returncode == 0, payload


def test_protect_lint_report_rejects_bad_input() -> None:
    result = subprocess.run(
        [sys.executable, str(PROTECT_SCRIPT)],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2


def test_safety_rail_denies_denylist() -> None:
    for command in (
        "rm -rf /",
        "git push origin main",
        "git push --force origin feat",
        "git reset --hard",
        "git clean -fd",
        "git checkout -- README.md",
        "git stash drop",
        "git add .",
        "git commit --amend",
        "git commit --no-verify",
    ):
        assert _run(SAFETY_RAIL_SCRIPT, _terminal(command)).returncode == 2, command


def test_safety_rail_allows_normal_commands() -> None:
    for command in (
        "git --no-pager log --oneline -n 30",
        "git add README.md docs",
        "git push origin feat",
        "python3 doc_lint.py --brief doc-work/x/doc-brief.json",
    ):
        assert _run(SAFETY_RAIL_SCRIPT, _terminal(command)).returncode == 0, command


def test_ensure_llm_profiles_provisions(tmp_path: Path) -> None:
    home = tmp_path / "home"
    profiles = home / ".openhands" / "profiles"
    profiles.mkdir(parents=True)
    (home / ".openhands" / "settings.json").write_text(
        json.dumps({"active_profile": "test-model"}), encoding="utf-8"
    )
    template = {"schema_version": 1, "model": "test-model", "auth_type": "api_key"}
    (profiles / "test-model.json").write_text(json.dumps(template), encoding="utf-8")
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    result = _run(ENSURE_PROFILES_SCRIPT, {}, env=env)
    assert result.returncode == 0
    assert json.loads(result.stdout)["missing"] == []
    for name in ("vibebb-author", "vibebb-review"):
        profile = json.loads((profiles / f"{name}.json").read_text(encoding="utf-8"))
        assert profile["model"] == "test-model"


def test_ensure_llm_profiles_tolerates_missing_settings(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path / "nohome"), "PATH": "/usr/bin:/bin"}
    result = _run(ENSURE_PROFILES_SCRIPT, {}, env=env)
    assert result.returncode == 0
    assert json.loads(result.stdout)["missing"] == ["vibebb-author", "vibebb-review"]
