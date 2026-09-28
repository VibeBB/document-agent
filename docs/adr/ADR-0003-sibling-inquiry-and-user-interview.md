# ADR-0003: Asking siblings through shared artifacts and read-only reviewers; interviewing the user

> Status: Accepted
> Date: 2026-09-28

## Context

Facts about a VibeBB product live with the sibling agent that designed that
part: wiring (wire), enclosure (mech), electronics (circuit), user research
(ux). The siblings are separate plugins that may or may not be installed, and
they must not be coupled by imports.

## Decision

1. `doc-liaison` reads sibling artifacts in the shared workspace first
   (`*.contract.json`, `*.envelope.json`, `*.brief.json`, `*.ux.json`, …) —
   the ownership table lives in the `doc-inquiry` skill.
2. For a fact still missing, it asks the owning sibling one focused question
   through `task` with that sibling's read-only reviewer or researcher
   (`wire-review`, `mech-review`, `circuit-review`, `ux-research`), only when
   that agent is registered. Answers are recorded in `inquiries.md` and cited
   as `sibling_agent` sources; unavailable siblings are recorded as
   `not_available`, never guessed.
3. Conflicting answers are recorded as conflicts in `survey.md`; the writer
   does not pick a side silently — it becomes an open question.
4. Why the product exists, who it is really for, and what must never be said
   come only from the user. `/doc:interview` asks at most five questions once
   per run and records answers verbatim in `interview.md`.
5. bard songs are tone references only, never facts.

## Consequences

- Documentation works with any subset of siblings installed.
- Sibling answers are as good as the sibling's artifacts; the brief records
  who said what.
