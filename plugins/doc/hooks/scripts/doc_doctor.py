#!/usr/bin/env python3
"""Diagnose the doc plugin install when a session starts.

Resolves the plugin root through the same env-var chain the hooks use
(`DOC_PLUGIN_ROOT`, `$OPENHANDS_PROJECT_DIR/plugins/doc`,
`~/.agents/plugins/doc`, `~/.openhands/plugins/installed/doc`,
`~/plugins/installed/doc`, `$OH_PERSISTENCE_DIR/plugins/installed/doc`), checks the
plugin layout (`.plugin/plugin.json`, `agents/`, `skills/`), and reports which
sister plugins are installed next to it so the doc agents know whom to ask and
which questions must go to the user instead. It also counts liaison requests
addressed to doc so a session starts knowing whether a sister is waiting for an
answer. The hook is
advisory and always exits 0.

Python standard library only.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_ENV = "DOC_PLUGIN_ROOT"
PROJECT_ENV = "OPENHANDS_PROJECT_DIR"
SELF_PATH = Path("hooks") / "scripts" / "doc_doctor.py"
REQUIRED_PATHS = (".plugin/plugin.json", "agents", "skills")
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
LIAISON_DIR = "liaison"
REQUEST_SUFFIX = ".ux-request.json"
RESPONSE_SUFFIX = ".ux-response.json"
PLUGIN = "doc"


def _plugin_dirs(name: str) -> list[Path]:
    project = os.environ.get(PROJECT_ENV) or "."
    home = Path.home()
    dirs = [
        Path(project).expanduser() / "plugins" / name,
        home / ".agents" / "plugins" / name,
        home / ".openhands" / "plugins" / "installed" / name,
        # OpenHands docker conversation runtime: inner
        # HOME=/var/openhands/.openhands holds the installed plugins.
        home / "plugins" / "installed" / name,
    ]
    persistence = os.environ.get("OH_PERSISTENCE_DIR")
    if persistence:
        dirs.append(Path(persistence).expanduser() / "plugins" / "installed" / name)
    return dirs


def _candidate_roots() -> list[Path]:
    candidates: list[Path] = []
    root = os.environ.get(ROOT_ENV)
    if root:
        candidates.append(Path(root).expanduser())
    return candidates + _plugin_dirs("doc")


def _resolve_root() -> Path | None:
    """Resolve the plugin root exactly like the hooks.json command template."""
    for candidate in _candidate_roots():
        if (candidate / SELF_PATH).is_file():
            return candidate.resolve()
    return None


def sister_status() -> dict[str, bool]:
    return {
        name: any((d / ".plugin" / "plugin.json").is_file() for d in _plugin_dirs(name))
        for name in SISTERS
    }


def _payload(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def inbox_counts(project: Path) -> dict[str, int]:
    """Count liaison requests addressed to doc without validating them fully."""
    directory = project / LIAISON_DIR
    counts = {"for_doc": 0, "unanswered": 0, "unreadable": 0}
    if directory.is_symlink() or not directory.is_dir():
        return counts
    for path in sorted(directory.glob(f"*{REQUEST_SUFFIX}")):
        if path.is_symlink():
            counts["unreadable"] += 1
            continue
        payload = _payload(path)
        if payload is None:
            counts["unreadable"] += 1
            continue
        if payload.get("target_agent") != PLUGIN:
            continue
        counts["for_doc"] += 1
        stem = path.name[: -len(REQUEST_SUFFIX)]
        if not (directory / f"{stem}{RESPONSE_SUFFIX}").is_file():
            counts["unanswered"] += 1
    return counts


def findings(root: Path | None) -> list[str]:
    lines: list[str] = []
    if root is None:
        lines.append(
            "plugin root unresolved; checked "
            + ", ".join(str(c) for c in _candidate_roots())
        )
    else:
        missing = [rel for rel in REQUIRED_PATHS if not (root / rel).exists()]
        if missing:
            lines.append(
                f"plugin layout incomplete at {root}: missing {', '.join(missing)}"
            )
        else:
            lines.append(f"plugin layout ok at {root}")
    status = sister_status()
    lines.append(
        "sisters: "
        + ", ".join(
            f"{name}={'installed' if ok else 'missing'}" for name, ok in status.items()
        )
    )
    if not any(status.values()):
        lines.append(
            "no sister plugins found; gather facts from workspace files and ask"
            " the user for anything they cannot answer"
        )
    project = Path(os.environ.get(PROJECT_ENV) or ".")
    counts = inbox_counts(project)
    lines.append(
        "liaison inbox: requests for doc={for_doc} unanswered={unanswered}"
        " unreadable={unreadable}".format(**counts)
    )
    if counts["unanswered"]:
        lines.append(
            "answer waiting liaison requests with doc_ux_inbox then doc_ux_respond"
        )
    return lines


def main() -> int:
    try:
        context = "doc doctor: " + "; ".join(findings(_resolve_root()))
    except Exception as exc:  # noqa: BLE001 - the doctor is advisory
        print(f"doc_doctor: {exc}", file=sys.stderr)
        context = "doc doctor: probe failed; see the hook stderr log"
    print(json.dumps({"decision": "allow", "additionalContext": context}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
