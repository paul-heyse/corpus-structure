# Library applicability assessments

This collection holds contextual briefings and focused library capability knowledge that grew out of
[codebase opportunities](../codebase/README.md). It is maintained by the
[library assessment skill](../../../.claude/skills/leverage-library-assessment/SKILL.md) under the
[framework](../library-leverage-framework.md), using the [base patterns](../patterns.md), the
[additional assessment patterns](../assessment-patterns.md), the
[shared vocabulary](../references/shared-language.md) and the
[writing guidance](../references/collection-writing.md).

Each library's account keeps two kinds of material apart:
- **Reusable opportunity types** are repository-agnostic. They are retained even when they have no
  current match.
- **Applicability** is a contextual judgment, made at a stated revision, of whether the type fits a
  named opportunity.

Neither is a comparative preference. Choosing between options belongs to
[comparative reviews](../reviews/README.md).

## Library-led briefings

The optional [discovery skill](../../../.claude/skills/leverage-library-discovery/SKILL.md)
maintains one briefing per investigated family. A briefing records representative local uses,
capability territory and proposed research priorities at an inspected baseline. The
[discovery and evidence guide](../references/discovery-and-evidence.md) defines its evidence
and output. The first pilot is the [PostgreSQL typed-domain discovery](postgresql/briefing.md)
(2026-11-09): nine libraries, seven responsibility topics and complete overview coverage. It has
its own baseline and does not refresh the October applicability judgments below.

<a id="baseline"></a>

## Inspected baseline

| | |
|---|---|
| Codebase account consumed | publication `d739b88` (CBO-001…024; source reconciled through `f697233`) |
| Source baseline | `d739b88`, captured 2026-10-29T14:32-04:00 with a clean tree. Researchers read the live tree through `6b2335a`/`3d97504`. Concurrent SP-08 commits `7cfd7f8`, `f40a9c4` and `9c04975` landed during reconciliation; where they bear on a conclusion, the conclusion says so. They were not reassessed in full |
| Library realizations | the installed versions recorded in `uv.lock`, named on each library page |
| Date | 2026-10-29 |
| Criteria | framework 0.2; base patterns 0.2; additional patterns LOP-X001–X007, revised by this pass |
| Method | Six read-only library researchers each read their assigned [overviews](../../libraries/README.md) end to end, then followed up through Context7, primary documentation, GitHub at the installed tag and the installed `.venv` source. The coordinator researched DuckDB 2.0 personally, because Context7 lacks v2. Pure-Python probes ran only where documentation and source left a consequential question open: no database connections, no installs. The coordinator verified the decisive source line or probe output behind every "fits" conclusion and every negative result |
| Kind | First assessment; there is no preceding account |
| Publishing commit | the commit that adds this account |

**Operator direction (2026-10-29).** Prioritize the libraries the project actually uses, especially
the major ones likely to address the audit's opportunities. Libraries that are not adopted get light
treatment, and only where an opportunity points squarely at them.

## Protobuf ecosystem extension assessment

The [2026-11-03 protobuf assessment](protobuf-ecosystem_2026-11-03.md) covers reusable runtime,
validation, descriptor, RPC and research capabilities plus contextual applicability. It has its
own baseline and does not refresh the older assessments below.

## Researched libraries

