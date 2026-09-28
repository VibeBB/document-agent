# Doc brief contract (schema 0.1)

`doc-work/<slug>/doc-brief.json` is the fact ledger for one product's
documentation. The doc writer creates it before writing any document;
`plugins/doc/skills/doc-lint/scripts/doc_lint.py` validates it fail-closed and
lints every target document against it. A complete, passing example is
`plugins/doc/skills/doc-lint/examples/desk-timer/`.

## Work directory

| File | Written by | Contents |
| --- | --- | --- |
| `context.md` | parent (`/doc:write`) | conversation summary, each item tagged `[conversation]`, `[file:<path>]`, or `[git]` |
| `survey.md` | `doc-liaison` | facts found in the workspace and sibling artifacts, missing facts, conflicts |
| `inquiries.md` | `doc-liaison`, `/doc:interview` | questions to siblings and to the user, with status and answers |
| `interview.md` | `/doc:interview` | the user's answers, verbatim, as `A1`, `A2`, … |
| `doc-brief.json` | `doc-writer` | this contract |
| `outline.md` | `doc-writer` | reader journeys, diagram plans, shared terminology |
| `review.md` | `doc-writer` | `doc-review` findings and their disposition |
| `doc-lint.json` | `doc_lint.py` only | the lint report (hand edits are denied by a hook) |

## Brief

Unknown keys are rejected at the top level and in `product`.

| Key | Type | Rule |
| --- | --- | --- |
| `artifact_kind` | string | `"doc_brief"` |
| `schema_version` | string | `"0.1"` |
| `language` | string | `"ja"` or `"en"` |
| `product.name` | string | 1..80 chars; must appear in every target document |
| `product.tagline` | string | 1..140 chars |
| `product.summary` | string | 1..1200 chars |
| `product.audience` | string[] | 1..6 items |
| `product.problem` | string | 1..800 chars |
| `product.value` | string[] | 1..6 items |
| `product.vision` | string | optional, 1..1200 chars; only with `vision_source` |
| `product.vision_source` | string | a source id of kind `user_interview` |
| `targets` | object[] | 1..3 `{kind, path}` |
| `sources` | object[] | at least one `{id, kind, ref[, agent]}` |
| `facts` | object[] | at least one `{id, text, sources}` |
| `inquiries` | object[] | optional `{id, to, question, status[, answer, source]}` |
| `open_questions` | string[] | optional, 0..50 items |

### Targets

- `kind`: `readme`, `user_manual`, `technical_reference` — each at most once.
- `path`: a relative POSIX path ending in `.md`, without `..`, unique.
- `quality_plan`, `test_report`, `risk_assessment`, `inspection_record` are
  reserved for a later schema and rejected (ADR-0005).

### Sources

- `id`: `S<n>`, unique.
- `kind`: `file`, `git_log`, `conversation`, `user_interview`,
  `sibling_agent` (an answer from a sibling agent via `task`),
  `sibling_artifact` (a file a sibling wrote).
- `ref`: where to find it — a path, `path#anchor`, or a commit range.
- `agent`: required for the two sibling kinds, forbidden otherwise; one of
  `wire`, `mech`, `circuit`, `ux`, `bard`.

### Facts

- `id`: `F<n>`, unique; `text`: 1..800 chars.
- `sources`: at least one id from `sources`. A claim without a source is not
  a fact and must not appear in any document.

### Inquiries

- `id`: `Q<n>`, unique; `to`: a sibling name or `"user"`.
- `status`: `answered`, `unanswered`, or `not_available` (the sibling is not
  installed or could not answer).
- `answered` requires `answer` and a `source`: for `to: user` a
  `user_interview` source, otherwise a sibling source whose `agent` equals
  `to`. `answer`/`source` are forbidden for other statuses.

## Document rules

Every target document:

- is UTF-8 and starts with exactly one H1 heading;
- names the product as in `product.name`;
- contains no placeholders outside code blocks (`TODO`, `TBD`, `FIXME`,
  `XXX`, `lorem ipsum`, `<placeholder>`, `要確認`, `未定`);
- closes every code fence; every `mermaid` block starts with a known diagram
  type and has a body;
- has relative links that stay inside the root and resolve.

Per kind (section names match English or Japanese keywords on H2/H3):

| Kind | Rules |
| --- | --- |
| `readme` | a product-explanation H2 and a diagram (Mermaid block or image) before the `Quick start` / `クイックスタート` section; the quick start has 2..7 numbered steps; links to every other target |
| `user_manual` | a usage section (`How to use`, `使い方`, …) and a troubleshooting / FAQ section |
| `technical_reference` | an architecture section containing a diagram; an interface / specification section; a development / build / test section |

## Report

`doc-lint.json` (next to the brief unless `--out` is given) is deterministic
(sorted keys, no timestamps):

```json
{
  "artifact_kind": "doc_lint_report",
  "schema_version": "0.1",
  "linter": "doc_lint.py 0.1.0",
  "mode": "full",
  "verdict": "pass",
  "brief": {"path": "doc-work/<slug>/doc-brief.json", "sha256": "<hex>"},
  "brief_problems": [],
  "documents": [
    {"kind": "readme", "path": "README.md", "sha256": "<hex>", "problems": []}
  ],
  "unanswered_inquiries": 0,
  "open_questions": 0
}
```

`sha256` is `null` for a missing or undecodable document. The Stop hook
compares these hashes with the current files and reports a changed brief or
document as `stale`.

## CLI

```bash
python3 <doc plugin root>/skills/doc-lint/scripts/doc_lint.py --brief doc-work/<slug>/doc-brief.json [--brief-only] [--no-write] [--root DIR] [--out PATH]
```

Exit `0` pass, `1` fail (the report is still written in full mode), `2`
usage error or unreadable brief (nothing written).
