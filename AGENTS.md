# Agent Work Contract

> Target: OpenHands Software Agent SDK v1.49.6, Python 3.12+

This document is the working contract for implementation, validation, and
documentation in this repository. The README is the product overview,
`docs/` contains specifications and operating policy, and `docs/adr/`
contains architectural decisions. README (English first, followed by a
Japanese section), docs, issues, PRs, commit messages, code comments, and
identifiers are written in English.

## Purpose

doc is the documentation specialist of the VibeBB agent family. It writes a
product's documentation into the OpenHands workspace — a README a first-time
user understands (a product explanation with a diagram, then a quick start),
a user manual, and an engineer-facing technical reference — asking sibling
agents for facts they own and interviewing the user for what only they know.
Quality documents are planned (ADR-0005).

## Layout

```text
plugins/doc/
├── .plugin/plugin.json
├── agents/
│   ├── doc-liaison.md        # Gathers facts: workspace survey, sibling inquiries (task)
│   ├── doc-writer.md         # Brief, outline, README / manual / technical reference, lint
│   └── doc-review.md         # Read-only review as first-time reader, user, engineer
├── commands/
│   ├── write.md              # /doc:write — context.md, liaison, interview, writer, verify
│   ├── interview.md          # /doc:interview — ask the user, record answers verbatim
│   └── doctor.md             # /doc:doctor — plugin root, layout, sibling availability
├── hooks/                    # session_start doctor + profiles, pre_tool_use report guard +
│                             # safety rail, stop status report (stdlib only)
└── skills/
    ├── doc-craft/            # Reader-first writing rules, templates, Mermaid rules, checklist
    ├── doc-inquiry/          # Fact ownership per sibling, inquiry records, interview bank
    ├── doc-lint/             # doc-brief.json contract + doc_lint.py (stdlib only) + example
    └── doc-brief-rules/      # Path-triggered rule on doc-brief.json / doc-lint.json
docs/
├── doc-brief-contract.md     # Canonical brief / report contract
├── operations.md
└── adr/
scripts/                      # Plugin-load, docs, release, and dependency helpers (stdlib only)
tests/                        # Linter, hook, and plugin-asset tests
```

## Invariants

- Every product claim in a generated document is a fact in
  `doc-work/<slug>/doc-brief.json` citing at least one source. Unknowns go to
  `open_questions`; documents never contain placeholders or guesses
  (ADR-0002).
- The maker's intent (`product.vision`) comes only from a user interview,
  recorded verbatim (ADR-0003).
- Sibling facts come from sibling artifacts or a sibling's answer through
  `task`; conflicts are recorded, never silently resolved (ADR-0003).
- `doc-lint.json` is written only by `doc_lint.py`; the `pre_tool_use` hook
  denies hand edits, and the stop hook reports stale reports (ADR-0004).
- The linter judges structure; `doc-review` judges fact agreement and
  readability and returns findings only — it never edits documents.
- `doc_lint.py` and the hook scripts use only the Python standard library.
- Text-reading and text-writing paths specify `encoding="utf-8"`.
- Never put API keys, tokens, or secrets in logs, inputs, or commits.
- Files containing externally sourced code retain the original license
  notices and attribution.

## Plugin boundary

- Do not build custom tool, event, history, or executor infrastructure;
  delegate to the OpenHands SDK.
- Invoke sub-agents only with `task` (`TaskToolSet`) (ADR-0001). A task
  sub-agent does not receive the parent's conversation history: the parent
  writes `doc-work/<slug>/context.md`, and the sub-agents read the workspace.
- Do not import sibling plugin code. Cooperate through shared-workspace
  artifacts and the siblings' registered agents.
- Sub-agents do not inherit plugin hooks; agent frontmatter repeats the
  `pre_tool_use` hooks from `hooks/hooks.json` verbatim.
- AgentDefinitions do not declare `skills:`; prompts reference SKILL.md paths
  under the resolved plugin root.

## Verification

```bash
uv sync --locked --group sdk-check
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest -q
uv run python scripts/verify_docs.py
uv run --group sdk-check python scripts/check_plugin_load.py
```

The linter has negative tests that deliberately break a passing brief or
document and confirm the rejection. Contract changes update
`docs/doc-brief-contract.md`, the `doc-lint` skill, the example, and the
tests in the same change.

## Git

Write commit messages in English. Do not use `git add .`, amend commits,
`--no-verify`, force push, direct pushes to main, `reset --hard`, `clean -fd`,
`checkout -- file`, or `stash drop`. Do not commit `doc-work/`, `out/`,
secrets, or environment files. Use `git mv` when renaming files.
