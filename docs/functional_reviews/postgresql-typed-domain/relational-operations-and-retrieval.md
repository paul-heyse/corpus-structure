# Complete relational operations and retrieval

**2026-11-09 · Proposed recommendations.** Source inspected at `d18183a22`, unchanged through
`f917260f8`. [Discovery](../../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md)
provides capability evidence; no native execution or quantitative performance claim is made.

<a id="O05"></a>
## O05 — Complete operations with preparation at their owner

A corpus comparison, coverage investigation or resident transformation should consume source/release/
cut bindings and return one coherent result. Existing projection recipes and companion projections
already prepare typed ordered Core statements. Extend complete activities, such as cross-run
contribution coverage, without first collecting intermediate identifiers in Python.

Prefer Core joins, correlated exists, typed VALUES/array membership, CTEs, lateral/table_valued and
windows where appropriate. Keep database-derived sets resident. A selected resident transformation
can use Insert.from_select and required ON CONFLICT/RETURNING inside existing protected staging/
publication, with explicit conflict and identity behavior. Extend the recipe vocabulary only for
repeated model-owned semantics; a specialized Core operation is preferable to a universal language.
Typed helpers/compiler extensions can own recurring fragments; CTAS/views need actual materialized
consumers and the migration lifecycle. [Core APIs](https://docs.sqlalchemy.org/en/21/core/selectable.html),
[selected capability account](../../libraries/postgresql/sqlalchemy.md).

Reuse release/projection preparation and structural compilation first; lambda_stmt is justified only
for remaining repeated stable construction. Psycopg prepare_threshold/prepared_max concern session
plans, pipeline sync/executemany(returning=True) residual protocol calls. They do not substitute for
set composition, and pipelines exclude COPY/server cursors. Compare retaining a simple specialized
operation before introducing another cache or preparation owner.

Deliver an ordinary multi-run coverage report and selected resident transformation. Migrate their
key loops/duplicate builders with independent membership expectations. Reads retain snapshot and
cancellation; writes retain admission and receipt settlement. Complete preparation determinants
include release, namespace, types and policy. Row partitions/yield_per are alternatives only where
an ordinary export benefits over existing analytical capture.

<a id="O06"></a>
## O06 — One exact retrieval operation with typed transient inputs

Contextual linking needs complete eligible membership and inspectable dense/lexical/alias candidates.
[Current retrieval](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_retrieval.py)
executes membership plus three channel statements, each reconstructing the eligible CTE.

Prefer one Core statement with a shared MATERIALIZED eligible CTE and tagged UNION ALL output:
complete membership records plus bounded channel records retaining channel/score/target order.
Validate full returned membership before candidates, then retain fuse_candidates and witness policy.
Separate statements do not share physical CTE preparation. Replace transient vector Text/str(list)
assembly with VECTOR(dimension) VALUES/binds through the official adapter. Retain dimension/profile/
runtime/source validation: typed adaptation alone cannot enforce them and selected binding still
serializes text. [VECTOR source](https://github.com/pgvector/pgvector-python/blob/v0.5.1/pgvector/sqlalchemy/vector.py).

Retaining separate statements is reasonable if tagged decoding adds disproportionate machinery.
Full SQL RRF is a larger alternative requiring exact score/evidence preservation; it is not required
for composed channel execution. Candidate-list public shape can remain stable; the internal result
gains membership/channel variants. Remove replaced execution/literal assembly after consumer migration.
Deliver complete/empty/missing/duplicate inventories, equal scores, profile mismatch and witness/alias
precedence through contextual consumers. Keep owned snapshot/cancellation and exact-scan barrier.
No speed benchmark is necessary unless a serious regression question arises.

<a id="O07"></a>
## O07 — Richer retrieval as assessable policies

Scientific terminology search could add sparse neural weights; page/region search could use token or
visual multivectors. These are plausible new product/research workflows, not assumed current demand.
Prefer a selected policy declaring representation, metric, tokenizer/vocabulary, normalization and
aggregation. Store multivectors as qualified rows tied to retained page/region/representation rather
than assume opaque arrays provide per-element indexing. Late interaction declares matching/reduction,
candidate universe and witnesses. Sparse retrieval needs a chosen encoder/term-weight contract, not
merely SPARSEVEC. Vector aggregates/normalization similarly require domain-defined semantics.

Keep D3's exact FP32 eligible cosine baseline. HNSW/IVFFlat, matching opclasses, filtered/partial
indexes and iterative scans become alternatives for a selected scale/quality need. Halfvec,
quantization and subvectors may generate candidates for canonical reranking; strict order is not exact
recall, and reranking cannot recover missing candidates.
[Extension0.8.7](https://github.com/pgvector/pgvector/blob/v0.8.7/README.md).

Compare sparse/multivector routes with current lexical+dense and a bounded cross-encoder over existing
candidates. Deliver an actual terminology or page-region journey with retained evidence, approximation
status and independent relevance references. Evaluation, export and explanation share policy identity.
Activation needs compatible profiles, native index migration and build/update failure handling.
Retire replaced experimental channels/configuration. Re-enter on a selected corpus/model and consumer;
representation suitability and quality remain unresolved until then. Distributed global top-k needs
its own identity/selection contract, not an automatic sharding extension.
