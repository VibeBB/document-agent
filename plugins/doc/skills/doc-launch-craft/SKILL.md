---
name: doc-launch-craft
description: Writing rules and templates for fact-grounded launch material - audiences, key messages, channels, the product page (landing page copy), the press release, the demo video script, and the launch plan, plus the claim rules for numbers, prices, dates, and superlatives. Use before writing or reviewing marketing or launch documents.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - product page
  - landing page
  - press release
  - launch
  - marketing
  - demo video
  - pitch
  - 製品ページ
  - ランディングページ
  - プレスリリース
  - ローンチ
  - マーケティング
  - デモ動画
---

# Doc launch craft

Launch material is chosen truth, well ordered. The brief (`doc-brief.json` schema 0.2) holds
the facts; this skill decides which of them a reader sees first.

## 1. Claim rules (checked by the linter where marked)

- Every number in the product page and the press release — price, dates, sizes, times,
  ratings — appears in a fact **(checked)**. Remove the number or add the fact with a source.
- Superlatives and absolutes (`best`, `No. 1`, `world's first`, `guaranteed`, `perfect`,
  `世界初`, `最高`, `唯一`, `保証`, …) are allowed only when a fact says them, e.g. a sourced
  award or a warranty term **(checked)**.
- Price, availability date, where to buy, and the press contact come from the user or a
  workspace file. Unknown means the material stays silent and the question goes to
  `open_questions` — never "coming soon at a great price".
- Comparisons with named competitors need a sourced fact about both products; otherwise do
  not compare.
- The maker's quote uses `product.vision` verbatim.

## 2. Audiences and messages

- 1..6 `launch.audiences`, each with a name the documents use and an `insight`: the need or
  frustration the copy answers, in the audience's words. Back each with facts (interview,
  survey, UX personas).
- 1..12 `launch.messages`, each one short sentence a reader could repeat. Tie each to the
  facts that make it true and to the target kinds that must use it **verbatim (checked)**.
- `launch.call_to_action.text` is the one action the product page asks for (e.g.
  `Pre-order Tomo Timer`); its facts are the price and availability. The product page's
  call-to-action section uses it verbatim **(checked)**.

## 3. Product page template

1. `# <Product>` and the tagline **(checked)**, then the lead key message.
2. An image or a Mermaid use-flow **(checked)**: what the reader does and gets.
3. `## Why <Product>` / `特長` **(checked)**: 3..5 benefits, each "benefit, then the fact that
   proves it".
4. `## Specifications` / `仕様`: a table from facts, with units.
5. `## <call to action>` (`Pre-order`, `Buy`, `Get`, `購入`, `予約`) **(checked)**: the call to
   action text, price, availability.

## 4. Press release template

1. `# <headline>`: product and the news in one line.
2. Lead paragraph that names the product **(checked)** and answers what, who, when, where.
3. Two or three body paragraphs: the problem, how the product solves it (key messages), a
   verbatim maker's quote when `product.vision` exists.
4. `## About <Product>` / `について` **(checked)**.
5. `## Media contact` / `報道関係のお問い合わせ` **(checked)**: only a sourced contact;
   otherwise say where to write (e.g. the shop's contact form) and list the open question.

## 5. Demo video script template

- A shot table with time, visual, and narration / audio columns **(checked)**; 15..60 s total
  for a first demo.
- Show the core experience from the UX contract in the order a user lives it; the first
  shot shows the problem, the last the product and the call to action.
- Use the product's own sounds (bard `cues.json`) for the moments they play on the device.
- Every on-screen claim follows the claim rules above.

## 6. Launch plan template

`## Audience`, `## Key messages`, `## Channels`, and `## Checklist` (or `Schedule`) sections
**(checked)**. Every `launch.audiences[].name` appears **(checked)**. The checklist has at least
two task items (`- [ ] ...`) **(checked)**; open questions that block the launch are items too.

## 7. Review checklist

- [ ] A reader of the product page can say what it is, why it matters to them, and what to do
      next after the first screen.
- [ ] Each audience finds its insight answered by at least one message.
- [ ] No number, price, date, comparison, or superlative lacks a fact.
- [ ] The key messages read the same in every document that uses them.
- [ ] The demo script shows the core experience, not a feature list.
- [ ] Open questions are listed for the user, not papered over.

## Records

Follow `doc-records/SKILL.md`: record hash-bound impressions after the plan, writing, and review
stages and decisions for consequential audience, message, or claim choices. Vision reviews are
advisory and never alter the doc-lint verdict.
