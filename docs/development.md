# Development

This repository builds the `doc` OpenHands plugin and its standard-library
runtime helpers. The repository contract in [AGENTS.md](../AGENTS.md) is the
authoritative contribution checklist.

## Repository map

| Path | Responsibility |
| --- | --- |
| `plugins/doc/agents/`, `commands/`, `skills/` | OpenHands agents, slash commands, keyword skills, and path rule |
| `plugins/doc/scripts/` | Record, figure, liaison, CLI, and MCP runtime |
| `plugins/doc/hooks/` | Hook configuration, family hook copies, and doc-specific hooks |
| `plugins/doc/skills/doc-lint/scripts/` | Deterministic brief/document linter |
| `plugins/doc/skills/doc-lint/examples/` | Shipped product and launch example workspaces |
| `docs/`, `docs/adr/` | Technical reference, contracts, research index, and accepted decisions |
| `tests/` | Unit, contract, hook, asset, and release-script tests |
| `scripts/` | Plugin-load, docs, shared asset, release, and dependency tooling |

The plugin scripts do not depend on the repository's development packages.
Avoid adding a plugin-runtime dependency: hooks and MCP tools run with host
`python3` and the standard library. SDK integration checks use the separately
pinned `sdk-check` group.

## Local setup and checks

The project requires Python 3.12+ and pins the `uv` version in
`pyproject.toml`. Set up the locked development and SDK-check environments:

```sh
uv sync --locked --group sdk-check
```

The main contributor checks are:

```sh
uv run ruff check . && uv run ruff format --check .
uv run pyright
env -u BASH_ENV -u "BASH_FUNC_gh%%" uv run pytest -q
uv run python scripts/check_shared_hooks.py
uv run python scripts/check_shared_workflows.py
uv run python scripts/verify_docs.py
uv run --group sdk-check python scripts/check_plugin_load.py
```

Ruff excludes the canonical shared `_records.py` and `require_records.py`
copies because they follow wire's 100-character line length; their shared
integrity is checked by `scripts/check_shared_hooks.py`, and Pyright still
checks them.

CI runs pytest through `scripts/structural_coverage.py run`, which gates the
C0, C1, decision, C2, MC/DC and boundary floors in `pyproject.toml`
([test-coverage.md](test-coverage.md)). CI also runs the two
shipped-example lint commands shown in [operations](operations.md#verification).
The docs verifier checks local links and that accepted ADRs are indexed.

## Extending the plugin

- **Brief or report contract:** update `doc-brief-contract.md`, the linter and
  path-triggered guidance, examples, and regression tests together. Add
  negative tests for invalid inputs; do not weaken a contract to accept an
  ungrounded fact.
- **MCP tool:** add its closed input schema and handler in `doc_mcp.py`, route
  to the deterministic implementation, document arguments/results/errors in
  [MCP tools](mcp.md), and add focused tests.
- **VRP or SLP contract:** change the canonical producer/validator contracts
  together, preserve hash and workspace-path validation, and update
  [contracts](contracts.md), [records and vision](records-and-vision.md),
  and the relevant tests. Shared hook copies are maintained by the family's
  checker; do not patch them ad hoc.
- **Hook or event:** update `hooks/hooks.json`, the responsible stdlib script,
  agent frontmatter where needed (agents do not inherit plugin hooks), and
  [hooks](hooks.md); test both success and fail-mode behavior.
- **New skill or command:** add the SDK-compatible plugin asset, register it
  in the manifest only when required, describe its activation/arguments in
  the technical docs, and cover plugin loading with the existing checker.
- **Architecture change:** write an ADR with context, decision, consequences,
  and alternatives; add it to the [docs index](README.md#accepted-architecture-decisions).

Do not edit sibling repositories as part of a document-agent change. Avoid
secrets and generated workspace output in commits. Follow the explicit
staging and branch rules in `AGENTS.md`.

## Versions and release

The current package and plugin manifest version is `0.1.0`; the repository
release workflow keeps version declarations and `uv.lock` synchronized.
Version releases are driven by `.github/workflows/release.yml` and
`scripts/release_bump.sh`; see [operations](operations.md#release-process)
before changing the release process. The declared SDK version is
`openhands-sdk==1.53.0` (also checked by the exact README declaration).
