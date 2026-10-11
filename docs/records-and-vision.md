# Records and vision

doc follows the VibeBB Record Protocol (VRP) v2 — the same chained,
append-only logs every sibling keeps under `observations/<plugin>/`; the
family specification is `wire-agent` `docs/records-protocol.md`. Records are
advisory evidence of how a documentation result was produced. They are not a
source of product facts unless the brief cites a record explicitly, and they
never change the deterministic lint verdict.

## Record locations

| Path | Contents |
| --- | --- |
| `observations/doc/decisions.jsonl` | Consequential choices, alternatives, rationale, risks, and evidence |
| `observations/doc/impressions.jsonl` | Structured, grounded stage impressions bound to artifacts |
| `observations/doc/vision-reviews.jsonl` | Primary, blind and tiebreak reviews bound to an image hash or vision-tool event |
| `observations/doc/reconciles.jsonl` | Agreement or split between the reviews of one dual-review image |
| `observations/doc/insights.jsonl` | Adopted, deferred and rejected insight status |
| `observations/doc/reads.jsonl` | Read receipts for sister artifacts taken in |
| `observations/doc/song-receipts.jsonl` | Receipts for bard songs addressed to doc |
| `observations/doc/vision-tool-events.jsonl` | Successful `inspect_image_with_vision` calls, with answer hash rather than full answer |
| `observations/doc/image-observations.jsonl` | Successfully viewed images and their hashes |
| `observations/doc/records-status.json` | Most recent Stop-hook pass/fail and outstanding record problems |
| `observations/doc/.sessions/<session>.json` | Session start time and bounded Stop-denial count |

Every record line carries `schema_version` 2, `sequence`, `prev_event_id`,
`writer` and `event_id` (the sha256 of the canonical record). The writer
verifies the chain before appending and refuses a log that was edited,
truncated or reordered; readers report such a log under
`integrity_problems` and never resolve references into it. A log written
entirely by VRP v1 is renamed to `<name>.v1.jsonl` on the first v2 write.
Records are written only through `doc_tool.py record …`, the
`doc_record_*` MCP tools or the hooks; `protect-lint-report` denies hand
edits.

## What a record must contain

A **decision** names ≥2 options with pros and cons, principles, ≥1 evidence
reference bound by sha256, assumptions, unknowns, risks and a revisit
trigger.

A **stage impression** follows every completed stage:

- prose ≥400 characters and ≥3 sentences, refused when it is a near
  duplicate of an earlier impression of the same stage;
- `facets`: ≥2 `observed`, `works`, `concerns` (id, severity, `about`,
  anchor), `feelings.maker` / `feelings.user`, `next_actions`;
- ≥2 `claims`, each an exact token (`anchor`) of the cited text artifact (a
  brief fact, a heading, a label), checked against the file bytes;
- `confidence`, `unknowns`, optional `insights` and `upstream` answers.

`record digest` lists open sister concerns and unanswered reads; answer each
one acted on in `upstream` (`adopted` / `deferred` / `disputed` / `noted`).
A disputed concern cannot be raised again while the artifact bytes are
unchanged, and a rejected insight is only re-proposed with `revisits` and a
reason. `record search` filters every sister log by text, kind, stage,
artifact or severity. `record status` runs before finishing.

## Blind figure review

A vision review carries the same facets, claims and confidence, plus a
`lookback` verdict per claim. `dual_review_globs`
(`doc-work/*/figures/*.png`) require a `blind` review by `doc-blind-review`,
whose `blind-guard` hook hides earlier reviews and records, and a
`record reconcile` of `[primary, blind]`; a split gets one `tiebreak` round
(at most 2 rounds) and stays `unknown` if unresolved.

## Bard songs

bard may address a song to doc as an immutable, sha-pinned
`liaison/<id>.bard-song.json`. SessionStart lists songs still waiting; doc
answers with `record song-receipt` (`delivery`, `felt`,
`prompted_review`, optional `follow_up`). The receipt pins the delivery
sha256, is accepted once per delivery, and never asks bard for another
song, so the exchange cannot loop.

## Session requirements

At SessionStart, `require-records` writes a marker and recalls open sister
concerns and waiting songs. At Stop it checks records since that marker
according to `plugins/doc/hooks/records-policy.json` and:

- verifies every log chain and validates every new record;
- requires a vision review for each successful vision-tool event and each
  distinct viewed-image hash;
- requires a blind review and reconcile for each changed dual-review image;
- requires a fresh stage impression covering each changed path selected by
  `records-policy.json` globs; and
- requires at least one decision if any covered artifacts changed.

The stop hook denies completion at most twice (`max_stop_denials`). If
requirements remain unmet, the next Stop is allowed with the missing records
included in context, and the last fail remains recorded. `report-doc-status`
separately warns about stale or missing lint reports, open questions,
unanswered inquiries, and figures without reviews. Findings are categorized
as `info`, `warning`, or `error`; they are observations, not pass/fail
judgments.

## Figures and image viewing

`doc_figures` reads target Markdown documents from the brief and inventories
image links and Mermaid blocks. It reports missing figures, file metadata,
SHA-256, and linked review event IDs. `doc_figure` returns metadata for one
workspace file. These tools are read-only.

`doc_view_figure` returns a supported image inline and appends an
image-observation event. It accepts PNG, JPEG, GIF, and WebP up to
5 MiB (5,242,880 bytes), validates the file signature, and rejects SVG and
unsupported formats. A successful view returns an event ID; record the
review against that ID or the image path. The tool’s size and format checks
bound the bytes sent for inline inspection.

The `inspect_image_with_vision` post-tool hook records successful calls
without the image answer text, binding the event to the model/profile,
question, response hash, and tool-call provenance. `record-image-observation`
captures direct PNG/JPG/JPEG views made through `file_editor`. A vision review
must cite the relevant event or image, and the image hash must still match.

Vision observations are advisory. They may identify readability, missing
labels, confusing relationships, or visible concerns; they do not validate
electrical, mechanical, thermal, regulatory, or other engineering safety.
Any uncertainty or issue is handed back to the responsible sister or user.
