# Phase 0 pool and interchange: the relational pool, the in-process engine, writes and exports

**Status:** Active. **Built (2026-10-29):** P0-P-1 (pool contract and ADBC loader), P0-P-2 (DuckDB engine,
set-equality harness) and P0-P-4. **Partly built:** P0-P-3 (bulk writer; `ci export` and the
`referencing.Registry` left; pgpq not adopted, §11 P3-01). Q-5 done; Q-7 deferred to P2's merge test;
Q-8 withdrawn. Part of the [phase 0 series](../phase-0_2026-10-28.md), which owns
shared decisions, contracts, the dependency graph and the findings table (§11).

**Basis.** This document builds the alignment review's R09 and the runtime half of R10:
- [design review](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md), its
  R09 and R10;
- the [target model](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md),
  cited here as "TM", in particular §10 on where each operation runs.

It follows coordinator decisions 22 and 24, and RC02 (ADR-0021, superseding ADR-0016, at P0-D-1) and
RC15. The operator directed on 2026-10-28 that these foundations be built in phase 0, even though the
review places most of their use from phase 1.

**The libraries.** DuckDB 2.0 and PyArrow 26 are recent, major releases. Their mechanisms here come from
the operator's overviews ([DuckDB 2.0](../../libraries/duckdb_2.md), [PyArrow 26](../../libraries/pyarrow.md)),
their versioned documentation, and the review's library notes, which include DuckDB 2.0.0 checks run on
scratch data on 2026-10-28 (Interface-checked).

Every design claim here is **Proposed** unless it carries another label.

## 1. What this document builds

**Today's design** loads the consolidation pool with Python queries and runs every step as procedural
Python. Its set-based steps (grouping, joins, aggregates) are therefore expressed as loops, and two
consumers cannot share a typed relational form of the pool.

**The target** makes the pool a contract: a set of model-typed Arrow relations, loaded as of the run's
cut. Two implementations run its set-based steps:
- the **Python reference implementation**;
- an **in-process DuckDB 2.0 engine**, with no persistent state.

The two must be set-equal on the same inputs, which gives mechanism substitution A of the review. The
following stay in Python and reach the engine as data:
- identity and canonical forms (keys, `text_form`, `normalize_label`, token form);
- TeX, SymPy, z3 and inference.

They stay in Python for three reasons:
- neither engine has `casefold`;
- Unicode table versions differ between engines;
- VARIANT and JSONB reorder keys and collapse duplicates.

Splitting identity across engines would give it two owners (Interface-checked: DuckDB 2.0.0
`lower('Straße')` keeps `ß`).

The document also builds:
- the **bulk writer** from the generated schemas;
- a **Parquet run export** (`ci export`), whose `KV_METADATA` carries the registry ids;
- a **`referencing.Registry`** for external consumers of the JSON Schemas;
- the **evidence catalog**, generated from `Record`, with record citations checked (DA-021).

Consolidation keeps the semantics and selection of its steps: which steps run, and what each means.
This document owns the contract, the loader, the engine wrapper, the conformance harness between the
two implementations, the writer and the exports.

## 2. Contracts

### 2.1 Consumed

| Contract | Owner |
|---|---|
| Arrow schemas with `cs.*` metadata; payload-schema registry ids; DuckDB `SHREDDING` specs | model and projections (M3, M4) |
| The generated `MetaData`; the repository and pool (connection lifecycle) | model and projections (M2); foundations (F4) |
| The run cut, `ops.run.cut_at` | orchestration (O1) |
| Consolidation's step semantics (alias-equality linking, fusion by key, alternative grouping, pack `views:` facts) | consolidation (C1); schema and rules (`views:`, S2) |
| ADR-0021; D5 §3.6 must-link order (RC15) | coordinator P0-D-1, P0-D-2 |

### 2.2 Produced

| Contract | Consumers |
|---|---|
| `pool.load(run, cut)` returning model-typed Arrow relations; T3 hydration into the keyed candidate set | consolidation (C1) |
| The engine interface, with both implementations and the set-equality harness | consolidation (C1); evaluation (run diffs, candidate pairs, score aggregates) |
| The Arrow-native write route and the export, over F4's bulk-write primitives | consolidation once P3 lands (C1 is built on F4's primitives and switches without change of meaning), the export |
| `ci export`: Parquet run export | the operator; downstream tools |
| The evidence catalog and checked citations | `tools/evidence`; design and ADR text |

## 3. Design of the parts

### 3.1 The pool contract and loader (P1)

**The pool tables** are one Arrow relation each, with schemas from M3: candidate entities, statements,
`ExternalReference` candidates, claims, alternatives, unsupported items, supports, the observation index,
and the reference run's entities and aliases (which alias-equality linking joins). Each relation carries the
`cs.*` metadata.

