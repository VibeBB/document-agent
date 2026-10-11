# ADR-0010: VRP v2 records, blind figure review and song receipts

Status: Accepted
Date: 2026-10-11

## Context

VRP v1 (ADR-0008) let a model append free prose that nobody had to answer:
logs could be edited or truncated unnoticed, the same concern could be
raised forever, a rejected idea could come back unchanged, one vision review
of a figure was taken as seen, and doc had no way to acknowledge a bard song
addressed to it. wire-agent shipped VRP v2 as the family reference; the user
chose to port all of it to every plugin.

## Decision

- Copy the canonical v2 hooks (`_records.py`, `require_records.py`,
  `blind_guard.py`) byte-for-byte; `scripts/check_shared_hooks.py` pins the
  digests. `doc_records.py` stays a stdlib writer but imports the validators
  from the hook copy, so the writer and the Stop hook cannot drift.
- Hash-chained logs, structured grounded impressions, near-duplicate
  refusal, read receipts, insight lifecycle, dispute no-re-raise, reconcile
  rounds and digest/search behave exactly as in wire (see
  `docs/records-and-vision.md`).
- `doc-work/*/figures/*.png` is a dual-review image: the new
  `doc-blind-review` sub-agent records the blind round behind
  `blind-guard`, and the caller reconciles.
- doc only consumes bard songs: `record song-receipt` pins an immutable
  `liaison/<id>.bard-song.json` addressed to `doc` by sha256, once. A
  receipt never asks bard for another song, so the exchange cannot loop.
  `protect-lint-report` denies hand edits of song deliveries.
- The MCP input schemas in `plugins/doc/scripts/records-schemas.json` are
  generated from wire's Pydantic inputs, so doc's MCP surface matches the
  family reference.

## Consequences

Records remain advisory: no lint or gate verdict reads them. Existing v1
logs are archived as `<name>.v1.jsonl` on the first v2 write. Callers that
recorded impressions with the v1 shape now get a validation error naming the
missing v2 fields. The vendored core adds about 1,000 statements to the
coverage base.
