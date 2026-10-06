# Operations

Operational detail for maintainers and installers: the release process,
plugin update caveats, runtime surfaces, and verification recipes. For a
product overview see the [README](../README.md).

## Supported runtime and availability

The plugin manifest and Python project are currently version `0.1.0`. The
declared target is OpenHands Software Agent SDK v1.52.0, with Python 3.12+
for repository development. There is no doc tools image: hooks and the MCP
server invoke host `python3`; plugin record, liaison, figure, and lint
scripts use only the Python standard library. The SDK/tool packages are
installed by the repository’s `sdk-check` development group for plugin-load
verification, not as a runtime dependency embedded in the plugin. Initial
installation steps are in the [product README](../README.md).

## Release process

Run the `release` workflow manually with `workflow_dispatch`. Select a `bump`
input (`patch`/`minor`/`major`, defaulting to `patch`) or a `version` input
(an explicit `X.Y.Z` override). Setting `dry_run` rehearses the pipeline:
it validates the version arithmetic and runs verify, install-smoke, and the
release build against HEAD, but commits nothing, pushes nothing, and skips
the tag and Release — use it to exercise the workflow before a real release.
It runs only on `main`:

1. **bump-version** — `scripts/release_bump.sh` drives the state machine:
   `scripts/bump_version.py` checks the versions in
   `plugins/doc/.plugin/plugin.json`, `pyproject.toml`, the `doc-lint` and
   `doc-craft` `SKILL.md` files, and `uv.lock`, writes the new version, and
   checks that the `v<version>` tag does not exist. When the ruleset rejects
   a direct push to main, the bump goes through an auto-merged pull request.
   An explicit `version` equal to the current version releases `main` HEAD.
   The script's branches are covered by `tests/test_release_bump.py`, which
   stubs `gh`/`git` and rehearses dry-run, direct-push, and PR-fallback
   flows.
2. **verify** — the normal CI through the reusable workflow.
3. **install-smoke** — `scripts/smoke_install_plugin.py` installs from the
   target SHA with `install_plugin` and checks agents, skills, commands, and
   hooks.
4. **release** — zips `plugins/doc` (with `LICENSE` and
   `THIRD_PARTY_NOTICES.md`), and creates the tag and Release. (The shipped
   examples are linted by the verify job at the same SHA.)

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

`/doc:write` and `/doc:launch` use `task` only when it is in the
conversation's tool list. Otherwise they run their stages in the parent
conversation and report the no-task fallback. Since
SDK 1.51.0, the profile's `tools` is the only tool control: add
`task_tool_set` there. The retired `enable_sub_agents` and
`enable_switch_llm_tool` switches still fold into `tools` with a deprecation
warning until they are removed in SDK 1.56.0.

Sister inquiries through `task` need the sister plugin installed in the
same Agent Canvas. `/doc:doctor` lists which sisters it can see; missing
sisters are recorded as `not_available` and their facts come from their
workspace artifacts only.

## OpenHands runtime surfaces

- `model:` resolves through `LLMProfileStore` (`~/.openhands/profiles/`):
  `vibebb-author` for `doc-writer`, `doc-liaison`, and `doc-launch`;
  `vibebb-review` for `doc-review`. The `session_start` hook
  `ensure_llm_profiles.py` copies the conversation's `active_profile` into
  those names only when they are absent, and reports whether the review
  profile appears vision-capable.
- `permission_mode: never_confirm` is set on all four agents. Their prompt
  contracts limit product-document writes to the assigned stage; hooks
  protect generated lint and record artifacts separately.
- Sub-agents do not inherit plugin hooks, so each agent declares
  `protect-lint-report` and `safety-rail` in its frontmatter with the same
  commands as `hooks/hooks.json` (a test keeps them identical).
