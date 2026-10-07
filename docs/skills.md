# Skills

Skills are defined by `SKILL.md` under `plugins/doc/skills/`. Agent
definitions refer to these files from their prompts; they do not declare a
`skills:` list. Keyword-triggered skills and path-triggered rules are distinct
SDK mechanisms.

| Skill | Trigger | Purpose |
| --- | --- | --- |
| `doc-brief-rules` | Path rule for `**/doc-brief.json` and `**/doc-lint.json` | Keep edits aligned with the brief contract, source requirements, and linter guidance |
| `doc-craft` | `readme`, `user manual`, `technical reference`, `quick start`, `quickstart`, `documentation`, `ドキュメント`, `取扱説明書`, `技術資料`, `クイックスタート`, `製品説明` | Reader-first product-document structure, templates, diagrams, accessibility, and review checklist |
| `doc-inquiry` | `sister`, `inquiry`, `interview`, `ask the user`, `姉妹`, `聞いて回`, `インタビュー`, `想い` | Fact ownership, read-only sister questions, inquiry/interview records, and the question bank |
| `doc-launch-craft` | `product page`, `landing page`, `press release`, `launch`, `marketing`, `demo video`, `pitch`, `製品ページ`, `ランディングページ`, `プレスリリース`, `ローンチ`, `マーケティング`, `デモ動画` | Fact-grounded launch audiences, messages, channels, templates, and claim rules |
| `doc-lint` | `doc-brief.json`, `doc-lint`, `doc_lint`, `documentation lint` | Brief schema summary, CLI usage, examples, and rejection-to-fix guidance |
| `doc-out-rules` | Path rule for `**/out/**` | Generated artifacts under `out/` are read-only projections written by the owning sisters — cite them as fact sources; change the design inputs and regenerate, never hand-edit |
| `doc-records` | `doc record`, `design rationale`, `vision review`, `stage impression` | VRP decision/impression/review requirements and record commands |

The path rules are injected when a matching brief, report, or generated
artifact is touched. The other five entries use keyword triggers. The
doc-lint skill summarizes the canonical contract in
[doc-brief-contract.md](doc-brief-contract.md) and links to its shipped
examples.
