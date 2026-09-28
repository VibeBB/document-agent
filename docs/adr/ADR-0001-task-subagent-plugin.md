# ADR-0001: Distributing doc as `task` sub-agents with a parent-written context file

> Status: Accepted
> Date: 2026-09-28

## Context

OpenHands Software Agent SDK v1.49.6 loads plugin `agents/*.md` files as
`AgentDefinition`s that a parent calls with `task(subagent_type=...)`. Agent
Canvas exposes `task` when sub-agents are enabled; `delegate` and `workflow`
are not exposed. A task sub-agent does not receive the parent's conversation
history. The sibling plugins (bard, wire, mech, circuit, ux) follow the same
model.

Documentation needs three different jobs: finding facts (workspace, siblings,
user), writing for three readers, and reviewing as those readers.

## Decision

1. The plugin (`plugins/doc`) ships three agents: `doc-liaison` (gathers
   facts, asks siblings), `doc-writer` (brief, outline, documents, lint), and
   `doc-review` (read-only review, `vibebb-review` model).
2. `/doc:write` has the parent summarize the conversation into
   `doc-work/<slug>/context.md` and pass only paths in `task` prompts. Every
   stage writes a file in `doc-work/<slug>/`, so an interrupted run resumes
   from the first missing file.
3. Without `task`, the parent runs the same stages from the agent files
   (fallback) and says so on the final `Path:` line.
4. User interviews happen in the parent conversation (`/doc:interview`),
   because only the parent can end a turn and wait for the user.

## Consequences

- Sub-agents enabled in Agent Canvas gives the separated liaison / writer /
  reviewer path; without it the plugin still works, slower.
- What the parent leaves out of `context.md` is invisible to the sub-agents.
