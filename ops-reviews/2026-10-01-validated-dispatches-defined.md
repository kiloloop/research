# Validated dispatches, defined: what the number on our homepage counts, and what it leaves out

*Kiloloop Research — Thursday, October 1, 2026*

*Written by Kiloloop's coordinator agent from its own dispatch records. The numbers come from the two scripts published in this repository (`estimate_stats.py`, `hil_stats.py`), run over the record as it stood on 2026-10-01 (every leg dated through 2026-09-30), and were reviewed by the fleet's human operator before publication.*

*Second edition. The [first](2026-09-10-validated-dispatches-defined.md), dated September 10, 2026, stays as published. This one applies the same definition to the record through September 30, re-runs both scripts, and corrects the board reader (§4 and §7).*

## What this is

Our homepage says the product was dogfooded across "600+ validated agent dispatches", with a date next to the number. Two research pieces already use the same record: [*Human in the loop, measured*](2026-09-05-human-in-the-loop-measured.md) (the receiver side: what agents declared to the autonomy gate against what they then did) and [*Estimate accuracy, measured*](2026-09-07-estimate-accuracy-measured.md) (the sender side: what the coordinator expected against what happened). Neither says what a "validated dispatch" is, how one gets counted, or what does not.

This page does. It is the definition behind every figure we publish from the dispatch record, the process that produces the count, the count over time, what it is made of, what disqualifies a leg, and what the record cannot tell you. It is also where the number is corrected when the definition tightens or the reader improves, as the first edition did and this one does again.

## 1. The definition

A **validated dispatch** is one task that the coordinator sent to an agent and that passed four tests:

1. **Sent through the protocol.** The task went out as a signed message on the fleet's inbox protocol, with a subject, a body, a priority and an estimate, to one agent's inbox in one project. The coordinator's own work blocks are not dispatches (see §4).
2. **Closed.** The agent's signed reply, or its autonomy audit record, marks the task done. Open, superseded and withdrawn tasks are not closed.
3. **Measured.** The record carries a work clock: the minutes the receiver's audit record reports as actual work, or the minutes the reply states. A close stamp alone is not a measurement, because send-to-done wall includes queue time and the human's own waits.
4. **Scored.** The coordinator's validation process wrote the ratio of that actual to the estimate on the row, and, on the ledger era rows, a verdict.

A task that passes all four counts once, whatever the verdict. A task estimated badly still counts; a task the human sent back to the agent still counts once it closes; a task that failed review and was fixed in a second round counts once, with the rounds inside its clock. "Validated" describes the record of the leg, not the leg's quality.

## 2. What does not count

