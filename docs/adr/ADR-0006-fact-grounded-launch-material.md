# ADR-0006: Fact-grounded launch material in brief schema 0.2

> Status: Accepted
> Date: 2026-09-28

## Context

VibeBB's making loop ends with putting the product in front of people: a
product page, a press release, a demo video, and a plan for who hears which
message where. No sister owned this marketing / launch role, and it is where
language models are most tempted to invent: prices, dates, "world's first",
awards, and comparisons. The doc plugin already owns a fact ledger
(ADR-0002), sister inquiry and user interview (ADR-0003), and a
deterministic linter, so launch material belongs here.

## Decision

1. Brief schema `0.2` adds the target kinds `product_page`, `press_release`,
   `demo_script`, and `launch_plan`, and a `launch` block with `audiences`,
   `messages`, `channels`, and `call_to_action`. Every entry cites facts; ids
   are cross-checked. Schema `0.1` briefs remain valid unchanged; a 0.1 brief
   using a launch kind or `launch` is rejected with a pointer to 0.2.
2. Claim rules are deterministic: a superlative or absolute must appear in a
   fact; key messages appear verbatim in the kinds they target; in the product
   page and the press release every number must appear in a fact. Each kind
   also has structural rules (call to action, About / media contact, shot
   table, checklist).
3. A new `doc-launch` agent, `/doc:launch` command, and `doc-launch-craft`
   skill write the material; `doc-review` gains a buyer / journalist pass with
   the `message`, `audience`, and `claim` categories. Price, availability,
   where to buy, and the press contact are user facts; unknowns become open
   questions, never "coming soon".
4. The demo script uses the product's own sounds from the bard cue set
   (`cues/<slug>/cues.json`) and the core experience from the UX contract as
   sources.

## Consequences

- Launch copy is less free-form: an unsourced number or superlative fails
  lint, and the fix is a real source or removing the claim.
- Keyword and number matching are heuristics; the reviewer still checks
  implied claims (endorsements, comparisons) that the linter cannot see.
- Quality-document kinds stay reserved (ADR-0005) for a later schema.
