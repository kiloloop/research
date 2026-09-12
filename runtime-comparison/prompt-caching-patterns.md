# Prompt Caching Patterns

How to reuse prompt context with Claude and Codex to reduce input cost and latency.

**Fact-checked 2026-09-12 UTC. All linked sources were retrieved on that date.**
API capabilities and product defaults are distinguished below; documentation does
not establish a workload's realized savings.

## Why It Matters

A cached prefix can reduce the work repeated requests spend processing context.
Savings depend on how much input is actually reused, cache writes and expiry,
plus output and tool costs. A discounted cache read is not the same as an equal
percentage reduction in the whole session's bill. See the provider mechanics
under [Cost Comparison](#cost-comparison).

## Claude

### Automatic Caching — API Opt-In, Claude Code Default

Automatic caching in the Claude Messages API requires request configuration.
Anthropic's instruction is to “add a single `cache_control` field at the top
level.” Use `{"type": "ephemeral"}` as its value; the API moves the cache
breakpoint as the conversation grows. This is distinct from Claude Code, which
handles caching automatically unless disabled.
([API caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching),
[Claude Code caching](https://code.claude.com/docs/en/prompt-caching))

The API caches an exact prefix in tools → system → messages order. The usual TTL
is five minutes; one hour is also available. Reuse refreshes expiry. Eligibility
and minimum prefix length depend on the model and platform: below-minimum Claude
API requests run uncached. Legacy Bedrock integrations for Opus 4.6 and earlier
require explicit block controls instead of top-level automatic caching.
([API caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching))

### Maximizing Cache Hits

1. Put stable instructions and reference material before changing requests.
2. Keep reusable content consistent; compare actual cost and quality before
   adding context merely to reach a caching threshold.
3. Measure the workload rather than assuming a particular hit rate.

These are optimization practices, not a savings guarantee.
([Cost optimization](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence))

### Explicit Cache Control (Custom API Integrations)

Place `cache_control` on supported blocks for explicit boundaries. Caching includes
the prefix through the marked block, subject to model and platform eligibility.
([API caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching))

### Headless Claude automation

Claude Code's defaults depend on how usage is paid: the main conversation uses
one hour for included subscription usage, but five minutes with API keys, cloud
providers, or usage credits. Other requests generally use five minutes. Inspect
the current TTL settings before planning reuse across separate jobs.
([Claude Code caching](https://code.claude.com/docs/en/prompt-caching))

Avoid changing the system prefix between related jobs. For print-mode automation,
`--exclude-dynamic-system-prompt-sections` can move machine-specific context into
the first user message; it is ignored with a replacement system prompt. This is
an option for sharing stable prefixes across machines.
([CLI reference](https://code.claude.com/docs/en/cli-reference))

### Multi-Agent Teams

Teammates have independent context windows, but that does not imply separate
server caches. Claude Code documents reuse between same-directory sessions with
matching prefixes; ordinary subagents and forks have different reuse behavior.
Measure reuse instead of inferring a hit rate from the number of agents.
([Agent teams](https://code.claude.com/docs/en/agent-teams),
[Claude Code caching](https://code.claude.com/docs/en/prompt-caching))

## Codex

### How It Works

OpenAI supports prompt caching, including cached-input pricing for Codex models.
Codex with an API key follows API pricing; ChatGPT plan allowances and credits
have their own accounting, which also reflects caching. Do not apply API dollar
rates directly to a subscription session.
([API prices](https://developers.openai.com/api/docs/pricing),
[Codex pricing](https://learn.chatgpt.com/docs/pricing))

For GPT-5.6 and later, the API offers implicit and explicit breakpoints, a
1,024-visible-token minimum, and `prompt_cache_options.ttl: "30m"` as the minimum
cache lifetime. Earlier models have different boundaries, minimums and retention
settings. A shared prefix needs an eligible matching cache boundary; reuse is
not guaranteed merely because two requests begin alike.
([Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching))

Cache lifetime and data retention are different controls. Check the selected
model, endpoint, region and organization policy; cached state may outlive the
minimum reuse window, and `store: false` is not a general cache-off switch.
([Data controls](https://developers.openai.com/api/docs/guides/your-data))

### Context Reuse Strategies

1. Keep stable instructions and tools first; append new messages and tool results.
   Rewriting history or compacting it can change the cached prefix.
2. For custom GPT-5.6+ API integrations, consider an explicit boundary after
   reusable content when later content changes. Use model-supported controls.
   ([Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching))
3. Treat conversation continuity separately from billing: `previous_response_id`
   carries state, but previous input in the chain remains billable.
   ([Conversation state](https://developers.openai.com/api/docs/guides/conversation-state))
4. In Codex tasks, name the relevant files and desired outcome in the prompt.
   Keep context useful and task-specific; shorter input is not itself proof of
   a cheaper completed task.

## Cost Comparison

These are billing mechanics, not a frozen dollar-price table. Multipliers apply
to the corresponding uncached input rate; output and tool charges are separate.

| Surface | Cache reads | Writes and retention |
|---|---|---|
| Claude API | Model-dependent: commonly 0.1×; Fable 5.1/Mythos 5.1 list 0.025×. | Five-minute writes: 1.25×; one-hour writes: 2×. [Pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| OpenAI API, GPT-5.6+ | 0.1×. | Writes: 1.25×; minimum lifetime: 30 minutes. [Pricing](https://developers.openai.com/api/docs/pricing), [caching](https://developers.openai.com/api/docs/guides/prompt-caching) |
| Earlier OpenAI API models | Use the model's cached-input rate. | No additional cache-write charge; model-specific retention. [Caching](https://developers.openai.com/api/docs/guides/prompt-caching) |

Compare the same model, API platform, context-length band and service tier.
Standard, Batch and faster processing can have different prices or availability;
use the current [Claude](https://platform.claude.com/docs/en/about-claude/pricing)
and [OpenAI](https://developers.openai.com/api/docs/pricing) schedules.

## Practical Guidelines

1. **Measure reads, writes and total cost.** Claude exposes
   `cache_read_input_tokens` and `cache_creation_input_tokens` separately from
   uncached `input_tokens`. Token hit share is reads / (reads + writes + uncached).
   ([API caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching))
   OpenAI Responses exposes `usage.input_tokens_details.cached_tokens` and, on
   GPT-5.6+, `cache_write_tokens`. Here, token hit share is `cached_tokens` /
   `input_tokens`. Aggregate counts across requests before dividing.
   ([Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching))
2. **Use a representative workload.** Compare repeated runs with the same model,
   task and service tier, including the first write and later misses.
3. **Investigate misses before redesigning prompts.** Check changing context,
   minimum length, cache boundaries and expiry. For custom integrations,
   [Claude diagnostics](https://platform.claude.com/docs/en/build-with-claude/cache-diagnostics)
   (Claude API only, beta) and
   [OpenAI diagnostics](https://developers.openai.com/api/docs/guides/prompt-caching/diagnostics)
   (Responses API, supported GPT-5.6+ models) compare request structure. Their
   results can be inconclusive; usage counters establish actual reuse.
4. **Optimize for task quality and total cost.** A cache-hit target alone does
   not measure whether the agent completed useful work efficiently.