| Library | Realization | Tier | Account | Probe evidence |
|---|---|---|---|---|
| SQLAlchemy | 2.1.5 | adopted, major | [sqlalchemy](sqlalchemy/README.md) | [relational](../../design_review/evidence/2026-10-29_library-leverage-relational/README.md) |
| psycopg / psycopg-pool | 3.3.6 / 3.3.3 | adopted, major | [psycopg](psycopg/README.md) | relational |
| PostgreSQL (native) | 18 | adopted, major | [postgresql](postgresql/README.md) | [postgres-migrations](../../design_review/evidence/2026-10-29_library-leverage-postgres-migrations/README.md) |
| Alembic | 1.20.0 | adopted, major | [alembic](alembic/README.md) | postgres-migrations |
| LinkML / linkml-runtime | 1.12.1 | adopted, major | [linkml](linkml/README.md) | [linkml](../../design_review/evidence/2026-10-29_library-leverage-linkml/README.md) |
| Pydantic | 2.14.1 | adopted, major | [pydantic](pydantic/README.md) | [pydantic](../../design_review/evidence/2026-10-29_library-leverage-pydantic/README.md) |
| DuckDB | 2.0.0 (held) | adopted, major | [duckdb](duckdb/README.md) | [duckdb](../../design_review/evidence/2026-10-29_library-leverage-duckdb/README.md) |
| pyarrow | 26.0.0 | adopted, major | [pyarrow](pyarrow/README.md) | [arrow](../../design_review/evidence/2026-10-29_library-leverage-arrow/README.md) |
| FastMCP | 4.1.3 | adopted, major | [fastmcp](fastmcp/README.md) | [interfaces](../../design_review/evidence/2026-10-29_library-leverage-interfaces/README.md) |
| rule-engine | 5.1.0 (pinned) | adopted, major | [rule-engine](rule-engine/README.md) | interfaces |
| pydantic-settings | 2.16.1 | adopted | [pydantic-settings](pydantic-settings/README.md) | pydantic |
| cattrs | 26.2.1 | adopted | [cattrs](cattrs/README.md) | — |
| adbc-driver-postgresql | 1.13.0 | adopted | [adbc-driver-postgresql](adbc-driver-postgresql/README.md) | arrow |
| Typer | 0.27.3 | adopted | [typer](typer/README.md) | — |
| Hypothesis | 6.170.12 | adopted (dev) | [hypothesis](hypothesis/README.md) | postgres-migrations |
| pytest | 9.2.0 | adopted (dev) | [pytest](pytest/README.md) | postgres-migrations |
| oaklib / linkml-term-validator | 0.7.4 / 0.4.5 | adopted, low pivot priority | [oaklib](oaklib/README.md) | — |
| curies | 0.15.5 | transitive, light | [curies](curies/README.md) | linkml |
| pytest-postgresql | 9.1.1 | not adopted, light | [pytest-postgresql](pytest-postgresql/README.md) | — |

<a id="types"></a>

## Reusable opportunity types

No type has been retired. Every type is retained whether or not it currently matches an opportunity.

