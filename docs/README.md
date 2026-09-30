# document-agent documentation index

| Document | Contents |
|---|---|
| [`../README.md`](../README.md) | Product overview, installation, usage |
| [`../AGENTS.md`](../AGENTS.md) | Working contract |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Contributor setup and PR guidance |
| [`../SECURITY.md`](../SECURITY.md) | Vulnerability reporting and scope |
| [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) | Third-party licenses |
| [`doc-brief-contract.md`](doc-brief-contract.md) | Canonical `doc-brief.json` and `doc-lint.json` contract |
| [`operations.md`](operations.md) | Release process, plugin update notes, verification recipes |
| [`research/sdk-v1.50.0-feature-evaluation.md`](research/sdk-v1.50.0-feature-evaluation.md) | OpenHands SDK v1.50.0 and uv 0.12.21 adoption review |

## Accepted ADR list

| ADR | Title |
|---|---|
| [0001](adr/ADR-0001-task-subagent-plugin.md) | Distributing doc as `task` sub-agents with a parent-written context file |
| [0002](adr/ADR-0002-fact-grounded-doc-brief.md) | Every product claim is a sourced fact in `doc-brief.json` |
| [0003](adr/ADR-0003-sibling-inquiry-and-user-interview.md) | Asking siblings through shared artifacts and read-only reviewers; interviewing the user |
| [0004](adr/ADR-0004-lint-report-protection.md) | `doc-lint.json` is generated only by `doc_lint.py` |
| [0005](adr/ADR-0005-quality-document-extension.md) | Reserving quality-document kinds for a later schema |
| [0006](adr/ADR-0006-fact-grounded-launch-material.md) | Fact-grounded launch material in brief schema 0.2 |
