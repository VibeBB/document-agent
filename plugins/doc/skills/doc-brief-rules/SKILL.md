---
name: doc-brief-rules
description: Path rule — doc brief contract and fact-grounding reminders injected whenever a doc-brief.json or doc-lint.json file is touched.
version: 0.1.0
license: BSD-3-Clause
paths:
  - "**/doc-brief.json"
  - "**/doc-lint.json"
---

# Doc brief file rules

- `doc-brief.json` follows the contract in `docs/doc-brief-contract.md` (schema 0.1). Check
  the summary in `skills/doc-lint/SKILL.md` before editing; do not read `doc_lint.py` to learn
  the contract.
- Every fact needs a source; every `answered` inquiry needs its answer and a source from the
  agent (or the user interview) that answered it. `product.vision` only from a
  `user_interview` source.
- Unknowns go to `open_questions`, never into the documents as guesses.
- `doc-lint.json` is written only by `doc_lint.py`; rerun the linter instead of editing it.