**The loader.** `pool.load` reads `kb.run_observation` and the payloads as of `cut_at`.
- Its route is chosen by probe Q-5: ADBC 1.13 `fetch_record_batch()`, or psycopg with a typed row
  factory.
- Probe Q-5 (`p0q.pool-roundtrip`, Tested 2026-10-28) chose ADBC. NUMERIC arrives as `arrow.opaque`
  strings and is kept as text; JSONB arrives as `arrow.json`. `$1`-parameterized `SELECT`s work in 1.13
  but bypass the COPY transport (about 1.4× slower), so the loader binds the run and the cut as literals
  from the run row or through a temporary table. `±infinity` timestamps do not survive.
- DuckDB 2.0 handling the probe found: a second `execute()` silently discards the rest of an open
  result, so each result is consumed or closed first; the session time zone is pinned to UTC; Arrow
  output drops the JSON tag, so the loader re-attaches it from the model's schema.

**T3 hydration** into the keyed candidate set is the reference path for Python steps.

**Determinism rules** (TM §10):
- results are sets;
- every ordered output has an explicit `ORDER BY` key;
- aggregates are ordered, e.g. `sum(x ORDER BY key)`;
- ties are broken by key.

Because of these, fixtures are Arrow tables, and the tests need no database server (FP-06).

### 3.2 The DuckDB engine (P2)

**DuckDB 2.0.0 becomes a product dependency**, pinned exactly, with a `docs/pins.md` hold row. The hold
is there because 2.0 is a week-old major release.

**The connection lifecycle** follows 2.0's rules (`duckdb_2.md` §3.5–3.7):
- Arrow comes back only from relations (`rel.to_arrow_reader()`, `to_arrow_table()`);
- an open `execute()` result blocks its connection until `con.complete()` or `con.abort()`;
- a busy connection used from another thread raises `ResourceInUseException`;
- a failed statement aborts the explicit transaction.

The engine holds one connection per pass, creates no persistent database, and registers the pool
relations from Arrow.

**The second implementation** covers these phase 0 set steps:
- alias-equality linking, as an equality or `SEMI` join;
- fusion by key and alternative grouping, as `GROUP BY` key or slot;
- the pack `views:` facts, compiled to joins and group-bys (`same_slot`, `alternative_of`,
  `family_params`, `given_by_others`).

Rule evaluation itself stays in rule-engine over hydrated objects (TM §10), because a DuckDB Python UDF
would run Python per batch and gain nothing.

**Not adopted in phase 0:**
- `NEAREST` (M14 bulk ranking, phase 2);
- statement triggers for incremental metrics.

Both are recorded in TM §10 for later.

### 3.3 Merge order (probe Q-7; RC15; F03)

D5 §3.6's union-find refuses any union that would join a cannot-linked pair, so its result depends on
processing order. RC15 fixes a declared must-link order: score, then key.

**Probe Q-7** checks two implementations of that order against each other, across shuffled input orders:
- the declared order in Python;
- DuckDB `WITH RECURSIVE … USING KEY (node, min(comp))` components with a cannot-link anti-join.

Merges are phase 2, so phase 0 builds only the probe and the fixture.

### 3.4 Writes and exports (P3)

**The bulk writer** builds on foundations' bulk-write primitives (F4), which own `Copy.set_types` and
any bulk-writer enforcement of INV-03/INV-08; this package adds the Arrow-native route and the export.
- psycopg `Copy.set_types` is the default. S6 measured it on the interim cluster: 100,000 observations
  in 1.1 s and 20,000 claims in 229 ms (Measured, 2026-10-28).
- pgpq 0.12 is not adopted (probe Q-5): NUMERIC as text is refused by the server, and only a text
  staging table with `::numeric` passes. It is reconsidered only if a measured writer cost calls for it,
  and then with the staging step.

**The Parquet run export**, `ci export RUN`:
- writes the run's knowledge tables through DuckDB
  `COPY … TO … (FORMAT parquet, KV_METADATA {model_revision, schema_version, payload_schema_id…}, ORDER_BY …)`;
- writes observation payloads per kind as VARIANT with the generated `SHREDDING` spec;
- reads back through `read_parquet(schema=…)` and `parquet_kv_metadata` in its test.

This is the operator's no-migration route for analytics: payload fields become typed columns with no
PostgreSQL DDL. On VARIANT field access, absent and null both read as SQL NULL; `json_exists` on the JSON
form distinguishes them.

**A `referencing.Registry`** (`with_resources`, `Draft202012Validator`) serves external consumers the
versioned JSON Schemas.

**Optional:** a streaming re-encode through PyArrow 26's `RecordBatchReaderSourceNodeOptions` and
`Declaration.to_reader()`, from an ADBC reader into pgpq. It is not required, because the Python Acero
API is experimental.

### 3.5 The evidence catalog and checked citations (P4)

