# Hooks

Hooks are configured in `plugins/doc/hooks/hooks.json`. Each command resolves
the plugin root by trying `DOC_PLUGIN_ROOT`,
`$OPENHANDS_PROJECT_DIR/plugins/doc`, `$HOME/.agents/plugins/doc`, and
`$HOME/.openhands/plugins/installed/doc`, then runs a host `python3` script.
Hooks that cannot find the plugin root usually skip; the lint-report guard
instead fails closed. The shared `require-records` and safety scripts are
standard-library copies of family-level hooks; do not edit them independently.

## Event matrix

| Event | Matcher | Hook | Behavior and fail mode |
| --- | --- | --- | --- |
| `session_start` | `*` | `require-records` (`session-start`) | Creates the session marker under `observations/doc/.sessions/` used to delimit new work. Policy or I/O errors print a skip note and exit `0`. |
| `session_start` | `*` | `doc-doctor` | Advises on plugin layout, installed sister plugins, and unanswered inbound liaison requests. Always emits an allow context and exits `0`, including when the probe fails. |
| `session_start` | `*` | `ensure-llm-profiles` | Copies the active OpenHands LLM profile into missing `vibebb-author` and `vibebb-review` profiles without overwriting existing ones; reports review-profile vision capability. Advisory and exits `0`. |
| `session_start` | `*` | `intake-attachments` | Scans available AgentCanvas events for user-attached images; materializes recognized data URLs, deduplicates by SHA-256, and appends an intake manifest. Idempotent and always exits `0`; unavailable remote event storage is a no-op, so attachments can be placed in `intake/` manually. |
| `user_prompt_submit` | `*` | `intake-attachments` | Repeats attachment intake to capture newly attached images. Same idempotent, non-blocking behavior as SessionStart. |
| `pre_tool_use` | `file_editor\|apply_patch\|terminal` | `protect-lint-report` | Denies writes to `doc-lint.json`, `observations/doc/*.jsonl`, record status/session files, and the attachment manifest. Allows reads and ordinary editable brief/document files. Invalid hook input or protected writes exit `2`; unresolved plugin root exits `2`. |
| `pre_tool_use` | `terminal` | `safety-rail` | Denies its explicit destructive-command, device-write, power-command, and prohibited-git-operation patterns. It is a narrow pattern matcher, not a general shell security analyzer; ambiguous or unrecognized commands pass. Invalid JSON exits `2`; a recognized denial exits `2`; otherwise exits `0`. |
| `stop` | `*` | `require-records` (`stop`) | Validates this session’s records, vision reviews, fresh impressions for changed artifacts, and a decision when artifacts changed. Writes the last pass/fail to `records-status.json`; denies finish for up to two attempts, then allows with the gaps reported in context. Hook errors skip with a stderr note and exit `0`. |
| `stop` | `*` | `report-doc-status` | Reports each `doc-work/*/doc-brief.json` lint state (`pass`, `stale`, `fail`, or no report), unanswered inquiries/open questions, and unreviewed figures. Allows when it can inspect the workspace; unreadable briefs/reports print an error and exit `1`. |
| `stop` | `*` | `intake-attachments` | Final idempotent attachment scan; always exits `0`. |
| `post_tool_use` | `inspect_image_with_vision` | `record-vision-tool-event` | Records only successful non-empty vision answers with model/profile, question, response hash, identity, and event ID. Errors, malformed input, or unavailable storage do not block the tool/session. |
| `post_tool_use` | `file_editor` | `record-image-observation` | Records successful `file_editor` `view` actions on existing PNG/JPG/JPEG paths, binding the path to the image SHA-256. Other file types, errors, and non-view actions are ignored; log errors are reported to stderr without blocking. |

## Protected paths and hand-managed results

`protect-lint-report` examines path-bearing tool inputs rather than arbitrary
file contents. For terminal calls it checks write operators and known
destination-taking commands; read-only inspection is allowed. Protected
reports and logs must be written through their producer: run `doc_lint.py`
for `doc-lint.json`, record tools for VRP JSONL, the Stop hook for the status
file, and attachment intake for the manifest.

The safety rail parses commands with `shlex` and checks a small explicit
denylist: root/home recursive forced deletion, block-device writes, selected
partition/filesystem/power tools, `kill -1`, and git operations prohibited by
the repository agreement. It allows commands it cannot positively identify
as prohibited. Do not rely on it as a substitute for careful review.

## Installation and agent hooks

Plugin hooks are not inherited by delegated agents. Each of the four
`AgentDefinition` files repeats the terminal safety rail and lint-report
guard in its own `pre_tool_use` list. The MCP server and hook launchers both
use the plugin-root resolution chain above. Missing optional attachment,
vision, or doctor context is advisory; record gate errors are bounded as
described in the event matrix.
