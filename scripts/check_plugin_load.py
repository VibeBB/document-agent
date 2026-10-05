"""Load plugins/doc through the OpenHands SDK plugin loader and assert the
expected agents, skills, commands, and manifest version.

Exits 0 on success and prints a one-line summary; exits 1 listing every
mismatch. Intended for the `plugin-load` CI job; the `sdk-check`
dependency group provides openhands-sdk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "plugins" / "doc"

EXPECTED_AGENTS = {"doc-launch", "doc-liaison", "doc-review", "doc-writer"}
EXPECTED_SKILLS = {
    "doc-brief-rules",
    "doc-craft",
    "doc-inquiry",
    "doc-launch-craft",
    "doc-lint",
    "doc-records",
}
EXPECTED_COMMANDS = {"doctor", "interview", "launch", "write"}
EXPECTED_SESSION_START_HOOKS = {
    "doc-doctor",
    "ensure-llm-profiles",
    "intake-attachments",
    "require-records",
}
EXPECTED_USER_PROMPT_SUBMIT_HOOKS = {"intake-attachments"}
EXPECTED_PRE_TOOL_USE_HOOKS = {"protect-lint-report", "safety-rail"}
EXPECTED_STOP_HOOKS = {"report-doc-status", "intake-attachments", "require-records"}
EXPECTED_POST_TOOL_USE_HOOKS = {"record-image-observation", "record-vision-tool-event"}


def _registered_tools() -> set[str]:
    """Import the builtin tool modules so their registrations exist."""
    import openhands.tools.preset.default  # pyright: ignore[reportMissingImports,reportMissingModuleSource]
    from openhands.sdk.tool.registry import (  # pyright: ignore[reportMissingImports,reportMissingModuleSource]
        list_registered_tools,
    )

    openhands.tools.preset.default.register_default_tools(enable_browser=False)
    import openhands.tools.glob.definition  # noqa: F401  # pyright: ignore[reportMissingImports,reportMissingModuleSource,reportUnusedImport]
    import openhands.tools.grep.definition  # noqa: F401  # pyright: ignore[reportMissingImports,reportMissingModuleSource,reportUnusedImport]
    import openhands.tools.task.definition  # noqa: F401  # pyright: ignore[reportMissingImports,reportMissingModuleSource,reportUnusedImport]

    return set(list_registered_tools())


def check_plugin(plugin_dir: Path) -> list[str]:
    """Return a list of mismatch reasons (empty means OK)."""
    from openhands.sdk.plugin import (  # pyright: ignore[reportMissingImports,reportMissingModuleSource]
        Plugin,
    )

    reasons: list[str] = []
    try:
        plugin = Plugin.load(plugin_dir)
    except Exception as e:  # noqa: BLE001 - surface any loader failure
        return [f"Plugin.load failed: {e}"]

    manifest = json.loads(
        (plugin_dir / ".plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    mcp_config = json.loads((plugin_dir / ".mcp.json").read_text(encoding="utf-8")).get(
        "mcpServers"
    )
    if not isinstance(mcp_config, dict) or set(mcp_config) != {"doc"}:
        server_names = (
            sorted(mcp_config) if isinstance(mcp_config, dict) else mcp_config
        )
        reasons.append(f".mcp.json servers {server_names!r} != ['doc']")
        expected_doc_server = None
    elif not isinstance(mcp_config["doc"], dict):
        reasons.append(".mcp.json server 'doc' must be an object")
        expected_doc_server = None
    else:
        expected_doc_server = mcp_config["doc"]

    if plugin.manifest.version != manifest.get("version"):
        reasons.append(
            f"manifest version {plugin.manifest.version!r} != "
            f"plugin.json {manifest.get('version')!r}"
        )

    plugin_mcp_config = plugin.mcp_config or {}
    if set(plugin_mcp_config) != {"doc"}:
        reasons.append(f"plugin mcp_config keys {sorted(plugin_mcp_config)} != ['doc']")

    agents = {a.name for a in plugin.agents}
    if agents != EXPECTED_AGENTS:
        reasons.append(f"agents {sorted(agents)} != {sorted(EXPECTED_AGENTS)}")

    for agent in plugin.agents:
        agent_mcp_config = agent.mcp_config or {}
        if set(agent_mcp_config) != {"doc"}:
            reasons.append(
                f"agent {agent.name!r} mcp_config keys "
                f"{sorted(agent_mcp_config)} != ['doc']"
            )
            continue
        if not isinstance(expected_doc_server, dict):
            continue
        agent_server = agent_mcp_config["doc"]
        if agent_server.command != expected_doc_server.get(
            "command"
        ) or agent_server.args != expected_doc_server.get("args"):
            reasons.append(
                f"agent {agent.name!r} mcp_config['doc'] command/args "
                "differ from .mcp.json"
            )

    skills = {s.name for s in plugin.skills}
    if skills != EXPECTED_SKILLS:
        reasons.append(f"skills {sorted(skills)} != {sorted(EXPECTED_SKILLS)}")

    commands = {c.name for c in plugin.commands}
    if commands != EXPECTED_COMMANDS:
        reasons.append(f"commands {sorted(commands)} != {sorted(EXPECTED_COMMANDS)}")

    if plugin.hooks is not None:
        hooks = plugin.hooks
        by_event = {
            "session_start": hooks.session_start,
            "user_prompt_submit": hooks.user_prompt_submit,
            "pre_tool_use": hooks.pre_tool_use,
            "stop": hooks.stop,
            "post_tool_use": hooks.post_tool_use,
        }
        collected: dict[str, set[str]] = {
            event_name: {
                h.name for group in groups for h in group.hooks if h.name is not None
            }
            for event_name, groups in by_event.items()
        }
        expected_hooks = {
            "session_start": EXPECTED_SESSION_START_HOOKS,
            "user_prompt_submit": EXPECTED_USER_PROMPT_SUBMIT_HOOKS,
            "pre_tool_use": EXPECTED_PRE_TOOL_USE_HOOKS,
            "stop": EXPECTED_STOP_HOOKS,
            "post_tool_use": EXPECTED_POST_TOOL_USE_HOOKS,
        }
        for event_name, expected in expected_hooks.items():
            if collected[event_name] != expected:
                reasons.append(
                    f"{event_name} hooks "
                    f"{sorted(collected[event_name])} != {sorted(expected)}"
                )

    registered = _registered_tools()
    min_examples = {
        "doc-writer": 3,
        "doc-liaison": 2,
        "doc-review": 2,
        "doc-launch": 3,
    }
    for agent in plugin.agents:
        for tool in agent.tools:
            if tool not in registered:
                reasons.append(f"agent {agent.name!r} tool {tool!r} not registered")
        want = min_examples.get(agent.name, 0)
        if len(agent.when_to_use_examples) < want:
            reasons.append(
                f"agent {agent.name!r} when_to_use_examples "
                f"{len(agent.when_to_use_examples)} < {want}"
            )
    for command in plugin.commands:
        for tool in command.allowed_tools:
            if tool not in registered:
                reasons.append(
                    f"command {command.name!r} allowed-tool {tool!r} not registered"
                )
    return reasons


def main() -> int:
    reasons = check_plugin(PLUGIN_DIR)
    if reasons:
        for r in reasons:
            print(r)
        return 1
    all_hooks = (
        EXPECTED_SESSION_START_HOOKS
        | EXPECTED_USER_PROMPT_SUBMIT_HOOKS
        | EXPECTED_PRE_TOOL_USE_HOOKS
        | EXPECTED_STOP_HOOKS
        | EXPECTED_POST_TOOL_USE_HOOKS
    )
    plugin_summary = (
        f"agents={{{','.join(sorted(EXPECTED_AGENTS))}}} "
        f"skills={{{','.join(sorted(EXPECTED_SKILLS))}}} "
        f"commands={{{','.join(sorted(EXPECTED_COMMANDS))}}} "
        f"hooks={{{','.join(sorted(all_hooks))}}}"
    )
    print(f"plugin-load OK: {plugin_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
