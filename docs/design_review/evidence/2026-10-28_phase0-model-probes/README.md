# Phase 0 model probes, 2026-10-28

**Status, 2026-10-28: Q-1 to Q-5 and the settings check have run and are finalized; Q-7 is running.**

These are bounded investigations that decide between the stated variants of the phase 0 model
foundations. They are owned by the [phase 0 series](../../../plans/phase-0_2026-10-28.md), whose §11
holds the row for each probe, and they implement the probes of the
[domain-model alignment review](../../reviews/design_review_domain-model-alignment_2026-10-28.md) §10.
A probe outcome selects a variant; it never reopens a decision. The folder writes no product code.

## The probes

| Probe | Package | Question | Decides | Record |
|---|---|---|---|---|
| Q-1 | P0-M-Q1 | Can a `PydanticGenerator` subclass, or an own emitter, over S4's `core.yaml` produce the core shapes? Discriminated `t`/`op` unions with a named recursive `Condition`, `MISSING`, frozen tuples, both `ci:form` variants and prefixed aliases | M5's variant: Stage B or the fallback | `p0q.stage-b` |
| Q-2 | P0-M-Q2 | Do permissible-value `in_subset` member properties pass `linkml-lint` and read back through `SchemaView`? | M1's declaration form: `in_subset` or `ci:properties` | `p0q.member-properties` |
| Q-3 | P0-M-Q3 | `MetaData` generated from a LinkML sketch of five D3 tables plus an overlay, compared with S6's DDL through a pglast-normalized projection; Alembic autogenerate with a `CreateView` table | M2's overlay/compiler split | `p0q.port-check` |
| Q-4 | P0-F-Q4 | COPY at run scale on `18/corpus`, with and without same-run composite FKs and per-version vocabulary FKs, paired with the `s6.volume` rerun | INV-03/INV-08 enforcement: FK or bulk writer | `p0q.fk-cost` |
| Q-5 | P0-P-Q5 | ADBC `fetch_record_batch` → DuckDB relation → Arrow → psycopg `Copy.set_types` and pgpq: absent versus null, JSONB, numeric, `timestamptz`, and the memory of one join | P1's loader, P3's writer, whether pgpq is adopted | `p0q.pool-roundtrip` |
| Q-7 | P0-P-Q7 | Declared must-link order against `USING KEY` components with a cannot-link anti-join, over shuffled inputs | F03's closure; the phase 2 merge implementation | `p0q.merge-order` |
| — | P0-F-5 | Validating a `BaseSettings` reads the environment | Coordinator decision 26's evidence | `p0q.settings-env` |

## Environment

The project in this folder is `pyproject.toml` with `uv.lock`, pinned exactly on 2026-10-28:
- linkml 1.12.1 and linkml-runtime 1.12.1;
- pydantic 2.14.1 and pydantic-settings 2.16.1;
- sqlalchemy 2.1.5 and alembic 1.20.0;
- pglast 8.7;
- psycopg 3.3.6;
- pyarrow 26.0.0, adbc-driver-postgresql 1.13.0, duckdb 2.0.0 and pgpq 0.12.0;
- jsonschema 4.26.0.

It is synced to `build/probe-venv`. Run a probe from the repository root:

```sh
UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv run --project docs/design_review/evidence/2026-10-28_phase0-model-probes python docs/design_review/evidence/2026-10-28_phase0-model-probes/code/<probe>.py
```

Check that the environment still matches its lock with
`UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv sync --project … --locked --check`.

Probes that need a database use their own databases on the `18/corpus` cluster (`p0q_*`) and drop them
afterwards. The `main` cluster is never touched.

## Layout

- `code/`: probe scripts.
- `results/<probe>/`: their outputs.
- `records/<id>.json`: evidence records (ADR-0010). Finalize with `just evidence finalize
  2026-10-28_phase0-model-probes <id>`, then run `just evidence`.

## Q-2: member properties (`p0q.member-properties`)

**Question.** Can member properties (modality `premise_forming` `{supposed}`, `attribution_identifying`
`{cited}`, `conflict_bearing` `{asserted, defined}`; statement-kind `claim_bearing`; segment-kind
`annotation_unit`, `statement_anchor`, `search_block`, `container`) be declared as native
permissible-value `in_subset`, linted, and read back through `SchemaView`? Otherwise, does one scalar
`ci:properties: "a b"` annotation per member round-trip?

**Method.** `code/q2_member_properties.py` reads S4's `core.yaml` and writes, under `results/q2/schema/`:
- `core_in_subset.yaml`, with the eight subsets declared;
- `core_ci_properties.yaml`;
- `core_seeded.yaml`, in which one member names an undeclared subset;
- an unchanged baseline copy, `core_s4_baseline.yaml`.

