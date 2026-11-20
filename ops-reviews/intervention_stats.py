#!/usr/bin/env python3
"""Intervention stats — how often a human stepped in, from a fleet's OACP autonomy audit records.

Companion to hil_stats.py (same loader, same record tree). Prints AGGREGATE numbers only: no per-run
identifiers, no task text, no model or runtime labels.

The unit is one evaluation record: one message evaluated once by one receiving agent's gate.

Three rates per UTC month, plus run length:
  asked    — the message paused at admission for the human
  changed  — the human's recorded answer was `modified` or `declined` (of recorded answers on paused admissions)
  stopped  — a checkpoint held the run for re-authorization at least once: at the record's last checkpoint,
             or earlier in the run (result.pause_intervals). Split by who cleared it; classify() gives the order.
  no_step  — not asked at admission, no recorded human answer, no stop the human (or nobody on record) cleared,
             and a completed state

Agent work per human step counts one human decision once: an ask at admission, each stop the human (or nobody
on record) cleared, and a recorded answer on a run with neither. A pass under a continuation grant counts in
either form the protocol has had (`review_continuation`, then `continuation_grant`).

Usage:
  python3 intervention_stats.py [--root <OACP_HOME>] [--until 2026-10-31] [--json out.json]
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
    sys.exit("PyYAML required")


def load_records(root: Path):
    for path in sorted(root.glob("projects/*/agents/*/audit/autonomy_decisions/**/*.yaml")):
        if path.name.endswith(".lock"):
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            yield {"_error": True}
            continue
        if not isinstance(data, dict):
            yield {"_error": True}
            continue
        parts = path.relative_to(root).parts  # projects/<project>/agents/<agent>/audit/…
        data["_receiver"] = f"{parts[1]}/{parts[3]}"
        yield data


def D(x):
    return x if isinstance(x, dict) else {}


def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


PAUSED = {"paused", "pause_for_human_approval"}
STOP_ACTIONS = {"resumed_after_reauthorization", "paused_for_reauthorization", "completed_after_human_approval"}


def classify(rec):
    res = D(rec.get("result"))
    ho = D(res.get("human_outcome"))
    tc = D(res.get("threshold_checkpoint"))
    re = D(tc.get("reauthorization"))
    asked = rec.get("decision") in PAUSED
    recorded = bool(ho.get("recorded"))
    answer = ho.get("decision") if recorded else None
    evaluated = bool(tc.get("evaluated"))
    breached = bool(tc.get("breached"))
    action = tc.get("action")
    # a stop at the record's last checkpoint
    stopped_last = breached and action in STOP_ACTIONS
    # earlier stops in the same run: the record keeps each cleared pause in result.pause_intervals
    hist = res.get("pause_intervals")
    hist = [D(x) for x in hist] if isinstance(hist, list) else []
    stopped = stopped_last or bool(hist)
    channel = re.get("channel")
    actor = re.get("actor")
    # an answer dated after the last checkpoint's pause is read as that stop's clearance
    answered_after_stop = bool(recorded and ho.get("decided_at_utc") and tc.get("paused_at_utc")
                               and str(ho["decided_at_utc"]) > str(tc["paused_at_utc"]))
    # who cleared the stop, in this order of precedence:
    #   1. the sender's reply with no human named            -> the sending agent
    #   2. a channel or an actor on the re-authorization     -> the human ("named")
    #   3. the record's answer is dated after the pause       -> the human ("later_answer")
    #   4. the action says it completed after human approval  -> the human ("legacy_action")
    #   5. otherwise                                          -> no record
    # a run stopped only earlier (history, no stop at the last checkpoint) is read from its intervals' channels
    stop_answer = None
    evidence = None
    if stopped_last:
        if channel == "sender_reply" and not actor:
            cleared_by, evidence = "sender", "sender_reply"
        elif channel or actor:
            cleared_by, stop_answer, evidence = "human", re.get("decision"), "named"
        elif answered_after_stop:
            cleared_by, stop_answer, evidence = "human", ho.get("decision"), "later_answer"
        elif action == "completed_after_human_approval":
            cleared_by, stop_answer, evidence = "human", "approved", "legacy_action"
        else:
            cleared_by, evidence = "unrecorded", "none"
    elif hist:
        chans = {h.get("channel") for h in hist}
        if chans == {"sender_reply"}:
            cleared_by, evidence = "sender", "sender_reply"
        elif chans - {"sender_reply", None}:
            cleared_by, evidence = "human", "named"
        else:
            cleared_by, evidence = "unrecorded", "none"
    else:
        cleared_by = None
    # human steps on stops: one per distinct recorded pause (history + last checkpoint) that the human cleared,
    # or that nobody on record cleared
    human_cleared = {str(h.get("paused_at_utc")) for h in hist if h.get("channel") not in ("sender_reply", None)}
    if stopped_last and cleared_by == "human":
        human_cleared.add(str(tc.get("paused_at_utc")))
    stamps = human_cleared | {str(h.get("paused_at_utc")) for h in hist if h.get("channel") is None}
    if stopped_last and cleared_by == "unrecorded":
        stamps.add(str(tc.get("paused_at_utc")))
    stop_steps = len(stamps)
    mins = res.get("actual_minutes")
    mins = mins if isinstance(mins, (int, float)) else None
    done = res.get("final_state") in ("done", "completed", "done_human_approved", "merged_and_cleaned_up")
    # a human step: asked at admission, a recorded human answer, or a stop the human (or nobody on record) cleared
    human_step = asked or recorded or cleared_by in ("human", "unrecorded")
    # the step count takes one human decision once. A run that was not asked has one answer slot, and when the
    # human cleared a stop on it that answer is the clearance: it is a step of its own only on a run with no
    # stop the human cleared. An ask at admission is always its own step, whatever was recorded later.
    answer_is_a_clearance = bool(recorded and not asked and human_cleared)
    steps = (1 if asked else 0) + stop_steps + (1 if (recorded and not asked and not human_cleared) else 0)
    # a pass under a continuation grant, in either form the protocol has had: the review-thread form
    # (`review_continuation`) and the general form (`continuation_grant`). One record carries at most one.
    grant_form = None
    if not asked:
        if D(rec.get("continuation_grant")).get("decision") == "accepted":
            grant_form = "general"
        elif D(rec.get("review_continuation")).get("decision") == "accepted":
            grant_form = "review_thread"
    return dict(asked=asked, recorded=recorded, answer=answer, evaluated=evaluated, breached=breached,
                action=action, stopped=stopped, stopped_last=stopped_last, cleared_by=cleared_by,
                evidence=evidence, stop_answer=stop_answer, mins=mins, done=done,
                stamped=bool(res.get("completed_at_utc")),
                at_final_checkpoint=bool(stopped_last and tc.get("terminal_time") is True),
                basis=(str(tc.get("breach_basis")) if stopped_last else None),
                answered_after_stop=bool(asked and stopped_last and answered_after_stop),
                cleared_on_earlier_approval=bool(stopped_last and evidence == "named" and re.get("decided_at_utc")
                                                 and tc.get("paused_at_utc")
                                                 and str(re["decided_at_utc"]) < str(tc["paused_at_utc"])),
                grant_pass=grant_form is not None, grant_form=grant_form, day=str(rec.get("created_at_utc"))[:10],
                answer_is_a_clearance=answer_is_a_clearance,
                human_step=human_step, steps=steps, cancelled=res.get("final_state") == "cancelled",
                cancelled_by=res.get("cancelled_by"), kind=rec.get("message_type"))


def q(vals, p):
    vs = sorted(vals)
    return vs[min(len(vs) - 1, int(p * len(vs)))] if vs else None


def block(rows):
    n = len(rows)
    asked = sum(r["asked"] for r in rows)
    rec = [r for r in rows if r["asked"] and r["recorded"]]
    ans = Counter(r["answer"] for r in rec)
    changed = ans.get("modified", 0) + ans.get("declined", 0)
    ev = [r for r in rows if r["evaluated"]]
    br = [r for r in ev if r["breached"]]
    st = [r for r in ev if r["stopped"]]
    st_last = [r for r in st if r["stopped_last"]]
    by = Counter(r["cleared_by"] for r in st)
    cont = sum(1 for r in br if r["action"] == "continued_with_grant")
    # no human step: not asked, no recorded human answer, no stop the human cleared, and a completed state
    no_step = [r for r in rows if not r["human_step"] and r["done"]]
    clocked = [r for r in rows if r["done"] and r["mins"] is not None]
    done_m = [r["mins"] for r in clocked]
    nostep_m = [r["mins"] for r in no_step if r["mins"] is not None]
    unstopped = [r for r in clocked if not r["stopped"]]
    unstopped_m = [r["mins"] for r in unstopped]
    steps_all = sum(r["steps"] for r in rows)
    steps_clocked = sum(r["steps"] for r in clocked)
    answered_stops = [r for r in st if r["cleared_by"] == "human" and r["stop_answer"] is not None]
    late = [r for r in rec if r["answered_after_stop"]]
    late_changed = sum(1 for r in late if r["answer"] in ("modified", "declined"))
    out = {
        "records": n,
        "asked": asked, "asked_pct": pct(asked, n),
        "passed_under_a_continuation_grant": sum(r["grant_pass"] for r in rows),
        "passed_under_a_grant_by_form": dict(Counter(r["grant_form"] for r in rows if r["grant_pass"])),
        "answers_recorded": len(rec), "approved": ans.get("approved", 0), "modified": ans.get("modified", 0),
        "declined": ans.get("declined", 0), "changed": changed, "changed_pct_of_answers": pct(changed, len(rec)),
        "answers_dated_after_a_stop": dict(Counter(str(r["answer"]) for r in late)),
        "changed_without_those": changed - late_changed, "answers_without_those": len(rec) - len(late),
        "named_clearances_decided_before_the_stop": sum(r["cleared_on_earlier_approval"] for r in rows),
        "checkpoints_evaluated": len(ev), "breached_at_last_checkpoint": len(br), "continued_under_grant": cont,
        "stopped": len(st), "stopped_pct_of_evaluated": pct(len(st), len(ev)),
        "stopped_at_last_checkpoint": len(st_last), "stopped_earlier_only": len(st) - len(st_last),
        "stopped_at_final_checkpoint_after_work": sum(r["at_final_checkpoint"] for r in st),
        "stop_basis_at_last_checkpoint": dict(Counter(r["basis"] for r in st_last)),
        "stop_cleared_by_human": by.get("human", 0), "stop_cleared_by_sender": by.get("sender", 0),
        "stop_clear_unrecorded": by.get("unrecorded", 0),
        "stop_clear_evidence": dict(Counter(str(r["evidence"]) for r in st)),
        "stop_answers": dict(Counter(str(r["stop_answer"]) for r in answered_stops)),
        "stop_answers_stored_on_the_record": sum(1 for r in answered_stops if r["evidence"] != "legacy_action"),
        "stop_answers_read_from_the_record_label": sum(1 for r in answered_stops if r["evidence"] == "legacy_action"),
        "stop_answers_not_recorded": by.get("human", 0) - len(answered_stops),
        "no_human_step": len(no_step), "no_human_step_pct": pct(len(no_step), n),
        "no_human_step_with_completion_stamp": sum(r["stamped"] for r in no_step),
        "unasked_with_recorded_human_answer": sum(1 for r in rows if r["recorded"] and not r["asked"]),
        "cancelled": sum(r["cancelled"] for r in rows),
        "work_minutes_total": round(sum(done_m)), "work_clock_n": len(done_m),
        "human_steps": steps_all, "human_steps_on_clocked_runs": steps_clocked,
        "unasked_answers_counted_once_as_the_stop_they_cleared": sum(r["answer_is_a_clearance"] for r in rows),
        "work_minutes_per_human_step": round(sum(done_m) / steps_clocked, 1) if steps_clocked else None,
        "run_minutes_no_recorded_stop": {"n": len(unstopped_m), "median": statistics.median(unstopped_m) if unstopped_m else None,
                                         "p90": q(unstopped_m, 0.9), "max": max(unstopped_m) if unstopped_m else None,
                                         "without_an_evaluated_checkpoint": sum(1 for r in unstopped if not r["evaluated"])},
        "run_minutes_no_human_step": {"n": len(nostep_m), "median": statistics.median(nostep_m) if nostep_m else None,
                                      "p90": q(nostep_m, 0.9), "max": max(nostep_m) if nostep_m else None},
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("OACP_HOME", os.path.expanduser("~/oacp")))
    ap.add_argument("--until", help="YYYY-MM-DD — keep records created on or before this UTC date")
    ap.add_argument("--json")
    a = ap.parse_args()
    recs = list(load_records(Path(a.root)))
    errors = sum(1 for r in recs if r.get("_error"))
    valid = [r for r in recs if not r.get("_error")]
    undated = [r for r in valid if not r.get("created_at_utc")]
    dated = [r for r in valid if r.get("created_at_utc")]
    set_aside = 0
    if a.until:
        keep = [r for r in dated if str(r["created_at_utc"])[:10] <= a.until]
        set_aside = len(dated) - len(keep)
        dated = keep
    by_month = defaultdict(list)
    for r in dated:
        by_month[str(r["created_at_utc"])[:7]].append(classify(r))
    allrows = [c for rows in by_month.values() for c in rows]
    # the counting unit: one evaluation record. A message id can recur, at two receivers or at one.
    receivers_by_id = defaultdict(list)
    for r in dated:
        receivers_by_id[str(r.get("message_id"))].append(r["_receiver"])
    repeated = {k: v for k, v in receivers_by_id.items() if len(v) > 1}
    out = {
        "window_until_utc": a.until, "records_read": len(recs), "unparsable": errors, "undated": len(undated),
        "set_aside_after_window": set_aside, "dated_in_window": len(allrows),
        "counting_unit": {
            "evaluation_records": len(allrows), "distinct_message_ids": len(receivers_by_id),
            "message_ids_with_more_than_one_record": len(repeated),
            "sent_to_two_receivers": sum(1 for v in repeated.values() if len(set(v)) > 1),
            "evaluated_more_than_once_by_one_receiver": sum(1 for v in repeated.values() if len(set(v)) == 1),
        },
        "all": block(allrows),
        "by_month": {m: block(rows) for m, rows in sorted(by_month.items())},
        "by_kind": {k: block([r for r in allrows if r["kind"] == k]) for k in ("task_request", "review_request", "brainstorm_request")},
        "by_month_by_kind": {
            m: {k: {"records": sum(1 for r in rows if r["kind"] == k),
                    "asked": sum(1 for r in rows if r["kind"] == k and r["asked"]),
                    "passed_under_a_continuation_grant": sum(1 for r in rows if r["kind"] == k and r["grant_pass"])}
                for k in ("task_request", "review_request", "brainstorm_request")}
            for m, rows in sorted(by_month.items())},
        "first_pass_under_a_grant_utc_date": {
            form: min((r["day"] for r in allrows if r["grant_form"] == form), default=None)
            for form in ("review_thread", "general")},
        "stop_actions": dict(Counter(r["action"] for r in allrows if r["breached"])),
        "cancelled_by": dict(Counter(str(r["cancelled_by"]) for r in allrows if r["cancelled"])),
    }
    print(f"records read {out['records_read']} · unparsable {errors} · undated {len(undated)} · set aside {set_aside} · in window {len(allrows)}")
    print("counting unit:", out["counting_unit"])
    hdr = "month    recs asked  ask%  ans  chg chg%  eval stop (last/earlier) (human/sender/unrec) stop%  nostep nostep%  min/step  run p50/p90/max (no recorded stop)"
    print(hdr)
    for m, b in list(out["by_month"].items()) + [("ALL", out["all"])]:
        rm = b["run_minutes_no_recorded_stop"]
        print(f"{m:8} {b['records']:4} {b['asked']:5} {b['asked_pct']!s:>5} {b['answers_recorded']:4} {b['changed']:4} {b['changed_pct_of_answers']!s:>5} "
              f"{b['checkpoints_evaluated']:5} {b['stopped']:4} ({b['stopped_at_last_checkpoint']}/{b['stopped_earlier_only']}) "
              f"({b['stop_cleared_by_human']}/{b['stop_cleared_by_sender']}/{b['stop_clear_unrecorded']}) "
              f"{b['stopped_pct_of_evaluated']!s:>5} {b['no_human_step']:7} {b['no_human_step_pct']!s:>6} {b['work_minutes_per_human_step']!s:>9}  {rm['median']}/{rm['p90']}/{rm['max']} n={rm['n']}")
    print("by kind:")
    for k, b in out["by_kind"].items():
        print(f"  {k:20} recs {b['records']:4} asked {b['asked_pct']}% changed {b['changed_pct_of_answers']}% of {b['answers_recorded']} stopped {b['stopped']} of {b['checkpoints_evaluated']} no-step {b['no_human_step']} ({b['no_human_step_pct']}%)")
    print("stop actions on breached last checkpoints:", out["stop_actions"])
    print("cancelled by:", out["cancelled_by"])
    a_ = out["all"]
    print("stops: evidence", a_["stop_clear_evidence"], "· at the final checkpoint", a_["stopped_at_final_checkpoint_after_work"], "· basis", a_["stop_basis_at_last_checkpoint"], "· answers", a_["stop_answers"])
    print("no-human-step runs:", a_["run_minutes_no_human_step"], "· work minutes", a_["work_minutes_total"], "over", a_["work_clock_n"], "clocks · steps", a_["human_steps"], "(on clocked runs", str(a_["human_steps_on_clocked_runs"]) + ")")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
