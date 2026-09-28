# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting a vulnerability

Please do not open public issues for security vulnerabilities. Report them
via GitHub's private vulnerability reporting on this repository, or by
contacting the maintainer directly. Include:

- the affected version/commit,
- a minimal reproduction (doc brief, command, or hook payload),
- impact assessment if known.

You can expect an acknowledgement within a few days. We will coordinate a
fix and disclosure with you before publishing details.

## Scope notes

The doc plugin writes Markdown into the OpenHands workspace. Its linter and
hooks use only the Python standard library, spawn no external tools, and add
no network listeners. The linter only reads files inside the workspace root
and refuses target paths and links that leave it.

Interview answers are recorded verbatim in `doc-work/<slug>/interview.md`.
Do not paste secrets or personal data into interviews; `doc-work/` is
git-ignored by this repository but may not be in yours.

Secrets must never be written to logs, inputs, or commits; see the
invariants in [AGENTS.md](AGENTS.md).
