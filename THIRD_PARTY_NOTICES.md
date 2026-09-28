# Third-Party Notices

document-agent is licensed BSD-3-Clause (see LICENSE). The linter and hook
scripts use only the Python standard library and bundle no third-party code.
Agents render Mermaid diagrams as Markdown text; no Mermaid code is shipped.
This file is not legal advice.

## Development tools

Used to build and verify the project; not distributed.

| Tool | License |
| --- | --- |
| ruff | MIT |
| pyright | MIT |
| pytest | MIT |
| uv | Apache-2.0 / MIT |
| zizmor (CI) | MIT |
| OpenHands SDK (`openhands-sdk`, `openhands-tools`) | MIT |

## Family scripts

Hook and release helpers (`safety_rail.py`, `ensure_llm_profiles.py`,
`scripts/bump_version.py`, `scripts/smoke_install_plugin.py`,
`scripts/check_dependency_updates.py`) are adapted from sibling VibeBB
repositories released under the same BSD-3-Clause license by the same
copyright holder.

If you add a bundled component, update this file in the same change.
