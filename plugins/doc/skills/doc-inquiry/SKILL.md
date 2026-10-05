---
name: doc-inquiry
description: Who owns which product facts (workspace files, sibling agents wire, mech, circuit, ux, bard, and the user), how to ask a sibling a read-only question, the inquiry and interview record formats, and the interview question bank about the maker's intent. Use before gathering facts for documentation or interviewing the user.
license: BSD-3-Clause
triggers:
  - sibling
  - inquiry
  - interview
  - ask the user
  - 姉妹
  - 聞いて回
  - インタビュー
  - 想い
---

# Doc inquiry

Documentation is only as true as its facts. Look in the workspace first, ask the sibling that
owns a fact second, and ask the user only for what nobody else can know.

## Who owns what

| Owner | Facts | Read first | Ask (task `subagent_type`) |
| --- | --- | --- | --- |
| workspace | product name, commands, versions, setup, source layout | `README*`, `docs/`, `pyproject.toml`, `package.json`, `Makefile`, `git --no-pager log` | — |
| wire | harness connectors, wires, pin assignments, cable lengths | `*.contract.json`, `*.connectivity.json`, `*.drawio.svg` | `wire-review` |
| mech | enclosure, dimensions, materials, assembly, mounting | `*.brief.json`, `*.envelope.json`, `design-report.json` | `mech-review` |
| circuit | power, electrical ratings, board interfaces, schematics | `*.brief.json`, `*.kicad_sch` | `circuit-review` |
| ux | personas, jobs to be done, journeys, UI states, wording | `*.ux.json`, `*.stories.json`, `ux-report.json` | `ux-research` |
| bard | songs about the work (tone only, never facts) | `songs/*/song.md` | — |
| user | why the product exists, who it is really for, what matters, what must never be said | `doc-work/<slug>/interview.md` | `/doc:interview` |

Sibling artifact names are hints: a sibling's own README or `AGENTS.md` wins when they differ.
A sibling that is not installed (see `/doc:doctor`) is `not_available`; its questions go to
the user only when the user can reasonably know the answer.

## Asking a sibling

One question per `task` call, read-only:

```text
task(subagent_type="<owner agent>",
     description="Read-only question from the doc agent",
     prompt="Read-only question from the doc agent; do not modify any file. Question: <one question>. Look at: <files>. Answer in at most five sentences and cite the files you used.")
```

Record the answer verbatim. If the answer contradicts a workspace file, record both under
Conflicts in `survey.md`; the writer states neither until it is resolved.

## Record format (`inquiries.md`)

```markdown
## Q1
- to: mech
- question: What are the enclosure outer dimensions?
- status: answered
- answer: 62 mm diameter, 28 mm height.
- cited: mech/tomo.brief.json

## Q2
- to: user
- question: Why did you build this product?
- status: unanswered
```

`status` is `answered`, `unanswered`, or `not_available`. The writer copies these into the
brief's `inquiries`; an `answered` sibling answer becomes a `sibling_agent` source and a user
answer becomes a `user_interview` source (`interview.md#A<n>`).

## Interview question bank

Ask at most five, in the conversation language, one numbered list, skippable. Prefer the
questions whose answers change the README the most.

1. In one sentence, what does the product do for the person using it?
2. Why did you build it? What moment or frustration started it?
3. Who is it for, and who is it not for?
4. What should someone feel or be able to do after the first five minutes?
5. What would you never want the documentation to say or promise?
6. Which words do you use for it (and which do you dislike)?
7. What is the one thing a new user most often gets wrong?
8. Is there anything planned but not ready that we must not describe as available?

The answers are quoted, not polished: the writer may shorten them for the README but never
changes their meaning, and statements of intent appear only when the user made them.

At the end of the survey and inquiry stages, record an impression bound to the stage files.
Record meaningful choices about evidence ownership, conflicts, and unanswered questions using
the document-records skill; do not treat a record as a fact source unless the brief cites it.
