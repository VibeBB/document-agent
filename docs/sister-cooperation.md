# Sister cooperation

`doc` does not import sister-plugin code. It gathers owned facts from the
shared workspace or read-only sister-agent delegation and cites the evidence
in `doc-work/<slug>/doc-brief.json`. `/doc:doctor` reports which sisters are
installed. When an owner is unavailable, the fact remains unknown and is
asked of the user only if the user can answer it.

## Fact ownership

| Owner | Facts and artifacts doc consults |
| --- | --- |
| Workspace | Product name, commands, versions, setup, and source layout |
| `ux` | User journeys, jobs, interface states, wording, and UX reports |
| `bard` | Song/cue content; never an engineering fact |
| `dashboard` | App routes, screens, platform, transport, and generated app evidence |
| `circuit` | Electrical ratings, schematics, PCB layout, and component evidence |
| `firmware` | Firmware behavior and board pin maps |
| `fpga` | FPGA design, bitstreams, pin maps, timing, and simulation reports |
| `mech` | Enclosure, dimensions, materials, assembly, and mounting |
| `prodeng` | Manufacturing plans and factory readiness |
| `sim` | Simulation setup and results |
| `wire` | Harness connectors, wires, pin assignments, and cable lengths |
| User | Product motivation, intended audience, priorities, and wording the docs must avoid |

The owner’s own README and documentation are authoritative for the exact
artifact names and contracts. A sister’s VRP decision can support a design
rationale, but doc cites it as a `sister_record` and verifies its event
reference and source hash; the record is not promoted to a product fact.
Conflicting sources are preserved in `survey.md` until resolved.

## Read-only question flow

`doc-liaison` asks one question per `task` call, names the files to inspect,
and requests a short answer that cites those files. It does not modify sister
workspaces or product documents. Its outputs are `survey.md` and
`inquiries.md`; user-only intent is gathered separately via
`/doc:interview` and quoted in `interview.md`.

An answered sister inquiry becomes a `sister_agent` source; a file-backed
answer becomes a `sister_artifact` source with owner, path, and current hash.
An unanswerable or unavailable question stays open. The writer cannot replace
an unresolved value with a plausible guess.

## SLP v2 document liaison

The cross-plugin request/response files live in the shared workspace:

1. A requesting sister writes
   `liaison/<id>.ux-request.json` with the request contract, target `doc`,
   source paths, and hashes.
2. `doc_ux_inbox` validates every request and reports `new`, `answered`,
   `stale`, or `blocked`, plus malformed files. `/doc:write` and
   `/doc:launch` check the inbox before work proceeds.
3. `doc_ux_respond` verifies that the request targets doc, rehashes inputs
   and claimed artifacts, checks VRP record references, and writes
   `liaison/<id>.ux-response.json`.
4. A `done` response is refused unless required gates pass, a passing
   `doc-lint` gate is declared, a valid decision and impression are cited,
   and each claimed Markdown artifact is covered by a fresh passing lint
   report. Changed inputs prevent `done`; missing inputs require
   `needs_info` or `rejected`.
5. The next inbox scan shows the answer or reports it stale if the request’s
   inputs changed.

## UX-creator compatibility gap

The current UX-creator producer contract advertises fewer target agents than
the family SLP v2 receiver allowlist and omits `doc`. Therefore, although doc
can validate and answer a correctly formed request that targets it, the
current upstream UX-creator producer does not offer doc as a target and will
not emit such a request through its normal flow. This is a documented
producer/receiver compatibility gap; this change does not modify UX-creator.

See [contracts](contracts.md#slp-v2-request) for the exchanged fields and
[MCP](mcp.md#liaison-tools) for the tool interfaces.
