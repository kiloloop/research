# Cross-Runtime Parity Matrix

**Date**: 2026-08-26

> Maintained by the Claude Code and Codex changelog skills; source path: `runtime-comparison/runtime_capability_matrix.md`.

This is a capability comparison across the currently profiled agent runtimes (Claude Code, Codex, ZCode), compiled from each runtime's self-report and current runtime changelogs. Cursor support is scaffold-only until Cursor-owned onboarding lands, so Cursor is intentionally excluded from this comparison table; see the public [runtime capability schema](https://github.com/kiloloop/oacp/blob/main/docs/protocol/runtime_capabilities.md) for its conservative scaffold defaults.

Claude was last checked against Claude Code `v2.1.246` (verified in-session 2026-08-26 via `claude --version`; release notes reviewed through `v2.1.247`) with Claude Fable 5 (`claude-fable-5`, serving model verified in-session on the 1M-context variant). Fable 5 (released 2026-06-09, first Mythos-class model) is now included in Max and Team Premium plan usage as part of the shared weekly limit pool (the launch-window free-inclusion/credit period has ended); the API rate is $10/$50 per MTok. Claude Opus 5 (`claude-opus-5`, released 2026-07-24) is the current Opus tier at $5/$25 per MTok with the same 1M context; Opus 4.8 remains available at the same price and remains the safeguard-fallback target for Fable 5's classifier fallbacks (unchanged by the Opus 5 release).

Codex was last checked against stable CLI `0.150.1`, GPT-5.6, Codex app changelog entries through 2026-08-25, and OpenAI API changelog entries through 2026-08-21. Runtime availability remains configuration-dependent: standard multi-agent support, memories, apps, browser use, computer use, goals, hooks, and workspace dependencies are stable and enabled in the checked runtime; multi-agent V2 is disabled, while token budgets, current-time reminders, and remote Code Mode may still require explicit enablement or experimental configuration. The GPT-5.6 API advertises a 1.05M context window, but the checked Codex runtime currently uses a 272K active window, so practical workflow sizing remains conservative.