A probe `SegmentKind` enum (D3's twenty kinds) is added. S4's `ci:claim_bearing` annotations are
replaced by the property. Each file is linted on its own with S4's `.linkmllint.yaml`, and the
membership read back is compared with a hand-written expectation table in the script. The table is
derived from neither file. The yaml/JSON dumps, `gen-json-schema` and `gen-pydantic` are also run.
Output: `results/q2/result.json`.

**Result (Tested, 2026-10-28, linkml 1.12.1).**
- **Lint.** Both forms lint with 0 errors. The only findings are the baseline's own two
  `standard_naming` warnings, on `t` and `v`. `no_undeclared_subsets` checks enum members, so the seeded
  undeclared subset is an error.
- **Readback.** `get_enum(E).permissible_values[m].in_subset` returns the subset names
  (`SubsetDefinitionName`), and so does `induced_enum`. All 8 properties equal the expectation table.
  The fallback annotation reads back as a string, and splitting it gives the same 8 of 8.
- **Round trip.** `yaml_dumper` and `json_dumper` keep `in_subset`, so the canonical JSON behind the
  revision hash carries the declarations. Both stock generators accept both files.
- **Accessors the plan named.** `permissible_value_ancestors` is the members' `is_a` closure and
  returns `['supposed']`: it does not expose subsets. `annotation_dict` addresses elements only, and a
  member raises `AttributeError`. A consumer reads `pv.in_subset` directly.
- **Shared namespace.** Member-property subsets share the schema's single subset namespace with the
  element subsets `structural` and `unsupported`. The declaration check (§3.1) must tell the two apart,
  for example by the set of names used on members.
- **Not tested.** A pack adding members with properties to a core enum: LinkML has no in-place enum
  extension.

**Feeds.** P0-M-1 (M1's declaration form). `in_subset` is viable, and `ci:properties` is not needed as
a fallback.

## P0-F-5: validating a `BaseSettings` reads the environment (`p0q.settings-env`)

**Question.** Coordinator decision 26 keeps operations models (run options, method `params`) frozen
plain `BaseModel`s, never `BaseSettings`. Its premise is that validating a `BaseSettings` from stored
data reads the current environment. Does it, under pydantic-settings 2.16.1?

**Method.** `code/settings_env.py` defines a `BaseSettings` with `env_prefix="P0Q_SETTINGS_ENV_"` and
two `int` fields `a` and `b` (default 0), and a plain `BaseModel` of the same shape. With
`P0Q_SETTINGS_ENV_A=1` set, it calls `model_validate({})`, `model_validate({"b": 2})` and
`model_validate_json("{}")` on each and compares the results with a hand-written expectation.
Output: `results/settings-env/result.json`.

**Result (Tested, 2026-10-28, Python 3.14.10, pydantic 2.14.1, pydantic-settings 2.16.1).**
- All three calls on the `BaseSettings` returned `a=1` from the environment; a supplied `b=2` was
  kept.
- The plain `BaseModel` kept `a=0` in all three.

**Feeds.** Coordinator decision 26 (foundations §3.5): a stored payload re-read through a
`BaseSettings` would mix in the current environment, so only `Settings` is one.

## Q-3: port check (`p0q.port-check`)

**Question.** Does `MetaData` compiled from a LinkML sketch of five D3 tables, plus a hand overlay,
reproduce S6's tested DDL through a normalized pglast projection? Which residue does the compiler
carry, which the overlay, and which differs by design? Does Alembic 1.20 autogenerate treat a
SQLAlchemy 2.1 `CreateView` table as a table, with and without `include_object`?

**Method.**
- **The sketch.** `code/q3/system_sketch.yaml` declares `ops.run`, `ops.task`, `kb.segment`,
  `kb.claim` and `meta.schema_slot` in S6's shape, using TM §4's `ci:store`, `ci:lifecycle` and
  `ci:invariant`. The referenced tables are stubs. It lints with 0 errors and one `standard_naming`
  warning (`results/q3/sketch.lint.json`).
- **Four declarations outside TM §4.** The sketch adds them, each marked "proposed":
  - `ci:on_delete` on a reference slot;
  - `ci:generated: insert_time`;
  - `ci:sql_type` on a type (`regconfig`);
  - the invariant template `iff_absent`.
- **The compiler.** `code/q3/compiler.py` builds `MetaData` from `SchemaView` with:
  - a naming convention and digest-named `CheckConstraint(col.in_(…))` for static enums;
  - FKs, `Identity(always=True)` and invariant CHECKs.

  It also relies on derived conventions:
  - the schema comes from a `meta`/`ops`/`kb` subset;
  - table names are snake case, and FK columns are `<slot>_id`;
  - a class without an identifier takes its sole unique key as the PK;
  - required nested slots and arrays get `DEFAULT '{}'`.
- **The overlay.** `code/q3/overlay.py` declares 12 indexes and binds to tables and columns by name.
  The BM25 index uses `postgresql_using`, `postgresql_with` and `postgresql_where`, with the kind list
  taken from the `search_block` member property (Q-2).
- **The comparison.** `code/q3_port_check.py` compiles `CreateTable` and `CreateIndex` for the
  PostgreSQL dialect. Both that DDL and S6's `code/s6_ddl_applied.sql`, copied to
  `results/q3/s6_ddl_applied.sql`, are parsed with pglast 8.7 and projected onto:
  - columns: type, NOT NULL and default;
  - the set of constraints: names ignored, and `IN` lists treated as sets;
  - indexes: `USING`, parameters with `DESC`, `WITH` and `WHERE`.

  Raw AST equality is not used. The generated DDL names every constraint and writes it table-level,
  while S6 writes constraints inline and unnamed. Ten seeded differences check that the comparator
  sees each dimension.
- **A strict compile.** A second compile ignores the four proposed declarations
  (`results/q3/generated_strict.sql`, `residue_strict.json`).
- **The database.** The generated `MetaData` is applied with `create_all` to a throwaway
  `p0q_portcheck` on `18/corpus`, cloned from `cs_template` (PostgreSQL 18.6, pg_textsearch 1.5.1).
  A `CreateView` table (`ops.finished_run`) is added, Alembic's `compare_metadata` and
  `produce_migrations` are run, and the database is dropped (`dropped: true`).

**Result (Tested, 2026-10-28; SQLAlchemy 2.1.5, Alembic 1.20.0, pglast 8.7).**

| Residue item | Class | Note |
|---|---|---|
| BM25 `WHERE` kind list | S6 DDL differs by design | Current D3 §5 has `caption` where S6 had `math_display`. The overlay follows the model's `search_block` |
| `created_at DEFAULT now()` (run, task) | compiler should carry; declaration missing from TM §4 | LinkML `ifabsent` has no `now()`. The sketch uses `ci:generated` |
| `ts_config regconfig` | compiler should carry; declaration missing | TM §4 says types carry a "projection type" but names no annotation. The sketch uses `ci:sql_type` |
| `ON DELETE CASCADE` (segment→rendition, claim→run, schema_slot→schema_version) | compiler should carry; declaration missing | Deletion semantics (D3 §8). The sketch uses `ci:on_delete` |
| `(parse_status = 'ok') = (parse_reason IS NULL)` | compiler should carry; declaration missing | TM §4's `iff_present(x, y = v)` cannot say "absent iff" without negation. The sketch uses `iff_absent` |
| 12 indexes, including partial, `DESC` and BM25 `USING`/`WITH` | overlay carries | 0 residue |

The comparison covers 84 columns, 38 constraints and 12 indexes.
- **With the proposed declarations,** the residue is 1 item: the BM25 kind list.
- **Strict (TM §4 only),** it is 11 items: 10 that need a declaration, plus the kind list.
- **Controls:** all 10 seeded differences are detected.

**Alembic.**
- **Views are treated as tables.** Without a filter, autogenerate emits
  `op.create_table('finished_run', …)` for the view, whether or not the view exists in the database.
  The reflected table names exclude views, and the installed Alembic 1.20.0 package contains no
  `is_view`, `CreateView` or `get_view_names`.
- **The native flag works.** An `include_object` that excludes tables with SQLAlchemy 2.1's
  `Table.is_view` yields no operations.
- **The `info` flag depends on the overlay.** `CreateView` leaves `Table.info` empty, so an
  `info["is_view"]` filter works only if the overlay sets the flag. Views therefore go through
  hand-written operations, not autogenerate.
- **Two other findings:**
  - with `compare_server_default=True`, autogenerate fails on the `regconfig` default.
    `SELECT 'english'::regconfig = 'english'` raises 22P02, the oid resolution of S6 F1;
  - reflection warns `Did not recognize type 'regconfig'`.

  With server defaults off, the 14 applied tables show no spurious differences.

**Feeds.** P0-M-2 (M2's overlay/compiler split and acceptance):
- the overlay carries every index;
- the compiler needs four declarations, or their equivalents, beyond TM §4;
- the migration environment's `include_object` should filter on `Table.is_view`;
- `compare_server_default` needs a `regconfig` workaround or must stay off for that column.

## Q-4: FK cost at run scale (`p0q.fk-cost`)

**Question.** At D3 §11's run scale (10⁵ observations, 10⁴–10⁵ claims), what do the target model's
same-run composite FKs (`UNIQUE (run_id, id)` targets; `kb.claim_ref` and `kb.claim_entity_ref`
with `FOREIGN KEY (run_id, …) REFERENCES kb.claim/kb.entity (run_id, id)`; `kb.claim.attribution_entity_id`)
and the per-version vocabulary FKs (`(schema_version_id, predicate) → meta.schema_slot`, INV-03;
`(schema_version_id, kind) → meta.statement_kind`) cost on binary COPY and on run deletion, on `18/corpus`?
Paired with the pending `s6.volume` rerun on the dedicated cluster.

**Method.** `code/q4_fk_cost.py all` (seed 20261028):
- **Base.** `p0q_fk` cloned from `cs_template`, S6's applied DDL and S6-B's row load, run from copies
  in `code/q4_s6/`. The copies are verbatim except for the cluster (port 5434, no `SET ROLE`, since the
  developer is already a non-superuser with CREATEDB), the database and result paths, and
  `s6_load.EVIDENCE` (S6's results are read as data). Every repetition runs on a fresh clone of the
  base, in its own process.
- **(a) the `s6.volume` rerun.** S6's `s6e_volume.py`, unchanged, five times. It loads 12,500 tasks,
  100,000 observations, 5,000 entities, 20,000 claims and 40,000 support and evidence rows, then runs
  the D3 queries, sizes and run deletion. Output: `results/q4/s6_rerun/rep*/`.
- **(b) the target model.** A scratch addendum over S6's DDL in three placements:
  - `t_none`: the TM §6 columns, the edge tables and their overlay indexes, with no same-run or
    vocabulary FK. This is the bulk-writer placement, and its run deletion deletes edges by `run_id`.
  - `t_samerun`: adds the `UNIQUE (run_id, id)` targets and the five composite FKs, cascading.
  - `t_all`: adds the two vocabulary FKs.

  Writes: S6's tasks and observations; 2,500 `Statement` entities with `kind`; claims with
  `schema_version_id`, an attribution on every tenth claim and `statement_id`; one `kb.claim_ref` row
  and four `kb.claim_entity_ref` rows per claim. That is 10⁵ edges at 2×10⁴ claims, and 5×10⁵ at 10⁵
  claims. Repetitions: five per placement at 2×10⁴ claims, with the order rotated between repetitions;
  three each of `t_none` and `t_all` at 10⁵ claims.
- **Checks.** Rolled-back negative inserts check which placement refuses a cross-run edge, an unknown
  predicate and an unknown kind. The bulk-writer equivalent check is timed: Python set membership over
  the same rows.
- **Measurement.** All writes are psycopg 3.3.6 binary COPY with `Copy.set_types`, in S6's
  transaction pattern. Times are client wall clock. The deletion trigger breakdown comes from an
  `EXPLAIN ANALYZE` pass that is rolled back before the timed deletion.
- **Outputs.** `results/q4/summary.md` and `summary.json` (`q4_fk_cost.py summary`),
  `results/q4/target/*.json` and `results/q4/base.json` (server facts).

**Environment (2026-10-28).**
- **Machine.** AMD Ryzen 9 9950X3D, 16 cores and 32 threads, 188 GiB RAM, Linux 7.0.0-38.
- **Server.** PostgreSQL 18.6 (Ubuntu 18.6-1.pgdg24.04+2) on `18/corpus`, configured by
  `ops/postgresql/corpus.conf`: `shared_buffers` 8 GB, `work_mem` 64 MB, `maintenance_work_mem` 8 GB,
  `synchronous_commit` off, `fsync` on, `io_method` io_uring, `wal_compression` zstd, `max_wal_size`
  8 GB, `jit` off. Extensions in `cs_template`: pg_textsearch 1.5.1, vector 0.8.7.
- **Client.** Python 3.14.10, psycopg 3.3.6 (binary implementation), libpq 18.6.
- **Concurrent load.** Another session's multiprocess S5 job was running. The 1-minute load average
  was 5–13 during the runs, and each output file records its own.

**Result (Measured, 2026-10-28, conditions above; medians, with min–max in `summary.md`).**

- **(a) The rerun matches the interim cluster.** The client builds every row in Python, so binary COPY
  is bound by the client, and the dedicated cluster's settings do not speed it up.

  | Step | Rerun (n=5) | `s6.volume` (interim cluster) |
  |---|---|---|
  | 100,000 observations | 1,190.8 ms (1,185–1,215) | 1,110 ms |
  | 20,000 claims | 232.6 ms | 229 ms |
  | 12,500 tasks | 107.1 ms | 103 ms |
  | 40,000 support and evidence rows | 201.2 ms | 214 ms |
  | run deletion | 304.0 ms | 261 ms |
  | qualifier `@?` query | 1.05 ms, `claim_pred` index scan | 1.00 ms, `claim_pred` bitmap scan |
  | "why a method ran" | 0.59 ms | 0.56 ms |
  | observations of the run by kind | 27.0 ms: a nested loop of 12,500 index scans on `observation_task_id_ordinal_key` | 17.9 ms: a hash join over a sequential scan of `kb.observation` |

  The two queries whose plans changed are carried by the same indexes. The plan change is likely
  `random_page_cost = 1.1` on `18/corpus`. This is an interpretation, not tested: S6 did not record
  `random_page_cost`, whose default is 4, and recorded `shared_buffers` 160 MB. On cached data, that setting makes the per-task index loop slower than
  the hash join. C2 should read run-wide `kb.run_observation` plans with this setting in mind.
  D6 §3's note holds again: float8 into `real` gives `22P03`.
- **(b) At 2×10⁴ claims and 10⁵ edges.** FK enforcement adds 577 ms to the 742 ms of materialized
  writes (+78%), which is +28% on the whole run load including observations:

  | Placement | `kb.claim` | `kb.claim_ref` | `kb.claim_entity_ref` | Materialized | Whole load | Deletion |
  |---|---|---|---|---|---|---|
  | `t_none` | 321 ms | 26 ms | 122 ms | 742 ms | 2,049 ms | 376 ms |
  | `t_samerun` | 350 ms | 127 ms | 507 ms | 1,255 ms | 2,546 ms | 579 ms |
  | `t_all` | 402 ms | 127 ms | 506 ms | 1,319 ms | 2,614 ms | 578 ms |

  Almost all of the cost is the edge rows' composite checks: about 2.4 µs per FK probe, two probes per
  edge row. The vocabulary FKs add about 52 ms on claims and 9 ms on entities.
- **At 10⁵ claims and 5×10⁵ edges.** `t_none` writes the materialized rows in 3,808 ms and `t_all` in
  6,744 ms (+2.9 s, +77%; the whole load ratio is 1.59). Deletion takes 1,680 ms against 2,666 ms. The
  cost is linear: 5.1× the 2×10⁴ difference for 5× the rows. The spread is under ±3% in every cell.
- **Enforcement.** `t_samerun` and `t_all` refuse a cross-run `claim_ref` target and a cross-run
  `claim_entity_ref` entity with `23503`. `t_all` also refuses an unknown predicate (INV-03) and an
  unknown statement kind. `t_none` accepts all four. The bulk writer's equivalent check over the same
  rows takes 3.6 ms (2×10⁴) and 21 ms (10⁵) in process, but it guards only rows that pass through the
  bulk writer.
- **A missing index in the TM §6 sketch.** The composite FK
  `(run_id, attribution_entity_id) → kb.entity` has no index on the referencing side. Deleting a run's
  7,500 entities then runs a NO ACTION check that scans the run's claims once per entity: 9.3 s of
  trigger time, against 32 ms with `CREATE INDEX … ON kb.claim (run_id, attribution_entity_id) WHERE
  attribution_entity_id IS NOT NULL` (`results/q4/trial_t_all_without_attribution_index.json`). The
  edge tables' composite FKs are carried by the overlay indexes `claim_ref_target` and
  `claim_entity_ref_entity`, and by the primary keys that lead with `claim_id`.
- **Operational finding.** As a non-superuser, `DROP DATABASE … WITH (FORCE)` fails with `42501` when
  an autovacuum worker is in a freshly loaded clone. A plain `DROP DATABASE` cancels autovacuum itself.
  This matters for F1's test-database fixtures.
- **Dataset for C2.** `results/q4/raw/p0q_fk_dataset.sql.gz` (Git LFS, 6.7 MB) is one `t_all` load
  at 2×10⁴ claims with its run kept. Restore it with `createdb -T cs_template <db>`, then
  `gunzip -c … | psql -d <db>`. The generator is `q4_fk_cost.py dataset`, with the same seed.

**Decision it feeds (P0-M-2, P0-F-4; ADR-0021's variants).** FK enforcement is acceptable at this
scale.
- **The cost.** It adds about 0.6 s to a 2×10⁴-claim run and about 3 s to a 10⁵-claim run, paid once
  at the run's final pass, plus 0.2–1.0 s of deletion. Against a run measured in hours, that is
  immaterial (a qualitative reading, FP-07).
- **What the database gives in return.** It refuses cross-run and unknown-vocabulary rows from any
  writer, and edge deletion cascades.
- **What the bulk-writer placement would need.** It saves that time, but needs its own check, which is
  cheap, and its own edge deletion. It leaves other writers unguarded.
- **Recommendation.** Declare INV-03 and INV-08 as FKs in 0001. Add a referencing-side index for every
  composite FK whose referencing columns no existing index leads with: at least `kb.claim
  (run_id, attribution_entity_id)`.

## Q-5: pool round trip (`p0q.pool-roundtrip`)

**Question.** Do absent versus null inside JSONB, JSON text, NUMERIC exactness and `timestamptz`
instants survive the round trip ADBC 1.13 `fetch_record_batch()` → DuckDB 2.0 relation (one join,
one group-by) → Arrow → PostgreSQL, by psycopg `Copy.set_types` and by pgpq 0.12? How does the loader
bind the run and cut? What memory does one join hold?

**Method.** `code/q5_pool_roundtrip.py all` runs on `p0q_pool`, cloned from `cs_template` and dropped
at the end.
- **The source rows.** `src_obs` has nine rows:
  - JSONB with field `b` present-null, absent and `false`; a JSON null at the top level and an SQL
    NULL; big and tiny JSON numbers; unicode and escapes; nulls inside arrays;
  - a `json` column with whitespace, key order and a duplicate key;
  - NUMERIC with 39 significant digits, `1.50`, `-0.000001`, `1e-40`, `NaN` and `±Infinity`;
  - `timestamptz` values at year 1, at both epochs, at the last microsecond of 9999, and with odd
    offsets;
  - text that is empty, NULL, or contains tabs and backslashes.

  `src_dim` is the join's dimension table.
- **Load.** ADBC `fetch_record_batch()` reads the rows, and the reader is consumed by `read_all`.
- **DuckDB.** The Arrow tables are registered. The probe runs a join `USING (kind)` and a group-by
  with `json_exists` and `->`, then returns Arrow with `rel.to_arrow_table()`.
- **Write-back.**
  - (a) psycopg binary COPY with `Copy.set_types`. JSON text goes through `Jsonb`/`Json` with an
    identity `dumps`, and NUMERIC through `Decimal`.
  - (b) pgpq `ArrowToPostgresBinaryEncoder.new_with_encoders` with the JSONB string encoder, then
    `Copy.write`. NUMERIC is tried three ways: as text, as a `decimal128(38, 9)` cast, and through a
    text staging table with a server-side cast.
- **Comparison.** Each destination is compared with the source in SQL. There are 11 checks per row,
  including `?`/`->` on `b`, `json::text` identity, `numeric::text` identity and `timestamptz`
  equality.
- **Other parts.**
  - psycopg as the alternative loader;
  - `±infinity`;
  - parameter binding, including which statements reached the server as `COPY` (read from
    `pg_stat_statements`);
  - memory at 10⁵ and 10⁶ observations of about 290 B JSONB each, joined with 2×10⁴ claims. The probe
    records RSS from `/proc/self/status`, `pa.total_allocated_bytes()` and DuckDB's
    `system.peak_buffer_memory` from JSON profiling.
- **Outputs.** `results/q5/fidelity.md`, `fidelity.json` and `memory_<N>.json`.

**Result (Tested and Measured, 2026-10-28; adbc-driver-postgresql 1.13.0, duckdb 2.0.0,
pyarrow 26.0.0, pgpq 0.12.0, psycopg 3.3.6, PostgreSQL 18.6, same machine as Q-4).**

- **ADBC's Arrow.**
  - JSONB and JSON arrive as `extension<arrow.json>`, with the jsonb canonical text and the json
    column's text byte for byte.
  - **NUMERIC arrives as `extension<arrow.opaque[storage_type=string, type_name=numeric]>`**, not
    plain `utf8` as pool-and-interchange §3.1 says. The digits are exact. The special values are
    spelled `nan`, `inf` and `-inf`; both `Decimal` and PostgreSQL accept these spellings.
  - `timestamptz` arrives as `timestamp[us, tz=UTC]`.
  - **`±infinity` does not survive.** Both become finite values near int64 minimum. ADBC adds the
    2000-epoch offset without special-casing them, so `+infinity` wraps around.
- **DuckDB 2.0.**
  - After `register`, `arrow.json` becomes `JSON` and the opaque numeric becomes `VARCHAR`.
  - `json_exists(payload, '$.b')` tells present-null (`true`, with `->` giving JSON `null`) from
    absent (`false`, with `->` giving SQL NULL).
  - Arrow output drops the JSON extension (plain `string`) and carries `timestamp[us,
    tz=<session TimeZone>]`, here America/New_York.
- **DuckDB 2.0's Python surface.**
  - Relations have no `fetchone()`.
  - `fetchall()` on a `TIMESTAMPTZ` needs `pytz`, which is not a dependency and fails here.
  - An unquoted column named `at` is a parse error.
  - A second `con.execute()` while a result is open does not raise `ResourceInUseException`. It
    silently ends the open result, whose remaining 4 of 5 rows are lost.
  - A relation re-runs on every call.
- **Write-back.**

  | Route | Outcome |
  |---|---|
  | psycopg `Copy.set_types` | all 11 checks pass on all 9 rows: absent vs null, JSON text, NUMERIC text (scale, 39 digits, NaN, ±Infinity), year 1 and 9999 instants |
  | pgpq, NUMERIC as text | refused by the server, `08P01 insufficient data left in message` (no silent corruption) |
  | pgpq, `decimal128(38, 9)` | refused by Arrow before COPY, `Rescaling Decimal value would cause data loss`; 39 digits and NaN/Inf cannot be decimal128 at all |
  | pgpq, text staging + `::numeric` | all checks pass |

  Notes on the routes:
  - pgpq's `Timestamp` encoder (it has no timestamptz) writes the UTC instant into a `timestamptz`
    column correctly. Binary COPY carries no per-field type, and the two types share the int64
    µs-since-2000 format.
  - The pgpq `Text` encoder into a `json` column keeps the text identical.
  - On the psycopg route, `to_pylist()` of DuckDB's New-York-zoned timestamps raises `OverflowError` at
    year 1. Casting the column to UTC first works, and the probe does so.
- **psycopg as loader.**
  - Its default loaders are lossy for this data. Binary JSONB goes through `json.loads`, so
    `12345678901234567890.123…` becomes the float `1.2345678901234567e+19`.
  - In a non-UTC session, loading `timestamptz` fails at year 1 (`DataError`), in both text and binary
    formats.
  - With `TextLoader` for jsonb, json and numeric and `TimeZone=UTC`, it equals ADBC's Arrow. The one
    difference is the special-value spelling: psycopg gives `NaN`, ADBC gives `nan`.
- **Binding.**
  - A `$1` parameterized SELECT works in 1.13, through both `fetch_arrow_table` and
    `fetch_record_batch`. The documented limit does not hold here.
  - But it reaches the server as a plain extended-protocol `SELECT`. Unparameterized SELECTs go out
    as `COPY (…) TO STDOUT (FORMAT binary)`.
  - At 10⁵ rows the parameterized load takes 161 ms against 115 ms for a literal; at 10⁶, 1,360 ms
    against 935 ms. Arrow schemas are equal.
  - The temporary-table route works: a parameterized `INSERT` into `q5_cut`, then a join, which is
    sent as COPY. A Python `str` does not bind to a `timestamptz` column (`42804`), but a tz-aware
    `datetime` does.
- **Memory (Measured; one process; 32 threads; DuckDB `memory_limit` default).**

  | Step | 10⁵ observations (Arrow 38 MB) | 10⁶ observations (Arrow 388 MB) |
  |---|---|---|
  | ADBC load | 163 ms; RSS +92 MB | 941 ms; RSS +430 MB |
  | join → Arrow | 11 ms; DuckDB peak buffer 21 MB; RSS +52 MB, the output copy of 39 MB | 40 ms; peak buffer 20 MB; RSS +420 MB, output 389 MB |
  | join + group-by → Arrow | 13 ms; peak buffer 31 MB | 32 ms; peak buffer 167 MB |
  | psycopg loader, same rows | 200 ms; RSS +138 MB | 1,979 ms (2.1× ADBC); RSS +1.5 GB |

  - ADBC's buffers are not in `pa.total_allocated_bytes()`, which reads 0: ADBC has its own allocator.
  - The join's own working memory is small, because the build side is the 2×10⁴ claims.
  - The output Arrow table is a full copy.

**Decision it feeds.**
- **P0-P-1, the loader: ADBC.**
  - Bind the run and cut as literals from the run row (they are ints and a timestamp the loader
    formats) or through a temporary table. Both keep the COPY transport.
  - Read NUMERIC as `arrow.opaque` string and keep it text in DuckDB. Never cast it to DECIMAL, since
    DuckDB's DECIMAL caps at 38 digits.
  - Treat `±infinity` as unsupported in pooled `timestamptz` columns: refuse or map it explicitly.
  - Pin the DuckDB session `TimeZone` to UTC.
  - Do not use `fetchall` on `TIMESTAMPTZ`, or add `pytz`.
  - Use one open result per connection. Prefer relations and `to_arrow_*`.
- **P0-P-3, the writer: stay on psycopg `Copy.set_types`.**
  - It is lossless on every case here, given an identity `dumps` for JSON text, `Decimal` for
    NUMERIC and a UTC cast before `to_pylist`.
  - pgpq preserves JSONB, JSON text and `timestamptz` instants. But it cannot write NUMERIC without a
    text staging table and a server-side cast. With that, it is lossless.
  - Adopt pgpq only if a measured writer cost calls for it, and then with the staging step.
  - The Alpha status and the missing timestamptz type stay as recorded (coordinator ruling 8).

## Q-1: Stage B (`p0q.stage-b`)

**Question.** Can a linkml 1.12.1 `PydanticGenerator` subclass, or an own emitter, over S4's
`core.yaml` produce the core shapes? The shapes are:
- discriminated `t`/`op` unions with a named recursive `Condition`;
- `MISSING` defaults (pydantic 2.14.1);
- frozen models with tuples;
- both `ci:form` variants;
- prefixed aliases.

The probe also asks how the result differs from `values.py` and `batch.py`, whether S4's 135 batches
validate alike, and whether the JSON Schemas equal `core/schemas/*.json` byte for byte.

**Method.**
- **The model.** `code/q1_build.py` patches a copy of S4's `core.yaml` with `code/q1/model_patch.yaml`,
  writing `results/q1/schema/core_stage_b.yaml`, which lints with 0 errors. The patch adds:
  - the condition node classes;
  - the batch items, evidence, a qualifiers class (`extra_slots` for schema qualifiers) and the
    envelope;
  - types and enums;
  - an `Expression` base for `Formula` and `SetExpr` (S4 had `SetExpr is_a Formula`);
  - typed interval bounds;
  - a declaration order that matches the hand unions.
- **The generator.** `code/q1/stage_b.py` subclasses `PydanticGenerator`. It keeps `render()`'s
  pipeline and the template machinery, with `template_dir` overrides in `code/q1/templates`: a frozen
  `CoreModel` base, PEP 695 `type` aliases, explicit `Field` sources. It overrides `_get_classes`,
  `generate_class`, `generate_slot`, `get_class_slot_range` and `before_generate_enums`. A
  form-expansion plan over `SchemaView` reads `ci:form`, `ci:required_in` and `ci:stored_range`: a
  class whose fields, ranges or members differ by form is emitted as `Authored…` and `Stored…`.
- **Behaviour.** Behaviour stays hand-written in `code/q1/hooks.py`, called through a proposed
  `ci:validator`. Spans and `scope_segment` presence are generated from `ci:invariant`.
- **The comparison.** `code/q1_stage_b.py` compares the generated module
  (`results/q1/generated/core_shapes.py`) with the product's hand shapes, imported read-only. It
  checks:
  - per class: field annotation, default, alias, `exclude_if`, order, config, bases and validators;
  - the union aliases;
  - the JSON Schemas, rendered with the product's `CoreJsonSchema`;
  - S4's 135 batches, as written, after S4's V1/V2 canonicalization and, for the stored batches,
    after a probe-local prefix migration (S4's batches predate the X2 prefixed-name ruling). Verdicts,
    `(loc, type)` error sets and dumps are compared;
  - 12 seeded errors;
  - stock `gen-pydantic` over the same schema, for contrast.

**Result (Tested, 2026-10-28; linkml 1.12.1, pydantic 2.14.1, Python 3.14.10).**
- **Every named feature is present** (12/12):
  - `AuthoredCondition`/`StoredCondition` are named `$defs` entries, discriminated on `op`;
  - the value unions are discriminated on `t`;
  - `MISSING` defaults are absent from dumps;
  - models are frozen with `extra="forbid"`, and sequences are tuples;
  - both forms are generated, with stored-only fields;
  - the stored qualifiers carry `core:` aliases (`validate_by_alias`, `serialize_by_alias`), and
    default modality and polarity are excluded from dumps.
- **The four union aliases are identical to the hand ones.** 35 of 45 classes are structurally equal.
- **The other 10 classes differ in three ways:**
  - the hand private bases `_Batch`, `_Claim`, `_Entity`, `_Qualifiers` and `_Span` are flattened.
    Their methods become functions: `_Batch.local_refs()` is used by tests;
  - `AuthoredQualifiers` field order is an artifact of the hand inheritance, and no single
    declaration order reproduces both forms' hand orders;
  - `NumberValue` uses a `pattern` instead of the hand canonical-decimal validator. The verdicts agree,
    but the error type changes (`string_pattern_mismatch` against `value_error`) and the "write '…'"
    suggestion is lost, unless the hand validator stays and the pattern becomes schema-only.
- **`CitationFrame` and `FrameEntry` stay hand-written** (a `RootModel` with methods).
- **Batches.** 300 validations of the 135 batches: verdicts and error sets agree in 300 of 300. The
  137 valid validations have identical dumps (17 authored, plus 120 stored after the prefix migration).
- **Seeded errors.** Both model sets reject all 12. The error sets are equal in 11; the twelfth is the
  number case above.
- **JSON Schemas.** 0 of 6 files are byte-equal: the committed descriptions are hand docstrings,
  which the model does not hold. Without descriptions:
  - 5 of 6 files are equal;
  - `batch.authored` is equal only key-order-insensitively, because of the qualifiers' property order.
- **Stock `gen-pydantic`** emits 0 discriminators, 0 `MISSING` and no tuples. It produces one class per
  model class, with both forms' fields optional.
- **Regeneration** is byte-identical.

**Interpretation.**
- **The variant is feasible.** The subclass works, but most of the work is the overridden class and
  slot generation plus the form expansion. It is close to an own emitter hosted in the generator,
  using the generator for orchestration and templates. An own emitter over `SchemaView` is the
  equivalent alternative and was not built.
- **Declarations needed beyond TM §4:**
  - the item and condition classes in `core` (TM §2 already places them there);
  - `ci:py_type` on types, for the min-length strings LinkML cannot state and for the `CITATION`
    marker;
  - `ci:validator` for hand behaviour;
  - `ci:py_name` or model renames (`SetExpr`→`SetValue`, `PhraseValue`→`Phrase`, `AndNode`→`And`, …).

  Whether the committed schema descriptions come from the model is a choice for M5.

**Feeds.** P0-M-5 (M5's variant): Stage B, with the residue above.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 6 current, 0 superseded.


**Phase 0 model probes**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Validating a pydantic-settings BaseSettings reads the environment](records/p0q.settings-env.json) | P0-F-5 | passed | coordinator decision 26, foundations §3.5 operations models, foundations §3.9 | 2026-10-28 |
| [Same-run composite FKs and per-version vocabulary FKs at run scale, with the s6.volume rerun on 18/corpus](records/p0q.fk-cost.json) | P0-F-Q4 | passed | P0-F-Q4, INV-03 and INV-08 enforcement placement (model-and-projections §3.4, foundations §3.8), D3 §11 pending rerun, ADR-0021 variants | 2026-10-28 |
| [Stage B: the core shapes generated by a PydanticGenerator subclass over S4's core.yaml](records/p0q.stage-b.json) | P0-M-Q1 | passed | P0-M-Q1, model-and-projections §3.3 Stage B or its fallback | 2026-10-28 |
| [Member properties on enum members: native in_subset versus a scalar ci:properties annotation](records/p0q.member-properties.json) | P0-M-Q2 | passed | P0-M-Q2, model-and-projections §3.1 member properties | 2026-10-28 |
| [Port check: MetaData generated from a LinkML sketch of five D3 tables plus an overlay, against S6's DDL; Alembic with a CreateView table](records/p0q.port-check.json) | P0-M-Q3 | passed | P0-M-Q3, model-and-projections §3.4 port check, model-and-projections §3.4 overlay/compiler split | 2026-10-28 |
| [Pool round trip: ADBC fetch_record_batch → DuckDB 2.0 → Arrow → psycopg Copy.set_types or pgpq](records/p0q.pool-roundtrip.json) | P0-P-Q5 | passed | P0-P-Q5, P0-P-1 loader route (pool-and-interchange §3.1), P0-P-3 writer and pgpq adoption (pool-and-interchange §3.4) | 2026-10-28 |
<!-- evidence-index:end -->
