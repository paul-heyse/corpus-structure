# Text preparation, scope indexes and candidate analysis

**Status:** Planned · **Created:** 2026-10-30 · **Packages:** PE-05–PE-07.

This document schedules [production review F04–F06](../../design_review/reviews/production-efficiency_2026-10-30.md#F04)
from review revision `534e956`, against production baseline `7fadeff`. The
[coordinator](../production-efficiency_2026-10-30.md) owns finding disposition, shared decisions
and series completion. This is production work; testing-code optimization, audit-premise updates
and new extraction capabilities are excluded. Verification below is planned, not executed.

## Target and foundation

Prepare the smallest reusable text and comparison inputs once per appropriate operation. Their
meaning comes from the release's declared context, eligibility, normalization and outcome policy;
private token/interval/candidate indexes are physical realizations of those contracts. A faster
algorithm does not acquire authority to change identity, source scope or ambiguity.

PE-01 supplies the admitted model-derived context and comparison contracts and their dependency
identity. These packages must consume those contracts in actual segmentation, scope assignment,
quote placement and matching calls. Do not add a second class hierarchy, qualifier-default map,
normalization policy or candidate-eligibility declaration in a cache or adapter. Physical options
such as worker counts remain execution choices under the shared resource contract; any existing
identity change belongs to PE-01's dependency decision, not an incidental local cache key.

Current strengths constrain replacement: `ingest.sentences.pipeline` caches loaded models;
`split` uses `Language.pipe` with prepared Docs; scope matchers are cached; M13 does not rerun
spaCy pipeline components; quote placement distinguishes exact, coarse and unlocated outcomes;
semantic alignment refuses ambiguous identity choices and preserves grouped alternatives.

The concrete opportunities are repeated tokenization after ingestion, flat scope rescans,
per-pair metadata reconstruction, repeated invariant comparisons and a Python scorer wrapper
that hides RapidFuzz's native callable identity. The direction is local prepared products and
operation-shaped candidate sets, not a new universal NLP service or persistent cache.

<a id="PE-05"></a>

## PE-05 — Reuse token layout; decide segmentation explicitly

**Source:** F04; accepted RC02. **Prerequisites:** PE-00's authority route and PE-01's text-context,
configuration and dependency contract. Text preparation may be designed against that published
contract, but consumers are not complete until they actually use its implemented form.

### Resulting behavior

An immutable prepared text layout represents the rendition's exact canonical text, words/spaces,
source offsets and math/reference atoms. Ingestion and scope analysis obtain the same layout
without tokenizing its prose pieces again. Its identity binds the rendition and applicable
model/tokenizer/atom configuration through PE-01. Start with operation-owned preparation; use
broader retention only when a real reuse lifetime repays retention and reconstruction.

Prefer a compact representation of the pre-pipeline token/atom layout over retaining every spaCy
annotation or persisting whole Docs. `Doc(nlp.vocab, words=..., spaces=...)` may construct an
owned mutable Doc for each consumer. `Language.pipe` accepts Docs and skips tokenization. Sentence
segmentation applies its declared pipeline; scope matching applies recorded sentence starts and
its own math annotations. Do not share a mutable Doc whose `Token._.math`, tags or sentence starts
can be overwritten by another consumer. Preserve the current one-word treatment of inline math
and references, display-boundary suppression and exact whitespace reconstruction.

Actual migration includes `ingest.sentences.make_doc/split`, `ingest.html._add_sentences`,
`methods.math.scope.segment_block/_sites/resolve_scopes`, and their production method/orchestration
callers. Consumers receiving a persisted rendition rather than an in-memory predecessor must
have an explicit reconstruction route; do not assume all stages share a Python process.
Remove duplicate prose-tokenization paths when those callers adopt the shared layout. Retain a
single reconstruction implementation for detached or cold inputs rather than a shadow fast path
with different atom rules.

### Segmentation decision and library mechanisms

Inspect the pinned model configuration and `nlp.analyze_pipes()` before removing any component.
Compare the existing dependency-parser route with a smaller valid component set, a configured
`SentenceRecognizer` (`senter`) and, only if justified, a rule-based segmenter. This comparison
is required; selection of `senter` is not predetermined. The selected profile states the
annotations it requires/produces and how math/reference constraints compose with segmentation.

RC02 permits a changed segmentation profile only as a declared new method configuration and
fresh semantic release. Different sentence boundaries produce different rendition/unit/anchor
identities. Never relabel or rewrite old renditions, source frames, reference anchors or results.
Keep the existing profile available for its bound releases. If no replacement has an acceptable
source-boundary contract, retain it and complete the safe token-reuse work; record that disposition
rather than silently omitting the comparison.

`DocBin`/`Doc.to_bytes` are candidates only when an actual process/persistence boundary requires
annotation transport. Select attributes and custom-extension handling deliberately; serialization
is not free reuse and must preserve the admitted source mapping. Hugging Face Tokenizers is not a
current production dependency or a substitute for sentence/scope semantics. `encode_batch` and
`Encoding.offsets` may inform a future neural-input mechanism, but no dependency or subword
replacement is required here. Normalization and offset mapping cannot change the canonical text
or split a math atom unnoticed.

**Library references:** [spaCy Doc-aware `pipe`](https://spacy.io/api/language#pipe),
[pipeline dependencies](https://spacy.io/usage/processing-pipelines),
[SentenceRecognizer](https://spacy.io/api/sentencerecognizer),
[Tokenizers alignment](https://huggingface.co/docs/tokenizers/quicktour), and local
`docs/libraries/spacy.md` / `tokenizers.md`. Qualify consequential APIs against the actual pins
through Context7 and installed configuration; vendor timing claims are not repository evidence.

### Completion

All named callers share source-preserving token preparation, cold/detached reconstruction is
explicit, and the segmentation comparison has a documented disposition. Independent source
cases challenge identical text reconstruction, math/reference atoms, unusual punctuation,
changed configuration and overlap handling. Observe production preparation and downstream use
on the same inputs, including retention/transfer costs. Any speed claim names its workload and
cold/warm conditions. Package completion does not authorize new segmentation by itself: the new
configuration/release and all anchor-consuming boundaries must be ready before activation.

<a id="PE-06"></a>

## PE-06 — Index scope and candidate preparation from declared context

**Source:** F05 and F06's invariant candidate preparation. **Prerequisite:** PE-01's effective
context, eligibility, identity and comparison-policy contracts. PE-05's stable token layout is
needed only for the scope consumer migration; indexing pure segment/site inputs can proceed
without waiting for a replacement segmenter.

### Resulting behavior

Scope resolution prepares rendition-local hierarchy/interval and per-symbol position indexes.
It uses an ordered sweep or suitable interval structure for enclosing units/sections, a
per-symbol previous eligible section-level site for reopen links, and indexed mention-to-site
queries. Preserve shortest enclosing extent, document-order ties, statement/section distinction,
position eligibility and reopening rules. Indexes bind the same source/macro/scope context as
the operation and are discarded or reused only within that declared validity.

In semantic comparison, prepare each side's attributes, names, normalized aliases, identity
groups, class/property metadata, anchor spans and reference dependencies once. Class compatibility
uses the model hierarchy, including ancestor/subclass eligibility; exact-class partitioning alone
is insufficient. Preserve the existing selected occurrence and evidence path for repeated
attribute predicates. An absent declaration or unresolved endpoint cannot become proof that a
candidate is incompatible.

Materialize candidate edges from semantically sufficient keys before expensive comparison.
Claim subject/predicate eligibility can be indexed; candidates conditional on entity/claim maps
remain represented until the relevant mapping decision is known. Known identity, scope, grouping
and global constraints are policy inputs, not post-hoc heuristics for truncating a list. A small
output does not justify dropping candidates that could affect an ambiguity or optimal assignment.

Actual migration includes `methods.math.scope._innermost/_with_reopens/_sites/resolve_scopes`
and `evaluate.semantic_alignment._entity_pairs/align_semantic`. Retire repeated full collection
scans and helper-local reconstructions of the same side metadata. Keep existing `Matcher` and
`PhraseMatcher(attr="LOWER")` preparation where it already fits; do not replace them with another
pattern engine solely for uniformity.

### Completion

The actual scope and matching operations consume model-derived preparation rather than recreating
policy per item. Independent cases challenge nested/equal extents, repeated symbols under different
scopes/macros, reopen sites, inherited classes, repeated predicates, unresolved references and
multiple equal candidates. Profile occurrence-rich documents and candidate populations where
index construction can plausibly repay its cost. Also retain a small-input route when constructing
a richer index would cost more than the required scan. No generic index framework, permanent
candidate register or extra domain authority is required.

<a id="PE-07"></a>

## PE-07 — Migrate matching and quote placement onto prepared inputs

**Source:** F06. **Prerequisites:** PE-01's comparison/outcome contracts and PE-06's side indexes
and conservative eligible edges. Quote-placement preparation can proceed independently once its
frame/context contract is implemented; it does not wait for every assignment-kernel decision.
PE-02–PE-04 supply mathematical products/comparison behavior when a candidate requires them;
this package must not define another symbolic-equivalence policy.

### Matching and dependency-sensitive computation

Separate invariant preparation/comparisons from work affected by the current entity or claim map.
Track relevant reference dependencies per comparison and invalidate affected work when mappings
change. Include conditional edges that become eligible later. If dependency completeness cannot
be established cheaply, conservatively recompute that component; do not reuse a decision merely
because the operands' raw text is unchanged. Preserve declared convergence, undecided outcomes,
comparison traces, alternative groups, counts and deterministic tie behavior.

Begin with smaller dense `scipy.optimize.linear_sum_assignment(..., maximize=True)` problems
where connected-component independence is proven. Dependencies and grouped alternatives can join
otherwise separate candidate regions; partitioning only by predicate or label is not sufficient.
`scipy.sparse.csgraph.min_weight_full_bipartite_matching` is a conditional candidate for large,
sparse regions. Before selecting it, specify maximize/minimize conversion, explicit versus absent
zero edges, dummy/unmatched vertices, infeasible full matching and tied optima. Retaining the
smaller dense route is a complete disposition when sparse semantics or construction costs do not
justify another mechanism. No greedy replacement of global matching is selected.

### Quote placement and native library boundaries

Prepare immutable sentence texts, offset/token arrays and useful quote patterns once per frame
or batch. Repeated quote/cited-anchor work may reuse an operation-local result keyed by the full
frame, macro and placement-policy context; anchor identity affects nearest-match selection.
Retain source-local remapping and evidence multiplicity even when placement computation is shared.

Pass the original `rapidfuzz.fuzz.partial_ratio` callable to `process.extractOne`. Remove the
runtime `_partial_ratio` forwarding function used to accommodate stubs; use correct typing or a
narrow typing-only cast without changing the callable. Do not copy private scorer capsules onto
a wrapper. Consider `process.cpdist` for already-paired eligible inputs and bounded `cdist` for
actual Cartesian regions. Supply the existing scorer, cutoff convention and required precision
explicitly; the APIs have different defaults. Avoid compact integer scores where rounding would
change thresholds or ties, and coordinate native `workers` with enclosing process capacity.

Retain the exact-cited → frame-exact → spacing/macro → fuzzy fallback contract, nearest-anchor
ordering, duplicate match counts, offsets, timeouts, placement labels and coarse/located/unlocated
outcomes. `regex` remains the bounded pattern/refinement mechanism; cached or batched work cannot
broaden fuzzy acceptance or turn a coarse placement into exact evidence.

Actual migration includes `semantic.proposals.locate_proposal`, the legacy production proposal
parser where still called (`methods.llm.parse`), `methods.llm.cascade`,
`evaluate.semantic_alignment`, and current agreement/reference-evaluation callers in
`evaluate.semantic`. Inventory callers of `evaluate.align` and pool/consolidation matching during
integration; migrate any shared helper consumers or preserve their explicit contract boundary.
Do not leave two nominally canonical comparison/placement implementations with different defaults.

GLiNER2 is a candidate/catalog capability, not a currently measured cost in this baseline.
`create_schema`/combined extraction and `batch_extract_entities` are relevant only to a separately
chosen extraction-mechanism substitution. They do not establish the current source-grounded
mathematical claims, qualifiers or scientific meaning. This package introduces neither that
feature nor a dependency/model download, and claims no latency reduction from deploying it.

**Library references:** [RapidFuzz processor APIs](https://github.com/rapidfuzz/RapidFuzz/blob/main/docs/Usage/process.rst),
[SciPy linear assignment](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html),
[SciPy sparse matching](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.min_weight_full_bipartite_matching.html),
[GLiNER2](https://github.com/fastino-ai/GLiNER2), plus local `rapidfuzz.md`, `scipy.md`, `regex.md`
and `gliner2.md`. Use Context7 first and actual installed/pinned sources for selection details.

### Completion and integration boundary

Matching and placement calls use their implemented preparation/eligibility contracts; obsolete
scorer wrappers, repeated token preparation and invariant comparison loops are retired. Required
negative cases preserve global ties, cycles, unknown mappings, alternative groups, exact values,
cutoff scales, repeated evidence and identical quotes under different cited anchors. Observe both
small and larger candidate populations and repeated citations; compare whole-operation work and
latency rather than a scorer microbenchmark alone. Source processing and reference evaluation
remain independent, with no human grading or quality-threshold tuning introduced.

Implementation uses targeted functional checks at coherent endpoints and the series' final
qualification owner. These are production correctness obligations, not authorization to redesign
testing infrastructure. Proposed performance benefits remain unmeasured until the relevant
production operation is exercised under named conditions. Update enduring D4/D5/D7/D8 contracts
when the implemented meanings or workflows change, through PE-00's decision route.
