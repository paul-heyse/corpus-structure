# Inputs to the production design review of 2026-11-18

**Question.** What is true in source, and what do the pinned libraries provide, for the
judgments the
[review of the unified domain model and execution](../../reviews/design_review_unified-domain-model-and-execution_2026-11-18.md)
and the [audit refresh](../../audit/README.md#refresh-2026-11-18) it consumed had to make?

**Consumer.** That review and that audit refresh. No record is finalized: these are readings
of source and of installed libraries, with small library probes on synthetic in-memory data,
not measurements.

## Method and limits

Each report was produced by a delegated read-only contributor on 2026-11-18. Source was read
in a frozen export of `main` at `d78c98765`; cited lines are exact for that commit. No project
test, provider, benchmark or database was run. The library reports record their probes
(statement or call, result, version); none touched project data. Paths in the reports that
begin with a session scratch directory refer to that export, which is not retained. Each
report states what it read fully, sampled or did not read. The reports were written under a
brief that called the model-owned SQL conversion complete; the independent challenge corrected
that (ADR-0131 and the declared-data-operations coordinator record residual SQL authoring as
open), and the audit pages and the review carry the correction. Read the lane reports with
that in mind.

| Report | What it holds |
|---|---|
| [lane-model-authority.md](lane-model-authority.md) | DA-070 to DA-074 and DA-081 re-read; the model map; the fact-ownership table; the roles of the data-model libraries |
| [lane-identity-and-caching.md](lane-identity-and-caching.md) | DA-068, 069, 075 to 078, 033 and 058 re-read; the lowering list; the identity inventory; the cache and prepared-state inventory |
| [lane-generators-and-sql.md](lane-generators-and-sql.md) | The typed-program and generator layer as new audit scope; remaining hand-written SQL; DA-079 and DA-080; the DuckDB modules |
| [challenge.md](challenge.md) | The independent challenge of the drafted audit refresh, with its corrections |
| [analytical-inventory.md](analytical-inventory.md) | Derived, analytical and set-wise computations: where each runs, its inputs, and whether it is bound to PostgreSQL authority |
| [library-data-model.md](library-data-model.md) | LinkML 1.12.1 and the other data-model libraries in use: what each can own, supported bridges, and what not to adopt |
| [library-duckdb.md](library-duckdb.md) | DuckDB 2.0.0: typed API coverage, what still needs SQL text, graph work, interchange, typing traps, concurrency, a decision rule |
| [library-cachetools.md](library-cachetools.md) | cachetools 8.0: classes, locks and conditions, removal hooks, limits, a reference architecture, concurrency recipes, migration from 7.2.7 |

The reports are inputs, not conclusions.
