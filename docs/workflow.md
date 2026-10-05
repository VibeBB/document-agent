# Workflow

The `/doc:write` and `/doc:launch` commands use a gather → clarify → draft →
lint → review flow. Both preserve facts and questions in `doc-work/<slug>/`
so delegated agents can work from the same evidence.

## Product documentation

1. **Scope and context.** The parent chooses a product slug and requested
   target documents, creates `context.md`, and names the reader, language,
   scope, and source files. Task agents read this file rather than the parent
   conversation.
2. **Survey and inquiry.** `doc-liaison` inspects the workspace and available
   sister artifacts, records `survey.md` and `inquiries.md`, and asks
   sister-owned questions read-only. It does not write product documents.
   `/doc:write` also checks the inbound `doc_ux_inbox`.
3. **Interview when needed.** The user answers questions only they can know.
   `/doc:interview` stores their answers verbatim in `interview.md` and links
   them from `inquiries.md`. Skipped answers remain open questions.
4. **Brief and outline.** `doc-writer` creates `doc-brief.json` and
   `outline.md`. Each factual claim cites a source; unresolved facts remain
   inquiries or `open_questions`.
5. **Draft.** The writer creates the requested README, user manual, and
   technical reference. The technical reference includes rationale when a
   brief cites a sister decision record.
6. **Lint and review.** `doc_lint.py` checks the brief and target documents.
   The writer fixes deterministic failures. `doc-review` separately reads
   for first-time-reader clarity, user steps, engineering accuracy against
   the brief, diagram usefulness, and jargon; it returns findings rather than
   editing the documents.
7. **Report.** The command reports written paths, lint verdict, applied or
   declined review findings, and every open question. `doc-lint.json` is
   written only by `doc_lint.py`.

## Launch material

`/doc:launch` follows the same evidence and review flow, with a schema 0.2
brief. `doc-launch` creates `launch-outline.md`, the requested
product page/press release/demo script/launch plan, and
`launch-review.md`. Audiences, key messages, channels, and the call to action
are linked to facts. Prices, dates, availability, numbers, and superlatives
must be supported by a sourced fact; otherwise they remain questions.

## Inbound liaison requests

At the start of a write or launch run, doc checks for requests that target
`doc`. `doc_ux_inbox` validates requests and reports each as `new`,
`answered`, `stale`, or `blocked`, with malformed files listed separately.
The responder records current input hashes and hashes claimed artifacts.
`done` is only accepted when its gates pass, a design decision and an
impression are referenced, and every claimed Markdown artifact is in a fresh
passing doc-lint report.

See [sister cooperation](sister-cooperation.md) for the request/response
contract and its upstream compatibility note.

## Records left by stages

The `doc-records` skill asks the agent to append an impression after each
completed stage and a decision record for every consequential choice.
Impressions include output paths and bind them to file or directory hashes.
When a figure is viewed, doc appends an image observation; when a vision model
is used, the post-tool hook appends a vision-tool event. Each image or event
must receive a long-form vision review before the session can finish.

| Stage or action | Work artifacts | Evidence to leave |
| --- | --- | --- |
| Gather | `survey.md`, `inquiries.md` | Stage impression; decisions about material source conflicts |
| Interview | `interview.md`, updated `inquiries.md` | Stage impression; user-source reference for intent |
| Brief and outline | `doc-brief.json`, `outline.md` or `launch-outline.md` | Stage impression; design decisions and source hashes |
| Draft | Target Markdown files | Stage impression for the completed draft; image review for each viewed figure |
| Lint and review | `doc-lint.json`, `review.md` or `launch-review.md` | Final stage impression; records cannot substitute for lint or review |
| Liaison response | `<id>.ux-response.json` | Valid VRP decision/impression references, gate verdicts, and current input/artifact hashes |

The Stop hook enforces the session-level subset described in
[records and vision](records-and-vision.md). Record files live under
`observations/doc/`; they are append-only operational evidence.
