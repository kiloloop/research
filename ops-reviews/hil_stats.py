#!/usr/bin/env python3
"""HiL stats — aggregate human-in-the-loop statistics from a fleet's OACP autonomy audit records.

Companion to "Human in the loop, measured" (Kiloloop Research, ops-reviews). Reads every
`projects/*/agents/*/audit/autonomy_decisions/**/*.yaml` under $OACP_HOME (archive subdirs
included), and prints AGGREGATE numbers only — no per-run cost, no per-run identifiers, no
model attribution. Reproducible: run it, paste the block. `--json <path>` also writes the
aggregates as JSON; `--since YYYY-MM` filters by the record's created_at_utc month.

Usage:
  python3 hil_stats.py [--root <OACP_HOME>] [--since 2026-07] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required (the default-PATH python3 has it)")


def load_records(root: Path):
    for path in sorted(root.glob("projects/*/agents/*/audit/autonomy_decisions/**/*.yaml")):
        if path.name.endswith(".lock"):
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # malformed → count, skip
            yield {"_error": str(exc), "_path": str(path)}
            continue
        if not isinstance(data, dict):
            yield {"_error": "not a mapping", "_path": str(path)}
            continue
        data["_path"] = str(path)
        data["_project"] = path.parts[path.parts.index("projects") + 1]
        yield data


def as_dict(x):
    """Older records carry strings where newer ones carry mappings — treat anything non-mapping as empty."""
    return x if isinstance(x, dict) else {}


# reason_codes mixes pause REASONS with evidence codes (checks that passed: message_valid, schema_valid, …).
# Only the codes below count as reasons; everything else is reported as "non-reason codes excluded".
REASON_FAMILIES = {
    "threshold": ["expected_files_touched_exceeds_threshold", "estimated_minutes_exceeds_threshold", "risk_threshold_exceeded",
                  "exceeds_max_estimated_minutes", "threshold_checkpoint_breached"],
    "side_effect": ["merges_pr_pause", "hard_stop_external_side_effect", "hard_stop_external_side_effects", "external_side_effects_not_pr_artifact",
                    "external_side_effects_pause", "external_side_effect_requested", "external_side_effects_requested", "public_visibility_pause",
                    "dependency_changes_pause", "destructive_ops_pause", "hard_stop_git_push_or_deploy", "git_push_or_deploy_pause",
                    "auth_config_or_secrets_pause", "hard_stop_destructive_command", "external_side_effect_requires_human_authorization",
                    "creates_or_updates_pr_requested", "merge_requested", "github_pr_side_effect_scope", "new_pr_no_standing_authorization",
                    "different_pr_resets_same_pr_reauthorization", "comments_or_oacp_review_request_requested", "reply_side_effect_requested",
                    "external_network_or_private_repo_access_requested", "nested_codex_execution_requested", "online_research_requires_user_approval",
                    "runtime_permission_denied"],
    "review_continuation": ["review_continuation_confirmation_required", "review_continuation_scope_exceeded", "review_continuation_round_exceeded",
                            "continuation_grant_missing_thread", "continuation_grant_missing_approval"],
    "profile_missing_or_invalid": ["task_profile_missing", "risk_obvious_no_profile", "task_profile_unparsable", "declaration_error", "task_profile_absent"],
    "content_hard_stop": ["hard_stop_sensitive_scope", "hard_stop_content_sensitivity", "hard_stop_sensitive_commercial_strategy",
                          "hard_stop_pricing_or_commercial_content", "commercial_public_distribution_strategy_scope",
                          "memory_or_org_memory_scope_question", "non_trivial_research_requested"],
    "mode_always_pause": ["mode_always_pause", "receiver_mode_always_pause", "always_pause", "human_authorization_required", "human_approval_required",
                          "human_confirmation_required", "requires_human_confirmation", "manual_confirmation_required"],
}
REASON_FAMILY = {code: fam for fam, codes in REASON_FAMILIES.items() for code in codes}


def month_of(rec) -> str:
    ts = rec.get("created_at_utc") or ""
    return str(ts)[:7] if ts else "unknown"


def pct(n, d):
    return f"{(100.0 * n / d):.0f}%" if d else "n/a"


def summarize(records):
    out = {}
    valid = [r for r in records if "_error" not in r]
    errors = [r for r in records if "_error" in r]
    out["records"] = len(records)
    out["parse_errors"] = len(errors)
    out["by_receiver"] = dict(Counter(r.get("receiver", "?") for r in valid))
    out["by_message_type"] = dict(Counter(r.get("message_type", "?") for r in valid))
    out["by_month"] = dict(sorted(Counter(month_of(r) for r in valid).items()))

    # Admission decisions
    decisions = Counter(r.get("decision", "?") for r in valid)
    out["admission_decisions"] = dict(decisions)
    paused = [r for r in valid if r.get("decision") == "paused"]
    out["admission_pause_rate"] = pct(len(paused), len(valid))
    reason_mix = Counter()
    for r in paused:
        for code in r.get("reason_codes") or []:
            reason_mix[code] += 1
    out["pause_reason_mix"] = dict(reason_mix.most_common())
    fam, evidence = Counter(), 0
    for code, cnt in reason_mix.items():
        if code in REASON_FAMILY:
            fam[REASON_FAMILY[code]] += cnt
        else:
            evidence += cnt
    out["pause_reason_families"] = dict(fam.most_common())
    out["non_reason_codes_excluded"] = evidence

    # Human outcomes on admission pauses
    ho = []
    for r in paused:
        h = as_dict(as_dict(r.get("result")).get("human_outcome"))
        if h.get("recorded"):
            ho.append(h)
    out["human_outcomes_recorded"] = len(ho)
    out["human_outcome_decisions"] = dict(Counter(h.get("decision", "?") for h in ho))
    lat = [h["decision_latency_seconds"] for h in ho if isinstance(h.get("decision_latency_seconds"), (int, float))]
    if lat:
        lat_sorted = sorted(lat)
        q = lambda p: lat_sorted[min(len(lat_sorted) - 1, int(p * len(lat_sorted)))]  # noqa: E731
        out["decision_latency_seconds"] = {
            "n": len(lat),
            "median": statistics.median(lat),
            "p80": q(0.8), "p90": q(0.9), "p95": q(0.95),
            "max": max(lat),
            "share_le_2m": pct(sum(1 for x in lat if x <= 120), len(lat)),
            "share_le_5m": pct(sum(1 for x in lat if x <= 300), len(lat)),
            "share_le_10m": pct(sum(1 for x in lat if x <= 600), len(lat)),
            "over_1h": sum(1 for x in lat if x > 3600),
        }
    out["unresolved_pauses"] = len(paused) - len(ho)

    # Mid-run threshold checkpoints
    ckpt = Counter()
    for r in valid:
        tc = as_dict(as_dict(r.get("result")).get("threshold_checkpoint"))
        if tc.get("evaluated"):
            ckpt["evaluated"] += 1
            if tc.get("breached"):
                ckpt["breached"] += 1
                for f in tc.get("breached_fields") or []:
                    ckpt[f"breached:{f}"] += 1
    out["threshold_checkpoints"] = dict(ckpt)

    # Completion + envelope fidelity (done records with declared + actual)
    final = Counter((as_dict(r.get("result")).get("final_state") or "?") for r in valid)
    out["final_state"] = dict(final)
    ratios_min, ratios_files = [], []
    for r in valid:
        res = as_dict(r.get("result"))
        if res.get("final_state") != "done":
            continue
        prof = as_dict(r.get("task_profile")) or as_dict(r.get("scope_envelope"))
        dm, df = prof.get("estimated_minutes"), prof.get("expected_files_touched")
        am, af = res.get("actual_minutes"), res.get("actual_files_touched")
        if isinstance(dm, (int, float)) and dm and isinstance(am, (int, float)):
            ratios_min.append(am / dm)
        if isinstance(df, (int, float)) and df and isinstance(af, (int, float)):
            ratios_files.append(af / df)
    for name, vals in (("actual_over_declared_minutes", ratios_min), ("actual_over_declared_files", ratios_files)):
        if vals:
            vs = sorted(vals)
            out[name] = {"n": len(vs), "median": round(statistics.median(vs), 2),
                         "p20": round(vs[int(0.2 * (len(vs) - 1))], 2), "p80": round(vs[int(0.8 * (len(vs) - 1))], 2),
                         "share_within_declared": pct(sum(1 for v in vs if v <= 1.0), len(vs))}

    # Per-month human-outcome table
    by_month = defaultdict(lambda: {"records": 0, "paused": 0, "recorded": 0, "approved": 0, "modified": 0, "declined": 0, "latencies": []})
    for r in valid:
        m = by_month[month_of(r)]
        m["records"] += 1
        if r.get("decision") == "paused":
            m["paused"] += 1
            h = as_dict(as_dict(r.get("result")).get("human_outcome"))
            if h.get("recorded"):
                m["recorded"] += 1
                d = h.get("decision")
                if d in ("approved", "modified", "declined"):
                    m[d] += 1
                if isinstance(h.get("decision_latency_seconds"), (int, float)):
                    m["latencies"].append(h["decision_latency_seconds"])
    table = {}
    for k in sorted(by_month):
        m = by_month[k]
        table[k] = {kk: vv for kk, vv in m.items() if kk != "latencies"}
        table[k]["median_latency_s"] = statistics.median(m["latencies"]) if m["latencies"] else None
    out["by_month_human_outcomes"] = table
    return out


def render(out) -> str:
    lines = ["## HiL stats — aggregate (autonomy audit corpus)", ""]
    lines.append(f"- Records: {out['records']} (parse errors {out['parse_errors']}); receivers {out['by_receiver']}; message types {out['by_message_type']}")
    lines.append(f"- Admission decisions: {out['admission_decisions']} → pause rate {out['admission_pause_rate']}")
    lines.append(f"- Pause reason families (a pause can carry several codes): {out['pause_reason_families']}; non-reason (evidence) codes excluded: {out['non_reason_codes_excluded']}")
    lines.append(f"- Pause reason mix, raw: {out['pause_reason_mix']}")
    lines.append(f"- Human outcomes on pauses: recorded {out['human_outcomes_recorded']} → {out['human_outcome_decisions']}; not recorded {out['unresolved_pauses']} (outcome recording began 2026-07; earlier pauses carry no outcome field)")
    if "decision_latency_seconds" in out:
        d = out["decision_latency_seconds"]
        lines.append(f"- Decision latency (s): n={d['n']} median {d['median']:.0f} · p80 {d['p80']:.0f} · p90 {d['p90']:.0f} · p95 {d['p95']:.0f} · max {d['max']:.0f}; ≤2m {d['share_le_2m']} · ≤5m {d['share_le_5m']} · ≤10m {d['share_le_10m']} · >1h {d['over_1h']}")
    lines.append(f"- Mid-run threshold checkpoints: {out['threshold_checkpoints']}")
    lines.append(f"- Final states: {out['final_state']}")
    for k in ("actual_over_declared_minutes", "actual_over_declared_files"):
        if k in out:
            lines.append(f"- {k}: {out[k]}")
    lines.append("")
    lines.append("| Month | Records | Paused | Outcome recorded | Approved | Modified | Declined | Median latency (s) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for k, m in out["by_month_human_outcomes"].items():
        ml = m["median_latency_s"]
        lines.append(f"| {k} | {m['records']} | {m['paused']} | {m['recorded']} | {m['approved']} | {m['modified']} | {m['declined']} | {ml if ml is None else f'{ml:.0f}'} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("OACP_HOME", os.path.expanduser("~/oacp")))
    ap.add_argument("--since", help="YYYY-MM — keep records created in this month or later")
    ap.add_argument("--json", help="write the aggregate dict here")
    args = ap.parse_args()
    records = list(load_records(Path(args.root)))
    if args.since:
        records = [r for r in records if "_error" in r or month_of(r) >= args.since]
    out = summarize(records)
    print(render(out))
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
