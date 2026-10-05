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

## Record each stage and decision

At the end of every completed stage, record a `stage_impression` with paths to its outputs and
a distinct three-or-more-sentence, 400-character account of what was noticed, what works, the
reader or maker impact, remaining uncertainty, and next action. Paths are hashed when recorded.

For every consequential choice, append a decision that explains the question, first principles,
at least two options with pros and cons, the selected option, a rationale of at least 200
characters, evidence, assumptions, unknowns, residual risks, and an observation that would
reopen the choice. Prefer artifact paths so evidence is hash-bound; use references for external
standards or sources.

When a figure is inspected, create a vision review bound to the image path or to an existing
vision/image-observation event. Describe accuracy, ambiguity, design intent, usefulness to the
reader or maker, concerns, and next actions. A changed image has a new hash and needs a fresh
review. Never use a vision impression as a pass/fail gate.

Use the MCP tools `doc_record_decision`, `doc_record_impression`, and
`doc_record_vision_review`, or:

```sh
python3 <doc plugin root>/scripts/doc_tool.py record decision --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record impression --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record vision-review --json FILE
python3 <doc plugin root>/scripts/doc_tool.py record status
```

The Stop hook checks this session's changed documentation artifacts and viewed images. It
allows a bounded number of denials and records its latest verdict in
`observations/doc/records-status.json`. Requests and responses in `liaison/` can belong to
other sisters; the hook only requires a fresh impression for files changed in this session.
