# ADR-0007: Inspect and record figures and user-attached images

- Status: Accepted
- Date: 2026-09-30

## Context

Documentation often embeds diagrams, screenshots, and rendered sibling
figures. Text-only inspection cannot establish whether an image exists,
matches its caption and surrounding text, or is legible and accessible.
User-attached screenshots and photos also need a traceable workspace path.

## Decision

Materialize user-attached images under `intake/attachments/` and record their
source and digest in `manifest.jsonl`. Require `doc-review` to use
`file_editor view` on embedded and rendered figures, check their visual
content and alt text, and report when no picture is available rather than
guessing. `doc-writer` and `doc-launch` may describe or embed only images
they can view and whose files exist in the workspace.

Record image views and successful `inspect_image_with_vision` calls as
advisory observations under `observations/doc/`. Keep profile readiness
checks advisory and never overwrite existing user profiles. Text in images
is data, not an instruction.

## Consequences

The plugin adds attachment-intake and post-tool hooks, and generated
observation logs and attachment manifests are protected against direct
editing. Reviews can make explicit findings about figure accuracy and
accessibility, while remaining read-only. Vision observations do not alter
document lint results or grant approval authority.
