# Records and vision

The VibeBB Record Protocol (VRP) is an append-only account of documentation
decisions, completed stages, and image/vision observations. It supports
traceability, but is not a source of product facts unless the brief cites a
record explicitly, and it never changes the deterministic lint verdict.

## Record locations

| Path | Contents |
| --- | --- |
| `observations/doc/decisions.jsonl` | Consequential choices, alternatives, rationale, risks, and evidence |
| `observations/doc/impressions.jsonl` | Long-form stage impressions bound to artifacts |
| `observations/doc/vision-reviews.jsonl` | Human-readable review bound to an image hash or vision-tool event |
| `observations/doc/vision-tool-events.jsonl` | Successful `inspect_image_with_vision` calls, with answer hash rather than full answer |
| `observations/doc/image-observations.jsonl` | Successfully viewed images and their hashes |
| `observations/doc/records-status.json` | Most recent Stop-hook pass/fail and outstanding record problems |
| `observations/doc/.sessions/<session>.json` | Session start time and bounded Stop-denial count |

All event logs are JSONL and append-only. `doc_records_status` summarizes
counts and the last status; it does not validate product claims or rerun
lint.

## Session requirements

At SessionStart, `require-records` writes a marker. At Stop it checks records
since that marker according to `plugins/doc/hooks/records-policy.json` and:

- validates every new VRP record and flags malformed log lines;
- requires a long-form vision review for each successful vision-tool event;
- requires a review for each distinct viewed-image hash (or matching view
  event);
- requires a fresh stage impression covering each changed path selected by
  `records-policy.json` globs; and
- requires at least one decision if any covered artifacts changed.

The stop hook denies completion at most twice. If requirements remain
unmet, the next Stop is allowed with the missing records included in context,
and the last fail remains recorded. A hook I/O or policy error skips the
gate with a stderr message. `report-doc-status` separately warns about stale
or missing lint reports, open questions, unanswered inquiries, and figures
without reviews.

The shared protocol’s 400-character, three-sentence minimum applies to
stage impressions and vision-review impressions. A vision review also
identifies the model and checklist. Findings are categorized as `info`,
`warning`, or `error`; they are observations, not pass/fail judgments.

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
