# Typed COPY and Arrow transfer

**Discovery · 2026-11-09.** Local observations are source-inspected at `51b3c28de`;
capability details are Interface-checked only where the cited selected source was inspected.
All candidate benefits and research priorities are **Proposed**. See the
[family briefing](../briefing.md) for environment, scope and evidence limits. These are research
leads, not applicability verdicts or selected replacements.

## Already substantial adoption

[ArrowWriteProfile](../../../../../python/corpus-structure/src/corpus_structure/semantic/arrow_transfer.py) checks names, complete ordered wire schema,
nullability and metadata-sensitive batch schema; it prepares stable facts and creates a fresh pgpq
encoder for each stream. It explicitly handles UTF8/LargeUTF8/StringView JSONB, refuses undeclared
nanosecond normalization and requires Decimal128 for numeric writes. Partial encoder output is not
published after failure. [Row publication](../../../../../python/corpus-structure/src/corpus_structure/semantic/publication.py) uses Psycopg set_types()
for genuine Python rows, on the same borrowed Core transaction.
[Analytics](../../../../../python/corpus-structure/src/corpus_structure/semantic/analytics.py) and [Companion export](../../../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py)
own separate ADBC snapshot reads, normalization and reader cleanup. The former bulk-pool loader
is historical, not current missing integration.

## Research shortlist

| State | Mechanism and actual seam | Proposed value | Countercondition; next question |
| --- | --- | --- | --- |
| Candidate underuse | Model-derived directional profiles extended to an actual new value family | Avoid repeated per-consumer coercion while preserving meaning | One universal schema would conflate Python, Arrow and wire contracts. Which supported value currently requires conversion outside its owned profile? |
| Conditional | Psycopg typed output COPY/set_types, custom Writer/FileWriter and vector binary adaptation | Simplify a concrete export/offline serialization seam | COPY still needs transaction/type/constraint custody. Does an actual consumer benefit over existing typed rows or ADBC? |
| Conditional | pgpq lists/structs, explicit encoder maps and qualified OIDs | Retain structured values without object hydration | Composite lifecycle/child nullability, dimensions/lower bounds and OID namespaces remain caller obligations. Can the precise required nested shape be encoded and admitted faithfully? |
| Conditional | ADBC Arrow C Array/C Stream binding/fetch and target-aware adbc_ingest | Remove real materialization or exploit destination-aware native conversion | A separate connection cannot join current Core publication. Identify a complete new input operation before considering a parallel transport |
| Candidate underuse | Existing normalization and schema metadata at analytics/export boundary | Preserve exact numeric and semantic type facts instead of erasing them during decoding | Consumers may require deliberate normalization. Which metadata is meaning-bearing, and which original lexical evidence must remain separately retained? |

## Fidelity limits and contrary evidence

pgpq0.12's physical positional compatibility is not semantic schema identity; current profile
checks supply that missing obligation. Encoder failure may leave bytes; fresh stream ownership is
necessary. Its flush threshold is not a memory ceiling. Generated DDL does not preserve every
precision/nullability/list-length constraint, and generated composites do not share a temporary
table's lifetime. Arbitrary struct-child remapping is not a general public Python plugin seam.
Namespace qualification and collision-safe type naming matter before using generated composites.

ADBC numeric reads are strings with semantic metadata; domains/enums/ranges can lower differently
from native structured values. Arrays can lose dimension/lower-bound distinctions. Timestamps,
timezone annotations, interval components and decimal precision need directional treatment.
Resolver recognition does not guarantee a structured decoder. `builtin` intentionally avoids
broad custom-type catalog loading, whereas `server` introduces cache/startup obligations.

ADBC destination-aware ingestion supports useful conversions not implied by new-table inference,
but neither inferred schema nor pgpq generated DDL becomes model authority. COPY retains native
constraints/triggers and is not general bad-row skipping/RLS insertion. `arrow-json` is an optional
nested-data bridge with serialization and SQL-null/JSON-null concerns, not a free fidelity improvement.
DuckDB's community ADBC extension has independent pushdown/concurrency/cache semantics; it is not
the Apache driver's behavior or an automatic replacement for current capture.

## Sources and next work

[pgpq overview](../../../../libraries/postgresql/pgpq.md) entire main/addendum; [psycopg overview](../../../../libraries/postgresql/psycopg.md) COPY sections;
[adbc-driver-postgresql overview](../../../../libraries/postgresql/adbc-driver-postgresql.md) types/ingest/C Stream sections.
[pgpq selected release source](https://github.com/adriangb/pgpq/tree/306cdf8cf2b8450a3162a9cd467422cb0849af5a),
[ADBC25 COPY writer](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/copy/writer.h).

First identify an actual remaining conversion, then compare complete directions: source value,
logical Arrow field, wire schema, admitted PostgreSQL value and readback. Independent expectations
should cover only consequential uncertain distinctions, such as null/empty nested values or
precision, rather than mirroring profile construction. No new transport probe was required here.