- `safety-rail` denies a deterministic denylist of terminal commands
  (root/home `rm -rf`, block-device writes, power commands, and the git
  operations the work contract bans). It is a narrow pattern matcher, not a
  security analyzer.
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
uv run python scripts/check_shared_hooks.py
uv run python scripts/check_shared_workflows.py
uv run --group sdk-check python scripts/check_plugin_load.py
```

The CI job also lints both shipped examples in full mode:

```bash
uv run python plugins/doc/skills/doc-lint/scripts/doc_lint.py \
  --root plugins/doc/skills/doc-lint/examples/desk-timer \
  --brief plugins/doc/skills/doc-lint/examples/desk-timer/doc-work/desk-timer/doc-brief.json \
  --no-write
uv run python plugins/doc/skills/doc-lint/scripts/doc_lint.py \
  --root plugins/doc/skills/doc-lint/examples/desk-timer-launch \
  --brief plugins/doc/skills/doc-lint/examples/desk-timer-launch/doc-work/desk-timer/doc-brief.json \
  --no-write
```

Coverage must meet the floors in `[tool.vibebb-coverage]` and `fail_under`
in `pyproject.toml` ([test-coverage.md](test-coverage.md)).

pytest selects subsets directly for a faster local check — `-k <expr>`, a
test path, or `-n 0` to disable the default `-n auto` workers:

```bash
uv run pytest -q tests/test_doc_lint.py
uv run pytest -q -k hooks
uv run pytest -q -n 0
```

Lint a workspace by hand (from its root):

```bash
python3 plugins/doc/skills/doc-lint/scripts/doc_lint.py --brief doc-work/<slug>/doc-brief.json --no-write
```

## Dependency updates

`.github/workflows/check-dependency-updates.yml` runs
`scripts/check_dependency_updates.py` weekly and aggregates update candidates
(PyPI direct/lock drift, the uv pin, Python minor, GitHub Actions pins
including subpath actions like `github/codeql-action/upload-sarif`, uvx tool
pins, and direct-download pins such as the zizmor wheel, the actionlint
release tarball, and trivy `version:` inputs) into a "Dependency update check
report" issue. Deferrals with reasons and re-check deadlines live in
`scripts/dependency_update_deferrals.json`.
Fetch failures are reported as unknown and keep the issue open until they
resolve.

The workflow also runs on pull requests that touch the collector's files
(the script, its tests, the deferrals file, or the workflow itself) and on
`workflow_dispatch` with `report_only: true`; in both cases it writes the
report to the step summary and a `dependency-update-report` artifact and
skips the tracking-issue update.

## Repository settings the CI design assumes

- **Dependency graph** must stay enabled (Settings → Advanced security);
  `dependency-review.yml` fails with "not supported on this repository"
  without it. The check is intentionally not required — it only reports on
  `pull_request` events.
- **Required checks** are `verify (3.12)`, `verify (3.13)`, `plugin-load`,
  and `zizmor`. Python 3.14 is not a required check. No `pull_request` trigger
  may gain a paths filter, or a required check can be skipped and auto-merge
  stalls.
- **"Allow GitHub Actions to create and approve pull requests"** must stay
  on: the release workflow's fallback path opens and auto-merges a
  version-bump PR when direct push is rejected.
- The branch ruleset requires **0 approving reviews** by design (solo
  maintainer plus bot auto-merge, including the unattended release
  fallback). Raising it makes release auto-merge PRs need human approval.

## CI runner network auditing

CI and image-publishing jobs use `step-security/harden-runner` in audit-only mode. It observes network egress without blocking requests; per-run insights are available in the GitHub Actions job summary.

## Settings-level posture (recorded decisions)

The following live in repository Settings rather than code; they are
intentional for the solo-maintainer bot-merge workflow and are recorded
here so audits do not re-flag them:

- Branch protection does not require approving reviews, code owners, or
  "apply to administrators": every merge is performed by automation
  (digest-lock, version-bump, and Devin PRs), so required approvers would
  only add friction to a pipeline that already gates on the required-check
  set. OpenSSF Scorecard reports this as Branch-Protection 3 and
  Code-Review 0; that is the recorded trade-off, not an oversight.
- The Dependency graph must stay enabled for `dependency-review.yml` to
  evaluate pull requests.
- `release.yml` is dispatch-only; run it once with `dry_run=true` before
  the first real release to rehearse bump, verify, and install-smoke
  without creating a GitHub release.
