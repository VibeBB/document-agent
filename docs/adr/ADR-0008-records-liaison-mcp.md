# ADR-0008: Standard-library records, liaison, and MCP tools

- Status: Accepted
- Date: 2026-10-05

## Context

The documentation plugin needed durable evidence for consequential decisions,
completed stages, and images viewed during a documentation run. It also
needed a way to answer structured requests from sister agents and expose the
record, figure, lint, and liaison operations to OpenHands agents.

The plugin is distributed without a tools image. Hooks and helper scripts
must run with host `python3`, and the family needs portable request and
record artifacts that do not depend on importing another plugin's code.
Every fact cited in documentation must still be bound to a current artifact
or record, and a liaison response must not claim completion on a stale lint
verdict.

## Decision

- Implement VRP v1 record writers and validation with Python’s standard
  library. Append decisions, stage impressions, and vision reviews to JSONL
  records under `observations/doc/`; bind artifacts and observations to
  SHA-256 hashes and stable event IDs.
- Implement the document side of SLP v2 as a strict local validator and
  responder. Exchange versioned JSON files under `liaison/`, validate safe
  workspace paths and current input/artifact hashes, and require passing lint
  coverage for `done` responses that claim Markdown artifacts.
- Use a standard-library newline-delimited JSON-RPC MCP server to expose the
  deterministic record, status, liaison, lint, and figure operations to
  agents. Keep the CLI available for the same host-runtime operations.
- Extend brief source records to cite hash-bound sister agents, artifacts,
  and decision events, and require technical references to explain cited
  design rationale in reader-facing context.
- Keep record and vision evidence advisory. Lint verdicts remain the
  deterministic result of the linter; neither a record nor a vision
  observation can turn a lint failure into a pass.

## Consequences

The plugin adds append-only observation logs, a bounded Stop-hook record
gate, MCP tools, and strict path/hash validation without adding plugin
runtime dependencies or a tools image. Maintainers must update the JSON
schemas, producer/consumer tests, user and technical documentation, and
family-wide hook copies together when contracts change.

The `done` gate is intentionally stricter than a success message: it requires
current inputs, a fresh lint report, cited decision and impression records,
passing declared gates, and current artifact hashes. The UX-creator producer
currently advertises fewer SLP targets and omits `doc`; document-agent does
not modify that producer, so normal upstream UX flow cannot yet initiate a
request to doc.

Records improve traceability but do not prove a product claim. Vision reviews
describe observations rather than issuing hardware safety approval. A failed
record gate is bounded to two Stop denials so missing evidence is eventually
reported rather than blocking termination indefinitely.

## Alternatives rejected

- **Pydantic/MCP dependency in a tools image:** rejected because the plugin
  has no tools image and its runtime helpers must remain standard-library
  only.
- **CLI-only interface:** rejected because OpenHands agents need structured,
  discoverable tool calls for image viewing, linting, record creation, and
  liaison responses. The CLI is retained as an operator interface, not the
  only integration.
- **Free-form records without hashes or cross-checking:** rejected because
  citations and completion claims must be tied to current files and existing
  events.
- **Vision-derived approval:** rejected because visual observations are
  advisory and cannot establish engineering safety.
