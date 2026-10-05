# Hooks

`plugins/doc/hooks/hooks.json` registers the document plugin's hooks. Shell commands resolve the
plugin root through `DOC_PLUGIN_ROOT`, the workspace checkout, `~/.agents/plugins/doc`, then
`~/.openhands/plugins/installed/doc`.

| Event | Matcher | Hook | Behavior and failure mode |
| --- | --- | --- | --- |
| `session_start` | `*` | `require-records` | Starts a VRP session marker; hook errors fail open. |
| `session_start` | `*` | `doc-doctor` | Reports plugin and workspace availability; missing plugin root skips. |
| `session_start` | `*` | `ensure-llm-profiles` | Provisions vision profiles when configured; missing root skips. |
| `session_start` | `*` | `intake-attachments` | Ingests attached files and provenance; unavailable optional inputs skip. |
| `user_prompt_submit` | `*` | `intake-attachments` | Processes prompt attachments; unavailable optional inputs skip. |
| `pre_tool_use` | `file_editor\|apply_patch\|terminal` | `protect-lint-report` | Denies hand edits of lint reports, VRP logs/status/session markers, and protected intake manifests. |
| `pre_tool_use` | `terminal` | `safety-rail` | Applies terminal safety policy; missing root skips. |
| `stop` | `*` | `require-records` | First stop hook; enforces session records with bounded denials and writes `records-status.json`. |
| `stop` | `*` | `report-doc-status` | Reports absent, failed, or stale doc-lint reports; unreadable reports fail closed. |
| `stop` | `*` | `intake-attachments` | Finalizes attachment intake; missing root skips. |
| `post_tool_use` | `inspect_image_with_vision` | `record-vision-tool-event` | Captures an image-tool event for later review binding; missing root skips. |
| `post_tool_use` | `file_editor` | `record-image-observation` | Captures viewed images when available; missing root skips. |

The document plugin's `liaison/*.ux-response.json` files are shared workspace artifacts: a
response may have been created by another sister. The VRP Stop hook requires fresh impressions
only for artifacts changed by the current session; it does not make this plugin the owner of all
liaison responses. Each agent frontmatter repeats the applicable command strings because
sub-agents do not inherit plugin hooks.
