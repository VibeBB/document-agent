# ADR-0005: Reserving quality-document kinds for a later schema

> Status: Accepted
> Date: 2026-09-28

## Context

The doc plugin is planned to also write quality documents (quality plans,
test reports, risk assessments, inspection records). Those need traceable
requirements, evidence, and approval fields that product documentation does
not.

## Decision

1. Schema 0.1 reserves the target kinds `quality_plan`, `test_report`,
   `risk_assessment`, and `inspection_record`; the linter rejects them with a
   "planned quality-document kind" message instead of treating them as
   unknown.
2. Quality documents will be added by a new schema version with their own
   per-kind rules and, where needed, a separate agent. The fact/source model
   of ADR-0002 is kept so every quality statement is traceable to evidence.

## Consequences

- Users asking for quality documents today get an explicit "not yet" rather
  than an ad-hoc document.
