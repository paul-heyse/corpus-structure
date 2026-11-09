# Schema evolution and catalog admission

**Discovery · 2026-11-09.** Local observations are source-inspected at `51b3c28de`;
capability details are Interface-checked only where the cited selected source was inspected.
All candidate benefits and research priorities are **Proposed**. See the
[family briefing](../briefing.md) for environment, scope and evidence limits. These are research
leads, not applicability verdicts or selected replacements.

## What is already delegated

[NativeTransitionOp](../../../../../python/corpus-structure/src/corpus_structure/semantic/alembic_native.py) already registers operations, implements
execution, comparison and rendering of frozen before/after native objects.
[Candidate authoring](../../../../../python/corpus-structure/src/corpus_structure/semantic/native_candidate.py) uses produce_migrations;
[Migration execution](../../../../../python/corpus-structure/src/corpus_structure/semantic/migrations.py) supplies a caller-owned connection and
transaction fence. [Native objects](../../../../../python/corpus-structure/src/corpus_structure/semantic/native_objects.py) and
[Catalog observation](../../../../../python/corpus-structure/src/corpus_structure/semantic/native_catalog.py) retain independent desired/observed facts.
[Default comparison](../../../../../python/corpus-structure/src/corpus_structure/semantic/alembic_defaults.py) and
[Index comparison](../../../../../python/corpus-structure/src/corpus_structure/semantic/alembic_indexes.py) contain narrow version-sensitive adapters.
The current environment refuses unsupported offline execution.

## Research shortlist

| State | Mechanism and local seam | Proposed value | Countercondition; next question |
| --- | --- | --- | --- |
| Candidate underuse | Alembic operation trees/Rewriter/renderers/directive hooks around frozen candidate generation | Avoid reassembling native facts in text and preserve structured change intent | Public hooks may not represent the exact object. Which residual source generation can be replaced without changing frozen payload identity or retirement ordering? |
| Candidate underuse | SQLAlchemy Inspector get_multi/reflection hooks/Table.to_metadata and supported comparator APIs | Replace narrowly pinned private/cache-dependent reflection glue | Reflection must observe actual state, not copy desired values into it. Can a public hook supply the exact missing collation/index/default fact at selected versions? |
| Conditional | CreateView/CreateTableAs, named-type DDL, conditional compilation and dialect operation constructs | Delegate construction of complete supported definitions | DDL construction does not imply comparison/history/ACL support. Which native object family actually gains simpler ownership? |
| Candidate underuse | Existing ADBC object/table/query schemas and Core catalog observations in database_description | Explain domain/physical/output type differences to operators more precisely | Metadata interfaces omit different properties. Which known typmod/semantic metadata can be exposed with honest source/principal scope, without becoming deployment admission? |
| Conditional | DOMAIN/exclusion/deferrable constraints, NOT VALID/VALIDATE, concurrent indexes, generated-column distinctions | Express new real invariants or reduce a demonstrated migration constraint | Concurrent/autocommit operations break enclosing atomicity and add lifecycle states. Does the supported workload actually require these semantics? |

## Concrete transformation and metadata seams

Candidate authoring calls produce_migrations, then manually walks/splits nested CreateTableOp and
ModifyTableOps, attaches ownership work and applies retirement ordering. Rewriter.rewrites/chain
could simplify local traversal, but global FK/ACL/dependency order remains application-owned.
This is a medium-priority organizational alternative, not replacement of a bespoke migration engine.

Database-description _fields currently drops field metadata and marks typmod unavailable uniformly.
Both table and prospective output schemas use it, although suitable output fields can retain numeric
typmod and PostgreSQL/Arrow semantic metadata. This is a concrete underuse candidate: expose useful
observed facts separately from unresolved domain definitions or declared NOT NULL. Existing Core
catalog inspection remains complementary. The current query-description contract refuses parameters;
parameter-schema discovery is a conditional functional extension, not a missing existing requirement.

## Reasons to keep the present boundary

Alembic autogeneration creates candidates, not complete correctness judgments. CHECK-by-name does
not compare expression meaning; digest-named CHECKs already compensate. Index predicates/methods,
functions, ACLs, ownership and other native properties need explicit coverage. A small well-scoped
adapter can remain preferable to adopting a larger plugin. Do not remove callable-default, array
or collation fixes because an unrelated release note mentions similar behavior.

ADBC table-schema metadata does not recover all PostgreSQL nullability/typmods. Query description
can carry numeric typmod not supplied by table schema. `get_info()` may return an unknown driver
version; installed package provenance is separate. Type-resolver caches and namespace-qualified
OID identity connect native-type adoption to [lifetimes](transactions-pools-and-outcomes.md).

Revision DAGs, multiple bases, dynamic revision kwargs, offline SQL, batch reconstruction,
pytest-alembic/Alembic Utils/enum companion packages and multi-database environments remain
conditional. Equal revision IDs must not conceal different runtime-argument effects. Existing
native controls already cover richer contracts than a generic at-head check; no extra gate or
historical downgrade promise follows from discovery.

## Sources and settling question

[alembic overview](../../../../libraries/postgresql/alembic.md), [sqlalchemy overview](../../../../libraries/postgresql/sqlalchemy.md) DDL/reflection addenda and
[adbc-driver-postgresql overview](../../../../libraries/postgresql/adbc-driver-postgresql.md) metadata addendum.
[Alembic plugin API](https://alembic.sqlalchemy.org/en/latest/api/plugins.html),
[autogeneration limits](https://alembic.sqlalchemy.org/en/latest/autogenerate.html),
[ADBC25 catalog implementation](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/connection.cc).
Live docs may describe newer versions; exact adapter retirement requires selected1.20.1/2.1.6 source.

Start with one existing reflection adapter and its independent drift case. A supported-hook
replacement must still detect a deliberately wrong catalog property; desired-equals-observed
through shared construction would not establish its correctness.
