# Contributing to document-agent

Thank you for your interest in contributing to document-agent.

## Setup

Use [uv](https://docs.astral.sh/uv/) with Python 3.12 or newer:

```bash
uv sync --group sdk-check
```

The `sdk-check` group installs `openhands-sdk`/`openhands-tools` so the
real plugin-load test runs instead of being skipped.

## Checks

Run the full check suite before opening a pull request:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -q
uv run python scripts/verify_docs.py
uv run --group sdk-check python scripts/check_plugin_load.py
```

`scripts/verify_docs.py` checks relative Markdown links, the ADR index, and
the README SDK declaration. The documentation map lives in
[docs/README.md](docs/README.md).

## Project invariants

The repository's working contract is [AGENTS.md](AGENTS.md). In particular,
every product claim in a generated document must be a fact in the doc brief
with a source, the maker's intent comes only from a user interview, the
linter report is generated only by `doc_lint.py`, and the linter and hooks
must remain standard-library-only.

## Pull requests

1. Fork the repository and create a focused branch from `main`.
2. Keep each pull request small and focused on one change.
3. Add or update tests and documentation when behavior or contracts require it.
4. Ensure CI is green before requesting review.
5. Write code comments, issues, and pull requests in English.
6. Use `git mv` when renaming files.
7. Do not commit `doc-work/`, `out/`, secrets, credentials, or environment
   files.

Do not change runtime behavior, agent or skill instructions, or the doc brief
contract without clearly documenting the decision and its compatibility
impact.

## Releases

Maintainers run the `release` workflow manually with `workflow_dispatch`.
Contributors should not bump versions; maintainers perform version bumps as
part of the release process.