- **The catalog.** The DuckDB tables are built from `Record`'s Arrow schema (`from_arrow`) instead of
  hand-written DDL, so the tool has one schema owner.
- **Checked citations.** `just evidence check` resolves record ids cited in `docs/design/` and
  `docs/adr/`, and warns on superseded ones. For example, `s0r2.scores` is cited by DESIGN §B1 and
  others.
- **Tracked reads.** `render` tracks every record read through `record()`, `query()` and `value()`.
- **Typed fields.** `answers` and `consumed_by` are typed.
- **Outcome vocabulary.** `Record.outcome` keeps `partial`; AGENTS.md admits it for records (RC17, as
  decided).

## 4. Probes

| Probe | Question | Decides | Evidence |
|---|---|---|---|
| **P0-P-Q5** (Q-5) | ADBC `fetch_record_batch` → DuckDB relation → Arrow → psycopg `Copy.set_types` or pgpq: do absent versus null, JSONB, numeric and `timestamptz` survive? What memory does one join hold? | P1's loader route; P3's writer (pgpq or not) | `p0q.pool-roundtrip` |
| **P0-P-Q7** (Q-7) | Declared must-link order against `USING KEY` components with a cannot-link anti-join, over shuffled inputs | F03's closure; the phase 2 merge implementation | `p0q.merge-order` |
| **P0-P-Q8** (Q-8, operator 2026-10-28) | A declarative inference layer: linkml-datalog (the capability reference: schema-driven inference of `symmetric`, `transitive` and inverse relationships, reified-association edges, embedded rules, validation over derived facts) patched to import on linkml-runtime 1.12.1 and run on Soufflé over the S4 statistics pack, against recursive DuckDB 2.0 SQL compiled from the same declarations and the pack's `derive:` rules over model-typed pool relations. Do they derive the same facts; do typed values, conditions and absent fields survive each route; what does each need declared? | The inference layer's engine (DuckDB recursion, Soufflé, or neither), where it lives (consolidation and the pool; phase 1 derived claims), and the declarations M1's `system.yaml` and S1's pack vocabulary carry | `p0q.inference-layer` |

## 5. Packages

| Package | Scope | Prerequisites | Done when (closure evidence) | Closes (§11) |
|---|---|---|---|---|
| P0-P-Q5 | Probe Q-5; pins adbc-driver-postgresql 1.13 and pyarrow 26 in the scratch environment | none | Record finalized; loader and writer routes chosen | Q-5 |
| P0-P-Q7 | Probe Q-7: deferred to P2's merge test (operator, 2026-10-28) | P0-D-2 (RC15 text) | A shuffled-order fixture gives equal partitions in both, as part of P2 | Q-7, F03 |
| P0-P-Q8 | Probe Q-8: withdrawn; the question moves to S1's pack vocabulary (operator, 2026-10-28) | — | — | Q-8 |
| P0-P-1 | Pool contract; loader as of `cut_at`; T3 hydration; Python reference implementation; Arrow fixtures; determinism rules | P0-M-3, P0-M-4, P0-F-4, P0-P-Q5 | Fixture-local tests with no server; equal outputs across repeated loads | DA-009 (registry ids in pool metadata) |
| P0-P-2 | DuckDB engine with the product pin and hold row; second implementation of the phase 0 set steps and the `views:` facts; set-equality harness | P0-P-1 | Both implementations give set-equal outputs and equal keys on the same fixtures | R09 (mechanism substitution) |
| P0-P-3 | Bulk writer from generated schemas; `ci export` with `KV_METADATA` and VARIANT shredding; `referencing.Registry`; pgpq per Q-5 | P0-P-1, P0-P-2, P0-M-4, P0-C-1 | Export round trip keeps the schema and the registry ids; writer round trip lossless per class (T5) | DA-009, R10 |
| P0-P-4 | Evidence catalog from `Record`; checked citations; tracked reads; typed fields | P0-D-1 | A superseded citation warns; the hand DDL is gone | DA-021 |

## 6. Tests

- **Set equality.** The two implementations agree on shuffled fixtures.
- **Determinism.** Repeated runs give byte-equal ordered outputs.
- **Loader.** The run's relations are as of the cut, so an observation written after `cut_at` is
  absent.
- **Export round trip.** The schema and `KV_METADATA` survive.
- **Writer.** Lossless per class; absent versus null kept.
- **Evidence.** The catalog regenerates from `Record`; a superseded citation is flagged.

## 7. Indicative size

About 700 product lines: pool and loader 200; engine and steps 250; writer and export 150; evidence 100.

## 8. Choices left to implementation

- Whether the loader uses ADBC or psycopg (Q-5).
- How `views:` compile to SQL: a small compiler, or hand-written per fact with a coverage test.
- Batch sizes.
- The export's partitioning (`PARTITION_PATH`).
