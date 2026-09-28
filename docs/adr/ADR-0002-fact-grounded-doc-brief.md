# ADR-0002: Every product claim is a sourced fact in `doc-brief.json`

> Status: Accepted
> Date: 2026-09-28

## Context

Language models write fluent product text that can silently invent specs,
ratings, and motivation. Product documents are read as promises: a guessed
voltage or dimension in a user manual is a defect.

## Decision

1. The writer first records every product claim as a fact in
   `doc-work/<slug>/doc-brief.json` (schema 0.1,
   [contract](../doc-brief-contract.md)). Each fact cites at least one
   source (`file`, `git_log`, `conversation`, `user_interview`,
   `sibling_agent`, `sibling_artifact`).
2. `product.vision` (the maker's intent) is allowed only with a
   `vision_source` of kind `user_interview`.
3. Unknowns go to `open_questions` and are reported to the user; documents
   never contain placeholders (TODO, TBD, 要確認, 未定, …).
4. `doc_lint.py` (standard library only) validates the brief fail-closed and
   lints each document against its kind: the README explains the product and
   shows a diagram before a 2..7-step quick start and links the other
   documents; the user manual has usage and troubleshooting; the technical
   reference has an architecture diagram, interfaces, and development.
5. The linter checks structure, not truth. Fact-to-text agreement is the
   reviewer's job (`doc-review`), from the brief.

## Consequences

- Documents may be shorter than a model would write unprompted; gaps are
  visible as open questions instead of hidden as guesses.
- The contract is versioned; new keys or kinds need a schema bump.
