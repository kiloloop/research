#!/usr/bin/env python3
"""Estimate stats — aggregate estimate-vs-actual statistics from a coordinator's dispatch-estimate records.

Companion to "Estimate accuracy, measured" (Kiloloop Research, ops-reviews) and the twin of `hil_stats.py`. Reads the
coordinator's validation ledgers (a detailed validation log, a one-row-per-task summary table, the calibration log the
estimator reads) and the dispatch board's day files, parses every row that carries an estimate, an actual and a ratio,
de-duplicates across the sources, and prints AGGREGATE numbers only: no per-run cost, no message text, no model
attribution. The records themselves stay private (rows carry task subjects); the script and the aggregates are the
disclosure. It reads the coordinator's own file layouts (paths below), so it is the exact computation behind the piece
rather than a portable tool. Reproducible: run it, paste the block.

Usage:
  python3 estimate_stats.py [--coordinator <coordinator repo root>] [--vault <vault_dir>] [--json out.json] [--rows out.tsv]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

RATIO_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[x×]?")
MIN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(h|m|s)(?![a-z])")   # (?![a-z]), not \b: the "m" of a compound "2m47s" is followed by a digit
RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*(h|m)\b")
TIER_RE = re.compile(r"^\**\s*(XS|XL|S|M|L)\b")
UNIT_ORDER = {"h": 0, "m": 1, "s": 2}
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
MD_RE = re.compile(r"^(\d{2})-(\d{2})$")
EXCLUDE_RE = re.compile(r"carv|exclud|skip|not valid|duplicate|pooled|unmeasured|withdrawn|cancel", re.I)

# task-class keyword map — hand-maintained, first match wins; agent == iris is classed first as a coordinator self-block
CLASS_MAP = [
    ("release / promote", re.compile(r"release|\bcut\b|promote|\btag\b|\bv\d+\.\d+|publish|pypi", re.I)),
    ("review / audit / verification", re.compile(r"review|lgtm|sign-?off|\br[1-9]\b|verdict|audit|re-?verify|verify|health check|re-?check", re.I)),
    ("brainstorm / research / design", re.compile(r"brainstorm|research|explore|landscape|deep-?dive|proposal|synthesis|\bq:|question|design|spec\b|plan\b|estimate", re.I)),
    ("docs / site content", re.compile(r"readme|changelog|\bdocs?\b|runbook|guide|seo|page|copy|content|blog|post\b", re.I)),
    ("implementation", re.compile(r"#\d+|implement|build|fix|feat|\bpr\b|wire|port|refactor|ship|scaffold|migrat|schema|\bcli\b|hook|script|skill|adapter|engine|store|sync|setup|config", re.I)),
]

def norm_agent(cell: str) -> str:
    c = (cell or "").lower()
    if "iris" in c and "dispatch" not in c: return "iris"
    if "/" in c or "c/co" in c or "claude/codex" in c: return "multi"
    for k in ("claude", "codex", "gemini", "cline", "zcode"):
        if k in c: return k
    if c.strip().startswith("c") and len(c.strip()) <= 2: return "claude"
    if c.strip().startswith("g") and len(c.strip()) <= 2: return "gemini"
    return "unknown"

def parse_minutes(cell: str):
    if not cell: return None
    c = cell.replace("**", "").strip()
    m = RANGE_RE.search(c)
    if m:
        a, b, unit = float(m.group(1)), float(m.group(2)), m.group(3)
        v = (a + b) / 2
        return v * 60 if unit == "h" else v
    total, last = 0.0, None
    for m in MIN_RE.finditer(c):       # the FIRST figure; a second one is added only as the adjacent smaller unit of a compound ("1h 20m", "35m33s")
        v, unit = float(m.group(1)), m.group(2)
        if last and not (UNIT_ORDER[unit] == UNIT_ORDER[last[0]] + 1 and not c[last[1]:m.start()].strip()): break
        total += v * (60 if unit == "h" else 1 if unit == "m" else 1 / 60)
        last = (unit, m.end())
    return total if last else None

def parse_ratio(cell: str):
    if not cell: return None
    c = cell.replace("**", "").strip()
    if c in ("—", "-", "n/a", "N/A", "") or EXCLUDE_RE.search(c): return None
    m = RATIO_RE.search(c)
    return float(m.group(1)) if m else None

def ledger_actual(cell: str):
    """A ledger actual cell, work-first: an explicit work/exec figure wins over a wall figure in the same cell ("15m work / 21m send→done",
    "~44m (19m work)"); a cell with no such figure parses as its first minutes figure. Same rule as the board reader's parse_actual."""
    v, _ = parse_actual(cell or "")
    return v if v is not None else parse_minutes(cell)

