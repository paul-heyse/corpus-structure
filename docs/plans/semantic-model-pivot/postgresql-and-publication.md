# PostgreSQL schema model and Core execution

**Status:** Planned · **Created:** 2026-10-29 · **Proposed.** [Coordinator](../semantic-model-pivot_2026-10-29.md) owns state. Consumes O03 and the [semantic contracts](semantic-model-and-releases.md). Supplies native persistence, publication and relational access to all consumers.

## SQLAlchemy is the relational foundation

Use SQLAlchemy Core intensively: model-derived `MetaData`, `Table`, typed columns, composite `ForeignKeyConstraint`, `UniqueConstraint`, `CheckConstraint`, `Index`, naming conventions, PostgreSQL types/operators, `select`/joins/`exists`, set DML, CTEs and recursive CTEs. PostgreSQL remains the planner/executor. Keep composable expression objects until execution rather than interpolating domain names into strings, materializing every row, or creating a bespoke SQL AST/planner. ORM object identity/unit-of-work machinery is unnecessary for this set-oriented contract.

The existing `schema/relational.py` already emits MetaData and `core/db/overlay.py` adds indexes/views. Extend that coherent projection instead of starting an unrelated metadata model. The LinkML source owns meaning; generated MetaData describes physical realization, shared by query construction, DDL and Alembic. Runtime semantic definitions are **rows** over fixed tables; do not call `Table()` or migrate whenever a domain class is discovered. Reflection/Inspector checks actual database structure at deployment/diagnosis, not semantic authority at request time. `create_all()` is not a migration planner.

A narrow generated DDL companion deploys publication routines, grants and other PostgreSQL objects not faithfully represented by ordinary MetaData. Its source is the same admitted physical/constraint mapping, with named ownership and reviewed Alembic deployment. Do not pretend MetaData or autogeneration fully represents procedure bodies or semantic data transitions. Custom SQL is bounded to this gap and database-native operations; pglast parses authored SQL but does not determine access authority or semantic correctness.

## Physical model

Use existing semantic/operational schema separation with fixed release/definition, realization/snapshot, entity/membership, assertion-occurrence, semantic-fact/support, recursive typed-value/role, evidence, derivation and coverage relations. Stable evidence/task/run tables remain ordinary relational tables. Scoped composite FKs prevent cross-release or cross-realization references. Definition IDs are scoped by release; semantic IRIs and occurrence/fact keys are distinct from database surrogates.

A typed value has a discriminator and mutually consistent scalar fields or recursive role rows. Native entity-reference FKs retain nested references; structured role rows retain order/multiplicity. Exact decimals use NUMERIC within its supported bounds and a lossless lexical/typed representation when necessary; query/projection lowering refuses unsupported exact operations. JSONB is reserved for declared opaque syntax/auxiliary payloads, not hidden relationship identity.

Declare indexes through MetaData expressions for scoped keys, property+subject/object, class membership, typed filter values and evidence. Select partial/expression indexes where justified. Do not add an index/table per semantic type. Promote hot access paths through rebuildable, declared views/projections; their lifecycle and visibility are separate from the semantic release. No speed claim is established by this design.

<a id="SP-02"></a>
## SP-02 — Stable metadata and immutable release persistence

**Input:** working SP-01 binding/registry row products and SP-00 decisions. **Owner:** schema/database integration.

Compile the new tables/constraints/access paths into one model-derived MetaData. Generate a fresh bootstrap revision with Alembic and explicit routines/grants deployment. Reuse the dedicated PostgreSQL 18 `18/corpus` service (5434); create a uniquely owned fresh database/realization rather than deleting or migrating old runs. Keep original frozen migrations recoverable; new execution must not import a legacy knowledge schema to bootstrap the new one.

Persist releases and exact artifacts atomically. Conflicting bytes under the same identity refuse, matching publication is idempotent. Definition projections are immutable to ordinary roles. Activate with expected-parent checking; failed preparation or activation leaves the existing pointer intact. New releases do not change existing bound operations. Stage SP-01 artifacts once, not a live compile for every row.

**Acceptance:** real fresh-database bootstrap, native constraint reflection, deterministic generated metadata, artifact conflict/idempotency, concurrent activation, immutable definitions and same-scope FKs. Compare selected metadata/DB constraints to independently specified required relationships, not only generator output against itself. A new semantic class/property changes registry rows while the physical schema stays unchanged.

<a id="SP-03"></a>
## SP-03 — Protected transactional publisher

**Input:** SP-02 and SP-01 scope-aware constraint/identity definitions. **Owner:** database publication; domain policy remains with consolidation.

SQLAlchemy `Connection` owns the transaction. Set SERIALIZABLE before autobegin; use the same connection's underlying psycopg driver for typed `Cursor.copy()`/`Copy.set_types()` staging. Never independently commit/rollback the driver or acquire a second connection for COPY. Preserve `store.py`'s single psycopg-pool + SQLAlchemy `NullPool` composition, including return/reset and extension checks; no nested pool or new connection service.

Stage a candidate batch in fixed-shape transaction-local relations. Call a protected database publication routine that validates candidate plus admitted state through native constraints and generated set checks. Grant ordinary writers staging/publication privileges but no unrestricted DML on admitted tables. Deploy routines with qualified object references, controlled search path and narrowly bounded privileges; treat staging contents as untrusted input and do not accept arbitrary table identifiers or caller-supplied validation booleans.

