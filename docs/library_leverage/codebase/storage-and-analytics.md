# Storage, publication and analytics

Opportunities in the physical model and migrations, protected publication, the typed-value codec,
analytical composition and inference. PostgreSQL 18 is the transactional authority; SQLAlchemy
MetaData/Core is the derived relational model; Arrow and DuckDB are derived only
([ADR-0024](../../adr/0024-semantic-release-preparation.md),
[ADR-0025](../../adr/0025-semantic-publication.md),
[ADR-0026](../../adr/0026-columnar-semantic-operations.md)). Baseline, scope and labels are in the
[README](README.md). Paths are relative to `python/corpus-structure/src/corpus_structure/` unless
they start with `python/` or `docs/`. Line numbers cite the reconciled tree at `f697233`.

Strengths that bound these opportunities:
- **Publication.**
  - A single SERIALIZABLE retry owner, with exact-receipt resolution of ambiguous commits
    (`semantic/publication.py`).
  - COPY runs on the SQLAlchemy connection's own psycopg driver.
  - The pgpq encoder asserts that the wire schema matches the protected staging layout.
- **Analytics.**
  - `pg_export_snapshot` plus a read-only ADBC import is sound, and literal binding is justified
    because COPY takes no parameters.
  - The decimal (HALF_EVEN) and float-hex boundaries in analytics are explicit policies, so these
    per-row loops are not opportunities. The original reason given, "Arrow refuses to rescale",
    was incomplete and was corrected on 2026-10-29 by the
    [library assessment](../libraries/pyarrow/README.md#applicability-cbo-015). `pc.round` does
    round decimals, but:
    - only within a bounded intermediate scale;
    - its errors fail the whole array;
    - pyarrow 26 decimal256 rounding returns wrong values on carry patterns.

    Separately, DuckDB rounds ties differently, and Arrow cannot parse hex floats.
- **Authored SQL** is admitted through a pglast visitor allowlist plus catalog checks under the
  restricted reader.
- **Store.** One psycopg-pool owner is lent to SQLAlchemy through `NullPool`. Claims use
  `FOR UPDATE SKIP LOCKED` with attempt and holder fences enforced natively.
- **Canonical forms.** `core/canonical.py` (NFC, refuses Decimals, truncated keys) and
  `semantic/identity.py` (no normalization, tagged decimals, full SHA-256) are *different*
  contracts. The legacy-only copies in `consolidate/assemble.py` and `pool/steps.py`, which only
  order JSON, retire with their callers.

<a id="cbo-008"></a>

## CBO-008 — The physical schema is written twice, drift is checked by column names, and the lowering lives in retiring code

**Label:** current; accepted planned for SP-10 "Physical evolution" and SP-09 retirement of the
legacy `schema` package. **Altitude:** subsystem.

**Operation and consumer.** Keep the frozen migration history consistent with the MetaData derived
from `model/semantic/physical.yaml`. Consumers are bootstrap, publication, query and analytics,
plus SP-10 controlled-revision evidence.

**Current mechanism.**
- **The schema is written twice.** `physical.yaml` compiles to the shared MetaData through
  `_compile_physical`, which lives in the legacy `schema/relational.py:604` and is imported by
  `semantic/metadata.py:18`. Every revision after 0001 then hand-freezes its DDL as SQL text, read
  and executed with `exec_driver_sql`. That text looks like the output of
  `CreateTable(...).compile()`, but no repository route generates it.
- **Comparison is configured but unused.** `semantic_alembic/env.py` already sets
  `compare_server_default=True` and the `checkconstraint_byname` autogenerate plugin. Nothing calls
  `compare_metadata` or `command.check` for the semantic history.
- **The drift test compares column names only.** `python/corpus-structure/tests/semantic/test_migrations.py:15-26`
  checks name sets per table. CHECK constraint names embed expression digests, so a by-name
  comparison would detect expression changes.
- **Structure is encoded as JSON strings.** Foreign keys, CHECK SQL and indexes are JSON text inside
  `ph:*` annotations (104 occurrences in `physical.yaml`). Some closed sets are written as SQL text
  rather than LinkML enums.

**Why it matters.**
- A migration with wrong types, nullability, foreign keys, CHECKs or indexes currently passes.
- SP-10 needs controlled-revision evidence; the test audit's
  [DTA-002](../../design_review/test-audit/execution-and-qualification.md#dta-002) records that no
  revision-pair route exists.
- SP-09's retirement of the legacy `schema` package must first extract the semantic lowering.

**Patterns.** [LOP-X002](../assessment-patterns.md#lop-x002), LOP-03 (Alembic comparison configured
but unused), LOP-10 (structure as JSON in annotations), [LOP-X001](../assessment-patterns.md#lop-x001)
(surviving lowering hosted in a retiring package).

**Preservation constraints.**
- ADR-0024: MetaData is derived.
- ADR-0025: frozen hand-reviewed SQL history; downgrade refused.
- Functions, triggers, grants and views live outside MetaData, so any comparison needs
  `include_object` filters.
- Repository rule: no new *alignment* lint. A physical-evolution check is a functional obligation;
  that reading should be confirmed when one is proposed.

**Counterevidence.**
- The frozen history is deliberate.
- Runtime constraint checks already catch some drift.
- The legacy store has a richer precedent: catalog diff plus `alembic check`, with its blind spots
  documented.

**Research leads.** [alembic](../../libraries/alembic.md): `compare_metadata`, `command.check`,
`produce_migrations`. [sqlalchemy](../../libraries/sqlalchemy.md): DDL compiler.
[linkml](../../libraries/linkml.md): structured annotation values.

**Questions for library research.**
1. Does `compare_metadata` against a head-migrated database come back clean, or explainable, today?
2. Can `CreateTable`/autogenerate emit the next frozen revision for review?
3. Does linkml-runtime 1.12 load nested annotation values?

**Library assessment (2026-10-29).** Premise corrected. Functions, triggers and grants do not need `include_object`, because Alembic never reflects them, so `command.check` proves table structure only. Partial-index predicates and views are further blind spots, and whether the check is clean at head is unsettled. SQLAlchemy `CreateTable` is the deterministic emitter ([alembic](../libraries/alembic/README.md#applicability-cbo-008)).

<a id="cbo-014"></a>

## CBO-014 — The protected transport routine is copied by hand into each revision; its generator is stale

**Label:** current; accepted planned (SP-08 intervention publication may add staged relations).
**Altitude:** shared mechanism.

**Operation and consumer.** Deploy the definer-owned `begin_stage` / `publish_batch` / `end_stage`
transport for each set of staged relations.

**Current mechanism.**
- `semantic/routines.py` contains a transport generator (`_transport_sql`, `deploy_routines`). Its
  only call is internal (`routines.py:113`); nothing in `src`, tests or migrations calls
  `deploy_routines`.
- Its template `semantic/sql/publication.sql` has drifted from the head transport.
- Five revisions each freeze a full hand copy of the transport: `semantic_0016`, `0017`, `0021`,
  `0024` and `0027`, 1,069 lines in all. Successive copies differ in per-relation create, verify,
  insert and drop lines.
- A recent repair (`51bba6c`) added disposal guards only to the two newest relations.

Adding one staged relation touches:
- a row dataclass, a `PublicationBatch` field and the row-type table (`semantic/publication.py`);
- the analytics `SPINE` (`semantic/analytics.py:51`);
- `physical.yaml`;
- DDL SQL;
- the transport SQL.

**Patterns.** [LOP-X002](../assessment-patterns.md#lop-x002), LOP-02, LOP-11 (stale generator).

**Preservation constraints.**
- Frozen, reviewed SQL (ADR-0025).
- Per-relation semantic inserts.
- Staging ownership and shape checks.

**Counterevidence.**
- The native verify block refuses a mismatched staging shape at publish time, so drift fails loudly
  at run time.
- The guards limited to the newest relations may be intentional divergence.

**Research leads.** No new library is needed beyond the SQLAlchemy DDL compiler and `psycopg.sql`.

**Questions for library research.**
1. Can one repository-owned generator, fed by MetaData and `STAGE_TYPES`, emit the next frozen
   transport file and the row types?
2. Which per-relation differences are intended?

**Library assessment (2026-10-29).** `STAGE_TYPES` already derives column types from MetaData. `CreateTable` reproduced the frozen 0027 `CREATE TABLE` text exactly (probe) ([sqlalchemy](../libraries/sqlalchemy/README.md#applicability-cbo-014)).

<a id="cbo-015"></a>

## CBO-015 — The typed-value codec is spread across encode, decode and meaning sites

**Label:** current; SP-08 consumers decode values. **Altitude:** several modules.

**Operation and consumer.** Convert typed values between release instances, staged rows, Arrow
columns and canonical meaning. Consumers are consolidation, inference, query, analytics, identity
and observations.

**Current mechanism.**
- **Encode:** `semantic/consolidation.py` and inference.
- **Python decode:** the query value reconstruction.
- **Arrow decode:** analytics.
- **Python meaning:** `semantic/identity.py:36` `_meaning`.
- **Native meaning and identity:** `semantic/sql/identity.sql` and migration functions.
- **Float hex encoding:** `semantic/observations.py:87`.
- **A detail worth examining:** decimals are encoded with `str(raw)` (`consolidation.py:137`), which
  can produce exponent forms, while native code canonicalizes.

The Python and native copies are a *deliberate* mirror across the enforcement boundary: the
database recomputes identity rather than trusting the writer. The test audit
([DTA-011](../../design_review/test-audit/evidence-and-discrimination.md#dta-011)) found that this
mirror is checked only by agreement between the two sides, with no pinned vectors.

**Why it matters.** Each SP-08 consumer that decodes values adds another copy on the application
side. Exponent-form decimals or float edge cases are where copies diverge.

**Patterns.** [LOP-X003](../assessment-patterns.md#lop-x003), LOP-09.

**Preservation constraints.**
- Native recomputation as the ADR-0025 trust boundary.
- The existing hand-picked parity vectors.
- Exact decimals and Unicode 16 casefold.

**Counterevidence.** Consolidating across the boundary would remove the protection. The leverage is
one specification, generated conformance testing and removing the extra copies on the application
side.

**Research leads.** [hypothesis](../../libraries/hypothesis.md): property or differential testing
of Python against native implementations; it is already a root dev dependency.

**Questions for library research.**
1. Can one Python codec per value kind serve encode, decode and Arrow normalization?
2. Can native parity be tested generatively, with pinned independent vectors to catch coordinated
   changes?

**Library assessment (2026-10-29).** Per-row Arrow loops are confirmed required, for corrected reasons: bounded intermediate scale, carry overflow and whole-array errors. pyarrow 26 decimal256 `pc.round` also returns wrong values on carry patterns. Hypothesis differential parity against native functions fits with conditions ([pyarrow](../libraries/pyarrow/README.md#applicability-cbo-015), [hypothesis](../libraries/hypothesis/README.md#applicability-cbo-015)).

<a id="cbo-018"></a>

## CBO-018 — DuckDB composition renames relations by regex and imports private legacy kernels

**Label:** current; SP-09 retires `pool`. **Altitude:** local.

**Operation and consumer.** Bind operation projections into one DuckDB scope and run the shared
disagreement and view kernels. Consumers are consolidation and domain decisions.

**Current mechanism.**
- `_compose` (`semantic/analytics.py:697`) rewrites relation names in SQL text with `re.sub`
  (`:714`).
- `operation_disagreements` and `views` import the private `_DISAGREEMENTS`, `_APPLIES`, `_SPECS`
  and `_VIEWS` from the legacy `pool.duckdb_engine` (`:673`, `:757`). `ViewSpec` comes from
  `pool.steps`.

**Why it matters.** Retiring `pool` breaks surviving analytics. Text rewriting is fragile as SQL
grows.

**Patterns.** [LOP-X001](../assessment-patterns.md#lop-x001), LOP-10, LOP-11.

**Counterevidence.** Current relation names are distinctive, so collision exposure is low.

**Research leads.** [duckdb_2](../../libraries/duckdb_2.md): replacement scans and
`query_table()`, table macros, a schema per operation with `search_path`, relation `query()`.

**Question for library research.** Which DuckDB binding mechanism gives scoped names without
rewriting SQL text, and where should these kernels live before `pool` is retired?

**Library assessment (2026-10-29).** DuckDB 2.0 `relation.query` (call-scoped name) and temporary table macros with `query_table` parameters bind per-operation inputs without rewriting SQL text (probe) ([duckdb](../libraries/duckdb/README.md#applicability-cbo-018)).

<a id="cbo-019"></a>

## CBO-019 — Native value meaning is recomputed by every consumer, and each publish revalidates the whole realization

**Label:** current; execution behaviour under SP-09/SP-10. **Altitude:** shared mechanism.

**Operation and consumer.** Derive canonical value meaning and qualification keys. Consumers are
publication, analytical capture and inference.

**Current mechanism.**
- `data.value_meaning` is recursive PL/pgSQL.
- The head `publish_batch` loops over every admitted fact of the realization on each publish,
  recomputing `fact_identity` per row
  (`python/corpus-structure/semantic_alembic/versions/semantic_0027_transport.sql:153`).
- Analytical capture recomputes `qualification_key` per fact (`semantic/analytics.py:303`).
- Inference references `value_meaning` three times in one statement.
- Admitted value graphs are guarded as immutable (`semantic_0027_transport.sql:99`), so a meaning
  key could be computed once.

**Patterns.** LOP-07, LOP-04 (row-by-row PL/pgSQL), LOP-09.

**Preservation constraints.**
- Fact identity rules.
- Meaning computed natively at the trust boundary.
- Unicode 16 casefold.

**Counterevidence.**
- Few batches reach each realization (one consolidation batch plus one inference batch), so
  whole-realization revalidation is roughly linear in practice.
- The recheck may be a deliberate defence whose premise should be confirmed.

**Research leads.** Native PostgreSQL only: a meaning-key column persisted at protected
publication, or delta-only checks with statement-level triggers and transition tables.

**Questions for library research.**
1. Does any admitted meaning depend on mutable state?
2. Would a persisted key serve inference, capture and SP-08 conflict grouping together?

**Library assessment (2026-10-29).** Generated columns are ruled out. The staged `pg_temp.sp_*` relations already are the delta, so transition-table triggers are unnecessary. The decisive premise is that `sem.*` rows read by qualified meaning are not trigger-enforced immutable ([postgresql](../libraries/postgresql/README.md#applicability-cbo-019)).

<a id="cbo-022"></a>

## CBO-022 — Inference runs a naive fixed point

**Label:** current; accepted planned (SP-09 derive step). **Altitude:** local.

**Operation and consumer.** Derive qualified conclusions within the finite rule profile, with direct
proofs.

**Current mechanism.**
- A `while True` loop (`semantic/inference.py` around `:140`) re-runs every rule over the full work
  table, including a full transitive self-join, until nothing is inserted.
- Proof extraction then re-joins and loops in Python.

**Patterns.** LOP-01 (semi-naive evaluation), LOP-04.

**Preservation constraints.**
- The finite qualified profile and context equality.
- Direct proofs only, with deterministic representative choice.
- [ADR-0027](../../adr/0027-bound-domain-operations.md): no generalized inference engine.
- linkml-datalog is deferred until inference must go beyond the finite qualified SQL profile.

**Counterevidence.** Work sets are small for the current profile, and correctness with mixed rule
kinds must hold.

**Research leads.** Native semi-naive delta tables, or `WITH RECURSIVE` per linear stratum;
[linkml-datalog](../../libraries/linkml-datalog.md) only as the deferred trigger.

**Question for library research.** Does a delta-driven loop keep identical conclusions and proofs?

**Library assessment (2026-10-29).** A semi-naive delta-table loop reaches the same least fixpoint, with identical conclusions and proofs. A single `WITH RECURSIVE` is ruled out, because the transitive rule is a non-linear self-join ([postgresql](../libraries/postgresql/README.md#applicability-cbo-022)).

## Minor observations (not standalone opportunities)

- **Retry SQLSTATEs.** The SERIALIZABLE retry SQLSTATE literals are duplicated between
  `semantic/publication.py` and `core/db/store.py`. The two owners deliberately differ: receipt
  lookup on a lost connection versus task retry and fencing.
- **Conflict mapping.** SQLSTATE `P0004` is mapped to a conflict in about seven places
  (`semantic/operations.py`, `semantic/arrow_publication.py`).
- **Read-only sessions.** `query.py` issues `SET TRANSACTION READ ONLY` by hand, although
  SQLAlchemy offers a `postgresql_readonly` execution option.
- **Arrow publication identity.** Arrow publication computes its content identity row by row. The
  exact-bytes receipt contract (ADR-0025) needs one canonical JSON on both sides, so the loop is not
  an opportunity by itself.
