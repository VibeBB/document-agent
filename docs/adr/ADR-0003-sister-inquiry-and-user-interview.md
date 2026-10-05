# ADR-0003: Asking sisters through shared artifacts and read-only reviewers; interviewing the user

> Status: Accepted
> Date: 2026-09-28

## Context

Facts about a VibeBB product live with the sister agent that designed that
part: wiring (wire), enclosure (mech), electronics (circuit), user research
(ux), and the dashboard, firmware, FPGA, production, and simulation systems.
The ten sisters are separate plugins that may or may not be installed, and
they must not be coupled by imports.

## Decision

1. `doc-liaison` reads sister artifacts in the shared workspace first
   (`*.contract.json`, `*.envelope.json`, `*.brief.json`, `*.ux.json`, …) —
   the ownership table lives in the `doc-inquiry` skill.
2. For a fact still missing, it asks the owning sister one focused question
   through `task` with that sister's registered read-only reviewer or
   researcher. Answers are recorded in `inquiries.md` and cited as
   `sister_agent` sources; unavailable sisters are recorded as
   `not_available`, never guessed.
3. Conflicting answers are recorded as conflicts in `survey.md`; the writer
   does not pick a side silently — it becomes an open question.
4. Why the product exists, who it is really for, and what must never be said
   come only from the user. `/doc:interview` asks at most five questions once
   per run and records answers verbatim in `interview.md`.
5. bard songs are tone references only, never facts.
6. A `sister_artifact` source binds the claim to a required file or tree
   SHA-256. A `sister_record` cites an event in that sister's VRP log; when
   present, the technical reference explains the rationale under an H2/H3
   heading matching `rationale`, `設計根拠`, or `設計判断`.

## Consequences

- Documentation works with any subset of sisters installed.
- Sister answers are as good as the sister's artifacts; the brief records
  who said what.
