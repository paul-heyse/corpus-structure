# PostgreSQL authoring and typed domain operations

**Source-inspected / Interface-checked, 2026-11-01; applications Proposed.** Source `f999ffcb`,
continuing diagnostic publication `54cd74cb` / UM-20261101-r3; core 3.3, heuristics 1.0,
code-intelligence 1.4. The [principal review](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md)
owns comparative selection. All seven PostgreSQL guides were read end to end, including addenda.
Concurrent PDF/model/native/SQL/test changes were preserved and distinguished from committed source.
Tests, probes, database mutation and dependency installation: **not_run**.

## Realizations and research route

Current pins/installed versions: SQLAlchemy 2.1.6, Alembic 1.20.1, pglast 8.7, Psycopg 3.3.6,
psycopg-pool 3.3.3, pgpq 0.12.0 and ADBC PostgreSQL 1.13.0. SQLGlot 30.27.0 is the guide/tagged
research candidate, absent from the current dependency manifest, lock and searched product source.
SQLAlchemy/Alembic guide main-body versions precede their addenda/current pins; development fixes
must not be credited to these pins.

Context7 first: `/sqlalchemy/sqlalchemy`, `/lelit/pglast`, `/tobymao/sqlglot`; relevant exact
installed interfaces and tagged SQLGlot source qualified consequential distinctions. Existing
PG-series exact-version transport research was reconciled with current source and corrected
guide addenda. Broader documented features retain their guide's evidence strength; a surveyed
feature is not a tested integration. Existing framework patterns suffice; no new pattern is added.

## Reusable capabilities and conditions

| Library | Complete capability families considered | Conditions / residual obligations |
|---|---|---|
| [SQLAlchemy](../../libraries/postgresql/sqlalchemy.md) | Core selects/joins/sets/recursive CTEs/lateral/windows/functions; DML/from-select/RETURNING/locks; MetaData/Inspector/DDL/views/CTAS; typed columns/results; types/comparators; syntax/compiler/traversal/cache extensions; ORM relationships/inheritance/hybrids/composites/collections/unit-of-work; loading/bulk/events/async/pooling. | Relational typing does not define domain identities or parameter signatures. ORM identity/loading/mutation and bulk bypass semantics must fit the actual aggregate. Native DDL generation differs from lifecycle comparison. Cache keys, NULL/defaults, RETURNING order and effect scope remain explicit. |
| [pglast](../../libraries/postgresql/pglast.md) | Native PostgreSQL 18 AST parsing and construction, JSON/Protobuf, visitors/rewrites, printers/deparser, source tokens/spans, referenced relations/fingerprints, PL/pgSQL inspection. | Stubs/runtime node checks do not supply analyzed catalog types or valid domain rows. Fingerprints collapse distinctions and are not semantic identity. PL/pgSQL parsing returns dictionaries; this is not complete typed procedural construction. SQL-standard bodies have a stronger structured route below. |
| [SQLGlot](../../libraries/postgresql/sqlglot.md) | Direct expression builders; dialect parsing/generation; Schema/MappingSchema, qualification/scopes/UDF typing; runtime annotate_types; relational rewrite/optimization; column lineage, AST diff, serialization/anonymization; JSONPath, custom dialects/rules and Python execution. | Supplied model/catalog coverage determines analysis. Runtime expression types are not static Python result types or PostgreSQL overload/ACL/collation semantics. Unsupported commands and lossy translation must fail explicitly. AST diff is not behavioral equivalence; Python execution is not PostgreSQL qualification. |
| [Alembic](../../libraries/postgresql/alembic.md) | Revision DAGs, structured Operations, reflection/comparison, operation-tree Rewriter, Plugin/custom comparator/operation/renderer, batch recreation, transaction/offline/programmatic/async hooks, native objects and PostgreSQL DDL options. | Detection, operation execution, rendering and reversibility are independent. Views/functions/triggers are not automatically compared merely because a DDL constructor exists. Renames/data transformations, same-name CHECK changes and some constraint/index families need explicit scope. Autocommit/concurrent DDL may change atomicity. |
| [Psycopg](../../libraries/postgresql/psycopg.md) | Binding/composition/template queries, preparation, cursor/row factories and static generics, custom adapters/types/composites/enums/ranges, row/block COPY, pipeline/batches, transactions/savepoints/TPC, pool/async/cancellation/notifications/libpq. | Row factories and adapters map representation; they do not prove projection or domain validity. Pipelines are not parallel transactions. Pool/session state and cancellation outcomes remain explicit. Notifications are not durable history; TPC is not a coordinator. |
| [pgpq](../../libraries/postgresql/pgpq.md) | Arrow/native encoder selection, explicit field encoders, schema/DDL helper, scalar/list/composite and JSON encodings, header/batch/footer ownership. | Encoder is not target schema/transaction authority. Wire ordering/type/nullability must match; unsupported Arrow forms must refuse. Whole batches are encoded before threshold emission. Errors can leave partial state: fresh encoder per stream, discard on failure. |
| [ADBC PostgreSQL](../../libraries/postgresql/adbc-driver-postgresql.md) | Arrow COPY reads, bound result queries/prepare/parameter schema, ingestion/create/append, OID/type resolution, catalog/statistics/result schema, C Stream/PyCapsule, clone/session/cancellation and driver discovery. | Bound results bypass COPY, ignore its batch hint and can execute lazily per bound row. Table-schema metadata lacks some typmods/nullability. Builtin resolver cannot decode arbitrary composites/custom types. Clone does not share transaction/temp state. Partition/Substrait interfaces are not supported merely by generic API presence. |

## Exact typing boundaries

