# Improvement notes

Collected while reading the repository end to end (AGENTS.md, README, docs, plugin agents/skills/commands/hooks,
scripts, tests, workflows) before the VibeBB Record Protocol / Sister Liaison Protocol refactor.

| # | Area | Finding | Action in this change |
|---|------|---------|-----------------------|
| 1 | Records | No decision, stage-impression or vision-review log; design rationale lived only in chat. | [done] Port VibeBB Record Protocol v1 (shared hooks, typed writer, Stop gate). |
| 2 | Tools | No MCP server; agents could only run scripts through `terminal`. | [done] Add a standard-library stdio MCP server with record, liaison, lint and figure tools. |
| 3 | Vision | Image observations were logged but never bound to a long-form review; embedded figures in documents were never inspected. | [done] Figure inventory, inline `doc_view_figure`, review binding by image hash, Stop-hook advisory for unreviewed figures. |
| 4 | Liaison | No machine-readable answer to UX change requests. | [done] Sister Liaison Protocol v2 inbox and responder with hash-bound inputs and gate-checked `done`. |
| 5 | Fact freshness | Sister artifacts cited by a brief were not hash-bound; a changed schematic or drawing silently kept stale facts. | [done] `sister_artifact` sources require `sha256`; doc lint rejects mismatches. |
| 6 | Design rationale | Technical references could not cite why a sister chose a design. | [done] `sister_record` sources and a required design-rationale section when they exist. |
| 7 | Family coverage | Doctor, brief schema and fact-ownership table knew only 5 of the 10 sisters. | [done] Extend to all 10 sisters with their agents and owned artifacts. |
| 8 | Hooks | `protect-lint-report` resolver missed the `~/.agents/plugins/doc` install location. | [done] Add the candidate to every resolver. |
| 9 | Wording | "sibling" in prompts, docs and output; the family term is "sister". | [done] Rename prose and brief source kinds. |
| 10 | Docs | operations.md described Python 3.14 as a required check; AGENTS.md counted 9 shared-hook copies. | [done] Correct both. |
| 11 | Docs | No architecture/agents/hooks/MCP reference; README mixed product and developer content. | [pending] Rebuild README for non-engineers and a complete technical doc set. |
| 12 | Rendering | Pages and Mermaid diagrams cannot be rendered to images without a tools image (doc is stdlib-only on the host). | Open: needs a pinned rendering image or a sister renderer; recorded as a gap. |
| 13 | Liaison safety | Hand edits to `liaison/*.ux-response.json` are not blocked, because the directory is shared by every sister and a doc hook must not block other sisters. | Open: needs a family-wide owner-aware guard. |