def parse_tier(cell: str):
    m = TIER_RE.match((cell or "").strip())
    return m.group(1) if m else None

def norm_verdict(cell: str):
    if not cell: return None
    c = cell.replace("**", "").replace("*", "").strip()
    if "→" in c: c = c.split("→")[-1]
    c = re.sub(r"\(.*?\)", "", c).replace("⚠️", "").strip().upper()
    for k, v in (("MISCAL", "MISCALIBRATED"), ("ACC", "ACCURATE"), ("OVER", "OVER"), ("UNDER", "UNDER")):
        if c.startswith(k): return v
    return None

def norm_review(cell: str):
    if cell is None: return "unrecorded"
    c = cell.lower()
    if re.search(r"lgtm|cross|bilateral|reviewed|round|codex→|claude→|human", c): return "cross-reviewed"
    if re.search(r"self", c): return "self-only"
    if re.search(r"no[- ]review|none|unreviewed", c): return "no review"
    if re.search(r"n/a|—", c): return "n/a (no PR)"
    return "unrecorded"

def classify(task: str, agent: str) -> str:
    if agent == "iris": return "coordinator self-block"
    for name, rx in CLASS_MAP:
        if rx.search(task or ""): return name
    return "other"

def split_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]

def read_vault(path: Path):
    for line in path.read_text().splitlines():
        if not line.startswith("| 2026-"): continue
        c = split_row(line)
        if len(c) < 9: continue
        yield dict(date=c[0], task=c[1], agent=norm_agent(c[2]), tier=parse_tier(c[3]), est=parse_minutes(c[3]),
                   actual=ledger_actual(c[4]), ratio=parse_ratio(c[5]), review=None, verdict=c[8], source="vault summary")

def read_calibration(path: Path):
    for line in path.read_text().splitlines():
        if line.startswith("## Retired inputs"): break
        if not line.startswith("| 2026-"): continue
        c = split_row(line)
        if len(c) < 10: continue
        agent = norm_agent(c[7]) if norm_agent(c[7]) != "unknown" else norm_agent(c[9])
        yield dict(date=c[0], task=c[1], agent=agent, tier=parse_tier(c[2]), est=parse_minutes(c[3]),
                   actual=ledger_actual(c[4]), ratio=parse_ratio(c[6]), review=c[5] if c[5] not in ("—", "") else None,
                   verdict=c[9], source="calibration log")

def read_detailed(path: Path):
    year, header = None, None
    for line in path.read_text().splitlines():
        m = re.match(r"^## (\d{4})-\d{2}-\d{2}", line)
        if m: year = m.group(1); header = None; continue
        if line.startswith("| Date |"):
            header = [h.strip().lower() for h in split_row(line)]; continue
        if line.startswith("|---") or line.startswith("| ---") or line.startswith("|--"): continue
        if header and line.startswith("| ") and year:
            c = split_row(line)
            if len(c) != len(header): continue
            g = dict(zip(header, c))
            d = g.get("date", "")
            md = MD_RE.match(d)
            date = f"{year}-{md.group(1)}-{md.group(2)}" if md else (d if DATE_RE.match(d) else None)
            if not date: continue
            task = g.get("task") or g.get("dispatch") or ""
            agent = norm_agent(g.get("agent", "")) if "agent" in g else norm_agent(g.get("class", "") + " " + g.get("notes", ""))
            est_cell = g.get("est", "")
            yield dict(date=date, task=task, agent=agent, tier=parse_tier(est_cell) or parse_tier(g.get("class", "")), est=parse_minutes(est_cell),
                       actual=ledger_actual(g.get("actual", "")), ratio=parse_ratio(g.get("ratio", "")), review=g.get("review"),
                       verdict=g.get("verdict") or g.get("notes"), source="detailed log")