The publisher validates all state-dependent required rules in the actual enforcing transaction. SERIALIZABLE only protects predicates actually read. Native keys/FKs/checks establish static invariants; release-aware relational predicates establish class applicability, membership, cardinality and uniqueness for their declared projection. Unsupported required graph-only integrity constraints refuse activation. PySHACL can independently cross-check/preflight but cannot authorize a skipped database check.

Structural invalidity aborts the batch. Conflicting source reports remain occurrence evidence; selected-value cardinality governs the accepted-value projection, not the number of sources. Consolidation supplies selection/assessment products subject to the same scope rules. Publish entities, values, occurrences, fact-support links and evidence atomically. Data-revision visibility and publication identity are recorded in that transaction.

One bounded retry owner retries the whole transaction after serialization failure with fresh state and renewed checks. Use batch identity plus exact content comparison for idempotency. An ambiguous commit outcome is resolved by that identity; never replay with fresh occurrence identities. No LLM/network ontology acquisition inside the write transaction. Failed publication leaves no admitted partial batch.

**Acceptance:** independent expected states under two concurrent conflicting insertions, COPY invalid rows, explicit null/missing values, FKs to a different scope, privilege bypass attempts, malicious staging references, serialization retry, interrupted/ambiguous commit and idempotent replay. Two equal occurrences from one source remain distinct; retry of one occurrence does not duplicate it. Use real application and migration roles, not only an owner connection.

## Authored SQL: pglast as a bounded compiler boundary

SP-02 owns parsing/admission of authored view/rule SQL that cannot reasonably be expressed directly through Core. Use `parse_sql`, typed AST nodes and `Visitor`; reuse `referenced_relations` for CTE-aware syntactic relation discovery rather than writing a regex scanner. Keep source coordinates for diagnostics. If a bounded rewrite is needed, mutate typed nodes and use `RawStream`; do not substitute text fragments. Ordinary programmatic queries remain Core expression trees, so there is no mandatory Core→SQL→pglast→SQL round trip.

Bind supported references against the model-derived MetaData and admitted semantic handles, with explicit qualified names, CTE scopes and required function dependencies. pglast produces a raw parse tree, not catalog-bound types or an execution plan. PostgreSQL analysis under the actual role/catalog supplies the final name/type/access check; read-only privileges and transaction controls enforce execution effects. AST statement classification alone cannot make arbitrary SELECT/functions safe. Unknown dependencies or unsupported constructs refuse authored-feature activation; no general PostgreSQL semantic analyzer is implemented here.

Preserve exact SQL, binding/release identity and parser/compiler versions in artifact dependencies. Fingerprints may group diagnostic query shapes; they are neither semantic equivalence nor artifact/cache identity. Initial pure SP-01 bindings can omit authored SQL; any release containing it additionally requires this SP-02 admission step before activation. Parser/server grammar compatibility belongs in SP-00.

Native acceptance includes quoted names, CTE shadowing, nested references, unknown objects, side-effecting function attempts under the execution role, malformed SQL, fingerprint collisions across changed literals, and rewrite precedence where rewriting is actually used. Test only the supported contract; no blanket parse-every-query lint or new alignment gate.

Alembic consumes the same `target_metadata` with the existing shared-connection route (`Config.attributes['connection']`). Deploy routines/views/grants through explicit reviewed operations when standard autogenerate cannot represent them. Check bootstrap and a subsequent physical projection/routine revision on a disposable new database; a semantic class addition must leave Alembic head unchanged. A migration that cannot be safely reversed must declare that and recover through rebuilding the fresh realization, rather than fabricate a safe downgrade.

Sources: [pglast overview §§2,5,7](../../libraries/pglast.md), [Visitor implementation](https://github.com/lelit/pglast/blob/v8/pglast/visitors.py), [pglast parsing](https://pglast.readthedocs.io/en/latest/introduction.html), [Alembic overview](../../libraries/alembic.md), [shared connection and explicit operations](https://alembic.sqlalchemy.org/en/latest/cookbook.html).

## Core query and DDL contracts

SP-02 supplies shared Table/Column objects and binding-to-registry mappings. SP-03 exposes a typed batch publication operation; no caller receives generic admitted-table write access. SP-04 composes selections directly from those objects. Deploy changed functions through reviewed explicit Alembic operations; autogenerate compares physical metadata but cannot infer semantic intent. Specialized SQL has located diagnostics and explicit supported bindings; it is not a replacement for Core composition.

Sources: [SQLAlchemy overview §§2–4,8–9](../../libraries/sqlalchemy.md), [MetaData](https://docs.sqlalchemy.org/en/21/core/metadata.html), [selectables](https://docs.sqlalchemy.org/en/21/core/selectable.html), [constraints](https://docs.sqlalchemy.org/en/21/core/constraints.html), [connections](https://docs.sqlalchemy.org/en/21/core/connections.html), [psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html), [Alembic autogeneration](https://alembic.sqlalchemy.org/en/latest/autogenerate.html). Current documentation/Context7 was consulted 2026-10-29; exact-pin behavior is verified by SP-00 and native package checks, not inferred from a documentation version.