| Handle | Need it serves | Current matches |
|---|---|---|
| [`sqlalchemy/composable-predicate-lowering`](sqlalchemy/README.md#sqlalchemy-composable-predicate-lowering) | Validated filters reach SQL predicates | CBO-001 |
| [`sqlalchemy/array-membership-binding`](sqlalchemy/README.md#sqlalchemy-array-membership-binding) | Unbounded key sets without parameter explosion | CBO-001, CBO-020 |
| [`sqlalchemy/recursive-closure`](sqlalchemy/README.md#sqlalchemy-recursive-closure) | Database-side reachability | CBO-001, CBO-020 |
| [`sqlalchemy/streamed-core-results`](sqlalchemy/README.md#sqlalchemy-streamed-core-results) | Large reads within one snapshot | CBO-001 |
| [`sqlalchemy/transaction-characteristics`](sqlalchemy/README.md#sqlalchemy-transaction-characteristics) | Isolation and read-only without hand SQL | CBO-001 |
| [`sqlalchemy/ddl-text-emission`](sqlalchemy/README.md#sqlalchemy-ddl-text-emission) | Deterministic DDL text from MetaData | CBO-014, CBO-008 |
| [`psycopg-pool/sqlalchemy-delegated-pool-per-login`](psycopg/README.md#psycopg-pool-sqlalchemy-delegated-pool-per-login) | Several authenticated logins behind SQLAlchemy | CBO-004 |
| [`psycopg/offline-sql-composition`](psycopg/README.md#psycopg-offline-sql-composition) | Composing SQL that cannot take parameters | CBO-014 |
| [`psycopg/sqlstate-error-classes`](psycopg/README.md#psycopg-sqlstate-error-classes) | Error classification by SQLSTATE | retry and `P0004` notes |
| [`postgresql/template-database-clone`](postgresql/README.md#postgresql-template-database-clone) | Fresh databases at a prepared state | CBO-010 |
| [`postgresql/recursive-fixpoint`](postgresql/README.md#postgresql-recursive-fixpoint) | Semi-naive fixed points in SQL | CBO-022, CBO-020 |
| [`postgresql/persisted-derived-key`](postgresql/README.md#postgresql-persisted-derived-key) | Derived keys computed once | CBO-019 |
| [`postgresql/privilege-isolation`](postgresql/README.md#postgresql-privilege-isolation) | Data isolation by role | CBO-006 |
| [`alembic/metadata-drift-check`](alembic/README.md#alembic-metadata-drift-check) | Migrations versus MetaData | CBO-008 |
| [`alembic/structured-diff-to-reviewed-artifact`](alembic/README.md#alembic-structured-diff-to-reviewed-artifact) | Change discovery and offline rendering | CBO-008 |
| [`alembic/programmatic-migration-lifecycle`](alembic/README.md#alembic-programmatic-migration-lifecycle) | Atomic upgrades, receipts, head checks | CBO-004, CBO-010 |
| [`pytest/outcome-reporting`](pytest/README.md#pytest-outcome-reporting) | Per-test outcomes, skip reasons, hangs | CBO-011 |
| [`hypothesis/route-profile-and-replay`](hypothesis/README.md#hypothesis-route-profile-and-replay) | Replayable generated cases | CBO-011 |
| [`hypothesis/differential-native-parity`](hypothesis/README.md#hypothesis-differential-native-parity) | Generative parity between Python and SQL | CBO-015 |
| [`pytest-postgresql/template-fixture-lifecycle`](pytest-postgresql/README.md#pytest-postgresql-template-fixture-lifecycle) | Template databases in pytest fixtures | CBO-010 (substantial conditions) |
| [`linkml-runtime/in-memory-import-closure`](linkml/README.md#linkml-runtime-in-memory-import-closure) | Multi-module schemas from bytes | CBO-002, CBO-021 |
| [`linkml-runtime/schemaview-lifecycle`](linkml/README.md#linkml-runtime-schemaview-lifecycle) | One induced schema shared by consumers | CBO-021 |
| [`linkml-runtime/type-chain-traversal`](linkml/README.md#linkml-runtime-type-chain-traversal) | Primitive, bounds and patterns from type chains | CBO-013, CBO-021 |
| [`linkml-runtime/reference-normalization`](linkml/README.md#linkml-runtime-reference-normalization) | In-document reference integrity (negative result) | CBO-017 |
| [`linkml-runtime/rdfc-canonical-serialization`](linkml/README.md#linkml-runtime-rdfc-canonical-serialization) | Byte-stable RDF for hashing | CBO-009 |
| [`linkml-runtime/structured-annotation-values`](linkml/README.md#linkml-runtime-structured-annotation-values) | Structured annotations rather than JSON strings | CBO-008 |
| [`curies/prefix-converter`](curies/README.md#curies-prefix-converter) | Closed prefix expansion and compaction | CBO-013 |
| [`linkml-term-validator/enum-expansion`](oaklib/README.md#linkml-term-validator-enum-expansion) | Dynamic enum composition | CBO-024 |
| [`oaklib/in-memory-pronto-adapter`](oaklib/README.md#oaklib-in-memory-pronto-adapter) | Ontology adapters from bytes | CBO-024 |
| [`pydantic/field-adapter-from-model`](pydantic/README.md#pydantic-field-adapter-from-model) | Per-field validators that keep model policy | CBO-013 |
| [`pydantic/presence-preserving-dump`](pydantic/README.md#pydantic-presence-preserving-dump) | Plain projections of explicitly set data | CBO-016, CBO-006 |
| [`pydantic/shared-defs-json-schema`](pydantic/README.md#pydantic-shared-defs-json-schema) | One JSON Schema across many models | CBO-003, CBO-013 |
| [`pydantic/annotated-marker-positions`](pydantic/README.md#pydantic-annotated-marker-positions) | Role positions by declared type | CBO-016 |
| [`pydantic/stdlib-dataclass-wire-adapter`](pydantic/README.md#pydantic-stdlib-dataclass-wire-adapter) | Wire validation for dataclass requests | CBO-001 |
| [`pydantic-settings/nested-section-resolution`](pydantic-settings/README.md#pydantic-settings-nested-section-resolution) | Typed nested process configuration | CBO-004 |
| [`cattrs/default-aware-structuring`](cattrs/README.md#cattrs-default-aware-structuring) | Absent optional collections become defaults | CBO-017 |
| [`duckdb/scoped-relation-binding`](duckdb/README.md#duckdb-scoped-relation-binding) | Operation-local inputs without SQL rewriting | CBO-018 |
| [`duckdb/parquet-export-with-metadata`](duckdb/README.md#duckdb-parquet-export-with-metadata) | Native Parquet export with identity metadata | CBO-007 |
| [`pyarrow/parquet-metadata-carriage`](pyarrow/README.md#pyarrow-parquet-metadata-carriage) | Schema and field metadata through Parquet | CBO-007 |
| [`pyarrow/exact-numeric-boundary`](pyarrow/README.md#pyarrow-exact-numeric-boundary) | Bounded decimal rounding and parsing (limits) | CBO-015 |
| [`pyarrow/ipc-owned-copy`](pyarrow/README.md#pyarrow-ipc-owned-copy) | Detaching tables from caller-owned memory | (sound existing use) |
| [`adbc-driver-postgresql/snapshot-consistent-capture`](adbc-driver-postgresql/README.md#adbc-driver-postgresql-snapshot-consistent-capture) | Multi-relation Arrow capture under one snapshot | CBO-007 |
| [`adbc-driver-postgresql/conninfo-connection`](adbc-driver-postgresql/README.md#adbc-driver-postgresql-conninfo-connection) | Bulk connection from libpq conninfo | CBO-007, CBO-004 |
| [`fastmcp/tool-refusal-translation-middleware`](fastmcp/README.md#fastmcp-tool-refusal-translation-middleware) | One place for refusal-to-`isError` mapping | CBO-012 |
| [`fastmcp/response-size-backstop`](fastmcp/README.md#fastmcp-response-size-backstop) | Lossy result size backstop | CBO-012, CBO-001 |
| [`fastmcp/sync-tool-execution-context`](fastmcp/README.md#fastmcp-sync-tool-execution-context) | Thread on which tools run | CBO-023 |
| [`fastmcp/bound-tool-input-schema`](fastmcp/README.md#fastmcp-bound-tool-input-schema) | Runtime-computed tool input schemas | CBO-012 |
| [`typer/central-exception-exit-mapping`](typer/README.md#typer-central-exception-exit-mapping) | Exception-to-exit mapping (negative result plus routes) | CBO-012 |
| [`typer/command-tree-resource-scope`](typer/README.md#typer-command-tree-resource-scope) | Resources tied to a command's lifetime | CBO-004 |
| [`rule-engine/typed-schema-from-python-types`](rule-engine/README.md#rule-engine-typed-schema-from-python-types) | Rule types from Python types | CBO-005 |
| [`rule-engine/logical-view-over-physical-records`](rule-engine/README.md#rule-engine-logical-view-over-physical-records) | Stable rule vocabulary over changing records | CBO-005 |
| [`rule-engine/compile-time-rule-introspection`](rule-engine/README.md#rule-engine-compile-time-rule-introspection) | Checks after compilation (negative result) | CBO-005 |

<a id="applicability"></a>

## Applicability by opportunity

Each conclusion is one of *fits*, *fits with conditions*, *ruled out for this context*, or
*unsettled*. These conclusions record capability fit only. They are not preferences between options.

| CBO | Conclusion (library parts) | Routes |
|---|---|---|
| [CBO-001](../codebase/consumers-and-operations.md#cbo-001) | Fits with conditions. Core predicates, set-oriented explain and the read-only option fit. Three exact-lowering gaps are recorded. Response budgets and continuation stay with the application. SP-08 `7cfd7f8` adopted a Core recursive closure in `serve/read.py` | [sqlalchemy](sqlalchemy/README.md#applicability-cbo-001), [pydantic](pydantic/README.md#applicability-informs), [fastmcp](fastmcp/README.md#applicability-cbo-001) |
| [CBO-002](../codebase/release-preparation.md#cbo-002) | Fits with conditions. importmap composition works, but duplicate refusal, missing-import refusal and URI materialization remain owned. The premise is updated: `regeneration.prepare_pack` now composes | [linkml](linkml/README.md#applicability-cbo-002) |
| [CBO-003](../codebase/release-preparation.md#cbo-003) | The shared-`$defs` capability fits, but changing the archive is a design decision. A verification record is sound only under `sem.*` immutability | [pydantic](pydantic/README.md#applicability-cbo-003), [postgresql](postgresql/README.md#applicability-cbo-003) |
| [CBO-004](../codebase/engineering-workflows.md#cbo-004) | Fits with conditions. A pool and engine per login; `NullConnectionPool` behind SQLAlchemy is ruled out at 3.3.3; the publisher is NOLOGIN. The premise is updated by `connection_settings` (`3d97504`). Whether "one pool per process" means one per login needs interpreting | [psycopg](psycopg/README.md#applicability-cbo-004), [pydantic-settings](pydantic-settings/README.md#applicability-cbo-004), [alembic](alembic/README.md#applicability-cbo-004), [typer](typer/README.md#applicability-cbo-004), [adbc](adbc-driver-postgresql/README.md#applicability-cbo-004) |
| [CBO-005](../codebase/consumers-and-operations.md#cbo-005) | The logical rule-view rebase fits with conditions. Deriving rule types from Pydantic is ruled out at 5.1.0. No public AST traversal exists. View nullability is part of the archived contract | [rule-engine](rule-engine/README.md#applicability-cbo-005) |
| [CBO-006](../codebase/consumers-and-operations.md#cbo-006) | Unsettled. Pydantic is not the decisive lever (a LOP-X001 decision). Privilege isolation is being implemented concurrently, with residuals recorded | [pydantic](pydantic/README.md#applicability-cbo-006), [postgresql](postgresql/README.md#applicability-cbo-006) |
| [CBO-007](../codebase/consumers-and-operations.md#cbo-007) | Fits with conditions, by either DuckDB `COPY … KV_METADATA` or pyarrow writers. DuckDB drops Arrow metadata. The ADBC connection premise is corrected. SP-08 `7cfd7f8` adopted the pyarrow plus `connection_settings` route | [duckdb](duckdb/README.md#applicability-cbo-007), [pyarrow](pyarrow/README.md#applicability-cbo-007), [adbc](adbc-driver-postgresql/README.md#applicability-cbo-007) |
| [CBO-008](../codebase/storage-and-analytics.md#cbo-008) | Fits with conditions, for tables only. Functions, grants, partial-index predicates and views are blind spots. Whether the check is clean at head is unsettled. `CreateTable` is the deterministic emitter | [alembic](alembic/README.md#applicability-cbo-008), [sqlalchemy](sqlalchemy/README.md#applicability-cbo-008), [linkml](linkml/README.md#applicability-cbo-008) |
| [CBO-009](../codebase/release-preparation.md#cbo-009) | Fits with conditions. The determinant set is now classified (bytes, acceptance, vocabulary), and pronto is missing from it. It remains a deliberate constant | [linkml](linkml/README.md#applicability-cbo-009) |
| [CBO-010](../codebase/engineering-workflows.md#cbo-010) | The native template fits with conditions, but **the database ACL must be replayed after cloning**. pytest-postgresql fits only with substantial conditions | [postgresql](postgresql/README.md#applicability-cbo-010), [pytest-postgresql](pytest-postgresql/README.md#applicability-cbo-010), [alembic](alembic/README.md#applicability-cbo-010) |
| [CBO-011](../codebase/engineering-workflows.md#cbo-011) | Fits with conditions. JUnit plus `-r` give outcomes and skip reasons. pytest-timeout's `signal` method conflicts with `SIGALRM`. faulthandler-exit loses JUnit. A `--hypothesis-profile` route gives replay | [pytest](pytest/README.md#applicability-cbo-011), [hypothesis](hypothesis/README.md#applicability-cbo-011) |
| [CBO-012](../codebase/consumers-and-operations.md#cbo-012) | Fits with conditions, through a custom middleware or decorator. The built-in `ErrorHandlingMiddleware` is wrong for this. The premise is partly stale after `3d97504` | [fastmcp](fastmcp/README.md#applicability-cbo-012), [typer](typer/README.md#applicability-cbo-012) |
| [CBO-013](../codebase/release-preparation.md#cbo-013) | Fits with conditions: per-field adapters on a root slot, `type_ancestors`, and curies with a wrapper. **A correctness gap was found:** `property_adapter` accepts NaN and infinity | [pydantic](pydantic/README.md#applicability-cbo-013), [linkml](linkml/README.md#applicability-cbo-013), [curies](curies/README.md#applicability-cbo-013) |
| [CBO-014](../codebase/storage-and-analytics.md#cbo-014) | Fits with conditions. `CreateTable` reproduced frozen DDL exactly. The PL/pgSQL generator stays owned | [sqlalchemy](sqlalchemy/README.md#applicability-cbo-014), [psycopg](psycopg/README.md#applicability-cbo-014) |
| [CBO-015](../codebase/storage-and-analytics.md#cbo-015) | Hypothesis differential parity fits with conditions. Vectorized Arrow normalization is ruled out, so the per-row loops are confirmed. pyarrow 26 decimal256 rounding has a defect | [hypothesis](hypothesis/README.md#applicability-cbo-015), [pyarrow](pyarrow/README.md#applicability-cbo-015) |
| [CBO-016](../codebase/consumers-and-operations.md#cbo-016) | The plain projection fits (`model_dump` equals `_native`). The walkers fit with conditions: their policy stays owned | [pydantic](pydantic/README.md#applicability-cbo-016) |
| [CBO-017](../codebase/release-preparation.md#cbo-017) | `ReferenceValidator` is ruled out for integrity. Collection defaults through cattrs fit. Generators are unsettled | [linkml](linkml/README.md#applicability-cbo-017), [cattrs](cattrs/README.md#applicability-cbo-017) |
| [CBO-018](../codebase/storage-and-analytics.md#cbo-018) | Fits with conditions: `relation.query` and temporary table macros with `query_table`. Kernel relocation stays owned | [duckdb](duckdb/README.md#applicability-cbo-018) |
| [CBO-019](../codebase/storage-and-analytics.md#cbo-019) | Native fits with conditions, only if `sem.*` is made immutable by triggers. Generated columns are ruled out. Staging already supplies the delta | [postgresql](postgresql/README.md#applicability-cbo-019) |
| [CBO-020](../codebase/consumers-and-operations.md#cbo-020) | Fits with conditions, as a two-phase load. The premise is corrected: labels and keys are decoded globally, and `.in_` sets hit a parameter ceiling | [sqlalchemy](sqlalchemy/README.md#applicability-cbo-020), [postgresql](postgresql/README.md#applicability-cbo-003) |
| [CBO-021](../codebase/release-preparation.md#cbo-021) | Fits with conditions: one materialized schema, immutable by convention. `materialize_derived_schema` is ruled out | [linkml](linkml/README.md#applicability-cbo-021) |
| [CBO-022](../codebase/storage-and-analytics.md#cbo-022) | A delta-table loop fits. `WITH RECURSIVE` fits only per linear stratum | [postgresql](postgresql/README.md#applicability-cbo-022) |
| [CBO-023](../codebase/consumers-and-operations.md#cbo-023) | Settled by probe. Default sync tools run off the main thread; an async or inline tool runs on main | [fastmcp](fastmcp/README.md#applicability-cbo-023) |
| [CBO-024](../codebase/release-preparation.md#cbo-024) | The workaround is still needed: term-validator 0.4.5 is the latest release | [oaklib](oaklib/README.md#applicability-cbo-024) |

## Questions for comparative review

These are the most consequential questions for
[`leverage-opportunity-review`](../reviews/README.md). Each library page lists its own. The first
comparative review (2026-10-29) answers them in its [synthesis](../reviews/README.md#synthesis) and
[unsettled decisions](../reviews/README.md#unsettled).

1. **`sem.*` immutability (CBO-003, CBO-019).** Should `sem.*` and admitted value rows become
   immutable, enforced by triggers? That single premise decides whether a verification record or a
   persisted meaning key can replace re-verification, and whether the whole-realization recheck stays.
2. **Principals (CBO-004).** Is it one pool per login principal, `NullPool` with plain creators for
   one-shot commands, or an amendment to ADR-0025/D3? And should principals be flat URL fields or
   nested settings sections?
3. **Exports (CBO-007).** Should exports be written through pyarrow (now adopted in `serve/export.py`)
   or DuckDB `COPY … KV_METADATA`? Should they come from the whole-spine packet or the query path?
   Does any consumer need field-level metadata?
4. **Test harness (CBO-010).** Should it be a native head template with database-ACL replay or
   pytest-postgresql? Who owns the residue sweep, and what does the template key cover?
5. **Hang classification (CBO-011).** Is the qualification route faulthandler-exit plus "a missing
   JUnit file means failed", or per-test subprocesses?
6. **Rule view (CBO-005).** Should it be a logical view with OBJECT and accessors, direct `DataType`
   construction, or the current string notation? Is the authored vocabulary, including nullability,
   the frozen contract?
7. **Drift check (CBO-008).** Is a tables-only `command.check` a worthwhile functional SP-10
   obligation, or should evidence compare full catalog snapshots, including functions, grants and
   owners?
8. **Read boundary (CBO-001).** Does a closed, release-validated predicate vocabulary fall inside
   SP-08's ban on a new query language? Should predicates without an exact lowering refuse or answer
   unknown?

## Discoveries outside capability fit

These are reported to the operator. Their repair is not an assessment output.

- **Correctness gap (CBO-013).** `PreparedRelease.property_adapter` builds adapters without the
  model's config, so with `strict=True` it accepts NaN and infinity that the generated models refuse
  ([pydantic](pydantic/README.md#applicability-cbo-013)).
- **Library defect (pyarrow 26).** decimal256 `pc.round` silently returns wrong values on carry
  patterns ([pyarrow](pyarrow/README.md#pyarrow-exact-numeric-boundary)). The repository does not use
  that path today.
- **Security posture for the harness (CBO-010).** A cloned migrated template would re-grant TEMP to
  every role ([postgresql](postgresql/README.md#applicability-cbo-010)).
- **Migration-premise drift.** Revisions number 28, and a fourth role now exists that the semantic
  fixture does not check.

## Coverage and limits

- **Not assessed** beyond mentions: linkml-map and linkml-datalog (deferred dispositions, recorded as
  triggers only), jsonschema, pglast and valuesets (no opportunity needs their capabilities), and the
  `adbc_driver_duckdb` package.
- **No probes against a database.** Whether the drift check is clean at head (CBO-008), clone timing,
  ACL loss as observed behaviour, and snapshot import remain documented or source-level.
- **Context7 lagged** for SQLAlchemy 2.1, pytest 9.2 and rule-engine 5.1, and has no DuckDB 2.0
  coverage. Installed source was decisive in those cases.
- **Concurrent SP-08 work** (`7cfd7f8`, `f40a9c4`, `9c04975`) changes the premises of CBO-001,
  CBO-007 and CBO-012 after this baseline. The [codebase account](../codebase/README.md) should be
  refreshed before comparative review.

## Maintenance

- Refresh in place.
- Keep reusable types when their matches retire, and correct them deliberately.
- Remove an applicability section when its opportunity retires, carrying justified lessons into the
  type.
- The pivot coordinator and later plans own scheduling. Comparative reviews own preference.

## Unified-model focused refresh — 2026-11-01

The [semantic applicability](unified-model-semantics_2026-11-01.md) and
[typed/analytical applicability](unified-model-boundaries_2026-11-01.md) accounts cover all eleven
selected libraries at source `1cb8e620`. They supersede only the explicitly reexamined premises,
including current field adapters, shared reference traversal and metadata-derived Arrow. Other
October 29 accounts retain their dates. Comparative selection belongs to the
[principal target review](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md).

## PostgreSQL authoring followup — 2026-11-01

The [seven-library applicability account](unified-model-postgresql_2026-11-01.md) connects typed
domain calls, relational/native authoring, Alembic evolution and directional transport. It
consumes UM-20261101-r3 and preserves exact source/version limits; comparative preference is
in the revised unified-model principal review. Earlier assessments retain their original scope.
