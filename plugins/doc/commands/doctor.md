---
description: Probe the doc plugin install — plugin root, layout, and which sister plugins can be asked.
allowed-tools:
  - terminal
---

# /doc:doctor

Resolve the doc plugin root the same way the hooks do (`$DOC_PLUGIN_ROOT`,
`${OPENHANDS_PROJECT_DIR}/plugins/doc`, `~/.agents/plugins/doc`,
`~/.openhands/plugins/installed/doc`, `~/plugins/installed/doc`,
`$OH_PERSISTENCE_DIR/plugins/installed/doc`), then run:

```bash
p=$(for c in "${DOC_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/doc" "${HOME:-}/.agents/plugins/doc" "${HOME:-}/.openhands/plugins/installed/doc" "${HOME:-}/plugins/installed/doc" "${OH_PERSISTENCE_DIR:-/nonexistent}/plugins/installed/doc"; do [ -f "$c/hooks/scripts/doc_doctor.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || { echo "doc plugin root unresolved" >&2; exit 1; }; python3 "$p/hooks/scripts/doc_doctor.py"
```

Report the `additionalContext` findings verbatim — plugin root resolution,
plugin layout, the sister list, and the liaison inbox counts. A `missing`
sister means questions it would own go to the user in the interview instead.
An unanswered liaison request means a sister is waiting: list it with
`doc_tool.py ux inbox` and answer it with `doc_tool.py ux respond`.
