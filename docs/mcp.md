# MCP tools

The doc MCP server is a small newline-delimited JSON-RPC process implemented
with Python’s standard library. The plugin’s `.mcp.json` starts
`python3 <plugin-root>/scripts/doc_tool.py mcp_server`. The active workspace
is `$OPENHANDS_PROJECT_DIR` when set, otherwise the current directory.
There is no separate MCP package dependency.

The server implements `initialize`, `ping`, `tools/list`, and `tools/call`.
`resources/list`, `resources/templates/list`, and `prompts/list` return empty
lists. Unknown methods return JSON-RPC `-32601`; invalid requests return
`-32600`. `tools/call` results contain `content`, `structuredContent`, and
`isError`. A caught input or I/O error is returned as
`{"ok":false,"errors":[...]}` with `isError: true`.

The following are all tools registered in `plugins/doc/scripts/doc_mcp.py`.
The tool input schemas declare `additionalProperties: false`, but runtime
validation is handler-specific. Record handlers validate their payloads;
`doc_lint` and figure handlers may ignore extra keys rather than reject them.
Do not rely on schema declarations alone to enforce unknown-key rejection.

## Record tools

| Tool | Arguments | Result and effects |
| --- | --- | --- |
| `doc_record_decision` | Decision input: `id`, `stage`, `question`, `principles`, `options`, `chosen`, `rationale`, `risks`, `revisit_when`, and `evidence` are required. Each option has `name`, non-empty `pros`, and non-empty `cons`; at least two uniquely named options are required. `assumptions`, `unknowns`, and `decided_by` are optional. See [contracts](contracts.md#vrp-v1-records). | Appends a `decision` event to `observations/doc/decisions.jsonl`; path and complete record are returned. Artifact evidence is hashed. |
| `doc_record_impression` | `stage`, non-empty `artifacts` paths, and `impression`. | Appends a `stage_impression` to `observations/doc/impressions.jsonl`; each artifact is bound to its current file/tree SHA-256. Impression requirements are in [records and vision](records-and-vision.md). |
| `doc_record_vision_review` | `model`, `checklist`, and `impression`; at least one of `image_path` or `source_event_id`; optional `findings` entries with `category`, `severity` (`info`, `warning`, `error`), and `note`. | Appends a `vision_review` to `observations/doc/vision-reviews.jsonl`. A path is bound to the current image SHA-256; an event reference must exist. |
| `doc_records_status` | No arguments. | Returns record counts by kind, number of session markers, and `latest_status` from `records-status.json` when present. Read-only. |

All record tools return `ok: false` and validation errors for invalid
payloads, missing files, invalid paths, or schema violations. Record writes
are append-only; they do not alter a lint verdict.

## Liaison tools

| Tool | Arguments | Result and effects |
| --- | --- | --- |
| `doc_ux_inbox` | No arguments. | Returns `requests`, `malformed`, and state `counts` for requests addressed to doc. Read-only. |
| `doc_ux_respond` | `request`, `status`, `artifacts` (workspace paths), `gate_verdicts` (objects with `gate` and `verdict: pass\|fail\|unknown`), `decision_refs`, `impression_refs`, and `questions_for_user`; optional `reason`. See [SLP v2](contracts.md#slp-v2). | Writes `liaison/<request>.ux-response.json` and returns its path and response. The responder hashes inputs and artifacts and validates event references. |

Inbox request entries report `new`, `answered`, `stale`, or `blocked`;
malformed request or response files are returned with their path and errors.
The response status is one of `accepted`, `in_progress`, `done`, `rejected`,
`deferred`, or `needs_info`. Validation failures return `ok: false`; a
`needs_info` response requires at least one question. A `done` response is
rejected unless all gates pass, includes a passing `doc-lint` gate, references
at least one decision and impression, and its Markdown artifacts are covered
by a fresh passing report.

## Lint and figure tools

| Tool | Arguments | Result and effects |
| --- | --- | --- |
| `doc_lint` | Required `brief`; optional `mode` is `full` (default) or `brief_only`. | Returns the deterministic report under `report`. Full mode writes `doc-lint.json` next to the brief; brief-only validates without writing. A report with `verdict: fail` is still a successful tool invocation (`ok: true`, `isError: false`); inspect the report verdict. |
| `doc_figures` | Required `brief`. | Returns `documents` and `figures` for target documents; reports Mermaid-block counts, image paths, existence, hash, MIME, and matching review event IDs. Read-only. |
| `doc_figure` | Required `path`. | Returns path, existence, SHA-256, MIME type, and `size_bytes`; read-only. |
| `doc_view_figure` | Required `path`. | Returns a supported image inline plus path, SHA-256, and an observation `event_id`. The MCP `content` contains an image block and a text block. On failure, returns `ok: false` with an error message. |

Figure tools resolve paths inside the active workspace. `doc_view_figure`
accepts PNG, JPEG, GIF, or WebP image files up to 5 MiB, checks file
signatures, and refuses SVG or unsupported formats. A successful view appends
an image-observation event; record a vision review against that event or the
image path.

## Result and failure details

- Normal results are exposed as compact JSON text and as structured content.
- If a handler returns `ok: false`, `isError` is true. Reported input errors,
  unknown tools, missing files, unsafe paths, and invalid records follow this
  error path. Extra-key handling depends on the runtime handler.
- `doc_lint` distinguishes invocation failure from a lint failure: if it
  successfully produced a report, inspect `report.verdict` and
  `report.brief_problems`/`report.documents[].problems`.
- `doc_view_figure` returns both structured metadata and image content. The
  image bytes are base64 encoded by the tool protocol; the MCP client renders
  the image.
- The server does not expose prompts or resources. Direct CLI alternatives
  are listed in [commands](commands.md).