Installed SQLAlchemy `sql/selectable.py:671–677` makes `with_cols` a static assertion returning
the same object without validation. `engine/base.py:1402–1417` propagates typed positional results
but accepts general execution parameter mappings. `engine/row.py:331–361` exposes `RowMapping`
values as `Any`. `sql/_annotated_cols.py:157–176` describes optional `__row_pos__` for whole-table
positional typing; current generator does not emit it. `GenericFunction[T]` types a scalar return,
not a domain argument signature. See [2.1 typing](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html).

Exact SQLGlot 30.27.0 [core](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/expressions/core.py)
accepts `**args: object` and stores `dict[str, Any]`; required argument flags are not schema-indexed
Python types. [annotate_types](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/optimizer/annotate_types.py)
executes at runtime. [Builders](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/expressions/builders.py)
accept already-built expressions, so SQL strings are not required to construct queries. Model
references and typed domain arguments can lower directly; their semantic/static contract must
remain at the domain boundary. pglast's generated stubs also have broad collection fields.

## Structured native function bodies: affirmative route

Installed pglast 8.7 `printers/ddl.py:1790–1848` prints `CreateFunctionStmt.sql_body` as an
`ast.ReturnStmt` or SQL-standard `BEGIN ATOMIC` statement sequence. This permits construction of
appropriate **LANGUAGE SQL** declarations and bodies from structured nodes, rather than an opaque
`AS` body string. The declaration printer is real capability, not proof of PostgreSQL execution,
equivalence or integration. See [printer](https://github.com/lelit/pglast/blob/v8/pglast/printers/ddl.py).

Current `semantic/native_inventory.py:20–26` requires one `AS` body and hashes its string;
`native_products.function_bodies` extracts that option. Accepting structured SQL bodies therefore
requires a deliberate versioned custody/catalog/admission change.
`native_objects.py:311–314` explicitly refuses catalog `prosqlbody` today. Definition-time dependency
binding, name resolution, replacement behavior and `pg_get_functiondef` normalization must be
qualified. It is not safe to relabel all PL/pgSQL as a single relational expression.

## Current contextual matches

Paths below are relative to `python/corpus-structure/src/corpus_structure/`.

| Responsibility | Current source | Applicability conclusion |
|---|---|---|
| Typed domain call | `semantic/operations.py:280–320` exposes `claim_tasks -> tuple[ClaimedTask,...]`, invokes text SQL and reconstructs mapping keys. | Generated request/signature/result materialization can close a real internal static-continuity gap while retaining the public domain boundary. A cast-only façade would not close it. |
| Typed physical expressions | `schema/relational.py:906–977`, `semantic/typed_generation.py:10–25` generate selected typed columns and narrow protocols. | Reuse and extend existing generation; distinguish whole-row and explicit positional projection typing. No second manually maintained schema. |
| Companion projections | `companion_projection.py:82–178`, `model/semantic/companion-projections.yaml:18–70`, `companion_projection_native.py:53–84` derive types but retain `cp:sql`/join/guard strings. | Model-resolved field/parameter/JSON-path/cast/projection expressions fit typed Core lowering. SQLGlot qualification/type/lineage is an affirmative candidate for derived dependency/output analysis, not automatic replacement of native authorization. |
| Relational inference | `semantic/inference.py:59–160` mixes typed Core rule conclusions with textual seed/update/workspace calls. | Core insert-from-select/update/function expressions fit these relational fragments; preserve common qualified closure and direct proofs. Retaining the engine does not require retaining authored SQL. |
| Native schema/lifecycle | `native_products.py:91–131,389–530`, `alembic_native.py:21–187`, `native_objects.py:98–186` provide DDL, CHECK-body comparison, before/after catalog and frozen operations. | Structured desired definitions can feed current lifecycle. Current string bodies are authoring choices, not proof that lifecycle needs textual source. Full-body/server/ACL coverage remains scoped. |
| Bulk write | `arrow_transfer.py:41–171` binds exact directional profile, fresh pgpq encoder and quoted COPY to caller's Core/Psycopg transaction. | Keep one model-derived wire/target contract. pgpq DDL is not replacement schema authority; switching ADBC sessions would change atomic scratch/adoption behavior. |
| Bulk read | `analytics.py:703–725,860–908`, `serve/companion_export.py:73–168` dialect-render Core and import snapshot into separate ADBC read transaction. | Generated execution text is compatible with a SQL-free caller. ADBC1.13 `$n` bound results are a valid alternative only after comparing non-COPY memory/batching/effect semantics. |
| Python values/types | `core/db/store.py:45–54,101–142` installs JSON callbacks and one shared Psycopg pool with SQLAlchemy NullPool. | Model-derived result decoders/adapters fit selectively; custom PG composite/domain types must earn OID/schema/lifecycle costs and preserve domain constraints. |

## Research limits and decision handoff

No server test established equivalence of rewritten routines, no new static checker demonstrated
generated operation signatures, and no SQLGlot package was installed. The principal review must
select complete boundaries, not claim the libraries automatically make the codebase fully typed.
Native procedural authoring still includes trigger NEW/OLD/RETURN semantics, IF/RAISE, mutable
records, loops and dynamic EXECUTE. The surveyed libraries do not establish a full typed emitter
for those constructs. Compare finite generation of selected model-owned patterns with retained
specialized kernels, counting any handwritten renderer/templates as remaining SQL maintenance.
Historical frozen artifacts remain immutable outputs, not targets for retroactive rewriting.

For a SQLGlot projection consumer, run strict qualification before lineage:
`qualify(..., dialect="postgres", validate_qualify_columns=True)`, then type analysis with
explicit unknown handling. Lineage's default internal qualification disables column validation.
Model routine parameters (declared identifiers) differ from driver placeholders; generate their
representations separately. Select strict unsupported generation rather than accepting warnings,
while recognizing that strict handling does not prove complete PostgreSQL equivalence.
