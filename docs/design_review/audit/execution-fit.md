# Execution fit

Findings under FP-07/A4 and the efficient-architecture heuristics, assessed qualitatively for the
declared workload: phase 0 on 78 statistics pages, and later corpora per the phases 1–5 roadmap.
No figure here is a measurement. Baseline, scope and scenarios are in the [README](README.md).

Choices that fit the workload and should be kept:
- The queue's claim and fencing were tested in S6. There is no reaper, and orphans are found
  through an advisory lock.
- Reuse is keyed on content, not provenance.
- The BM25 predicate comes from one constant.
- `LocatorIndex` is prepared once per rendition.
- The per-run full rebuild and materialization is a recorded, justified tradeoff, not a finding.

<a id="da-024"></a>

## DA-024 — The final consolidation transaction holds the run-row lock across measurement and evaluation

**Principles:** FP-07, A4, DP-19, DP-20.
**Subject:** accepted target, labelled Proposed (D6 §3.1; phase 0 orchestration plan).

**Diagnosis.** At finalize, the final transaction locks the run row `FOR NO KEY UPDATE`. Before it
commits, it then runs:
- the whole finalize pass;
- the M19 per-rule counts;
- the measure stage;
- `evaluate.score`, inside a savepoint.

(Phase 0 orchestration plan lines 436-458; D6 §3.1.) Agent completions take `FOR SHARE` on that row,
so they wait for all of it. So does twin settlement into a finishing run, since it share-locks every
twin's run.

The lock exists for a real requirement: the transaction that read the pool must set `finished_at`.
Evaluation and measurement do not need it, and evaluation already has its own route
(`ci eval RUN`).

**Consequence.** **S4 at phase 1 scale** (a full first pass of 10⁴–10⁵ claims): an agent working the
queue has its `propose_claims` and `write_golden` calls stall for the whole terminal computation,
and the long transaction holds back vacuum.

**Footprint.**
- Known: the final pass.
- Inferred: twin settlement.

**Counterevidence.** Phase 0's pool is thousands of rows, so the lock is short there, and fencing
keeps the result correct whatever the duration.

**Leads:** seal the cut in a short transaction, with readers comparing against the cut; run
measurement and evaluation after `finished`.

<a id="da-025"></a>

## DA-025 — Keying repeats rendition-wide work for each statement

**Principles:** FP-07, DP-10.
**Subject:** implemented (`core/keys.py`).

**Diagnosis.**
- **Statement anchors.** `statement_anchor` calls `ctx.index.annotation_units()`, a full walk of
  the tree, once for every statement that has no `unit` or `details` ancestor (`keys.py:388`).
- **Segment keys.** `KeyContext.segments` re-derives the content digest and every segment key from
  content, although the store holds them (`keys.py:333-337`).
- **Member keys.** `member_parts` recomputes `claim_parts`.

**Consequence.** Negligible at phase 0 size. The cost grows with statements × segments per finalize
pass. This is static evidence only; no speed is claimed.

**Leads:** prepare the annotation units and segment keys once per `KeyContext`.
