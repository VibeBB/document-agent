---
description: Write product documentation for this workspace — a user-friendly README with a diagram and quick start, a user manual, and a technical reference — asking sibling agents and the user for anything unknown.
argument-hint: "[all|readme|manual|tech] [one-line subject]"
allowed-tools:
  - terminal
  - file_editor
  - task_tool_set
---

# /doc:write

The doc sub-agents do not receive the parent's conversation history — you,
the parent, summarize what the user wants and pass it on through files.
Documentation takes many minutes, so make the plan visible before starting.

1. Read the scope from the arguments: `all` (default) = `readme`,
   `manual`, `tech`. Default target paths are `README.md`,
   `docs/user-manual.md`, `docs/technical-reference.md`; use other paths
   only if the user asked. The document language follows the argument or
   the conversation language (`ja`/`en`).
2. Write these lines in the thought of the first tool call and at the top
   of the final response (a response without a tool call ends the turn, so
   do not send them as a standalone message):

   ```text
   Scope: <readme, manual, tech> / Language: <ja|en> / Product: <one line>
   Output: <target paths> (work files: doc-work/<slug>/)
   Path: task sub-agent | fallback (no task)
   ```

   Decide the path from whether `task` exists in **the tool list actually
   available in this conversation**. If `task` is available you must call
   the sub-agents; do not run their stages yourself. Say which targets
   already exist — they will be rewritten, with their content used as a
   source.
3. Create `doc-work/<slug>/` (`<slug>`: short lowercase-hyphen product
   name; reuse an existing directory for the same product). Write
   `doc-work/<slug>/context.md` in the conversation language, 300..2000
   characters, every item tagged `[conversation]`, `[file:<path>]`, or
   `[git]`, nothing not present in the conversation:
   - what the product is, as the user described it,
   - the requested scope, targets, language, and readers,
   - anything the user said about their intent, audience, or tone,
   - words to use and words to avoid.
4. **Gather.** With `task`:

   ```text
   task(subagent_type="doc-liaison",
        description="Gather documentation facts",
        prompt="Work directory: doc-work/<slug>/. Targets: <kind=path, ...>. Read context.md first, then survey the workspace and ask sibling agents. Write survey.md and inquiries.md.")
   ```

   Without `task`: read `<doc plugin root>/agents/doc-liaison.md` and run
   its stages yourself, writing the same files.
5. **Interview (when needed).** If `inquiries.md` has `to: user` questions
   still `unanswered` and `doc-work/<slug>/interview.md` does not already
   answer them, run the `/doc:interview` procedure now: ask the questions
   and end your turn without a tool call. Resume from step 6 when the user
   replies (or says to skip — then the writer lists them as open
   questions). Ask the user once per run, never in a loop.
6. **Write.** With `task`:

   ```text
   task(subagent_type="doc-writer",
        description="Write the product documentation",
        prompt="Work directory: doc-work/<slug>/. Language: <ja|en>. Targets: <kind=path, ...>. Read context.md, survey.md, inquiries.md and interview.md (when present) first. Run every stage; lint until pass.")
   ```

   If `task` returns an iteration-limit/timeout error, run
   `ls doc-work/<slug>/` and call `task` again with the same
   `subagent_type`, appending `Resume: these files already exist: <list>.
   Continue from the first missing stage.` At most twice; then switch to
   the fallback and state why on the `Path:` line.

   Without `task`: read `<doc plugin root>/agents/doc-writer.md` and run
   its stages yourself; run the review as a separate pass following
   `<doc plugin root>/agents/doc-review.md`.
7. **Verify** before reporting. From the workspace root:

   ```bash
   python3 <doc plugin root>/skills/doc-lint/scripts/doc_lint.py --brief doc-work/<slug>/doc-brief.json --no-write
   ```

   The verdict must be `pass`. Also confirm `doc-brief.json`,
   `outline.md`, `review.md`, and every target exist. If anything is
   missing or failing, list it under `Missing:` — never claim it exists.
8. **Report**, in the conversation language:
   1. The documents written (paths), and which were rewritten.
   2. A three-line summary of the README as a first-time reader sees it.
   3. `Lint:` the verdict.
   4. `Review:` applied and declined findings (one line each).
   5. `Open questions:` every open question and unanswered inquiry, as
      questions the user can answer; offer to run `/doc:interview` for
      them.
   6. The last line must be exactly `Path: task sub-agent` or
      `Path: fallback (no task)` (the fallback may append ` — <reason>`),
      matching step 2.
