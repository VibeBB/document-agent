# Agents

Agent definitions are under `plugins/doc/agents/`. They share the doc MCP
server and the hooks declared in their frontmatter because plugin-level hooks
are not inherited by task sub-agents. All use `permission_mode: never_confirm`.

| Agent | Role | Model profile | Tools | Per-run limit |
| --- | --- | --- | --- | --- |
| `doc-liaison` | Survey workspace and sister evidence, write survey/inquiry files, and identify user questions; never writes product documents | `vibebb-author` | `terminal`, `file_editor`, `grep`, `glob`, `task_tool_set` | 60 iterations; budget 3.0 |
| `doc-writer` | Create brief, outline, README/manual/technical reference, lint, and incorporate review | `vibebb-author` | `terminal`, `file_editor`, `grep`, `glob`, `task_tracker`, `task_tool_set` | 120 iterations; budget 6.0 |
| `doc-review` | Review as first-time visitor, user, engineer, and (for launch material) buyer; return findings only | `vibebb-review` | `terminal`, `file_editor`, `grep`, `glob` | 30 iterations; budget 1.5 |
| `doc-launch` | Produce fact-grounded product page, press release, demo script, and launch plan | `vibebb-author` | `terminal`, `file_editor`, `grep`, `glob`, `task_tracker`, `task_tool_set` | 120 iterations; budget 6.0 |

The model profile names resolve through the OpenHands profile store. On
SessionStart, `ensure_llm_profiles.py` copies the active profile into a
missing `vibebb-author` or `vibebb-review` profile; it does not overwrite an
existing profile. An operator can route author and review work to different
models by editing those profiles.

`task_tool_set` is needed to delegate to sister agents and to run the
liaison/writer/reviewer stages as separate agents. The command prompts inspect
the tools actually available and use a parent-process fallback when task
delegation is absent. Task agents must read their workspace files because
they do not receive the parent’s conversation history.

The `doc-review` definition includes a file-editor tool for reading artifacts,
but its prompt contract is read-only: it reports findings and does not modify
the target documents. The deterministic linter, not an agent, owns the
`doc-lint.json` report.

Agent MCP configuration resolves the plugin root in this order:
`DOC_PLUGIN_ROOT`, `$OPENHANDS_PROJECT_DIR/plugins/doc`,
`$HOME/.agents/plugins/doc`, `$HOME/.openhands/plugins/installed/doc`,
`$HOME/plugins/installed/doc`, and
`$OH_PERSISTENCE_DIR/plugins/installed/doc`. It launches
`python3 <plugin-root>/scripts/doc_tool.py mcp_server`.
