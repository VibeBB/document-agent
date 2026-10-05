# Contracts

The canonical brief and lint-report specification is
[doc-brief-contract.md](doc-brief-contract.md); the linter, not prose here,
is authoritative for accepted payloads. This page indexes the workspace
interfaces introduced for records and sister cooperation.

## Brief and lint report

- `doc-work/<slug>/doc-brief.json` is the fact ledger and names the target
  Markdown documents. Schema 0.1 is used for product documentation; schema
  0.2 adds launch audiences, messages, channels, and calls to action.
- Each published claim is linked to one or more typed sources. Unknown
  details remain in inquiry or open-question fields rather than becoming
  document prose.
- Source kinds include `workspace_file`, `user_interview`, `sister_agent`,
  `sister_artifact`, and `sister_record`. Sister facts include the owner,
  current source path/hash, and—when applicable—the VRP event reference.
- `doc-lint.json` is a generated full-mode report. It binds the brief and
  each target to SHA-256 values. A content change makes the old report stale;
  only `doc_lint.py` may write it.
- A technical reference that relies on a `sister_record` includes a rationale
  section that explains the decision in the product’s design context. A
  record citation by itself does not explain why the decision matters to a
  reader.

See [sister cooperation](sister-cooperation.md) for fact ownership and
[commands](commands.md#doc_lintpy) for linter modes and exit codes.

## VRP v1 records

Record inputs are closed JSON objects; their required and optional keys are
enumerated in `plugins/doc/scripts/records-schemas.json`. Writers construct
the event envelope and `_records.py` revalidates stored events at Stop.
Unknown keys, malformed hashes, unsafe paths, or missing referenced
artifacts are rejected. The MCP tool descriptions expose the input schemas.

| Record | Required content | Stored log |
| --- | --- | --- |
| `decision` | Stable record ID, stage/question, principles, options, chosen option, rationale, risks, revisit condition, and evidence; assumptions, unknowns, and actor are optional. | `observations/doc/decisions.jsonl` |
| `stage_impression` | Stage, completed impression, and artifact paths with their current SHA-256 hashes. | `observations/doc/impressions.jsonl` |
| `vision_review` | Model, checklist, long-form impression, and either an image path or source event ID; optional findings use `info`, `warning`, or `error`. | `observations/doc/vision-reviews.jsonl` |
| `vision-tool-event` | Successful `inspect_image_with_vision` call identity, model/profile, question, response SHA-256, and provenance metadata. | `observations/doc/vision-tool-events.jsonl` |
| `image-observation` | Viewed image path and SHA-256 plus tool/session provenance. | `observations/doc/image-observations.jsonl` |

The shared validator requires a stage impression and vision review to contain
at least 400 characters and three sentences. Event IDs and sequence numbers
are validated. Record histories are append-only. The `records-status.json`
file is a hook-managed last-verdict snapshot, not a VRP event log.

A decision requires a question of at least 10 characters, one or more
principles (at least 12 characters each), two or more options with distinct
names and non-empty pros/cons, a chosen option name, a rationale of at least
200 characters, at least one risk and evidence item, and a revisit condition.
Evidence may bind a workspace path or provide a reference. `decided_by` is
`agent` or `user`.

## VRP policy

`plugins/doc/hooks/records-policy.json` declares schema version `1`, plugin
`doc`, records directory `observations/doc`, and the artifact globs checked by
the Stop hook: `doc-work/*/*.json`, `doc-work/*/*.md`,
`doc-work/*/figures/*`, and `liaison/*.ux-response.json`. It ignores
`examples/**`, `tests/**`, and `.devin/**` when looking for changed artifacts.
The maximum Stop denial count is `2`; the policy also carries the hint shown
when records are missing.

## SLP v2 request

Requests are stored as `liaison/<id>.ux-request.json`. They use
`schema_version: 2` and `system: "ux-creator"`, and contain `id`,
`target_agent`, `stage`, `risk`, `purpose`, `rationale`, `requested_changes`,
`inputs` (workspace paths with SHA-256 hashes), `expected_deliverables`,
`acceptance`, `depends_on`, and timezone-aware `created_at`. Stages are
`requirements`, `design`, `manufacturing_handoff`, `build`, `evaluation`, and
`revision`; risk is `low` or `high`. Purpose is at least 20 characters, and
high-risk rationale is at least 20 characters. Requested changes,
deliverables, and acceptance criteria must each contain at least one entry.
Supported target agents are `bard`, `circuit`, `dashboard`, `doc`,
`firmware`, `fpga`, `mech`, `prodeng`, `sim`, and `wire`.

The validator checks the schema, safe relative workspace paths, timestamp,
hash syntax and input freshness. Request filenames must agree with request
IDs. Requests are not trusted facts: the receiver inspects the cited files
and validates the answer’s current hashes.

## SLP v2 response

Responses use the same `schema_version: 2` and `system: "ux-creator"` and are stored as
`liaison/<id>.ux-response.json`. The closed response object contains
`request`, `responder`, `status`, `reason`, `input_hashes`, `artifacts`
(path plus tree SHA-256), `gate_verdicts`, `decision_refs`,
`impression_refs`, `questions_for_user`, and `responded_at`.

Allowed statuses are `accepted`, `in_progress`, `done`, `rejected`,
`deferred`, and `needs_info`; gate verdicts are `pass`, `fail`, and
`unknown`. `needs_info` requires a user question. Reasons are at least 20
characters except for `accepted` and `in_progress`. Missing request
inputs only permit `needs_info` or `rejected`; changed inputs prevent
`done`. The receiver’s decision and impression references must resolve to
events in the doc record logs.

A `done` response additionally requires all declared gates to pass and a
passing `doc-lint` gate; at least one decision and impression reference; a
fresh passing full lint report covering each claimed Markdown artifact; and
current artifact/input hashes. See [MCP](mcp.md#liaison-tools) for invocation
and [sister cooperation](sister-cooperation.md) for lifecycle behavior.

## Path and hash rules

Workspace paths are relative to the active workspace, must resolve inside it,
and cannot traverse through symlinks outside the workspace. Files use a
SHA-256 of their bytes; directory artifacts use a deterministic tree hash
over their files. The responder recomputes hashes rather than trusting
caller-supplied artifact digests.
