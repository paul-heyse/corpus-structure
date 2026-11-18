# Plan authoring: investigations behind the unified domain model and execution series — 2026-11-19

**Question.** What is true in source, and what did the declared-data-operations plan leave
open, for the decisions the
[unified domain model and execution plan series](../../../plans/unified-domain-model-and-execution_2026-11-19.md)
had to settle while it was written?

**Consumer.** That plan series. No record is finalized: these are readings of source and of
other plans, not probes or measurements.

## Method and limits

Each report was produced by a delegated read-only contributor on 2026-11-19, reading a frozen
export of `main` at `cb4e09667`, whose production source is identical to `5139eaba3`, the
baseline of the design review the series implements. Cited lines are exact for that commit.
No project test, provider, benchmark or database was run. Paths in the reports that begin
with a session scratch directory refer to that export, which is not retained. Receipts and
outcomes in the validation report are quoted from other plans, not re-observed. Each report
states what it read fully, sampled or did not read.

The design reports were written before the independent read and the coordinator's rulings
that followed it. Where they differ, the plan governs. The differences that matter: existing
operations with no validity family declare `none` and keep today's behaviour, where the
lowering report had old null rows convert to conservative validity; the program declaration
is the one home of which program validates a family; and nothing is tuned by the final runs.

| Report | What it holds |
|---|---|
| [lowering.md](lowering.md) | Design advice for the compiled model, the declaration grammar and vocabularies, per-operation facts lowered per release (nineteen selection sites), conservative validity, support edges, roles and purposes, and the passages superseded |
| [identity.md](identity.md) | Design advice for the program registry, the identity layers, revisions authored only when installed bytes differ, the execution path that generates nothing, carried assurance and the watermark |
| [caches.md](caches.md) | Current holders per cache tier with thread and process context, repeated work, on-disk conventions, settings and events, and the DuckDB, SQLite and retirement scope |
| [validation.md](validation.md) | The open qualification obligations taken over from the declared-data-operations plan, the state of the environments, what is recorded about the stopped book run, and the test and qualification surface |
| [independent-read.md](independent-read.md) | The independent read of the drafted series: coverage table, thirty-four defects with corrections, and spot checks |

The reports are inputs, not conclusions.
