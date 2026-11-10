# Native inspection and governed evolution

**2026-11-09 · Proposed recommendations.** Source inspected at `d18183a22`; concurrent PM2
work excluded. The [evolution discovery](../../library_leverage/libraries/postgresql/discovery/schema-evolution-and-catalog-admission.md)
supplies version-scoped leads; [D2](../../design/D2-schema-and-guidelines.md) and
[D3](../../design/D3-database.md) retain authority. Source inspection is not runtime qualification.

<a id="O10"></a>
## O10 — Explain database, parameter and result types honestly

An operator investigating a numeric export should be able to compare catalog column, Arrow
representation and released binding in one description. A developer could inspect positional input
types before supplying values. Currently `_fields()` in
[database_description.py](../../../python/corpus-structure/src/corpus_structure/serve/database_description.py)
drops Arrow metadata and uniformly marks domain, typmod and declared nullability unavailable.

Recommend extending the existing bounded description with attributed observations: interface/source,
Arrow type and relevant metadata, observed PostgreSQL type/typmod, separately observed declared
constraints and optional released field binding. Preserve principal, observation time, selectors and
limits. Distinguish unavailable, unsupported and refused. Separate sessions do not establish one
atomic catalog snapshot, and an Arrow nullable flag does not establish PostgreSQL NOT NULL.

Compose `adbc_get_objects`, SQLAlchemy `Inspector`, `adbc_get_table_schema` and
`adbc_execute_schema` for their different contracts. Numeric result metadata can include
POSTGRESQL:typmod missing from table schemas. Prefer complementary observations over a universal
schema inferred from Arrow, and keep this inspection separate from deployment admission.
Migrate `ci db describe` and machine consumers; retire blanket metadata loss while retaining unknowns.

A parameter-description extension would let query authors inspect expected inputs through
`adbc_prepare(sql)`. It requires an explicit bounded positional-parameter admission profile with
type declarations and ambiguous-type refusal: current
[authored_sql.py](../../../python/corpus-structure/src/corpus_structure/semantic/authored_sql.py)
and [description controls](../../../python/corpus-structure/tests/semantic/test_database_description.py)
refuse SELECT $1. Parameter support is a new capability, not a missing API call in an accepted one.
Activate it with a selected parameterized-query workflow. Delivery examples: constrained numeric
column, expression output, ambiguous parameter, and inaccessible relation.

See [ADBC overview, metadata/preparation addenda](../../libraries/postgresql/adbc-driver-postgresql.md).
Prioritize metadata preservation; parameter discovery remains conditional on the described workflow.

<a id="O11"></a>
## O11 — Make native evolution a reviewable composed workflow

A maintainer changing a signature or adding a native type should receive one candidate explaining
identities, dependents, retirements, grants and admission changes, then deploy its frozen reviewed
result. [NativeTransitionOp](../../../python/corpus-structure/src/corpus_structure/semantic/alembic_native.py)
already freezes before/after facts and refuses drift. Candidate authoring uses produce_migrations
but manually transforms nested operations and orders retirements.

Recommend preserving that model and independent catalog observer. Compare `Rewriter.rewrites/chain`
with the existing local traversal; use it only where it removes reconstruction cleanly. Keep global
FK/ACL/retirement ordering explicit. `process_revision_directives` serves revision generation but
need not replace the artifact-producing command. SQLAlchemy CreateView, DOMAIN/ENUM and explicit
Computed.persisted can construct selected definitions; they do not supply comparison/history/ACLs.
Migrate transformed-operation consumers and retire only replaced traversal. Retain the narrow
[default](../../../python/corpus-structure/src/corpus_structure/semantic/alembic_defaults.py) and
[index](../../../python/corpus-structure/src/corpus_structure/semantic/alembic_indexes.py) adapters
until selected supported APIs preserve independently observed drift facts.

This composed extension is preferable to another migration engine or wholesale Alembic Utils
adoption. Deliver a changed overloaded function, dependent trigger, explicit retirement, stale-state
refusal and actual restricted-role use. APIs and limits: [Alembic overview](../../libraries/postgresql/alembic.md).

Broader workflows remain worthwhile conditional propositions. A large retained table could admit
new writes under NOT VALID, repair old rows, then VALIDATE; a concurrent index could reduce build
blocking. Both need intermediate-state/retry/admission contracts. Concurrent deployment also needs a
fence spanning transaction boundaries; the current caller transaction and transaction-scoped advisory
lock cannot supply it. Require a concrete data-preservation/availability need and an ADR/D3 decision
before selecting that lifecycle. DOMAIN/exclusion/deferrable constraints similarly require declared
invariants or a transaction workflow.

Independent extension shipment could justify branch graphs/multiple bases; disconnected review
could justify offline SQL. The present single deployment favors its simpler atomic lifecycle.
Batch reconstruction, enum plugins and generic downgrade suites are unselected without a matching
consumer/contract gap. These are assessed alternatives, not omissions or automatic prerequisites.
