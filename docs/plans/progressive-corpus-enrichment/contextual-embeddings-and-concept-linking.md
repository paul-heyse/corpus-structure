# Contextual embeddings and concept linking

**Implementation target and bounded execution evidence · updated 2026-11-05.** This companion
develops PCE-05 and PCE-06 from the functional review's
[O05](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O05) and
[O06](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O06).
The [coordinator](../progressive-corpus-enrichment_2026-11-04.md) is the sole owner of
package state, opportunity disposition, accepted RC01–08 planning decisions dated 2026-11-04,
execution queue and assembled completion. The original planning baseline is `a3b0f21d`.
The execution boundary below supersedes blanket `not_run` statements for the selected route;
unselected alternatives remain Proposed.

## Selected implementation and evidence — 2026-11-05

**Implemented and bounded Tested.** `retrieve.contextual`v2 owns source-bound occurrence inputs,
curated target descriptors, the CPU encoder child, exact eligible candidate retrieval and scoped
denotation selection. Sentence Transformers6.2.0 runs pinned E5-small-v2 (384 dimensions, mean
pooling, query/passage prefixes) or Qwen3-Embedding-0.6B (1024 dimensions, last-token pooling,
explicit query instruction). Both run FP32 and L2 normalization with a512-token cap. The full
checkpoint revisions, effective package/tokenizer/profile identities and actual truncation/input
witnesses are in [local capability evidence](../../design_review/evidence/2026-11-05_pce-local-capabilities/README.md).
The vLLM/Sentence Transformers service alternatives below are not additional deployed routes.

The selected candidate channels are exact label/alias, PostgreSQL English full-text `ts_rank_cd`
and exact pgvector cosine over the same eligible inventory. RRF uses constant60 and equal channel
weights, K10 with30 candidates per channel and stable identity tie breaking. Known type/parent,
version and source exclusions apply before ranking; unknown constraints remain unknown. No ANN
index or generic embedding cache is needed for this bounded inventory. Official pgvector
SQLAlchemy types and preserving `text[]` migration replace the unconsumed generic vector scaffold.

Actual runs35/36 use17 independently supplied mentions in eight passages and20 curated targets.
Fresh source-only A/B/C retain their raw answers and exact source/target descriptors. Both models
include the independently correct target for all17 hybrid/dense cases; exact-alias and alias-first
lexical include16. Both selectors emit16 correct denotations and abstain on one retrieved density
function mention. These are exposed feature-fit cases, not discovery recall, population accuracy,
learned calibration or measured speed. C also identifies14 other passage relationships; those
are separate uncaptured questions, not denotation failures or generic comparison edges.

E5 is the initial route: the selected sample gives equal observed coverage with smaller vectors
and checkpoint. Qwen remains an attributable alternative; no throughput advantage is claimed.
Actual inventory expansion20→21 reuses exactly20 original target vectors, computes the new target
and all query vectors freshly, and rebuilds candidate lists/decisions. Original runtime/body/vector,
descriptor and rendered-tokenizer-input custody govern reuse; it adds no independent evidence vote.

Actual run38 freezes protected grade15 in its immutable publication dependencies and admits16
five-field denotation statements through common consolidation. The statement includes target,
target descriptor binding, relation, scope and effective version; generated list/decision IDs
remain provenance. Curated targets are described inputs, not canonical identities. Source-backed
definition targets await PCE-10's authenticated binding; unsupported target kinds refuse explicitly.
Full portable review, cross-document products and assembled adoption remain PCE-09–11.

## Purpose and responsibility

An anchored usage should yield plausible targets and an explicit account of the relationship
the source supports before a complete record exists. A target can be a curated glossary entry,
a source-backed definition passage or a provisional local sense. Global canonical identity is
neither a prerequisite nor an automatic consequence. This makes definition discovery and
cross-document comparison useful while retaining the difference between similar wording,
source-supported relationships and identity.

