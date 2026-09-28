# ADR-0004: `doc-lint.json` is generated only by `doc_lint.py`

> Status: Accepted
> Date: 2026-09-28

## Context

An agent under pressure to finish can hand-edit a failing report to `pass`.
Documents and the brief, on the other hand, must stay freely editable.

## Decision

1. `doc_lint.py` writes a deterministic `doc-lint.json` next to the brief,
   with the sha256 of the brief and of every target document.
2. The `protect-lint-report` pre-tool-use hook denies any `file_editor`,
   `apply_patch`, or shell write (redirects, `tee`, `cp`, `mv`, `sed -i`,
   `rm`, …) to a `doc-lint.json`. Reads and linter runs are allowed.
3. The `report-doc-status` stop hook recomputes the hashes and reports each
   brief as `linted=pass`, `fail`, `stale`, or `false`, plus unanswered
   inquiries and open questions. It is advisory (`decision: allow`) and
   fails closed (exit 1) on an unreadable brief or a foreign report.

## Consequences

- A report is trustworthy only for the exact bytes it hashes; any edit after
  linting shows as `stale` until the linter runs again.
