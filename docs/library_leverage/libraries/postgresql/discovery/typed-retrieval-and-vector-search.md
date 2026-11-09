# Typed retrieval and vector search

**Discovery · 2026-11-09.** Local observations are source-inspected at `51b3c28de`;
capability details are Interface-checked only where the cited selected source was inspected.
All candidate benefits and research priorities are **Proposed**. See the
[family briefing](../briefing.md) for environment, scope and evidence limits. These are research
leads, not applicability verdicts or selected replacements.

## Actual operation

[retrieve_candidates](../../../../../python/corpus-structure/src/corpus_structure/semantic/contextual_retrieval.py) validates vector dimension and
budgets, checks complete eligible membership, then executes dense/lexical/alias channel statements
and preserves their evidence in fuse_candidates. The materialized eligible CTE deliberately prevents
ANN changing exact neighbor membership. A CTE repeated in separate statements is not shared physical
execution across those statements. Published vectors bind profile, target, runtime and source context;
these are stronger contracts than a bare float array.

[D3](../../../../design/D3-database.md) selects FP32 exact eligible cosine, with ANN/halfvec
behind a scale/quality trigger. Generic unused embedding scaffolding is already retired.

## Research shortlist

| State | Mechanism and seam | Proposed value | Countercondition; next question |
| --- | --- | --- | --- |
| Candidate underuse | Generated VECTOR/profile/dimension/normalization contracts and typed VALUES parameters | Retain model distinctions through all transient and stored bindings | SQLAlchemy VECTOR is generically typed and its bind processor alone is not profile validation. Which text/primitive assembly remains after actual validate_vector/native admission? |
| Candidate underuse | One relational composition of eligible membership and three channels, windows/CTEs and RRF | Reuse eligibility work and reduce crossings while retaining complete channel evidence | Multiple purposes may require independent result detail/failure scope. Can one statement return exact membership plus all channel ranks with deterministic ties and witness/alias precedence unchanged? |
| Conditional | Psycopg register_vector/binary codecs on existing physical connections/COPY | Remove a specific text conversion in a driver-only producer/consumer | Current SQLAlchemy binding is adequate for ordinary queries; registration queries type metadata and changes session setup. Is there a real bulk vector seam with simpler complete custody? |
| Conditional | Vector avg/sum/l2_normalize/vector_dims and typed comparators | Avoid transferring vectors solely for a supported aggregate/check | Aggregation can change profile semantics. Which current domain operation defines the required normalization, metric and reduction? |

Root inspection of pgvector-python0.5.1 VECTOR shows text bind processing and list-valued result
processing; VECTOR(dim) is not a complete domain value type. Current stored/query validation is
therefore contrary evidence to a claim that introducing a wrapper alone fixes a missing invariant.
A Python Vector.to_numpy view also needs explicit mutable-buffer ownership before it can represent
immutable retained values.

## Concrete transient binding seam

[transient_vector_relation](../../../../../python/corpus-structure/src/corpus_structure/semantic/contextual_storage.py) constructs a VALUES Text column from
str(list(vector.values)) and casts it to VECTOR. A typed VECTOR bind is a direct alternative to
application literal construction within the existing Core operation. It would still serialize text
through the selected official adapter: do not claim binary transport, fewer numerical conversions
or a speed improvement. Existing dimension/profile/native admission remains necessary.

Compare composing bounded channels with moving RRF entirely into SQL as different-sized options;
small inventories may favor retaining the present straightforward Python fusion.

## Conditional search frontier

HNSW/IVFFlat, matching metric opclasses, iterative scans, filtered/partial indexes and partitioning
matter only after the current scale/quality trigger. Strict ordering is not exact recall. Halfvec
expression indexes, binary quantization/reranking and subvectors require explicit candidate versus
canonical precision; reranking cannot recover missing candidates.

SPARSEVEC and sparse neural channels need a chosen corpus/model/term-weight contract beyond existing
lexical+dense channels. Arrays of vectors, normalized vector rows and late-interaction page/token
retrieval are plausible visual-document directions, but arrays do not provide per-element ANN or a
native ColBERT index. Heterogeneous dimensions require profile-compatible casts/checks, not automatic
one-table-per-model decomposition. Cross-encoders, Citus/replicas/global top-k and other ORM/driver
integrations have no selected discovery consumer here.

## Sources and next assessment

[pgvector overview](../../../../libraries/postgresql/pgvector.md) §§1–11 including numerical and operational limits.
[Python0.5.1 VECTOR](https://github.com/pgvector/pgvector-python/blob/v0.5.1/pgvector/sqlalchemy/vector.py),
[extension0.8.7 reference](https://github.com/pgvector/pgvector/blob/v0.8.7/README.md).
The server version is recorded, not freshly checked in this pass.

First assess exact channel composition and a concrete remaining typed-binding seam. Retain independent
expected channel membership, tie order, empty inventory behavior and profile mismatch refusal. ANN
quality/scale experiments remain conditional; historical spike measurements do not qualify this route.