ZCode is profiled as a live in-session self-report by the ZCode runtime itself (GLM-5.3, `builtin:zai-coding-plan/GLM-5.3`), captured 2026-08-26 and re-verified in a second session the same day. The runtime is a desktop app only — ZCode `3.9.2` (`CFBundleVersion` 3.9.2.6069, verified via the app bundle's Info.plist; no standalone CLI binary on PATH) with auto-updates and release notes published only at zcode.z.ai/en/changelog. Its column reflects the tool surface, skills, and official plugin inventory available in those sessions (browser-use, document-skills, skill-creator, zcode-cua, zcode-guide; the plugin cache also ships android-emulator, ios-simulator, and restore-legacy-sessions, which are not skill-bearing in-session). The local provider config declares a 1M context and 128K output for GLM-5.3 on the coding-plan surface; pricing is not surfaced in-session and remains unstated.

---

## 1. Core Capability Matrix

| Capability             | Claude (Claude Code CLI)                                                   | Codex (Desktop App)                                                                            | ZCode (GLM-5.3)                                                        |
| ---------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Spawn background tasks | Yes — background-by-default Agent spawns, Bash `run_in_background`, and a Monitor tool that streams background output as notifications | Yes — shell background processes                                                               | Yes — Bash `run_in_background` plus background agents                  |
| Spawn subagents        | Yes — typed agents (Explore, Plan, general-purpose, code-reviewer, etc.) plus a `fork` type that inherits the full conversation and prompt cache; nested depth 3 by default; a first-call model 404 falls back to the session's model chain and `maxTurns` stops return partial output | Yes — stable native multi-agent lifecycle with runtime metadata and follow-up controls         | Yes — typed agents (general-purpose, Explore) with scoped tools        |
| Parallel agent teams   | Yes — named teammates in a per-session implicit team with SendMessage/ListAgents; shared task-list tools are env-gated (`CLAUDE_CODE_ENABLE_TODO_TOOLS=1`) on Opus 4.8, Sonnet 5, and Fable 5 | Partial — parallel delegation, a task dashboard, `codex queue`, and task mentions are supported; opt-in multi-agent V2 adds configurable models, reasoning, concurrency, and roles, but there is no shared team/task-list primitive | Partial — concurrent subagent launches with SendMessage and task-output tracking, but no shared team/task-list primitive |
| MCP tools              | Yes — extensible via MCP servers                                           | Yes — MCP/plugin support with `/mcp verbose`, per-server environment targeting, read-only MCP parallelism, scriptable plugin inventory, and default tool-search exposure where supported | Yes — user/workspace-configured MCP servers plus plugin-shipped servers (computer use, Node REPL, web reader) |
| Web search             | Yes — native WebSearch tool                                                | Yes — web search/fetch tools; hosted web tools are expanding in code-mode flows                | Yes — native WebSearch tool                                             |
| Browser interaction    | Yes — Claude in Chrome (first-party extension via `--chrome`/`/chrome`): navigate, click, type, screenshots, console and network reads, file uploads, GIF recording, under per-site permissions; requires the extension and a `/login` session (not API-key or third-party-provider auth). WebFetch (read-only, HTML→markdown) remains the fallback | Configuration-dependent — in-app Browser and supported browser extensions can navigate, click, type, inspect, and capture approved contexts; WebMCP can expose site-native tools on supported models, while history and site tools remain separately permissioned | Yes — browser-use plugin (navigate, click, type, screenshot) plus zcode-cua desktop computer use |
| File system access     | Sandboxed — configurable read/write allowlists                             | Policy-dependent per session; named permission profiles can include managed deny-read rules that persist across permission changes, and untrusted projects do not load project instructions | Permission-gated — Read/Write/Edit tools and Bash run behind a user-selected permission mode |
| Multi-folder projects  | Manual workspace composition — `--add-dir`/`additionalDirectories` extend the working set; no primary-folder model | Yes — in a trusted project, the primary folder controls new chats, Git, and automatic instruction/skill/config discovery; secondary folders provide file access | Manual workspace composition (single primary working directory)        |
| Git operations         | Yes — via Bash (may need sandbox configuration)                            | Yes — native; in a multi-folder project, operations are rooted in the primary folder           | Yes — via Bash                                                          |
| GitHub CLI (gh)        | Yes — via Bash (may need sandbox configuration)                            | Yes — authenticated                                                                            | Yes — via Bash                                                          |
| Session memory         | Strong — auto-loaded MEMORY.md + optional MCP memory                       | Partial — stable generated app memories plus OACP file memory; app memories are not protocol SSOT | Partial — no auto-loaded MEMORY.md; prior-session context via explicit session handoff (ReadSessionContext) |
| Interactive mode       | Yes — CLI chat with permission modes (including classifier-driven auto mode), plan mode, `/fork` into its own worktree, background sessions (`claude agents`), and Remote Control from claude.ai web/mobile | Yes — desktop app and CLI/TUI, including Plan and Goal modes, task dashboard and queue, task mentions, named and pinned sessions, side-chat switching, forks, and archive/unarchive/delete flows | Yes — CLI chat with permission modes and structured plan mode (explore → plan → approve) |
| Context window         | ~1M across the current lineup (Fable 5, Opus 5, Opus 4.8); auto-compaction extends indefinitely | GPT-5.6 Sol, Terra, and Luna advertise 1.05M through the API; the checked Codex runtime uses a 272K active window, with runtime-dependent compaction | GLM-5.3 local provider config declares 1M context / 128K output (coding-plan surface); automatic context summarization carries long sessions forward |
| Cost model             | Token-based, visible in statusline; Fable 5 API rate is $10/$50 per MTok (2× the $5/$25 shared by Opus 5 and Opus 4.8) | ChatGPT sessions do not surface per-session cost; Sol API pricing is temporarily $4/$20 per MTok through at least 2026-11-21, while Terra and Luna target lower-cost work | Token-based; per-session cost not surfaced in-session                  |
| Sandbox restrictions   | Yes — configurable read/write/network allowlists with wildcard read-deny precedence, credential masking (`sandbox.credentials`), and auto-mode classifier rules viewable and editable in `/permissions` | Session-dependent; supports persistent managed deny-read policies, isolated `codex exec`, named permission profiles, managed requirements, explicit approval policies, and trust-gated project instructions | Yes — user-selected permission mode gates tool calls                    |

---

## 2. Distinctive Capabilities

| Capability                       | Runtime       | Details                                                                      |
| -------------------------------- | ------------- | ---------------------------------------------------------------------------- |
| Typed subagent orchestration     | Claude        | Multiple agent types with scoped tools, model and effort selection, and a `fork` type that inherits the parent conversation |
| Team coordination primitive      | Claude        | Named teammates in a per-session implicit team, SendMessage/ListAgents (teammates listed since v2.1.239), shutdown and plan-approval protocol; shared task lists env-gated on newer models (v2.1.233) |
| Cross-task coordination          | Codex         | `codex agents`, `codex queue`, and task mentions coordinate native Codex tasks; their messages are context, not verified protocol authority |
| Dynamic multi-agent workflows    | Claude        | Workflow tool orchestrates tens–hundreds of agents; `/workflows` to view     |
| Plan mode                        | Claude, Codex | Claude has structured explore → plan → approve → implement; Codex CLI can move from planning into fresh-context implementation |
| Auto-compaction                  | Claude        | Context auto-compresses, enabling unlimited session length                   |
| Cross-session semantic search    | Claude        | MCP-based searchable memory (optional)                                       |
| Cross-session messaging          | Claude        | SendMessage reaches the user's other Claude Code sessions across machines (macOS/Linux/Windows) by name or `@`-mention, with ListAgents discovery (including the session's own name and live teammates); inbound delivery is configurable (`crossSessionInbound` accept/hold/refuse, `dialogExpiry`), refused, oversized, or dropped sends are reported to the sender, one-shot `notify_when_idle` subscriptions are available, and messages can initiate conversations with Remote Control sessions by name |
| Browser automation              | Claude, Codex, ZCode | Claude Code drives Chrome, Edge, and other Chromium browsers through the Claude in Chrome extension (navigate, click, type, screenshots, console/network, uploads, GIF recording) under per-site permissions. Codex in-app Browser and extensions for Chrome, Edge, Brave, Opera, and Vivaldi can act in approved contexts; WebMCP site tools are model- and configuration-dependent. ZCode ships a browser-use plugin backed by a fresh Node REPL kernel |
| GPT-5.6 model family            | Codex         | Sol, Terra, and Luna provide task-tier choices; the API advertises 1.05M context while the checked Codex runtime uses a 272K active window |
| Image generation                 | Codex         | Codex CLI image generation is enabled by default; ZCode exposes image search, not generation |
| Image search                     | ZCode         | `image_search` MCP tool from the document-skills plugin finds web images by query |
| URL content reading (no browser) | ZCode         | WebFetch converts pages to markdown; the web-reader MCP server fetches and converts URL content without a browser |
| PTY / terminal stdin             | Codex         | Codex: native PTY (Claude and ZCode lack stdin support)                      |
| `apply_patch` editing            | Codex         | Grammar-based file edits                                                     |
| App-level computer use           | Codex, ZCode  | Codex: foreground macOS and Windows app workflows in supported regions. ZCode: zcode-cua plugin drives macOS apps through accessibility-first semantic actions with pixel-level fallback |
| Windows computer use             | Codex         | Codex app can operate Windows desktop apps in the foreground when available                    |
| Remote host control              | Codex, Claude | Codex mobile or desktop remote control can run work on connected Mac or Windows hosts with host-local files, credentials, plugins, skills, and config. Claude Code's `claude remote-control` serves a local session to claude.ai web and mobile with host-local files, credentials, and config, and its cross-session messaging reaches those sessions by name |
| App-level artifact review        | Codex         | Sidebar preview for generated PDFs, spreadsheets, documents, and presentations |
| App-level PR review              | Codex         | PR sidebar can inspect changed files, review comments, and follow-up fixes   |
| Multi-folder projects            | Codex         | One trusted project can span repositories; the primary folder owns Git and automatic instruction, skill, and config discovery, while secondary folders are file-access-only |
| Session organization             | Codex         | CLI/TUI supports named and pinned sessions, side-chat switching, archive/unarchive, deletion, and temporary or persisted forks |
| Event-triggered tasks            | Codex         | ChatGPT web/mobile tasks can react to selected GitHub pull-request events; events may be coalesced, cannot be combined with a time schedule, and do not run against a local folder or worktree |
| Shared task snapshots            | Codex         | Read-only task snapshots can be shared by link; review secrets and private context first because link possession grants access to the snapshot |
| GitLab cloud tasks               | Codex         | GitLab support is available as a cloud beta; availability and repository authorization remain workspace-dependent |
| App-server automation            | Codex         | JSON-RPC app-server, SDK, schema generation, thread APIs, and authenticated transports; `codex mcp-server` is deprecated, the SDK is preferred for CI/jobs, and WebSocket/remote Code Mode surfaces remain experimental |
| Hosted site deployment           | Codex         | Sites preview can create, deploy, inspect, and manage hosted websites or internal tools through the Codex app |
| Plugin marketplace inventory     | Codex         | Agent Plugin manifests, workspace publishing, additional marketplaces, and `codex plugin list --json`; availability and trust remain configuration-dependent |
| Goal mode                        | Codex         | Stable long-running objective mode with dedicated state; candidate for OACP wait/review-loop experiments |
| Record & Replay                  | Codex         | Mac desktop workflows can be recorded and converted into reusable skills; candidate for private skill capture after privacy review |
| Current-time reminders           | Codex         | Announced CLI surface for relative-date work; feature availability must be checked before workflow dependence |
| Office document production       | ZCode         | document-skills plugin covers creation and editing of PDF, DOCX, PPTX, and XLSX |
| Cross-session handoff            | ZCode         | ReadSessionContext resumes prior sessions by ID with focused or handoff queries |
| Runtime diagnostics skills       | ZCode         | zcode-guide skills diagnose MCP, hooks, commands, plugins, and skills configuration problems |

