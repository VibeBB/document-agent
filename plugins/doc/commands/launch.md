---
description: Write fact-grounded launch material for this workspace's product — product page, press release, demo video script, and launch plan — asking sibling agents and the user for anything unknown.
argument-hint: "[all|page|press|demo|plan] [one-line subject]"
allowed-tools:
  - terminal
  - file_editor
  - task_tool_set
---

# /doc:launch

Launch material is persuasive, so it is where invented claims are most tempting. Every
number, date, price, and superlative in it must be a sourced fact in the doc brief; the rest
goes back to the user as open questions.

1. Read the scope from the arguments: `all` (default) = `page`, `press`, `demo`, `plan`
   (`product_page`, `press_release`, `demo_script`, `launch_plan`). Default paths are
   `docs/launch/product-page.md`, `docs/launch/press-release.md`,
   `docs/launch/demo-script.md`, `docs/launch/launch-plan.md`. The language follows the
   argument or the conversation (`ja`/`en`).
2. Write these lines in the thought of the first tool call and at the top of the final
   response:

   ```text
   Scope: <page, press, demo, plan> / Language: <ja|en> / Product: <one line>
   Output: <target paths> (work files: doc-work/<slug>/)
   Path: task sub-agent | fallback (no task)
   ```

   Decide the path from whether `task` exists in **the tool list actually available in this
   conversation**.
3. Create or reuse `doc-work/<slug>/`. Append a `## Launch` section to
   `doc-work/<slug>/context.md` (create the file if needed), 200..2000 characters, every item
   tagged `[conversation]`, `[file:<path>]`, or `[git]`: the requested material, the readers
   the user named, price / date / where to buy **only if the user said them**, tone, and
   words to avoid.
4. **Gather.** If `survey.md` is missing, run `doc-liaison` exactly as `/doc:write` step 4
   does, adding `Launch targets: <kinds>` to the prompt so it also lists price, availability,
   audience evidence, and demo-able behavior as needed facts. Ask `ux` for the core
   experience and `bard` for the product's sound cues (`cues/<slug>/cues.json`) when the demo
   script is in scope. At the start, also check `doc_ux_inbox` for requests addressed to doc
   and answer them through the SLP v2 workflow.
5. **Interview (when needed).** Price, availability date, where to buy, and the press contact
   are the user's facts. If `inquiries.md` has such `to: user` questions still `unanswered`,
   run the `/doc:interview` procedure and end your turn without a tool call. Ask once per run.
6. **Write.** With `task`:

   ```text
   task(subagent_type="doc-launch",
        description="Write the launch material",
        prompt="Work directory: doc-work/<slug>/. Language: <ja|en>. Targets: <kind=path, ...>. Read context.md, survey.md, inquiries.md and interview.md (when present) first. Run every stage; lint until pass.")
   ```

   On an iteration-limit/timeout error, call `task` again with the same `subagent_type`,
   appending `Resume: these files already exist: <list>. Continue from the first missing
   stage.` At most twice. Without `task`: read `<doc plugin root>/agents/doc-launch.md` and
   run its stages yourself.
7. **Verify** from the workspace root:

   ```bash
   python3 <doc plugin root>/skills/doc-lint/scripts/doc_lint.py --brief doc-work/<slug>/doc-brief.json --no-write
   ```

   The verdict must be `pass`, and `launch-outline.md`, `launch-review.md`, and every target
   must exist. List anything missing under `Missing:` — never claim it exists.
8. **Report**, in the conversation language: the documents written; the key messages;
   `Lint:` the verdict; `Review:` applied and declined findings; `Open questions:` every open
   question and unanswered inquiry, with an offer to run `/doc:interview`. The last line is
   exactly `Path: task sub-agent` or `Path: fallback (no task)` (the fallback may append
   ` — <reason>`).

At every completed stage, append the records required by
`<doc plugin root>/skills/doc-records/SKILL.md`; vision observations are advisory and do not
change the doc-lint result.