DAY_START = "2026-08-03"   # the two-level board convention: day files keep est/actual pairs verbatim from this date
STATUS_EXCL = re.compile(r"CANCELLED|WITHDRAWN|RETRACTED|SUPERSEDED|UNCONSUMED|NOT SENT|CALIBRATION EXCLUDE|carve|unmeasured|clean cancel|across \d+ sessions", re.I)
# a work/exec figure the board wrote next to the row's close: "42m27s exec", "11.65m measured", "(~38m incl. checkpoint", "Wall 36m", "in ~16m", "54m40s 0.46× declared"
WORK_RE = re.compile(r"(?:(?:measured|clocked|exec|wall|in|took|—|≤|≈|\()\s*~?(?P<m1>\d+(?:\.\d+)?)m(?:(?P<s1>\d+)s)?(?![\w/])(?![^|]{0,3}(?:est\b|declared|cap)))"
                     r"|(?:~?(?P<m2>\d+(?:\.\d+)?)m(?:(?P<s2>\d+)s)?[^\d|]{0,18}?(?:measured|exec\b|wall|incl\.|clocked|work\b|,\s*[\d.]+×|=\s*[\d.]+×|\s[\d.]+×\s*(?:est|of|vs|declared|expected|wall|in-band)))")
DONE_CLOCK = re.compile(r"(?:DONE|Done|LANDED|MERGED)\D{0,12}?(\d{1,2}):(\d{2})(?:\s*(?:PT)?\s*(\d{1,2})/(\d{1,2}))?")
DONE_RE = re.compile(r"DONE|✅|Done\b|LANDED|MERGED|PUBLISHED|COMPLETE")
DECLARED_RE = re.compile(r"declared\s*~?(\d+(?:\.\d+)?)\s*m", re.I)
WORK_FIRST = re.compile(r"~?(\d+(?:\.\d+)?)m(?:(\d+)s)?\s*(?:work\b|active\b|working\b)|(?:measured|working)\s*~?(\d+(?:\.\d+)?)m(?:(\d+)s)?\s*(?:working|work\b)")
ACTUAL_PATTERNS = [   # first match wins — the actual work / exec minutes as the board wrote them
    re.compile(r"DONE[^()|]{0,60}\((?:~|≈)?(\d+(?:\.\d+)?)\s*m\)"),                       # DONE 23:57 (~30m)
    re.compile(r"(?:Exec|exec|work clock|Work|work)[^|.;]{0,40}?(\d+)m(\d+)s"),                 # Exec 35m33s vs …
    re.compile(r"(\d+)m(\d+)s\s*(?:=|≈|vs|of|wall|send)"),                                     # 108m40s = 0.72×
    re.compile(r"(?:Actual|actual|Measured|measured|Exec|exec)\s*(?:wall\s*)?[:=]?\s*~?(\d+(?:\.\d+)?)\s*m\b"),
    re.compile(r"(\d+(?:\.\d+)?)\s*m\s*(?:wall\s*)?(?:=|≈)\s*[\d.]+\s*×"),                    # 14m = 0.47×
    re.compile(r"\((?:~|≈)(\d+(?:\.\d+)?)\s*m(?: wall| exec| work)?\)"),                       # (~17m) anywhere
    re.compile(r"~(\d+(?:\.\d+)?)\s*m\s*(?:wall|exec|work|actual)"),                          # ~17m wall
]
RATIO_STATED = re.compile(r"(?:=|≈)\s*(\d+\.\d+)\s*×\s*(?:of|vs)?\s*(?:the\s*)?(?:expected|wall|exec|est)", re.I)

def parse_actual(status: str):
    """Stated work/exec minutes: the earliest match of the specific patterns or the general one; None if the board wrote no figure."""
    m = WORK_FIRST.search(status)      # an explicit work/active figure beats an earlier wall figure in the same cell
    if m:
        mm = m.group(1) or m.group(3); ss = m.group(2) or m.group(4)
        return float(mm) + (float(ss) / 60 if ss else 0), "work-first"
    best = None
    for i, rx in enumerate(ACTUAL_PATTERNS):
        m = rx.search(status)
        if m and (best is None or m.start() < best[0]):
            v = float(m.group(1)) + (float(m.group(2)) / 60 if len(m.groups()) == 2 else 0)
            best = (m.start(), v, i)
    m = WORK_RE.search(status)
    if m and (best is None or m.start() < best[0]):
        mm = m.group("m1") or m.group("m2"); ss = m.group("s1") or m.group("s2")
        best = (m.start(), float(mm) + (float(ss) / 60 if ss else 0), "general")
    return (best[1], best[2]) if best else (None, None)

