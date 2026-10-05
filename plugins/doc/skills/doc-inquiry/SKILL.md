---
name: doc-inquiry
description: Who owns which product facts (workspace files, sister agents, and the user), how to ask a sister a read-only question, the inquiry and interview record formats, and the interview question bank about the maker's intent. Use before gathering facts for documentation or interviewing the user.
license: BSD-3-Clause
triggers:
  - sister
  - inquiry
  - interview
  - ask the user
  - 姉妹
  - 聞いて回
  - インタビュー
  - 想い
---

# Doc inquiry

Documentation is only as true as its facts. Look in the workspace first, ask the sister that
owns a fact second, and ask the user only for what nobody else can know.

## Who owns what

| Owner | Facts and owned artifacts | Read first on `origin/main` | Ask (task `subagent_type`) |
| --- | --- | --- | --- |
| workspace | Product name, commands, versions, setup, source layout | `README*`, `docs/`, `pyproject.toml`, `package.json`, `Makefile`, `git --no-pager log` | — |
| ux | User journeys, jobs, interface states, wording; `*.ux.json`, `*.stories.json`, `*.production.json`, UX reports, liaison contracts | [UX-creator README](https://github.com/VibeBB/UX-creator-agent/blob/main/README.md), [ADR-0003](https://github.com/VibeBB/UX-creator-agent/blob/main/docs/adr/0003-sibling-cooperation-via-contracts.md) | `ux-creator`, `ux-liaison`, `ux-producer`, `ux-research`, `ux-review`, `ux-statechart` |
| bard | Song and cue content; `song.md`, `song.mid`, `song.proposal.json`, `song.provenance.json`, `cues/<slug>/cues.json`, `cues.md` (songs are tone only, never engineering facts) | [bard README](https://github.com/VibeBB/bard-agent/blob/main/README.md) | `bard`, `bard-critic`, `bard-cue` |
| dashboard | App routes, screens, platform and transport; `.dash.json`, generated app and screenshots | [dashboard README](https://github.com/VibeBB/dashboard-agent/blob/main/README.md) | `dashboard-architect`, `dashboard-developer`, `dashboard-review` |
| circuit | Electrical ratings and PCB; design briefs, schematics, PCB layouts, and `kicad-cli` JSON reports | [electrical-circuit README](https://github.com/VibeBB/electrical-circuit-agent/blob/main/README.md) | `circuit-brief`, `circuit-layout`, `circuit-library`, `circuit-part-author-a`, `circuit-part-author-b`, `circuit-review`, `circuit-schematic` |
| firmware | Firmware behavior and board pin maps; `*.fw.json`, firmware sources, `fw-reports/<name>.fw-pinmap.json` | [firmware README](https://github.com/VibeBB/firmware-agent/blob/main/README.md) | `firmware-architect`, `firmware-developer`, `firmware-review` |
| fpga | FPGA design, bitstreams, pin maps, timing and simulation reports; `*.fpga.json` | [FPGA README](https://github.com/VibeBB/fpga-agent/blob/main/README.md), [circuit/FPGA interchange ADR](https://github.com/VibeBB/fpga-agent/blob/main/docs/adr/ADR-0006-circuit-fpga-interchange.md) | `fpga-architect`, `fpga-developer`, `fpga-review` |
| mech | Enclosure, dimensions, materials, assembly and mounting; `intake.json`, `design.brief.json`, STEP/STL/3MF/DXF, manifest, provenance, design reports | [mechanical README](https://github.com/VibeBB/mechanical-agent/blob/main/README.md) | `mech-brief`, `mech-design`, `mech-review` |
| prodeng | Manufacturing plans and factory readiness; `*.prodeng.json`, `*.prodeng-request.json`, `out/<product>/` | [production-engineering README](https://github.com/VibeBB/production-engineering-agent/blob/main/README.md) | `prodeng-ftm`, `prodeng-liaison`, `prodeng-planner`, `prodeng-review` |
| sim | Simulation setup and results; `*.sim.json`, connectivity/envelope/contract imports, `out/<name>/sim-report.json`, manifest, provenance | [simulation README](https://github.com/VibeBB/simulation-agent/blob/main/README.md), [architecture](https://github.com/VibeBB/simulation-agent/blob/main/docs/architecture.md) | `sim-analyst`, `sim-liaison`, `sim-review` |
| wire | Harness connectors, wires, pin assignments, cable lengths; `*.contract.json`, intake sidecar, wire list, cut table, BOM, harness diagram | [wire README](https://github.com/VibeBB/wire-agent/blob/main/README.md) | `wire-brief`, `wire-design`, `wire-review` |
| user | Why the product exists, who it is really for, what matters, and what must never be said | `doc-work/<slug>/interview.md` | `/doc:interview` |

Each sister's VRP decision source is `observations/<plugin>/decisions.jsonl`;
cite the selected event with a `sister_record` source when it explains a design
rationale. Each sister's own `origin/main` README and docs remain authoritative
if artifact names here differ. A sister not installed (see `/doc:doctor`) is
`not_available`; ask the user only questions they can reasonably answer.

## Asking a sister

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
brief's `inquiries`; an `answered` sister answer becomes a `sister_agent` source and a user
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
the `doc-records` skill; do not treat a record as a fact source unless the brief cites it.