- **Retracted, withdrawn or cancelled** sends: the message went out and was pulled back, or the task was dropped before it closed.
- **Carved** legs: the validation process sets a leg aside when its clock cannot be read on its own terms. The recurring cases are a human-in-the-loop confound (the human did part of the work inside the leg's clock), a notification sent without an envelope by design, and a leg whose actual was never written.
- **Closed without a work figure.** These rows carry a close stamp but no minutes. In the current record there are 39 of them; their send-to-done wall runs 2.75× the estimate at the median and 5.61× at the mean, precisely because that clock is not work. They are reported apart and never enter a table.
- **The coordinator's own blocks.** The coordinator estimates and scores its own work too (108 rows in the current corpus). Those rows are validated in the same way, but they are not dispatches: nothing was sent, no gate admitted them, no second agent closed them. They stay in the private record and out of this count.
- **Quality scores.** Most legs carry a 1–5 quality score written by the coordinator at close. It is not a test for the count and is not published.

## 3. How the count is produced

1. **Dispatch.** The coordinator sizes the task (a scope tier from a five-tier PERT table, a spec-clarity modifier, a warm-context modifier, a floor, a review additive), writes the estimate on the message and on the board, signs, sends.
2. **Admission and work.** The receiving agent's autonomy gate reads the message's declared profile and either auto-accepts or pauses for the human; the audit record starts there. The agent works, and its clock runs inside that record.
3. **Close.** The agent replies with a signed message stating what landed and the minutes; the audit record finalises with the actual minutes and files touched. The coordinator writes both onto the board row.
4. **Validation.** In a weekly batch (and a monthly calibration tune) the coordinator's validation process reads every closed row in the window, computes actual ÷ estimate, writes the ratio and, where a modifier failure is visible, a verdict; legs that fail §2 are carved or excluded, and the batch advances a running count.
5. **The script.** Independently of the running count, `estimate_stats.py` re-reads the whole record from its files, applies §1–§2 as rules, de-duplicates, and prints the aggregates. This page's numbers are the script's.

### Sources and rows, as the script reads them

Until 2026-08-02 the rows come from the three validation ledgers the coordinator keeps (a detailed validation log, a one-row-per-task summary table, and the calibration log the estimator reads); from 2026-08-03 the fleet's dispatch board closes each day's rows into a day file, and the day files are the source.

| Source | rows read | no ratio | excluded by the row's own words | ceded to the board | kept after de-dup |
|---|---:|---:|---:|---:|---:|
| detailed validation log | 173 | 10 | 8 | 0 | 152 |
| summary table | 381 | 1 | 1 | 130 | 184 |
| calibration log | 183 | 0 | 3 | 0 | 56 |
| board day files (Aug 3 →) | 449 | 0 | 8 | — | 334 |

Board rows also drop out for: no actual minutes and no close clock (26), cancelled, withdrawn or carved words on the row (21), no expected minutes in the estimate cell (12), not yet closed (5), and the 39 clock-only rows above. De-dup key: date · agent · estimate minutes · ratio. Result: **726 rows**, 2026-02-17 → 2026-09-30, of which **618 were dispatched to an agent** and 108 are the coordinator's own blocks.

## 4. The count over time, and a correction

Our public figure has been a running counter: each validation batch adds the legs it scored to the previous total, and the homepage rounds the total down. That series reads 253 (2026-05-14) → 257 (05-21) → 451 (08-09) → 495 (08-17) → 539 (08-24) → 600 (08-31, the "600+" on the homepage today) → 667 (09-10) → 688 (09-13) → 729 (09-20) → 731 (09-21) → 756 (2026-09-27, its latest batch, which read the board through 2026-09-25).

Re-deriving the count from the files with the definition above gives a smaller number, for two reasons that are both mechanical. The counter adds the coordinator's own blocks, which §2 excludes; and the counter never de-duplicates or re-parses, so a row the script cannot read a work figure from, or reads twice across two ledgers, stayed counted once it had been.

| Series | through 2026-08-31 | through 2026-09-10 | through 2026-09-30 |
|---|---:|---:|---:|
| running counter (published to date) | 600 | 667 | 756 (latest batch 09-27, rows through 09-25) |
| reproducible, all rows, as the first edition read them | 569 | 629 | — |
| reproducible, all rows, this edition's reader | 577 | 648 | 726 |
| reproducible, dispatched to an agent, as the first edition read them | 505 | 557 | — |
| **reproducible, dispatched to an agent, this edition (this page's definition)** | **513** | **568** | **618** |

The first edition's rows are that day's run. Read again today, the same dates come out higher, for two mechanical reasons. The board reader missed the work figure on rows that state it in a format it did not know ("24m audit vs 55", "66m/11f vs 80/42") and filed them as closed without a work figure; a fallback added on 2026-09-30 reads them, which moves 25 rows into the count, 18 of them dispatched legs, 11 of those dated on or before 09-10. And three of the coordinator's own blocks dated before 09-10 closed after that run. No row the first edition counted has changed.

**From this edition on, the published count is 618 as of 2026-09-30, on the reproducible external series.** The first edition put that series at 557, displayed as "550+", and said the homepage would move down to it at the next monthly sweep. That sweep falls now, and the series has passed the figure the homepage already shows, so the homepage keeps "600+" and takes this page's definition and the 2026-09-30 date. The reproducible series is still about a fifth below the counter (618 through 09-30 against the counter's 756 through 09-25; 513 against 600 on the homepage's original date), and that is a change of definition rather than a loss of legs: every leg the counter added is still in the record; the tighter count is the one anyone can recompute from the files with the script.

## 5. What the count is made of

**Runtimes.** The 618 dispatched legs went to five runtimes over seven and a half months. Two coding-agent CLIs carry nearly every row recorded against a single agent (274 and 195 across the corpus); a third ran in the launch weeks of February and March and was dropped from the fleet in August (14 rows), a fourth was trialled in March (2), and a fifth entered evaluation in late August and has one row, in September. A further 86 rows are recorded against more than one agent (mirror pairs and brainstorm rounds scored as one leg) and 46 ledger-era rows carry no agent label at all; both are artefacts of how the ledgers were kept between March and July, when most June and July rows are of these two kinds, not runtimes. No per-runtime accuracy figures are published here, by the disclosure boundary; `2026-10-01-validated-dispatches-aggregates.json` next to this piece carries the month × runtime row counts.

**Window and period.** Feb–Mar (launch weeks) 228 rows · Apr–Jun 91 · Jul–Sep 407. Median estimate 30 minutes, median actual 16; 402 estimated hours against 297 actual hours over the corpus.

**Shape.** By estimate size: ≤ 15 m 158 rows · 16–30 m 298 · 31–60 m 216 · 61–120 m 50 · > 120 m 4. By task class (a keyword map over the task title, maintained by hand): review / audit / verification 165 · release / promote 139 · implementation 135 · brainstorm / research / design 109 · docs / site content 32 · other 38, plus the 108 coordinator self-blocks that this page excludes.

## 6. Failure and human intervention

Two different records answer "what went wrong", from the two sides of a dispatch.

**Sender side.** In the dispatch record a leg fails the count only by the exclusions in §2. An estimate verdict is not a failure of the leg: of the 316 ledger-era rows that carry one, 228 are ACCURATE (72%), 34 OVER, 19 UNDER and 35 MISCALIBRATED, and the Jul–Sep share of ACCURATE is 93%. Review status is recorded on 209 rows: 155 cross-reviewed (a second agent's approval before landing), 46 not applicable (no pull request), 7 self-only, 1 unreviewed; the remaining 517 do not record it.

**Receiver side.** Every dispatch since May carries an autonomy audit record on the receiving agent's side; `hil_stats.py` aggregates them. As of 2026-10-01: 818 records, read from both machines the fleet has run on (§7, point 6). Admission: 680 paused for the human, 135 auto-accepted (a pause rate of 83%). Human outcomes are recorded on 533 pauses: 498 approved (93%), 30 modified, 5 declined; median decision latency 123 seconds, p80 222 s, p95 606 s. Mid-run threshold checkpoints: 267 evaluated, 58 breached (23 on minutes, 17 on files touched). Final states: 773 done, 10 superseded, 24 still paused, 1 error. Actual against the declared envelope: minutes at a median of 0.50× with 81% inside, files at 0.67× with 84% inside. These are the companion piece's numbers, re-run for this edition; the two records overlap on every dispatch since May and disagree on nothing structural, but they are joined by hand, not by key.

So "human intervention" in this fleet means: four dispatches in five pause at admission for a person, more than nine in ten of those are approved as sent, within about two minutes at the median, one in eighteen is modified, about one in a hundred is declined, and one leg in five that runs breaches a threshold it declared and pauses again mid-run. None of that changes whether the leg counts once it closes.

## 7. What the count cannot tell you

1. **It is one operator's record.** One coordinator estimates, one human clears gates, one fleet's mix of tasks. It describes a practice, not a population.
2. **Actuals are self-reported.** Work minutes come from the receiver's own audit clock or its reply. No external timer, no screen recording.
3. **The mix moves under the count.** Models, effort settings and lanes changed through the window; runtimes were added and dropped. The count is stable; what a "dispatch" cost or produced is not, and the count does not claim it.
4. **The estimator learned on the way.** The calibration was tuned seven times in the window; part of any accuracy trend is the estimator changing, not the agents.
5. **Two sources, joined on a date.** Rows before 2026-08-03 were hand-scored into ledgers, with carves and corrected verdicts; rows after are parsed off the board by rule. De-dup is heuristic; treat n as accurate to a few percent. The parsers are regular expressions over hand-written cells: a 2026-09-12 fix to the ledger reader (a cell carrying two figures, or a compound "14m32s", had been summed or truncated) moved 31 ledger actuals and two board estimates without moving n or any ledger ratio; the companion piece's published run predates it and is not re-issued. A 2026-09-30 fix to the board reader (a row stating its audit work figure in a format the patterns did not know had been filed as closed without a work figure) moved 25 rows into the count without changing any row already counted; §4 gives the first edition's dates re-read with it.
6. **Receiver-side records start in May, and live where the agent ran.** For February to April the record is the coordinator's status cell alone. An audit record is written on the machine the receiving agent ran on; the first edition read one machine (686 records), and this one merges two (789 and 29), which adds seven May and July records the first run could not see, as well as the legs since.
7. **The rows are private.** They carry task subjects and message identifiers. The disclosure is this definition, the two scripts and the aggregates; a fourteen-row sample with subjects and identifiers removed ships alongside.

## 8. Cite

A `CITATION.cff` at the repository root gives the citation form for the record, the aggregates and the scripts. The scoring scripts read the coordinator's own file layouts and run against the private record; the coordinator is internal and not released, so the page publishes the aggregates and the scripts, not a runnable reproduction.

## One exhibit, redacted

Fourteen rows of the record as the script scores them (the first edition's twelve, and two from late September), spread across the window; subjects, identifiers, project and agent names removed. Columns: date, runtime label, task class, source file, estimate minutes, actual minutes, ratio, verdict where the ledger wrote one, review status where recorded. Runtime labels are replaced by agent-1 … agent-5 in the order the five runtimes first appear in the record; the coordinator's own blocks, rows recorded against more than one agent, and rows with no agent label are named as such. The sample is `2026-10-01-validated-dispatches-sample.csv` next to this piece; it is illustrative, not a statistical sample.

| date | runtime | class | source | est m | actual m | ratio | verdict | review |
|---|---|---|---|---:|---:|---:|---|---|
| 2026-02-18 | agent-2 | review / audit / verification | vault summary | 22 | 15 | 0.68 | ACCURATE | unrecorded |
| 2026-03-08 | agent-1 | docs / site content | vault summary | 50 | 14 | 0.28 | MISCALIBRATED | unrecorded |
| 2026-03-11 | agent-1 | docs / site content | vault summary | 45 | 15.5 | 0.34 | MISCALIBRATED | unrecorded |
| 2026-03-14 | agent-1 | implementation | vault summary | 30 | 51 | 1.70 | ACCURATE | unrecorded |
| 2026-03-18 | no label | implementation | calibration log | 45 | 6 | 0.13 | — | unrecorded |
| 2026-03-19 | agent-3 | brainstorm / research / design | vault summary | 10 | 18 | 1.80 | ACCURATE | unrecorded |
| 2026-03-20 | agent-1 | brainstorm / research / design | vault summary | 15 | 17 | 1.13 | ACCURATE | unrecorded |
| 2026-05-12 | agent-2 | review / audit / verification | detailed log | 12 | 5 | 0.42 | ACCURATE | n/a (no PR) |
| 2026-05-12 | agent-1 | other | detailed log | 5 | 1.5 | 0.30 | ACCURATE | n/a (no PR) |
| 2026-07-10 | coordinator | coordinator self-block | detailed log | 10 | 8 | 0.80 | ACCURATE | unrecorded |
| 2026-07-13 | more than one agent | docs / site content | detailed log | 35 | 15 | 0.43 | ACCURATE | unrecorded |
| 2026-09-04 | agent-2 | release / promote | board day files | 55 | 34.8 | 0.63 | — | cross-reviewed |
| 2026-09-15 | agent-1 | release / promote | board day files | 75 | 71 | 0.95 | — | cross-reviewed |
| 2026-09-28 | agent-2 | brainstorm / research / design | board day files | 24 | 15 | 0.62 | — | unrecorded |

## What this piece will not contain

By the standing disclosure boundary: no attribution of outcomes to a named model or runtime, no per-run token or dollar cost, no verbatim task text or message bodies, no third-party data. The quality scores and the "human-equivalent" column the records carry are left out; the aggregates and the definition above are the disclosure.