def send_to_done(sent: str, status: str):
    """Wall minutes from the row's Sent stamp to the first DONE/LANDED/MERGED clock in the status (next-day markers honoured)."""
    m = DONE_CLOCK.search(status)
    if not m: return None
    try:
        sh, sm = int(sent[11:13]), int(sent[14:16]); dh, dm = int(m.group(1)), int(m.group(2))
    except ValueError: return None
    wall = (dh * 60 + dm) - (sh * 60 + sm)
    if m.group(3): wall += 24 * 60          # "DONE 00:55 8/7" = next day
    elif wall < 0: wall += 24 * 60          # crossed midnight without a marker
    return float(wall) if 0 < wall <= 24 * 60 else None

def read_dayfiles(dirs):
    files = sorted({f for d in dirs if d.exists() for f in d.glob("2026-*.md")}, key=lambda f: f.name)
    for f in files:
        date = f.stem
        if date < DAY_START: continue
        for line in f.read_text().splitlines():
            if not line.startswith("| 2026-"): continue
            c = split_row(line)
            if len(c) < 8: continue
            agent = norm_agent(c[2]); task = c[3]; est_cell = c[5]; status = "|".join(c[7:])
            row = dict(date=date, task=task, agent=agent, tier=parse_tier(est_cell), est=None, actual=None, ratio=None, review=None,
                       verdict=None, source="board day files", declared=None, msg=c[6])
            head = status[:160]
            if STATUS_EXCL.search(head): row["skip"] = "cancelled/withdrawn/carved"; yield row; continue
            if not DONE_RE.search(status): row["skip"] = "not closed"; yield row; continue
            exp_cell = est_cell.split("(")[0]
            expected = parse_minutes(exp_cell)
            m = DECLARED_RE.search(est_cell); declared = float(m.group(1)) if m else None
            actual, pat = parse_actual(status); basis = "stated work minutes"
            if actual is None:
                m2 = RATIO_STATED.search(status)
                if m2 and expected: actual, pat, basis = float(m2.group(1)) * expected, "stated-ratio", "stated ratio"
            if actual is None:
                wall = send_to_done(c[0], status)
                if wall: actual, pat, basis = wall, "send→done", "send-to-done wall"
            if expected is None: row["skip"] = "no expected minutes in the estimate cell"; yield row; continue
            if actual is None: row["skip"] = "no actual minutes and no DONE clock in the status cell"; yield row; continue
            row.update(est=expected, actual=actual, ratio=round(actual / expected, 2), declared=declared, pattern=pat, basis=basis,
                       review="cross" if re.search(r"LGTM|APPROVE|review", status) else None)
            yield row

def q(xs, p):
    if not xs: return None
    s = sorted(xs); k = (len(s) - 1) * p; f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)

def summarize(rows):
    r = [x["ratio"] for x in rows]
    if not r: return dict(n=0)
    return dict(n=len(r), mean=round(statistics.fmean(r), 2), median=round(statistics.median(r), 2), p20=round(q(r, .2), 2), p80=round(q(r, .8), 2),
                over_est=round(100 * sum(1 for v in r if v < 0.5) / len(r)), within=round(100 * sum(1 for v in r if 0.5 <= v <= 2.0) / len(r)),
                under_est=round(100 * sum(1 for v in r if v > 2.0) / len(r)), exact_1=round(100 * sum(1 for v in r if v == 1.0) / len(r)),
                exact_03=round(100 * sum(1 for v in r if v == 0.3) / len(r)))

def fmt(s, label):
    if s.get("n", 0) == 0: return f"| {label} | 0 | — | — | — | — | — | — | — |"
    return f"| {label} | {s['n']} | {s['mean']:.2f} | {s['median']:.2f} | {s['p20']:.2f} | {s['p80']:.2f} | {s['over_est']}% | {s['within']}% | {s['under_est']}% |"

