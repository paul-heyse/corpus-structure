# Domain types and native invariants

**Discovery · 2026-11-09.** Local observations are source-inspected at `51b3c28de`;
capability details are Interface-checked only where the cited selected source was inspected.
All candidate benefits and research priorities are **Proposed**. See the
[family briefing](../briefing.md) for environment, scope and evidence limits. These are research
leads, not applicability verdicts or selected replacements.

## Current use and remaining question

[The relational compiler](../../../../../python/corpus-structure/src/corpus_structure/schema/relational.py) already derives columns, arrays, JSONB,
ranges, defaults and digest-named CHECKs from model declarations. It emits TypedColumns and narrowed
protocols. [CompanionProjection](../../../../../python/corpus-structure/src/corpus_structure/semantic/companion_projection.py) prepares typed binds,
table-valued return columns and separate Python/Arrow materializations. JSONB-to-text in the Python
statement deliberately preserves SQL NULL versus JSON null. These are adopted foundations.

Installed SQLAlchemy `sql/selectable.py`, `FromClause.with_cols`, explicitly returns self without
runtime validation. Its static shape cannot enforce model constraints or verify a query projection.
Psycopg row factories likewise construct objects; they do not authenticate result meaning.

## Research shortlist

| State | Mechanism and local consumer | Potential value | Countercondition and next question |
| --- | --- | --- | --- |
| Candidate underuse | Extend existing generated TypedColumns/Named and result protocols beyond currently selected tables/functions | Carry identifiers and value distinctions into consumer composition | Scalar `python_type` and generic JSON values can erase distinctions. Which wrong consumer bindings can current Pyrefly shapes reject, and which model-derived type would close a real gap? |
| Unused in inspected source | SQLAlchemy TypeDecorator bind/result processors, coerce_compared_value/comparator_factory, bind_expression/column_expression and cache_ok at repeated codec boundaries | Replace repeated mechanical conversions under one released definition | Implicit conversions can hide trust-boundary checks or repeat validation. Which conversion is context-free and stable over a release, and which must remain an explicit domain operation? |
| Unused in inspected source | Psycopg scoped Dumper/Loader, CompositeInfo/register_composite, EnumInfo/register_enum and range/multirange registration | Preserve structured values without intermediate dictionaries/text | Named OIDs and adapter inheritance are session-specific. Can a released declaration supply both conversion directions without another editable type map? |
| Conditional | class_row, args_row/kwargs_row and custom RowFactory/RowMaker for small domain reads | Derive object construction instead of per-consumer assembly | Column names/order and constructor signatures must agree; Core already owns ordinary reads. Identify a repeated assembly responsibility before adding a driver-specific read path |
| Conditional | DOMAIN, ExcludeConstraint, native range/multirange and qualified FK/unique/deferrable constraints | Enforce a real scalar, interval or relationship invariant at the native boundary | Native range canonicalization may erase source spelling/bounds; composite children are not automatically NOT NULL. Which invariant is not already adequately expressed by current model-derived CHECKs or membership relations? |
| Conditional structural alternative | Imperative Table mapping, composite(), dataclasses, hybrids, association objects/proxies and custom collections | Potentially simplify a coherent persisted object graph | ORM identity/UoW/instrumentation can add a second interpretation/lifecycle. Does one actual graph justify that total burden while keeping LinkML authoritative and immutable values faithful? |

The textual search covered application Python under `python/corpus-structure/src`; no application
TypeDecorator, named composite/enum registrations or row-factory use was found in the planning
scope. External/dynamic use is unresolved; this is not a package-wide absence claim.

## Concrete typed-generation seam

The compiler retains enum, pattern and range facts in Column.info, but render_typed_column_class
chiefly uses type.python_type (JSONB becomes JsonValue and arrays become Python lists).
Companion static rendering likewise retains richer source facts upstream but exposes primitive
result columns. Distinct semantic identifiers can consequently share a str surface. This is a
concrete LOP-02/X004 research seam, not evidence that the existing wrong-field protection failed.
Assess model-derived literal/nominal distinctions against actual caller errors before introducing
a new adapter or mapping framework.

## Fidelity and cross-topic obligations

Compare exact/unbounded decimals, integer magnitude and overload selection, finite/nonfinite floats,
SQL NULL/JSON null/omission, empty arrays, range emptiness/inclusivity/unboundedness, timestamp offsets,
Unicode and embedded NUL at the actual boundary. PostgreSQL or Arrow canonicalization must not silently
replace source occurrence identity. A native constrained scalar is not required for every semantic kind.

ADBC may expose enums as strings, domains through base storage and ranges as opaque bytes. Stronger
native typing therefore depends on [directional transfer](typed-copy-and-arrow-transfer.md) and
[session/catalog evolution](schema-evolution-and-catalog-admission.md). Keep existing codecs and native
admission where they enforce different properties; LOP-X003 warns against deleting independent guards.

## Sources and settling work

[sqlalchemy overview](../../../../libraries/postgresql/sqlalchemy.md) main§4/addendum§§7–8; [psycopg overview](../../../../libraries/postgresql/psycopg.md) main§§7–8/addendum§3;
[adbc-driver-postgresql overview](../../../../libraries/postgresql/adbc-driver-postgresql.md) type sections. Primary routes:
[SQLAlchemy custom types](https://docs.sqlalchemy.org/en/21/core/custom_types.html),
[Psycopg adaptation](https://www.psycopg.org/psycopg3/docs/advanced/adapt.html),
[3.3.6 composite source](https://github.com/psycopg/psycopg/blob/3.3.6/psycopg/psycopg/types/composite.py).
The selected composite implementation needs make_sequence for non-sequence bidirectional objects;
a dataclass factory alone is insufficient. Context registration does not update existing child connections.

First assess one repeated conversion and one generated query/result distinction. A focused negative
construction or round-trip check is useful only after identifying the exact contract; no blanket
new type framework or native-type migration is selected.