PCE-05 owns contextual representations, encoder execution, derived vectors, frozen eligible
inventories and reproducible lexical/dense/hybrid candidate lists. PCE-06 owns selection of
typed relationships from those lists, including ambiguity and unresolved outcomes. D1/D2 and
PCE-01 own the authoritative semantic declarations; D5 and the existing identity operation
retain canonical equivalence and exclusion authority. PCE-03 owns independent assessment
protocols; PCE-04 owns local public admission; PCE-09 owns complete review/export adoption;
PCE-10 consumes these products for structural products. These boundaries do not require a
separate service, table or task for every conceptual product.

## Current foundation and required changes

The baseline's [source search](../../../python/corpus-structure/src/corpus_structure/serve/source_search.py)
already searches selected source products through PostgreSQL English `to_tsvector`,
`websearch_to_tsquery` and `ts_rank_cd`. It preserves native source selections, deterministic
score/ID ordering, continuation identity and read budgets. It is an appropriate owner for source
retrieval and shared source addressing; its scores are not BM25, and its source-view hits are
not a concept inventory. Add a concept-candidate operation with its own meaning and reuse
source pinning rather than reclassify that existing API.

[D4 M04/M14](../../design/D4-method-catalog.md), legacy embedding declarations and older spike
plans are design leads. They do not establish a working contextual encoder, deployed extension
or vector relation. The current semantic physical model, migration/admission machinery and
[D3 PostgreSQL capability owner](../../design/D3-database.md#postgresql-capability-realization)
govern new storage. The provisioning specification selects pgvector 0.8.7; implementation must
inspect actual extension capability on the selected database before authoring its forward
migration. Do not hand-edit legacy tables or frozen revisions.

The [identity resolver](../../../python/corpus-structure/src/corpus_structure/semantic/identity_resolution.py)
already partitions label candidates with explicit exclusions and distinct input anchors.
[ADR-0029](../../adr/0029-identity-exclusions-scoped-reference.md) and
[D5's exclusion owner](../../design/D5-consolidation-identity-confidence.md#identity-exclusions-in-the-semantic-profile)
require located evidence, scoped endpoints and refusal of mandatory-key contradictions. New
semantic links must consume those constraints rather than acquire identity authority from
their similarity score. Earlier D5 phase descriptions of automatic aliases/new entities are
not the target for contextual selection; RC05/RC06 require the owning design and operation
contracts to change before dependent writes.

The foundation assessment therefore selects three improvements: make occurrence and target
representations explicit before encoder integration; distinguish reusable vectors from
inventory-dependent retrieval; and separate contextual selection from canonical equivalence.
This removes repeated rendering and avoids invalidating vectors whenever a glossary changes.
The costs are versioned derived storage and explicit consumer migration, justified by repeated
retrieval, selection and dossier consumers. No universal retrieval/provider framework is needed.

## Inputs, products and observable outcomes

An occurrence representation consumes a source-qualified occurrence from PCE-01/02, its exact
anchor and the selected context. Render literal mention, bounded sentence or list item,
informative heading and discriminating parent context. Tables may need headers/caption;
procedures may need their heading. Keep exact source address and rendered text separate.
Preserve language, unknown type, local parent, scope, effective version and coverage; unknown
type leaves plausible classes eligible rather than becoming an unsupported hard filter.

A target representation binds a stable target ID to canonical label, aliases, declared type,
source-backed definition or registry description, scope/effective version and meaningful parent.
A provisional sense has its own identity and qualification; matching words do not promote it
to a global entity. An independently curated inventory is an input product, not a privileged
source of truth or a disguised evaluation reference. Assessment-only labels remain protected.

Use the shared typed-product and operation contracts from
[contributions and semantic contracts](contributions-and-semantic-contracts.md). Extend them
with candidate channel evidence and explicit relation questions. A candidate list records
eligible target IDs, each contributing channel's raw score/rank, fusion rank, evidence pointers,
final unique-target budget and coverage/refusal information. Deduplication is by target ID;
equal labels and identical vectors do not merge targets.

The selector returns one of the following meanings, with source support and policy identity:

| Outcome | Meaning and limit |
|---|---|
| Selected relationship | The stated relation holds for these endpoints under this scope, version and evidence. `denotes`, scoped `alias-of`, `defined/explained-by`, `specializes`, `compared-with`, `participates-in` and domain workflow relations remain distinct. |
| Permissible alternatives | More than one target/relation remains supported; keep alternatives rather than invent one winner. |
| Local sense | Evidence supports a scoped sense whose global identity remains unestablished. |
| New-concept proposal | Evidence supports proposing a distinct concept relative to the declared inventory and examined alternatives. This creates a proposal, not a canonical identity. |
| Insufficient evidence | No justified relationship decision can be made. Record whether the limitation is source ambiguity, unavailable context, inventory coverage or candidate retrieval. |

Missing inventory membership, retrieval miss, low similarity and absent source evidence are
different observations. An empty or low-scoring list alone cannot establish novelty, absence,
local sense or identity difference. A failed/cancelled computation is not an empty successful
list. Avoid a universal `semantically_related_to` edge that erases the assessment question.

## PCE-05 — Contextual encoder, vectors and hybrid candidate retrieval

### Prerequisite slice and work sequence

PCE-01 must provide executable occurrence/target/product identities, qualification and operation
outcomes; PCE-02 must provide source-qualified adapters and retained raw report references for
the selected statistics slice. PCE-03 supplies an independently authored reference-mention and
target-coverage frame before comparison. Complete-record acceptance and every parser family are
not prerequisites. The implementer first publishes the selected RC05 semantic/physical changes
through D1/D2/D3/D4/D6 and the existing ADR/release route, then integrates the following slices:

1. Freeze one bounded statistics inventory and occurrence slice with exact source/release
   selections. Author a deterministic context recipe with inspected truncation behavior; retain
   the mention and discriminating cues even when a heading or long paragraph must be shortened.
2. Resolve the exact package/model profiles below, add only their required exact dependency
   pins, inspect lock changes and run the affected environment checks. Load one model under an
   owned CPU lifetime, batch rendering/encoding and retain actual implementation provenance.
3. Extend the active physical model with derived vector/profile and inventory/list products
   through the current compiler and frozen forward migration/admission route. Admit dimensions,
   nonfinite/zero vectors, source/target membership and profile compatibility before use.
4. Implement independent lexical and exact dense channels over the same eligible inventory,
   then bounded fusion. Wire the operation/report/task/read interfaces and selected statistics
   consumer together; persist retained list reports rather than immediately calling a selector.
5. Compare reference-mention lexical-only, dense-only and hybrid lists at the same final count
   of unique target IDs. Select the released profile from the observed tradeoff and retain
   challenger results and failures. A model's published benchmarks do not select the winner.

### Encoder composition and precise profiles

Use direct local CPU `SentenceTransformer` first. `encode_query` encodes the contextual usage;
`encode_document` encodes target descriptions. These methods select saved prompt/task roles
when configured; they do not guarantee that a downloaded model contains the required prefixes.
The profile must either supply explicit prompts or validate the pinned model's saved prompts,
and must prevent double-prefixing. Hash the actual final encoder input and role configuration.
Use the library's batching, tokenizer and pooling modules rather than implement a parallel
embedding kernel. The [Sentence Transformers usage contract](https://github.com/huggingface/sentence-transformers/blob/main/docs/sentence_transformer/usage/usage.rst)
and [prompt configuration](https://github.com/huggingface/sentence-transformers/blob/main/skills/train-sentence-transformers/references/prompts_and_instructions.md)
were consulted through Context7 on 2026-11-04; exact installed-version syntax remains an
implementation admission obligation.

| Proposed profile | Required realization and decision before activation |
|---|---|
| `intfloat/e5-small-v2` compact English baseline | Pin an immutable model/tokenizer revision and exact compatible Sentence Transformers/Transformers/Torch versions. Explicit `query: ` and `passage: ` roles, attention-mask mean pooling, L2 normalization and 384 dimensions; keep the complete input within its 512-token limit with an occurrence-preserving context recipe. Declare compute and stored precision. |
| `Qwen/Qwen3-Embedding-0.6B` challenger | Pin this exact model identity and an immutable revision, not a generic Qwen model. Record the task instruction/query template and document role explicitly, last-token pooling, padding convention, normalization, chosen dimension and actual input cap. Start with the full 1024-dimensional output; a smaller dimension is a separately assessed profile. Its advertised 32K context does not justify unbounded context or establish CPU feasibility. |

These model-specific requirements come from the
[E5 card](https://huggingface.co/intfloat/e5-small-v2) and
[Qwen card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), inspected 2026-11-04.
Exact revision hashes, package versions, CPU precision and supported root-Python combination
are deliberately unresolved until the bounded compatibility decision; they must be fixed before
generation, not discovered through mutable `main` at run time. A failure to find a compatible
root Python 3.14.10 tuple constrains this slice and needs an explicitly owned alternative
environment decision. No dependency/model installation is part of plan authoring. The older
Jina v5 recommendation remains an alternative if evidence changes the chosen tradeoff, not an
obligation to run a third model or a license-based rejection.

### Eligible retrieval and physical route

Freeze eligibility before scoring: corpus/source selection, target representation versions,
scope/effective-version rules and reliable type/parent constraints. Query PostgreSQL/pgvector
exact cosine over that eligible relation with `<=>`, ascending distance and stable target-ID
secondary ordering. Reject incompatible vector spaces and invalid vectors explicitly. Keep an
exact scan path independent of any future ANN index; an index-selected query must not silently
change an operation claiming exact neighbors. The selected precision is part of this claim.
The [pgvector 0.8.7 query/index contract](https://raw.githubusercontent.com/pgvector/pgvector/v0.8.7/README.md)
provides the distance operator and distinguishes exact from approximate search.

Keep alias/exact, lexical/fuzzy and dense ranks separately. Start with reciprocal-rank fusion: sum `1 / (60 + rank)` across active channels, using
one-based ranks, equal channel weights and at most one contribution per target per channel.
Deduplicate by target ID and apply one final unique-target budget. A changed formula/constant
is a new retrieval policy assessed on the same development frame. Pin that formula, tie rule and channel
budgets rather than adding incompatible raw scores. One target nominated through several aliases
retains all channel evidence without consuming several final slots. Lexical-only, dense-only
and hybrid use the same eligibility and final budget; channel overfetch is explicit and bounded.

Preparation remains proportional to the statistics slice: encode stable target descriptions once
per profile; batch occurrence encoding; score/filter/project inside PostgreSQL; hydrate source
evidence for selected targets. Avoid a Python loop with one database request per target or a
dense all-pairs matrix. Scope and type filtering reduce examined work where justified, while
unknown types and ambiguous parents retain plausible alternatives. Highly common labels and
empty results must remain feasible under declared inventory scope, not merely refuse after an
unbounded scan. No speed or memory improvement is claimed until measured.

Keep these determinants separate:

| Product | Identity and invalidation |
|---|---|
| Vector | Object/address identity, rendered-input digest, context recipe, model/tokenizer revision, role/prompt, pooling, normalization, dimension and compute/storage precision. Input or encoding changes regenerate affected vectors. |
| Inventory | Frozen eligible membership plus target representation versions, corpus, source/scope/version rules and effective constraints. Additions, removals and eligibility changes create a new inventory. |
| Candidate list | Occurrence/vector identity, inventory selection, lexical/dense implementations and versions, channel/fusion/deduplication policies, budgets and tie ordering. Inventory changes invalidate affected lists while unchanged vectors remain usable. |
| Relationship decision | Candidate-list identity, explicit relation question, source context, selector policy, exclusions and qualifications. Exclusion/policy changes can invalidate selection without encoding again. |

Retain negative lookups and consumed counterevidence as computational dependencies where their
change can alter a result. An input unchanged under one recipe need not be interchangeable under
another. Claim embeddings for semantic comparison require their qualifications; these anchored
usage embeddings do not wait for whole-record acceptance.

### Conditional runtime and retrieval alternatives

vLLM pooling is a concrete alternative when repeated consumers justify resident model/service
lifetime. Tagged [vLLM 0.26 embedding documentation](https://raw.githubusercontent.com/vllm-project/vllm/v0.26.0/docs/models/pooling_models/embed.md)
describes `LLM(model=..., runner="pooling")`, `LLM.embed(...)` and vectors in
`output.outputs.embedding`; its [pooling server route](https://raw.githubusercontent.com/vllm-project/vllm/v0.26.0/docs/models/pooling_models/README.md)
provides `/v1/embeddings`. This is an alternative execution boundary for the same pinned
representation/profile, not evidence of equivalent vectors, CPU support or superior throughput.
The [local overview](../../libraries/analytical_infrastructure/vllm.md#63-pooling-models-embeddings-classification-and-reranking)
targets 0.32.0; do not substitute its APIs for the service's 0.26.0 contract.

The existing [Nemotron service](../../../services/nemotron-parse/pyproject.toml) pins vLLM
0.26.0 in Python 3.12, separately from root Python 3.14.10, and loads a recognition model.
Do not replace its loaded model, mutate its environment or repurpose its endpoint. A selected
embedding service needs its own exact compatible Python/package/model profile, managed process,
health/admission, queue, cancellation and cleanup owner. The tagged
[CPU installation](https://raw.githubusercontent.com/vllm-project/vllm/v0.26.0/docs/getting_started/installation/cpu.md)
documents Python 3.10–3.13; root compatibility remains unverified rather than presumed impossible.
Select this alternative only after actual workload/runtime comparison and semantic parity of
the declared profile; the current plan does not require running both runtimes.

HNSW/IVFFlat follow demonstrated scale need. Their admission requires exact-neighbor recall
comparison at the same eligible inventory, separate correct-target recall assessment, filtered
underfill controls and new index/profile identity. Strict distance ordering of retrieved ANN
neighbors does not make neighbor membership exact. Reduced storage precision is another
approximation, assessed independently. A pairwise reranker follows fixed-list evidence of a
ranking/selection problem; it cannot repair missing occurrences or missing inventory targets.
Neither conditional branch blocks the initial exact retrieval capability.

## PCE-06 — Scoped relationship selection and identity integration

PCE-06 can define the relation-question/outcome slice with PCE-01 before all encoder work
finishes. Its actual selection consumer requires an implemented, frozen PCE-05 list and PCE-03
fixed-list judgments. It consumes lexical/alias witnesses, contextual type/parent, explicit
definition/alias language, source scope/effective version and the selected exclusion snapshot.
Start with declared evidence and compatibility policies. A fuzzy score, cosine score or
normalized shortlist is a ranking feature, not a calibrated identity probability.

Implement the source-supported distinction between an alias assertion, contextual denotation,
definition support, specialization and comparison. Alias-of is explicitly scoped and may support
a later canonical identity operation only when that operation's independent preconditions hold.
Comparison links do not become alias links because their endpoints are close. Process,
subprocess, checklist, form and system action keep distinct roles. Conflicting valid versions
remain separate; no "current" version is chosen from similarity or request time.

The package changes D1/D2/D4 M14/D5 and corresponding operation declarations, reports,
publication guards and reader projections coherently. It supplies one implementation of relation
compatibility for selector/publication consumers, with independent expectations in tests.
Canonical assignments continue through existing source/known-input identity and exclusion
owners; no neighbor clustering or selector-side union-find is introduced. A–B and B–C similarity
with an A/C cannot-link must never collapse A/C. Mandatory-key contradictions still refuse
publication atomically; label-only proposals retain compatible separate identities.

Splink is conditional on a real structured record identity task with useful comparison attributes,
null handling and independent match judgments. If selected later, its blocking, comparisons,
training/frequency lifecycle and constrained clustering require their own scoped assessment and
the same exclusion/anchor contract. It is not the default engine for contextual semantic
relationships, nor a required dependency of PCE-06.

Expose selected, ambiguous, local-sense, new-proposal and insufficient-evidence outcomes through
the ordinary operation reader and PCE-09 review surface. PCE-04 decides which qualified local
contributions are publicly admissible; a list or selector success does not bypass that decision.
The same pinned list must be available to the assessor and explanation reader. If a fitted scorer
is warranted, use operation-specific labels with held-out assessment; do not train on the fixed
test frame or treat scores as probability without calibration evidence.

## Migration, resource lifetime and consumer completion

PCE-05/06 own their new release/migration and the working selected-slice consumers together.
PCE-01 supplies shared declarations; PCE-09 owns complete inventory/export integration and
PCE-10 owns structural queries. Coordinate edits to shared model, operation/report declarations,
native SQL/migrations and read bindings rather than independently adding conflicting schemas.
Preserve existing source search and canonical identity semantics for their existing operations.
Retire or supersede active M14 configuration/card assumptions that these new operations replace;
do not rewrite historical raw reports, source selections or archived release bytes.

Introduce a new immutable release and forward physical migration through current compiler,
Alembic/native-candidate and admission owners. Build only selected derived vectors and lists;
activation checks exact extension/profile support. Rebuilding derived products is explicit and
does not re-run extraction when retained anchored inputs suffice. Old results keep their original
product/release identities; unsupported new reads refuse with the existing rebuild/admission
route. Do not add an unneeded historical upcast or migrate old record grades into link judgments.

One operation/task owns model lifetime, batches and cancellation. Capture small immutable input
references under a short reader transaction; release it before CPU encoding. Publish only after
rechecking the intended source/inventory binding under existing task/attempt fences. Cancellation
stops admission, cancels or drains owned encoder work, releases model/buffers/borrowed readers
and preserves completed immutable reports. Failure retains its actual phase and cause; uncertain
commit acknowledgement settles through the existing receipt identity rather than blind retry.
No new workflow engine, lease loop, global cache or nested retry owner follows.

The first integration journey runs source occurrence → representation → frozen inventory →
candidate list → relationship decision → bounded explanation and review export on the statistics
slice. A subsequent real business-document slice, when available and frozen, exercises changed
types/versions without changing the identity semantics. It is a bounded transfer check, not a
second released corpus obligation or an enterprise effectiveness claim.

## Independent acceptance and remaining decision points

PCE-03's assessment companion owns frames, judgments and declared thresholds; PCE-11 owns
assembled qualification. Package-local controls and selected provider results establish only
their declared scope. Use independently authored reference mentions for candidate generation
and frozen lists for selection so extraction, inventory, retrieval and selection errors remain
separable. Required controls include:

- Inventory coverage distinguishes an eligible correct target missing from the inventory from
  an eligible target present but missed by retrieval. Unknown type, same-label distinct targets,
  scope/version exclusion and new membership/deletion changes exercise eligibility and reuse.
- Equal-budget lexical/dense/hybrid retrieval reports correct-target inclusion and rank under
  one frozen inventory. Independent small-vector cosine/tie cases challenge distance ordering,
  deduplication and budget identity; round-trip checks cover dimension/precision corruption.
- Fixed-list selection distinguishes normal/standard normal; CLT/normal distribution; the same
  parameter symbol under different parent families; explicit definition versus example; an alias
  in the wrong effective version; and ambiguity, local sense, justified new proposal and unknown.
- Exclusion controls include A–B–C bridging, distinct known-input anchors, source-backed cannot
  links and atomic mandatory-key refusal. Comparison/alias edges cannot silently mutate identity.
- Actual selected encoder execution, input truncation/prompt witnesses, cancellation, interrupted
  publication and bounded reader/export round trips cover the implemented resource boundary.
  A mocked encoder does not qualify the native model profile.

Record actual commands/outcomes at the coordinator/evidence owner when implemented. Existing
whole-record A/B/C bytes and grades retain their meanings. No agent task benchmark is required;
the evidence concerns source linkage and its consumers. Model revision/package compatibility,
context/input caps, selector relation policies and the selected inventory/assessment frame must
be resolved before their dependent work executes. Runtime/index/reranker substitutions remain
conditional, with their stated triggers, rather than unresolved mandatory branches.
