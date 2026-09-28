---
name: doc-lint
description: The doc brief contract (doc-brief.json schema 0.1 / 0.2), the doc_lint.py CLI, and the rejection table for README, user manual, technical reference, and launch documents (product page, press release, demo script, launch plan). Use before writing a doc brief or when a lint problem needs fixing.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - doc-brief.json
  - doc-lint
  - doc_lint
  - documentation lint
---

# Doc lint

`scripts/doc_lint.py` (Python standard library only) validates the brief and lints the target
documents. Run it from the workspace root; target paths are relative to it.

```bash
python3 <doc plugin root>/skills/doc-lint/scripts/doc_lint.py --brief doc-work/<slug>/doc-brief.json --brief-only
python3 <doc plugin root>/skills/doc-lint/scripts/doc_lint.py --brief doc-work/<slug>/doc-brief.json
```

| Option | Meaning |
| --- | --- |
| `--brief-only` | Validate the brief only; writes nothing. |
| `--no-write` | Full lint without writing the report. |
| `--root DIR` | Resolve target paths against `DIR` (default: current directory). |
| `--out PATH` | Report path (default: `doc-lint.json` next to the brief). |

Exit `0` pass, `1` fail (report still written in full mode), `2` usage error or unreadable
brief (nothing written). The report is deterministic and records the sha256 of the brief and
every document, so the Stop hook reports it `stale` when either changes after linting.

## Brief contract summary

Complete examples: `examples/desk-timer/doc-work/desk-timer/doc-brief.json` (schema 0.1)
and `examples/desk-timer-launch/doc-work/desk-timer/doc-brief.json` (schema 0.2, launch). The canonical
contract: `docs/doc-brief-contract.md`.

| Key | Rule |
| --- | --- |
| `artifact_kind` | `"doc_brief"` |
| `schema_version` | `"0.1"`, or `"0.2"` for launch kinds |
| `language` | `"ja"` or `"en"` |
| `product.name` / `tagline` / `summary` / `problem` | strings, 1..80 / 1..140 / 1..1200 / 1..800 chars |
| `product.audience` / `value` | 1..6 strings each |
| `product.vision` + `vision_source` | optional, together; source must be `user_interview` |
| `targets[]` | `{kind, path}`, unique kinds; 0.1: `readme`, `user_manual`, `technical_reference`; 0.2 adds `product_page`, `press_release`, `demo_script`, `launch_plan`; relative `.md` path |
| `sources[]` | `{id: S<n>, kind, ref}`; kind `file`, `git_log`, `conversation`, `user_interview`, `sibling_agent`, `sibling_artifact`; sibling kinds need `agent` (`wire`, `mech`, `circuit`, `ux`, `bard`) |
| `facts[]` | `{id: F<n>, text, sources: [S<n>, ...]}`, at least one fact, at least one known source each |
| `inquiries[]` | `{id: Q<n>, to, question, status}`; `answered` needs `answer` and a `source` from that sibling (or `user_interview` for `to: user`) |
| `open_questions[]` | 0..50 strings |
| `launch` | 0.2 only; required with, and only allowed with, a launch target |
| `launch.audiences[]` | 1..6 `{id: A<n>, name, insight, facts}` |
| `launch.messages[]` | 1..12 `{id: M<n>, text, audiences, facts, targets}`; `targets` are launch kinds in the brief |
| `launch.channels[]` | 0..12 `{id: C<n>, kind, audiences, messages}`; kind `product_page`, `press`, `social`, `video`, `email`, `event`, `crowdfunding`, `store`, `community` |
| `launch.call_to_action` | `{text, facts}` |

Unknown keys are rejected. Quality-document kinds (`quality_plan`, `test_report`,
`risk_assessment`, `inspection_record`) are reserved and rejected by schema 0.1.

## Rejection table

| Problem | Fix |
| --- | --- |
| `missing: target document does not exist` | Write the document at the target path. |
| `structure: the first heading must be a single H1 title` | Start with one `# <Product>` heading. |
| `placeholder text left in document` | Remove TODO/TBD/FIXME/要確認/未定; move the unknown to `open_questions`. |
| `identity: product name ... never appears` | Name the product as in `product.name`. |
| `unknown mermaid diagram type` / `empty mermaid block` | Start the block with a Mermaid type (`flowchart LR`, `sequenceDiagram`, …). |
| `broken relative link` / `link leaves the root` | Link to files that exist inside the workspace. |
| `unclosed code fence` | Close every fence. |
| `readme: no Quick start section` | Add an H2 `Quick start` / `クイックスタート`. |
| `readme: the product explanation ... before the Quick start` | Put a "what is it" H2 before the Quick start. |
| `readme: no diagram ... before the Quick start` | Add a Mermaid diagram (or an existing image) to the explanation. |
| `readme: Quick start needs >=2 numbered steps` / `has N steps (max 7)` | Numbered steps, 2..7; move detail to the manual. |
| `readme: must link to the user_manual / technical_reference` | Link every other target from the README. |
| `user_manual: no usage section` / `no troubleshooting / FAQ section` | Add `How to use` / `使い方` and `Troubleshooting` / `トラブルシューティング` sections. |
| `technical_reference: no architecture section` / `architecture section has no diagram` | Add `Architecture` / `アーキテクチャ` with a Mermaid diagram inside it. |
| `technical_reference: no interface / spec section` | Add `Interfaces` / `仕様` (API, CLI, protocol, ratings). |
| `technical_reference: no development / test section` | Add `Development` / `開発` (build, test, release). |

| `unsourced superlative '...'` | Remove it, or add the fact (with a source) that says it. |
| `number N is not in any fact` (product page, press release) | Remove the number, or add the fact with a source. Numbers in links and inline code are ignored. |
| `<kind>: key message not used verbatim` | Use each `launch.messages[].text` assigned to the kind word for word. |
| `product_page: the tagline does not appear` / `no product image or diagram` | Show `product.tagline` and an image or Mermaid use-flow. |
| `product_page: no features / benefits section` / `no call-to-action section` | Add `Why <Product>` / `特長` and a `Pre-order` / `Buy` / `購入` section. |
| `product_page: the call-to-action section does not use launch.call_to_action.text` | Put the call-to-action text verbatim in that section. |
| `press_release: the lead paragraph ... must name the product` | Name the product in the first paragraph after the headline. |
| `press_release: no About section` / `no media contact section` | Add `About <Product>` and `Media contact` / `報道関係のお問い合わせ`. |
| `demo_script: no shot table ...` | Add a table with time, visual, and narration / audio columns. |
| `launch_plan: no audience / message / channel / checklist section` | Add `Audience`, `Key messages`, `Channels`, `Checklist` sections. |
| `launch_plan: checklist needs >=2 task items` / `audience '...' never appears` | Use `- [ ]` items; name every audience from the brief. |

Section names match by keyword (English or Japanese) on H2/H3 headings, so natural titles such
as `## How to use Tomo Timer` or `## 使い方` pass.