HEAD = "| Slice | n | mean | median | p20 | p80 | <0.5× (over-estimated) | 0.5–2.0× | >2.0× (under-estimated) |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coordinator", dest="coordinator", default=str(Path.home() / "iris"), help="coordinator repo root: the ledgers, the calibration log and the board day files live under it")
    ap.add_argument("--iris", dest="coordinator", help=argparse.SUPPRESS)   # the flag's earlier spelling; still accepted
    ap.add_argument("--vault", default=None, help="vault dir (default: vault_dir from <coordinator>/config.yaml)")
    ap.add_argument("--json"); ap.add_argument("--rows", help="write the de-duplicated rows as TSV (private — do not publish)")
    ap.add_argument("--private", action="store_true", help="also print the per-agent-label view (coordinator's own use)")
    a = ap.parse_args()
    iris = Path(a.coordinator).expanduser()
    vault = a.vault
    if not vault:
        for line in (iris / "config.yaml").read_text().splitlines():
            if line.strip().startswith("vault_dir:"): vault = line.split(":", 1)[1].strip().strip('"').strip("'")
    vault = Path(vault).expanduser()
    sources = [("detailed log", read_detailed(iris / "analysis/estimate_validations.md")),
               ("vault summary", read_vault(vault / "research/agent-estimate/estimate_validations.md")),
               ("calibration log", read_calibration(iris / ".claude/skills/estimate/calibration_log.md")),
               ("board day files", read_dayfiles([iris / "memory/dispatches", iris / "memory/archive/dispatches"]))]
    raw = Counter(); no_ratio = Counter(); excluded = Counter(); seen = {}; rows = []; skips = Counter(); day_after = Counter(); wall_rows = []
    for name, it in sources:
        for x in it:
            raw[name] += 1
            if name != "board day files" and x["date"] >= DAY_START: day_after[name] += 1; continue   # the board is the source from DAY_START
            if x.get("skip"): skips[x["skip"]] += 1; continue
            if x.get("basis") == "send-to-done wall": wall_rows.append(x); continue   # a different clock (queue + human waits) — reported apart, never mixed in
            if x["ratio"] is None: no_ratio[name] += 1; continue
            if EXCLUDE_RE.search(x.get("verdict") or "") or EXCLUDE_RE.search(x.get("task") or ""): excluded[name] += 1; continue
            key = (x["date"], x["agent"], round(x["est"] or -1), round(x["ratio"], 2))
            if key in seen: continue
            seen[key] = name
            x["verdict_n"] = norm_verdict(x["verdict"]); x["review_n"] = norm_review(x["review"]); x["class"] = classify(x["task"], x["agent"]); x["month"] = x["date"][:7]
            rows.append(x)
    rows.sort(key=lambda x: x["date"])
    out = {"corpus": {"raw_rows": dict(raw), "no_ratio": dict(no_ratio), "excluded": dict(excluded), "deduped": len(rows), "board_skips": dict(skips),
                      "ledger_rows_after_day_start": dict(day_after), "kept_from": dict(Counter(seen.values())), "first": rows[0]["date"], "last": rows[-1]["date"]}}
    print("## Corpus\n")
    print(f"| Source | rows read | no ratio (carved / unscored) | excluded by note | ceded to the board (dated ≥ {DAY_START}) | kept after de-dup |\n|---|---:|---:|---:|---:|---:|")
    for name, _ in sources:
        print(f"| {name} | {raw[name]} | {no_ratio[name]} | {excluded[name]} | {day_after.get(name, 0)} | {out['corpus']['kept_from'].get(name, 0)} |")
    print(f"\nBoard rows not scored: " + " · ".join(f"{k} {v}" for k, v in skips.most_common()) + ".")
    wr = [x["ratio"] for x in wall_rows]
    out["corpus"]["wall_only_rows"] = dict(n=len(wr), mean=round(statistics.fmean(wr), 2) if wr else None, median=round(statistics.median(wr), 2) if wr else None)
    print(f"Closed board rows whose status carries a close clock but no work figure: {len(wr)} — their send-to-done wall runs "
          f"{out['corpus']['wall_only_rows']['median']}× the estimate at the median (mean {out['corpus']['wall_only_rows']['mean']}×) because that clock includes queue and human waits; "
          f"they are reported here and kept OUT of every table below.")
    print(f"\nDe-duplicated rows: **{len(rows)}** ({rows[0]['date']} → {rows[-1]['date']}). Ledger rows carry the corpus to {DAY_START}; from that date the board's day files "
          f"are the source (expected wall = the first minutes in the estimate cell, midpoint of a range; actual = the first work-minutes figure the status cell states — rows with no such figure are excluded, see above). "
          f"De-dup key = date · agent · estimate minutes · ratio (2 dp).\n")
    all_s = summarize(rows); out["all"] = all_s
    print("## Headline\n"); print(HEAD); print(fmt(all_s, "all rows"))
    print(f"\nRatios sitting exactly on 1.00×: {all_s['exact_1']}% · exactly on 0.30×: {all_s['exact_03']}%.\n")
    # eras: back-fill (before the 2026-05-14 refresh) vs scored (weekly validation from day files)
    eras = [("Feb–Mar (launch weeks)", lambda x: x["date"] < "2026-04-01"), ("Apr–Jun", lambda x: "2026-04-01" <= x["date"] < "2026-07-01"), ("Jul–Sep", lambda x: x["date"] >= "2026-07-01")]
    print("## By period\n"); print(HEAD.replace(" |\n|---|", " | exact 1.00× | exact 0.30× |\n|---|").replace("|---:|\n", "|---:|---:|---:|\n") if False else HEAD.split("\n")[0] + " exact 1.00× | exact 0.30× |\n" + HEAD.split("\n")[1] + "---:|---:|")
    out["period"] = {}
    for label, f in eras:
        s = summarize([x for x in rows if f(x)]); out["period"][label] = s
        print(fmt(s, label) + f" {s.get('exact_1', 0)}% | {s.get('exact_03', 0)}% |")
    print("\n## By month\n"); print(HEAD); out["month"] = {}
    for mth in sorted({x["month"] for x in rows}):
        s = summarize([x for x in rows if x["month"] == mth]); out["month"][mth] = s; print(fmt(s, mth))
    print("\n## By estimate size (minutes in the estimate cell)\n"); print(HEAD); out["size"] = {}
    bands = [("≤ 15 m", 0, 15), ("16–30 m", 15, 30), ("31–60 m", 30, 60), ("61–120 m", 60, 120), ("> 120 m", 120, 10**6)]
    for label, lo, hi in bands:
        s = summarize([x for x in rows if x["est"] is not None and lo < x["est"] <= hi]); out["size"][label] = s; print(fmt(s, label))
    s = summarize([x for x in rows if x["est"] is None]); out["size"]["no minutes"] = s; print(fmt(s, "estimate carries no minutes"))
    tiered = [x for x in rows if x["tier"]]
    print(f"\n(A tier letter XS/S/M/L/XL is recorded on {len(tiered)} rows; the size bands above use the minutes, which every row carries.)")
    print("\n## By task class (keyword map in the script; hand-maintained)\n"); print(HEAD); out["class"] = {}
    for cls, _ in [(c, None) for c, _ in CLASS_MAP] + [("coordinator self-block", None), ("other", None)]:
        s = summarize([x for x in rows if x["class"] == cls]); out["class"][cls] = s; print(fmt(s, cls))
    print("\n## By receiving side (coordinator self-blocks vs dispatched agents)\n"); print(HEAD); out["side"] = {}
    for label, f in (("dispatched to an agent", lambda x: x["agent"] != "iris"), ("coordinator self-block", lambda x: x["agent"] == "iris")):
        s = summarize([x for x in rows if f(x)]); out["side"][label] = s; print(fmt(s, label))
    out["agent"] = {ag: summarize([x for x in rows if x["agent"] == ag]) for ag in Counter(x["agent"] for x in rows)}
    if a.private:
        print("\n## By agent label (--private: coordinator's view, not for publication)\n"); print(HEAD)
        for ag, s in sorted(out["agent"].items(), key=lambda kv: -kv[1].get("n", 0)): print(fmt(s, ag))
    vr = [x for x in rows if x["verdict_n"]]; vc = Counter(x["verdict_n"] for x in vr); out["verdict"] = dict(vc); out["verdict_n"] = len(vr)
    print(f"\n## Recorded verdicts (n={len(vr)} rows carry one)\n\n| Verdict | n | share |\n|---|---:|---:|")
    for v in ("ACCURATE", "OVER", "UNDER", "MISCALIBRATED"): print(f"| {v} | {vc.get(v, 0)} | {round(100 * vc.get(v, 0) / max(1, len(vr)))}% |")
    print("\nBy period:\n\n| Period | n with verdict | ACCURATE | OVER | UNDER | MISCALIBRATED |\n|---|---:|---:|---:|---:|---:|"); out["verdict_period"] = {}
    for label, f in eras:
        e = [x for x in vr if f(x)]; c = Counter(x["verdict_n"] for x in e); out["verdict_period"][label] = dict(c)
        print(f"| {label} | {len(e)} | " + " | ".join(f"{round(100 * c.get(v, 0) / max(1, len(e)))}%" for v in ("ACCURATE", "OVER", "UNDER", "MISCALIBRATED")) + " |")
    print("\n## Review status (where the row records it)\n"); print(HEAD); out["review"] = {}
    for rv, _ in Counter(x["review_n"] for x in rows).most_common():
        s = summarize([x for x in rows if x["review_n"] == rv]); out["review"][rv] = s; print(fmt(s, rv))
    decl = [x for x in rows if x.get("declared")]
    if decl:
        rv = [x["ratio"] for x in decl]; rd = [x["actual"] / x["declared"] for x in decl]
        out["declared"] = dict(n=len(decl), vs_expected_mean=round(statistics.fmean(rv), 2), vs_expected_median=round(statistics.median(rv), 2),
                               vs_declared_mean=round(statistics.fmean(rd), 2), vs_declared_median=round(statistics.median(rd), 2),
                               over_declared=round(100 * sum(1 for v in rd if v > 1.0) / len(rd)), over_expected=round(100 * sum(1 for v in rv if v > 1.0) / len(rv)))
        o = out["declared"]
        print(f"\n## Declared envelope vs expected wall (board rows that carry both, n={o['n']})\n\n| Basis | mean | median | share over 1.0× |\n|---|---:|---:|---:|\n"
              f"| actual ÷ expected wall | {o['vs_expected_mean']:.2f} | {o['vs_expected_median']:.2f} | {o['over_expected']}% |\n| actual ÷ declared envelope | {o['vs_declared_mean']:.2f} | {o['vs_declared_median']:.2f} | {o['over_declared']}% |")
        by_m = defaultdict(list)
        for x in decl: by_m[x["month"]].append(x)
        print("\n| Month | n | vs expected (median) | vs declared (median) | over declared |\n|---|---:|---:|---:|---:|")
        for mth in sorted(by_m):
            xs = by_m[mth]; rd2 = [x["actual"] / x["declared"] for x in xs]
            print(f"| {mth} | {len(xs)} | {statistics.median(x['ratio'] for x in xs):.2f} | {statistics.median(rd2):.2f} | {round(100 * sum(1 for v in rd2 if v > 1) / len(rd2))}% |")
    # size of the dispatched work: estimate and actual minutes where both parse
    both = [x for x in rows if x["est"] and x["actual"]]
    out["minutes"] = dict(n=len(both), est_median=round(statistics.median(x["est"] for x in both)), actual_median=round(statistics.median(x["actual"] for x in both)),
                          est_sum_h=round(sum(x["est"] for x in both) / 60), actual_sum_h=round(sum(x["actual"] for x in both) / 60))
    m = out["minutes"]
    print(f"\n## Minutes (rows where both the estimate and the actual parse, n={m['n']})\n\n| | median | total |\n|---|---:|---:|\n| estimated | {m['est_median']} m | {m['est_sum_h']} h |\n| actual | {m['actual_median']} m | {m['actual_sum_h']} h |")
    if a.json: Path(a.json).write_text(json.dumps(out, indent=2, default=str))
    if a.rows:
        with open(a.rows, "w") as fh:
            fh.write("date\tsource\tagent\tclass\ttier\test\tactual\tratio\tverdict\treview\tdeclared\tpattern\tbasis\ttask\n")
            for x in rows: fh.write("\t".join(str(x.get(k, "")) for k in ("date", "source", "agent", "class", "tier", "est", "actual", "ratio", "verdict_n", "review_n", "declared", "pattern", "basis", "task")) + "\n")
    if a.rows:
        with open(a.rows.replace(".tsv", "_skipped.tsv"), "w") as fh:
            for name, it in [("board day files", read_dayfiles([iris / "memory/dispatches", iris / "memory/archive/dispatches"]))]:
                for x in it:
                    if x.get("skip"): fh.write(f"{x['date']}\t{x['skip']}\t{x['agent']}\t{x['task'][:120]}\n")

if __name__ == "__main__":
    main()
