"""Shared fixtures: the doc_lint module and a copy of the example workspace."""

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "doc"
LINT_SCRIPT = PLUGIN_ROOT / "skills" / "doc-lint" / "scripts" / "doc_lint.py"
EXAMPLE = PLUGIN_ROOT / "skills" / "doc-lint" / "examples" / "desk-timer"
BRIEF_REL = Path("doc-work") / "desk-timer" / "doc-brief.json"


@pytest.fixture(scope="session")
def doc_lint() -> ModuleType:
    spec = importlib.util.spec_from_file_location("doc_lint", LINT_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["doc_lint"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    shutil.copytree(EXAMPLE, root)
    return root
