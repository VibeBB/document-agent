# OpenHands SDK v1.51.0 feature evaluation (document-agent)

Scope: `openhands-sdk`, `openhands-tools`, and any directly pinned OpenHands packages move from 1.50.1 to 1.51.0 (PyPI upload 2026-10-03T07:38Z). The complete 18-commit upstream range `v1.50.1..v1.51.0` was reviewed. uv moves from 0.12.21 to 0.12.22. ruff was already pinned at the latest release (0.16.10); no change.

Primary source: [OpenHands SDK v1.51.0 release](https://github.com/OpenHands/software-agent-sdk/releases/tag/v1.51.0) and the [v1.50.1...v1.51.0 compare](https://github.com/OpenHands/software-agent-sdk/compare/v1.50.1...v1.51.0).

## SDK 1.50.1 -> 1.51.0

| Upstream change | Decision | Evaluation |
| --- | --- | --- |
| #5151 agent-profiles: `tools` is the only tool control, selected from one server catalog | adopted | `enable_sub_agents` and `enable_switch_llm_tool` are retired (deprecated in 1.51.0, removed in 1.56.0) and fold into `tools` with a warning. All four doc agents already select `task_tool_set` in their frontmatter `tools`, and `scripts/check_plugin_load.py` passes under 1.51.0. README install steps and `docs/operations.md` now tell users to add `task_tool_set` to the profile `tools` instead of `enable_sub_agents`. |
| #5358 keep delegated sub-agents within the profile's tools and MCP servers | adopted implicitly | Tightens what `task` sub-agents can reach; consistent with the plugin boundary (doc sub-agents only need their declared `tools`). No plugin change needed. |
| #5406 launch every agent through resolve and finalize | adopted implicitly | Internal launch-path unification; plugin load and agent definitions are unaffected (`check_plugin_load.py` passes). |
| #5449 let a profile replace the agent's persona | not adopted | VibeBB profiles (`vibebb-author`, `vibebb-review`) are LLM profiles, not agent personas; doc agents keep their shipped personas. |
| #5450 loaded tools supply their system-prompt guidance (browser) | not applicable | The plugin does not load the browser tool (`register_default_tools(enable_browser=False)` in the plugin-load check). |
| #1326 fix find_dotenv assertion error in local conversation | adopted implicitly | Plugins run in local conversations; the crash fix applies with the pin. |
| #5332 resolve prompt_cache_key via real provider for proxied models | adopted implicitly | Correctness fix for LLM profiles resolved through proxies; no repo configuration to change. |
| #5274 make OpenRouter a verified provider | not adopted | Available upstream; VibeBB profiles do not require OpenRouter, so nothing to configure. |
| #5412 router: send system+user classifier messages for direct-routing | not applicable | LLM-router internals; the repo does not configure a routing model. |
| #5434 deprecate `ACPAgentSettings.llm` | not applicable | No ACP agents in this repository. |
| #5417 agent-server: resolve provider connection in `/switch_llm` | upstream image | This repository does not build or manage an OpenHands agent-server image. |
| #5419 bump pydantic 2.12.5 -> 2.13.5 | lock-only | Picked up through `uv.lock` transitively. |
| #5425, #5428 TypeScript client eslint bumps | not applicable | This repository does not use the SDK TypeScript client. |
| #4945, #5415 upstream CI fixes | not applicable | Changes to the upstream repository's own workflows only. |
| #5397 stress-test run slot | not applicable | Upstream test-only change. |
| #5470 release commit | not applicable | Release housekeeping. |

## uv 0.12.21 -> 0.12.22

| Upstream change | Decision | Evaluation |
| --- | --- | --- |
| CPython 3.10.22, 3.11.17, 3.12.15, 3.13.16, 3.14.8 builds | inherent | `uv python` can install newer patch releases; no repo change. |
| Record workspace-member default groups / dependency-group Python requirements in lockfiles | inherent | This repo is a single project (no workspace members); the metadata additions are harmless. |
| Verify unchanged requirements against existing lockfile hashes when relocking | inherent | Reliability fix for `uv lock`; applies automatically. |
| `UV_PYTHON_ARCH` configuration | not adopted | No architecture-specific interpreter selection needed on CI or the dev VM. |
| Preview: `--no-default-groups` honored by `uv audit`, clearer offline errors | n/a | `uv audit` is a preview feature the repo does not invoke. |
| Binary size reduction (compressed embedded Python metadata) | inherent | Applies automatically. |

## Compatibility deferrals

MCP 2.x remains deferred: installed SDK 1.51.0 metadata still requires `fastmcp>=3.2.0,<4`, which caps `mcp<2` (installed: fastmcp 3.4.7, mcp 1.30.0). This repository keeps no `mcp` deferral entry in `scripts/dependency_update_deferrals.json` — the cap is transitive — and the existing `python-version` deferral (3.14 pending upstream verification) is unchanged. The `openhands-agent-server` image tag `1.51.0-python` is available upstream; no committed image lock is edited by this bump.