---

## 3. Public OACP Skills Coverage

Scope: skills shipped in [`kiloloop/oacp-skills`](https://github.com/kiloloop/oacp-skills). Private/local skills (debrief, sync, blitz, team-stats, worktree-workflow, send-message, etc.) are intentionally not tracked here — this table is meant as a cross-runtime parity signal for distributable skills only.

| Skill                  | Claude  | Codex    | ZCode        |
| ---------------------- | ------- | -------- | ------------ |
| `check-inbox`          | Working | Working  | Not packaged |
| `doctor`               | Working | Working  | Not packaged |
| `review-loop-reviewer` | Working | Working  | Not packaged |
| `review-loop-author`   | Working | Working  | Not packaged |
| `self-improve`         | Working | Working  | Not packaged |

ZCode loads skills from its plugin cache plus four conventional directories — user scope `~/.zcode/skills/` then `~/.agents/skills/`, workspace scope `<repo>/.zcode/skills/` then `<repo>/.agents/skills/` (`.zcode` scanned before `.agents`, first same-named skill wins, discovery at session start) — using the same SKILL.md + YAML frontmatter format. The `~/.agents/skills/` overlap means skills shared with Codex load in ZCode unchanged, so convention-based adoption is straightforward even without packaged variants (verified live 2026-08-26: a Codex-shared skill symlinked into `~/.agents/skills/` and a ZCode-only skill symlinked into `~/.zcode/skills/` both load).

---

## 4. Strengths Summary

| Dimension       | Claude                                                                 | Codex                                                                   | ZCode                                                                 |
| --------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Best at         | Orchestration, multi-agent teams, persistent memory, plan-then-execute | Terminal-native execution, GPT-5.6 agentic coding, fast iterative patching, native delegation and cross-task coordination, app-assisted review, browser/site tools, app-server automation, protocol discipline | Agentic coding with GLM-5.3, plugin-driven browser and desktop automation, office document production, scheduled automations |
| Ideal task type | Team coordination, complex multi-file refactors, long-running sessions | Shell-heavy workflows, long-horizon coding, targeted file edits, deterministic scripts, PR follow-up, artifact review, event-driven cloud follow-up, CLI planning passes, plugin/app-server automation prototypes | Full-stack coding with GUI verification, document generation pipelines (PDF/Office), cross-session handoff workflows, MCP integrations |
| Cost profile    | Flexible (haiku subagents for cheap tasks, opus for complex, Fable 5 at 2× Opus API rates for the hardest work) | Per-session ChatGPT cost not visible; Sol, Terra, and Luna provide quality/speed/cost tiers, with temporary Sol API promotional pricing | Token-based; details not surfaced in-session (unverified)              |

---

## 5. Known Limitations Summary

| Limitation                    | Claude                        | Codex                                                          | ZCode                                |
| ----------------------------- | ----------------------------- | ------------------------------------------------------------------ | ------------------------------------ |
| No subagents                  | —                             | —                                                                  | —                                    |
| No browser automation         | Configuration-dependent — requires the Claude in Chrome extension and a `/login` session; WebFetch alone is read-only | Configuration-dependent — Browser/Chrome plugins and an approved context are required | —                                    |
| No image generation           | Yes                           | —                                                                  | Yes (image search only, no generation) |
| No persistent writable memory | —                             | Partial (app memories are not a replacement for OACP durable memory) | Yes — no auto-loaded memory file; prior-session context only via explicit session handoff |
| Sandbox friction              | Yes (configurable)            | Session-dependent                                                  | Partial (permission-mode gating)     |
| No team primitive             | —                             | Partial — native delegation, task dashboard, queue, and task mentions exist, but not a shared task-list/broadcast primitive | Yes — concurrent subagents and SendMessage exist, but no shared team/task-list/broadcast primitive |
| Context limits                | Auto-compaction mitigates     | The API advertises 1.05M for GPT-5.6, but the checked Codex runtime uses a 272K active window; compaction behavior is runtime-dependent | Automatic context summarization mitigates; provider config declares 1M/128K for GLM-5.3 |
| No terminal stdin             | Yes                           | —                                                                  | Yes                                  |
| Cost not surfaced             | —                             | Yes                                                                 | Yes                                  |
| Permanent session delete      | —                             | `codex delete` is available; use archive/unarchive for routine cleanup and reserve delete for explicit destructive cleanup | —                                    |
| Serving model can change mid-session | Yes (Fable 5 only — cyber/bio-chem/distillation classifiers fall back to Opus 4.8, a target unchanged by the Opus 5 release; enabled by default and user-configurable in Claude interfaces — off-toggle in Settings > Capabilities, or Config > MODEL & OUTPUT in Claude Code, after which a flagged request pauses instead of switching; a session event is emitted on switch; <5% of sessions) | — | — |

---

## 6. Parity Gaps — Actionable Items

These are the highest-impact gaps where one runtime's limitation blocks effective collaboration:

| Gap                         | Affected Runtime(s)                | Impact                                                             | Proposed Fix                                                                   |
| --------------------------- | ---------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| No shared team/task-list primitive | Codex, ZCode                | Codex adds a task dashboard, queue, mentions, and parallel delegation but still lacks Claude-style shared task lists and broadcast; ZCode has concurrent subagents and agent-to-agent messaging but no shared team primitive | Agent cards — let runtimes discover and delegate to capable peers |
| Memory asymmetry            | Codex (partial), ZCode (handoff only) | Cross-session context degrades without MEMORY.md equivalent        | Standardize memory protocol; each runtime implements its own persistence layer |
| Sandbox blocks git/gh       | Claude                             | Every git/gh call needs sandbox configuration                      | Configure sandbox allowlists (`excludedCommands` globs such as `git *`, `gh *`) or disable sandbox for specific commands |
| Full browser automation gap | Claude without the Claude in Chrome extension; Codex without configured Browser, browser-extension, or site-tool access | Claude falls back to read-only WebFetch when the extension is absent or the session is API-key-authenticated; Codex browser control depends on an enabled surface and an approved context | Install the Claude in Chrome extension (`/chrome`), or delegate to a browser-capable runtime (configured Codex, or ZCode) after privacy review |
| Reviewer cost               | All (especially Claude)            | High cost for single PR review with polling pattern                | Stateless reviewer rounds — one round per invocation                           |
| Public skill coverage       | ZCode                              | `kiloloop/oacp-skills` ships `claude/` and `codex/` variants for all 5 public skills; no `zcode/` variants — ZCode users must rely on convention-based adoption | Add `zcode/` variants to each public skill, or document the convention-based pattern as a first-class install path |

---

## 7. Additional Dimensions

| Dimension                    | Claude                           | Codex                                      | ZCode                                           |
| ---------------------------- | -------------------------------- | ------------------------------------------ | ----------------------------------------------- |
| Max parallel tool calls      | ~10+                             | Yes (parallel independent calls)           | Yes (parallel independent calls)                |
| Side conversations           | Partial — `/fork` into a separate worktree and named background sessions (`claude agents`); no in-session side chat | Yes — named/pinned sessions and side-chat switching in CLI/TUI | No                                              |
| Hooks system                 | Yes (pre/post tool-call hooks plus lifecycle hooks — SessionStart/SessionEnd, PreCompact/PostCompact, Notification, PermissionDenied, worktree create/remove — as shell or HTTP handlers) | Yes (stable hooks and extension lifecycle hooks; plugin-bundled hooks are configuration-dependent) | Yes (tool-call hooks with event matchers; see zcode-guide diagnostics) |
| Automation scheduling        | Yes (`CronCreate`, `ScheduleWakeup`, `/loop`, `/schedule` skills) | Yes (desktop heartbeats, Goal mode, app-server/SDK automation, and web/mobile GitHub event-triggered tasks; event tasks have no local folder/worktree) | Yes — `CronCreate`/`CronUpdate`/`CronList`/`CronDelete` automations persist across restarts |
| Notebook editing             | Yes (NotebookEdit tool)          | No                                         | No                                              |
| PDF reading                  | Yes (max 20 pages/request)       | No native tool                             | Yes — document-skills `pdf` skill               |
| Image reading (multimodal)   | Yes                              | Yes (desktop app local image/view support) | Yes — Read renders images and video             |
| Artifact system              | Yes — Artifact tool publishes self-contained HTML pages as private-by-default, shareable, commentable claude.ai artifacts | Yes (sidebar preview for generated files) | No                                              |
| Video recording              | No (GIF capture of browser sessions via Claude in Chrome) | No                                         | No                                              |
| Image generation             | No                               | Yes (enabled by default in CLI)            | No (image search via plugin)                    |
| MCP diagnostics              | Partial (`/mcp` status and tool listing; `claude mcp list/get` health checks with disabled servers marked) | Yes (`/mcp verbose`, per-server environment targeting, read-only MCP parallelism, plugin JSON inventory) | Yes — `zcode-guide:diagnosing-mcp` skill covers connection and config problems |
| Multi-file editing primitive | Edit tool (one file at a time)   | `apply_patch` (one file)                   | Edit tool (one file at a time; `replace_all` within a file) |
| Workflow file format         | SKILL.md with YAML frontmatter   | SKILL.md with YAML frontmatter             | SKILL.md with YAML frontmatter                  |
| Policy visibility at runtime | Yes (`/permissions` shows allow/deny rules and, since v2.1.246, the auto-mode classifier rules; sandbox config is surfaced in tool context) | Yes (session policy, approval policy, sandbox, and named permission profiles) | Partial — user-selected permission mode gates tool calls |
| Long-running shell sessions  | Bash tool (no stdin; `run_in_background` with Monitor streaming) | Yes (PTY + stdin; multiple terminals in app) | Bash (no stdin; background tasks supported)     |
| App-server / SDK             | Yes (Claude Agent SDK for Python and TypeScript runs the same agent loop as a library — hooks, subagents, MCP, sessions; headless `claude -p` with JSON/stream-JSON output for other languages) | Yes (JSON-RPC app-server, Python SDK, thread/fork APIs, and authenticated transports; SDK preferred for CI/jobs, WebSocket and remote Code Mode experimental) | No                                              |
| Multi-folder projects        | No native primary-folder model (`--add-dir` extends file access) | Yes (in a trusted project, the primary folder owns Git and automatic instruction/config discovery; secondary folders are file-access-only) | No — single primary working directory           |
| Hosted site deployment       | No                               | Yes (Sites preview, app-only/cloud-hosted with separate secret management) | No                                              |
| Desktop workflow capture     | No                               | Yes (Record & Replay on Mac; privacy-sensitive and best treated as private-skill capture until reviewed) | No                                              |

---

## 8. Source Notes

- GPT-5.6 model availability, stable memories and multi-agent support, task coordination, trusted-project behavior, event-triggered tasks, browser/site tools, multi-folder behavior, and app-server changes come from OpenAI's Codex changelog: <https://developers.openai.com/codex/changelog>.
- Codex app/CLI capability changes are reviewed through the 2026-08-25 app entries and stable CLI `0.150.1`; workstation-specific app and alpha CLI versions are intentionally kept out of this public matrix.
- GPT-5.6 API model, context, regional processing, prompt caching, and pricing changes through 2026-08-21 come from the OpenAI API changelog and official model pages: <https://developers.openai.com/api/docs/changelog>.
- Sites, Amazon Bedrock, Remote, Record & Replay, app-server, plugin, and permissions details come from the official Codex docs under <https://developers.openai.com/codex/>.
- Claude Fable 5 release date and pricing come from Anthropic's 2026-06-09 announcement: <https://www.anthropic.com/news/claude-fable-5-mythos-5>; the current plan-inclusion posture (Max/Team Premium shared weekly pool, launch promo ended) reflects Anthropic's plan policy as of 2026-07-20. Claude Opus 5 model ID, pricing ($5/$25 per MTok), 1M context, and its release as the current Opus tier were re-verified 2026-08-03 against Anthropic's model documentation (models overview + migration guide at <https://platform.claude.com/docs/en/about-claude/models/overview.md>): Opus 5 is a drop-in at Opus 4.8's pricing, and Opus 4.8 stays available. Present-day interface fallback behavior comes from Anthropic's Help Center article "Why Claude switched models in your conversation with Fable 5" (2026-07-01, verified 2026-08-04): automatic switching to Opus 4.8 is enabled by default and user-configurable — Settings > Capabilities in the apps, Config > MODEL & OUTPUT in Claude Code ("Switch models when a message is flagged" toggle); with it off, a flagged request pauses the conversation. The Fable 5 / Mythos 5 system card §1.5 ("Novel safeguards") remains the source for the safeguard design, the observed fallback-rate/session-event facts, and the API posture: the Messages API blocks by default with a structured refusal category and offers opt-in server-side fallback — whose category-routed default likewise targets Opus 4.8 for cyber-class refusals, so the fallback target is unchanged post-Opus-5. The serving model (claude-fable-5) and Claude Code version (v2.1.246) in the header were verified in-session by the Claude runtime on 2026-08-26, with release notes reviewed through v2.1.247. Cross-session messaging capabilities (SendMessage across sessions and machines, ListAgents discovery, crossSessionInbound/dialogExpiry settings, `notify_when_idle`, delivery-failure reporting, Windows support), the subagent and team changes (fork subagents and background-by-default spawns in v2.1.232, env-gated task-list tools in v2.1.233, teammate listing in v2.1.239, model-404 fallback in v2.1.247), and the `/permissions` auto-mode tab (v2.1.246) come from the Claude Code release notes: <https://github.com/anthropics/claude-code/releases>. Browser automation details come from the Claude Code Chrome integration docs (<https://code.claude.com/docs/en/chrome>) and Agent SDK details from its overview (<https://code.claude.com/docs/en/agent-sdk/overview>); the Artifact tool and the lifecycle hook set were verified in-session.
- The ZCode column is a live in-session self-report captured 2026-08-26 by the ZCode runtime itself (GLM-5.3, `builtin:zai-coding-plan/GLM-5.3`) and re-verified in a second session the same day. Verification evidence: app version `3.9.2` (`CFBundleVersion` 3.9.2.6069) from `/Applications/ZCode.app/Contents/Info.plist`; GLM-5.3 1M context / 128K output from the local provider config (`~/.zcode/v2/config.json`); skill-discovery paths and precedence from the bundled zcode-guide configuration skill; plugin inventory from `~/.zcode/cli/plugins/cache/`. Release notes exist only at <https://zcode.z.ai/en/changelog> — there is no GitHub product-repo release feed or public RSS/JSON endpoint (verified 2026-08-26). Pricing is not surfaced in-session and remains unstated.

---

*Each runtime should update only its own column. Discrepancies should be resolved by the runtime owner.*
