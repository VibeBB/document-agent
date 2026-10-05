# Doc brief contract (schema 0.1 / 0.2)

`doc-work/<slug>/doc-brief.json` is the fact ledger for one product's
documentation. The doc writer creates it before writing any document;
`plugins/doc/skills/doc-lint/scripts/doc_lint.py` validates it fail-closed and
lints every target document against it. A complete, passing example is
`plugins/doc/skills/doc-lint/examples/desk-timer/`; a passing schema 0.2
launch example is `plugins/doc/skills/doc-lint/examples/desk-timer-launch/`.

Schema 0.2 is schema 0.1 plus the marketing/launch target kinds and the
`launch` block (ADR-0006). Source kinds follow this contract in both schema
versions; retired source-kind names are rejected.

## Work directory

| File | Written by | Contents |
| --- | --- | --- |
| `context.md` | parent (`/doc:write`) | conversation summary, each item tagged `[conversation]`, `[file:<path>]`, or `[git]` |
| `survey.md` | `doc-liaison` | facts found in the workspace and sister artifacts, missing facts, conflicts |
| `inquiries.md` | `doc-liaison`, `/doc:interview` | questions to sisters and to the user, with status and answers |
| `interview.md` | `/doc:interview` | the user's answers, verbatim, as `A1`, `A2`, … |
| `doc-brief.json` | `doc-writer` | this contract |
| `outline.md` | `doc-writer` | reader journeys, diagram plans, shared terminology |
| `review.md` | `doc-writer` | `doc-review` findings and their disposition |
| `launch-outline.md` | `doc-launch` | per-target reader, messages, and the fact behind every number |
| `launch-review.md` | `doc-launch` | `doc-review` launch findings and their disposition |
| `doc-lint.json` | `doc_lint.py` only | the lint report (hand edits are denied by a hook) |

## Brief

Unknown keys are rejected at the top level, in `product`, and in each source
object.

| Key | Type | Rule |
| --- | --- | --- |
| `artifact_kind` | string | `"doc_brief"` |
| `schema_version` | string | `"0.1"`, or `"0.2"` for launch kinds and `launch` |
| `language` | string | `"ja"` or `"en"` |
| `product.name` | string | 1..80 chars; must appear in every target document |
| `product.tagline` | string | 1..140 chars |
| `product.summary` | string | 1..1200 chars |
| `product.audience` | string[] | 1..6 items |
| `product.problem` | string | 1..800 chars |
| `product.value` | string[] | 1..6 items |
| `product.vision` | string | optional, 1..1200 chars; only with `vision_source` |
| `product.vision_source` | string | a source id of kind `user_interview` |
| `targets` | object[] | 1..3 `{kind, path}` (0.1), 1..7 (0.2) |
| `sources` | object[] | at least one `{id, kind, ref[, agent, sha256, event_id]}`; allowed keys depend on `kind` |
| `facts` | object[] | at least one `{id, text, sources}` |
| `inquiries` | object[] | optional `{id, to, question, status[, answer, source]}` |
| `open_questions` | string[] | optional, 0..50 items |
| `launch` | object | 0.2 only; required with a launch target, forbidden without one |

### Targets

- `kind`: `readme`, `user_manual`, `technical_reference` — each at most once.
  Schema 0.2 adds the launch kinds `product_page`, `press_release`,
  `demo_script`, and `launch_plan`; a 0.1 brief naming one is rejected.
- `path`: a relative POSIX path ending in `.md`, without `..`, unique.
- `quality_plan`, `test_report`, `risk_assessment`, `inspection_record` are
  reserved for a later schema and rejected (ADR-0005).

### Sources

- `id`: `S<n>`, unique.
- `kind`: `file`, `git_log`, `conversation`, `user_interview`, `sister_agent`,
  `sister_artifact`, or `sister_record`.
- `ref`: where to find it — a path, `path#anchor`, or a commit range.
- `agent`: required for each sister kind, forbidden otherwise; one of
  `bard`, `circuit`, `dashboard`, `firmware`, `fpga`, `mech`, `prodeng`,
  `sim`, `ux`, `wire`.
- `sha256`: optional for `file` and required for `sister_artifact`. It is the
  file SHA-256 or deterministic tree SHA-256 for a directory. The linter
  checks current hashes in every mode and reports a changed source.
- `event_id`: required only for `sister_record`; it is a lowercase SHA-256
  event ID from the selected sister's decision, impression, or vision-review
  log. Its `ref` must be exactly
  `observations/<agent>/decisions.jsonl`,
  `observations/<agent>/impressions.jsonl`, or
  `observations/<agent>/vision-reviews.jsonl`. The linter verifies the event
  exists there and the record's `plugin` equals `agent`.

### Facts

- `id`: `F<n>`, unique; `text`: 1..800 chars.
- `sources`: at least one id from `sources`. A claim without a source is not
  a fact and must not appear in any document.

### Inquiries

- `id`: `Q<n>`, unique; `to`: a sister name or `"user"`.
- `status`: `answered`, `unanswered`, or `not_available` (the sister is not
  installed or could not answer).
- `answered` requires `answer` and a `source`: for `to: user` a
  `user_interview` source, otherwise a `sister_agent` or `sister_artifact`
  source whose `agent` equals `to`. `answer`/`source` are forbidden for
  other statuses.

### Launch (schema 0.2)

Unknown keys are rejected in `launch` and in each entry.

| Key | Rule |
| --- | --- |
| `audiences` | 1..6 `{id: A<n>, name (1..120), insight (1..400), facts: [F<n>, ...]}` |
| `messages` | 1..12 `{id: M<n>, text (1..200), audiences: [A<n>, ...], facts: [F<n>, ...], targets: [kind, ...]}`; `targets` are launch kinds present in `targets` |
| `channels` | optional, 0..12 `{id: C<n>, kind, audiences, messages}`; `kind` is `product_page`, `press`, `social`, `video`, `email`, `event`, `crowdfunding`, `store`, or `community` |
| `call_to_action` | `{text (1..120), facts: [F<n>, ...]}` — the facts are typically price and availability |

Every id list is non-empty and every id must exist.

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
| `technical_reference` | an architecture section containing a diagram; an interface / specification section; a development / build / test section; if any `sister_record` source is present, a rationale section whose H2/H3 heading matches `rationale`, `設計根拠`, or `設計判断` |
| `product_page` | shows `product.tagline`; a diagram or image; a features / benefits section; a call-to-action section containing `launch.call_to_action.text` |
| `press_release` | the first paragraph after the headline names the product; an About section; a media contact section |
| `demo_script` | a table whose header has time, visual, and narration / audio columns |
| `launch_plan` | audience, message, channel, and checklist / schedule sections; >=2 task items (`- [ ]`) in the checklist; every audience name appears |

Claim rules for every launch kind:

- A superlative or absolute (`best`, `No. 1`, `world's first`, `guaranteed`,
  `世界初`, `最高`, `唯一`, `保証`, …) outside code must appear in a fact.
- Each `launch.messages[].text` appears verbatim in every kind it targets.
- In `product_page` and `press_release`, every number in prose and tables
  (outside code blocks, inline code, and link targets; the product name is
  ignored) must appear in a fact.

The README's "links to every other target" rule covers only `user_manual` and
`technical_reference`.

## Report

`doc-lint.json` (next to the brief unless `--out` is given) is deterministic
(sorted keys, no timestamps):

```json
{
  "artifact_kind": "doc_lint_report",
  "schema_version": "0.1",
  "linter": "doc_lint.py 0.2.0",
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
