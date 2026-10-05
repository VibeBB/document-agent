# document-agent documentation

This index points to the reader-facing overview, implementation references,
contracts, operations guides, research notes, and accepted architecture
decisions.

## Start here

| Document | Contents |
| --- | --- |
| [Product README](../README.md) | What doc does, what to provide, how the VibeBB plugins cooperate, and how to start |
| [Architecture](architecture.md) | Components, trust boundaries, workspace data flow, and runtime |
| [Workflow](workflow.md) | Write, launch, interview, review, and evidence-recording stages |
| [Sister cooperation](sister-cooperation.md) | Fact ownership, SLP v2, hash checks, and current compatibility |

## Plugin reference

| Document | Contents |
| --- | --- |
| [Agents](agents.md) | Agent roles, models, tools, budgets, and write boundaries |
| [Skills](skills.md) | All model-invocable skills and the path-triggered rule |
| [Commands](commands.md) | Slash commands, CLI entry points, and exit behavior |
| [MCP tools](mcp.md) | Stdio server and every registered tool’s inputs, outputs, errors, and effects |
| [Hooks](hooks.md) | Every event, matcher, hook action, and failure behavior |

## Contracts and operations

| Document | Contents |
| --- | --- |
| [Contracts](contracts.md) | Brief/report, VRP, SLP, figure observation, and policy JSON contracts |
| [Document brief contract](doc-brief-contract.md) | Canonical brief, facts, sources, targets, and lint-report structure |
| [Records and vision](records-and-vision.md) | VRP v1 records, figure inspection, hash binding, and Stop checks |
| [Performance and limits](performance-and-limits.md) | Measured example lint times, file counts, size limits, and known constraints |
| [Operations](operations.md) | Install, runtime, troubleshooting, release, and verification |
| [Development](development.md) | Repository map, safe extension points, and contributor checks |
| [Improvement notes](improvement-notes.md) | Refactor findings and their implementation status |

## Repository policies

| Document | Contents |
| --- | --- |
| [Working contract](../AGENTS.md) | Implementation and repository invariants |
| [Contributing](../CONTRIBUTING.md) | Contributor setup and review guidance |
| [Security](../SECURITY.md) | Vulnerability reporting and scope |
| [Third-party notices](../THIRD_PARTY_NOTICES.md) | Third-party licenses |

## Research

| Document | Contents |
| --- | --- |
| [SDK v1.50.0 evaluation](research/sdk-v1.50.0-feature-evaluation.md) | SDK v1.50.0 and uv 0.12.21 adoption review |
| [SDK v1.50.1 evaluation](research/sdk-v1.50.1-feature-evaluation.md) | SDK v1.50.1 adoption decisions |
| [SDK v1.51.0 evaluation](research/sdk-v1.51.0-feature-evaluation.md) | SDK v1.51.0 and uv 0.12.22 adoption review |
| [SDK v1.52.0 evaluation](research/sdk-v1.52.0-feature-evaluation.md) | SDK v1.52.0 adoption review |

## Accepted architecture decisions

| ADR | Decision |
| --- | --- |
| [0001](adr/ADR-0001-task-subagent-plugin.md) | Use `task` sub-agents with a parent-written context file |
| [0002](adr/ADR-0002-fact-grounded-doc-brief.md) | Require every product claim to cite a brief fact |
| [0003](adr/ADR-0003-sister-inquiry-and-user-interview.md) | Gather sister-owned facts and interview the user for intent |
| [0004](adr/ADR-0004-lint-report-protection.md) | Allow only `doc_lint.py` to write the lint report |
| [0005](adr/ADR-0005-quality-document-extension.md) | Reserve quality-document kinds for a later schema |
| [0006](adr/ADR-0006-fact-grounded-launch-material.md) | Bind launch claims and messaging to schema 0.2 facts |
| [0007](adr/ADR-0007-vision-lane.md) | Inspect and record figures and user-attached images |
| [0008](adr/ADR-0008-records-liaison-mcp.md) | Combine standard-library MCP tools, VRP, SLP v2, and hash-bound facts |
