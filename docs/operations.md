# Operations

Operational detail for maintainers and installers: the release process,
plugin update caveats, runtime surfaces, and verification recipes. For a
product overview see the [README](../README.md).

## Release process

Run the `release` workflow manually with `workflow_dispatch`. Select a `bump`
input (`patch`/`minor`/`major`, defaulting to `patch`) or a `version` input
(an explicit `X.Y.Z` override). It runs only on `main`:

1. **bump-version** — `scripts/bump_version.py` checks the versions in
   `plugins/doc/.plugin/plugin.json`, `pyproject.toml`, the `doc-lint` and
   `doc-craft` `SKILL.md` files, and `uv.lock`, writes the new version, and
   checks that the `v<version>` tag does not exist. When the ruleset rejects
   a direct push to main, the bump goes through an auto-merged pull request.
   An explicit `version` equal to the current version releases `main` HEAD.
2. **verify** — the normal CI through the reusable workflow.
3. **install-smoke** — `scripts/smoke_install_plugin.py` installs from the
   target SHA with `install_plugin` and checks agents, skills, commands, and
   hooks.
4. **release** — lints the shipped example, zips `plugins/doc` (with
   `LICENSE` and `THIRD_PARTY_NOTICES.md`), and creates the tag and Release.

If any step fails, neither a tag nor a Release is created.

## Updating the plugin

Agent Canvas caches a plugin repository per source string. If a new ref does
not take effect, uninstall the plugin, delete
`~/.openhands/cache/extensions/document-agent-*` and its `.lock` file, and
install again; then confirm the installed plugin's `resolved_ref` matches the
intended commit:

```bash
curl -sS -H "X-Session-API-Key: $KEY" http://127.0.0.1:8000/api/plugins/installed
```

## If sub-agents do not activate

`/doc:write` uses `task` only when it is in the conversation's tool list.
Otherwise it runs the liaison, writer, and review stages in the parent
conversation and says so on its final `Path: fallback (no task)` line. With
SDK 1.49.x, `enable_sub_agents` adds `task` only when the agent profile's
`tools` is unspecified; if `tools` is set explicitly, add `task_tool_set`.

Sibling inquiries through `task` need the sibling plugin installed in the
same Agent Canvas. `/doc:doctor` lists which siblings it can see; missing
siblings are recorded as `not_available` and their facts come from their
workspace artifacts only.

## OpenHands runtime surfaces

- `model:` resolves through `LLMProfileStore` (`~/.openhands/profiles/`):
  `vibebb-author` for `doc-writer` and `doc-liaison`, `vibebb-review` for
  `doc-review`. The `session_start` hook `ensure_llm_profiles.py` clones the
  conversation's `active_profile` into those names when they are absent.
- `permission_mode: never_confirm` on all three agents; their only write
  paths are the target documents and `doc-work/<slug>/`.
- Sub-agents do not inherit plugin hooks, so each agent declares
  `protect-lint-report` and `safety-rail` in its frontmatter with the same
  commands as `hooks/hooks.json` (a test keeps them identical).
- `safety-rail` denies a deterministic denylist of terminal commands
  (root/home `rm -rf`, block-device writes, power commands, and the git
  operations the work contract bans). It is advisory depth, not a security
  analyzer.
- The plugin root resolves in this order: `$DOC_PLUGIN_ROOT`,
  `$OPENHANDS_PROJECT_DIR/plugins/doc`, `$HOME/.agents/plugins/doc`,
  `$HOME/.openhands/plugins/installed/doc`.

## Verification

```bash
uv sync --locked --group sdk-check
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest -q
uv run python scripts/verify_docs.py
uv run --group sdk-check python scripts/check_plugin_load.py
```

Lint a workspace by hand (from its root):

```bash
python3 plugins/doc/skills/doc-lint/scripts/doc_lint.py --brief doc-work/<slug>/doc-brief.json --no-write
```

## Dependency updates

`.github/workflows/check-dependency-updates.yml` runs
`scripts/check_dependency_updates.py` weekly and aggregates update candidates
(PyPI direct/lock drift, the uv pin, Python minor, GitHub Actions pins, uvx
tool pins) into a "Dependency update check report" issue. Deferrals with
reasons and re-check deadlines live in
`scripts/dependency_update_deferrals.json`.
Fetch failures are reported as unknown and keep the issue open until they
resolve.

## CI runner network auditing

CI and image-publishing jobs use `step-security/harden-runner` in audit-only mode. It observes network egress without blocking requests; per-run insights are available in the GitHub Actions job summary.
