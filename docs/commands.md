# Commands and CLI

## OpenHands commands

| Command | Arguments | Behavior |
| --- | --- | --- |
| `/doc:write` | `[all\|readme\|manual\|tech] [one-line subject]` | Default `all` writes the README, user manual, and technical reference; gathers facts, interviews the user when needed, lints, reviews, and reports open questions. |
| `/doc:launch` | `[all\|page\|press\|demo\|plan] [one-line subject]` | Default `all` writes the product page, press release, demo script, and launch plan using schema 0.2 facts. |
| `/doc:interview` | `[slug] [topic]` | Ask up to five user questions, then store answers verbatim and update inquiry references. |
| `/doc:doctor` | None | Resolve the plugin root and report layout, sister-plugin availability, and inbound liaison counts. |

`/doc:write` and `/doc:launch` delegate only if the current tool list includes
`task_tool_set`; their command instructions provide a fallback otherwise.
`/doc:interview` may end after asking its questions so the user can answer in a
later turn. See [workflow](workflow.md) for generated files and stages.

## `doc_tool.py`

The standard-library CLI is
`plugins/doc/scripts/doc_tool.py`. Record and liaison JSON payloads are read
from a UTF-8 file; `--json -` reads JSON from standard input.

| Invocation | Input and result |
| --- | --- |
| `python3 <plugin-root>/scripts/doc_tool.py record decision --json FILE` | Append a VRP decision; prints one JSON result. |
| `... record impression --json FILE` | Append a hash-bound stage impression. |
| `... record vision-review --json FILE` | Append a vision review bound to an image or existing event. |
| `... record status` | Summarize record counts, session-marker count, and latest Stop status. |
| `... ux inbox` | Validate and list liaison requests targeting doc. |
| `... ux respond --json FILE` | Validate and write the response described by the JSON payload. |
| `... figures --brief PATH` | Inventory figures and Mermaid blocks in brief target documents. |
| `... figure --path PATH` | Return file metadata, including SHA-256, MIME type, and byte size. |
| `... mcp_server` | Start the newline-delimited JSON-RPC MCP server on standard input/output. |

The CLI prints compact JSON. Successful commands exit `0`; an input,
validation, or I/O error prints `{"ok":false,"errors":[...]}` and exits `2`.
The MCP server is the only inline figure-view entry point; there is no
`doc_tool.py` command that returns image bytes.

## `doc_lint.py`

Run the standalone deterministic linter from the workspace root:

```sh
python3 <plugin-root>/skills/doc-lint/scripts/doc_lint.py \
  --brief doc-work/<slug>/doc-brief.json [--root DIR] [--out PATH] \
  [--brief-only] [--no-write]
```

`--root` defaults to the current directory. The default report is
`doc-lint.json` next to the brief. `--brief-only` validates only the brief
and writes no report; `--no-write` performs a full lint without writing one.
Exit `0` means pass, `1` means a valid brief or document failed lint (a full
mode report is still written unless `--no-write`), and `2` means usage,
workspace, or brief-loading failure.

The report is protected by the `protect-lint-report` hook; never edit it by
hand. See [MCP tools](mcp.md) for the equivalent registered tools and
[contracts](contracts.md) for payload schemas.
