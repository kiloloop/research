# Kiloloop Research

Curated research from Kiloloop — runtime comparisons, operational reviews, practical guides, and protocol patterns for multi-agent coordination.

## What's here

Research published from our internal pipeline. Each piece is reviewed and sanitized before landing here.

| Directory | Contents |
|-----------|----------|
| `runtime-comparison/` | Runtime capability comparisons and benchmarks |
| `ops-reviews/` | Operational reviews of our own agent fleet, with the scripts behind the numbers |

## Pieces

| Date | Piece | Where |
|------|-------|-------|
| 2026-09-10 | [Validated dispatches, defined: what the number on our homepage counts, and what it leaves out](ops-reviews/2026-09-10-validated-dispatches-defined.md) — the definition behind the dispatch count: four tests, the exclusions, the count over time with its correction to 557 dispatched legs, what the count is made of, and failure and human-intervention criteria from both records; aggregates, a redacted sample and [`CITATION.cff`](CITATION.cff) ship alongside, and the numbers come from [`estimate_stats.py`](ops-reviews/estimate_stats.py) and [`hil_stats.py`](ops-reviews/hil_stats.py) | `ops-reviews/` |
| 2026-09-07 | [Estimate accuracy, measured: seven months of dispatch estimates against their actuals](ops-reviews/2026-09-07-estimate-accuracy-measured.md) — actual-to-estimate ratios from 606 dispatch rows by period, month, estimate size and task class, the declared-envelope headroom on review-loop legs, verdicts and review status; the computation behind the numbers is [`estimate_stats.py`](ops-reviews/estimate_stats.py) | `ops-reviews/` |
| 2026-09-05 | [Human in the loop, measured: four months of autonomy-gate records](ops-reviews/2026-09-05-human-in-the-loop-measured.md) — pause rates, human outcomes and latency, checkpoint breaches and declared-vs-actual fidelity from 602 audit records; reproducible with [`hil_stats.py`](ops-reviews/hil_stats.py) | `ops-reviews/` |
| refreshed 2026-09 | [Runtime capability matrix](runtime-comparison/runtime_capability_matrix.md) — what each coding-agent runtime can and cannot do, self-reported and cross-verified by the agents | `runtime-comparison/` |
| refreshed 2026-09 | [Prompt caching patterns](runtime-comparison/prompt-caching-patterns.md) — Claude and Codex caching defaults, billing mechanics, and measurement | `runtime-comparison/` |

## License

Code: [Apache License 2.0](LICENSE)
Content: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
