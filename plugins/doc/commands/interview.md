---
description: Interview the user about the product — why it exists, who it is for, what matters to them — and record the answers for the doc writer.
argument-hint: "[slug] [topic]"
allowed-tools:
  - terminal
  - file_editor
---

# /doc:interview

You interview the user through this conversation. Their answers are the only
source of the maker's intent in the documents, so record them verbatim and
never paraphrase them into something they did not say.

1. Pick the work directory `doc-work/<slug>/`: the slug from the arguments,
   else the only existing `doc-work/*/`, else a short lowercase-hyphen name
   for the product (create the directory). If `inquiries.md` exists there,
   start from its `to: user` questions that are still `unanswered`.
2. Choose at most five questions from the question bank in the doc-inquiry
   Skill (`<doc plugin root>/skills/doc-inquiry/SKILL.md`), adding the
   argument topic if given. Ask in the conversation language, one numbered
   list, and say the user may skip any question or answer "skip".
3. Send the questions as your response **without a tool call** — that ends
   your turn and hands the conversation to the user. Do not answer them
   yourself and do not continue until the user replies.
4. When the user replies, append to `doc-work/<slug>/interview.md`
   (create it if missing) one block per question:

   ```markdown
   ## A<n>
   - question: <the question as asked>
   - answer: <the user's words, verbatim>
   - status: answered | skipped
   ```

   Update the matching entries in `inquiries.md` to `status: answered` (or
   leave them `unanswered` when skipped) and add `answer_ref:
   interview.md#A<n>`.
5. Show the user a two-to-four line summary of what you recorded and ask
   whether anything is wrong. If they correct something, rewrite that block.
   If `/doc:write` was waiting on this interview, continue it now.
