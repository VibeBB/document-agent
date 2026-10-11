---
name: doc-records
description: Record document-work decisions, completed stages, and figure observations as hash-bound VRP events.
triggers:
  - doc record
  - design rationale
  - vision review
  - stage impression
---

# Document work records

Records are durable, append-only evidence of how a documentation result was produced. They
are advisory and never change the deterministic doc-lint verdict.

## Record each stage and decision (VRP v2)

At the end of every completed stage, record a `stage_impression` with paths to its outputs. The
prose is at least 400 characters and three sentences and must not repeat an earlier impression
of the stage. Add `facets` (two or more `observed`, `works`, `concerns` with id, severity,
`about` and anchor, `feelings.maker` and `feelings.user`, `next_actions`), two or more `claims`
whose `anchor` is an exact token of the cited artifact (a brief fact, a heading, a label), and
`confidence` plus `unknowns`. Paths are hashed when recorded and each log is hash-chained.

For every consequential choice, append a decision that explains the question, first principles,
at least two options with pros and cons, the selected option, a rationale of at least 200
characters, evidence, assumptions, unknowns, residual risks, and an observation that would
reopen the choice. Prefer artifact paths so evidence is hash-bound; use references for external
standards or sources.

Before writing, run `record digest`: answer every sister concern you act on in `upstream`
(`adopted`, `deferred`, `disputed`, `noted`) and record a `read` receipt for sister artifacts you
took in. A disputed concern cannot be raised again on unchanged bytes; a rejected insight comes
back only with `revisits` and a reason. Answer a bard song addressed to doc with
`song-receipt`; never ask bard for another song in return.

When a figure is inspected, create a vision review bound to the image path or to an existing
vision/image-observation event, with facets, claims and a `lookback` verdict per claim. Every
changed `doc-work/<name>/figures/*.png` also needs a blind review by the `doc-blind-review`
sub-agent and a `reconcile` of both reviews (one `tiebreak` round if they split; an unresolved
split stays `unknown`). A changed image has a new hash and needs a fresh review. Never use a
vision impression as a pass/fail gate.

Use `doc_figures --brief <work dir>/doc-brief.json` to inventory Markdown and HTML image
references and Mermaid blocks. `doc_view_figure` accepts workspace PNG, JPEG, GIF, and WebP
images up to 5 MiB. It appends an image-observation event and returns a source event ID; bind
the review to that event or the image path. SVG must be rendered to PNG by the owning sister.
Review checklists are `figure-caption-match` (writer), `figure-reader` (review), and
`launch-visual` (launch). Intake and liaison should inspect user photos and sister figures that
carry facts, and preserve any disagreement as a conflict.

Use the MCP tools `doc_record_decision`, `doc_record_impression`, `doc_record_vision_review`,
`doc_record_reconcile`, `doc_record_insight`, `doc_record_song_receipt`, `doc_record_read`,
`doc_records_status`, `doc_records_digest` and `doc_records_search`, or:

```sh
python3 <doc plugin root>/scripts/doc_tool.py record decision --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record impression --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record vision-review --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record reconcile --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record insight --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record song-receipt --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record read --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record search --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record digest
python3 <doc plugin root>/scripts/doc_tool.py record status
```

The Stop hook checks this session's changed documentation artifacts and viewed images. It
allows a bounded number of denials and records its latest verdict in
`observations/doc/records-status.json`. Requests and responses in `liaison/` can belong to
other sisters; the hook only requires a fresh impression for files changed in this session.
