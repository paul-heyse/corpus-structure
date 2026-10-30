# Extraction and relational views

**State:** Implemented and scoped Tested, 2026-10-30; the coordinator owns assembled acceptance.
**Scope:** PP-07. Current package state, opportunity dispositions and execution order belong to the
[coordinator](../parsing-pipeline_2026-10-30.md#PP-07).

## Purpose and boundaries

Deliver source inspection, useful relationship queries, attributed extraction and explainable
quote placement over the connected parsing products. Carry forward functional-review
[O03](../../functional_reviews/parsing-pipeline_2026-10-30.md#O03),
[O05](../../functional_reviews/parsing-pipeline_2026-10-30.md#O05) and the applicable O01/O02/O06
guarantees. A derived article, graph or metadata object must retain its relationship to the
selected source/build; none becomes an alternative authority for source custody or meaning.

The [target model](../../functional_reviews/parsing-pipeline_2026-10-30_target-model.md) supplies
the source/representation/occurrence/mapping distinctions. PP-01 owns their executable meanings;
PP-04 owns persisted products and selection. This document owns their use in views and extraction,
including the consumers that would otherwise reconstruct meaning independently. Conceptual
products below do not mandate one schema, worker, class or durable task per concept.

Design assessment uses core 3.3, its efficient-architecture companion, code-intelligence 1.4 and
the repository binding. The relevant qualitative choices are native relational filtering before
hydration, graph construction only for topology algorithms, preparation shared over its real
validity, and validation where a view introduces uncertainty. This plan creates neither a broad
diagnostic audit nor another alignment gate. PP-00 owns clause-level authority changes before
implementation relies on them; these proposals do not amend D1–D8 or an accepted ADR.

## Baseline and the foundation being extended

Static inspection for planning used main `b3a8313` on 2026-10-30 and the functional review's
recorded library research. It establishes the following starting points, not new runtime results:

- `ingest/profile.py` compiles cssselect2 source-profile rules. `ingest/html.py` produces an
  html5lib/lxml tree, canonical text, segments and selective author-markup observations. Retain
  the native tree and profile composition; a new selection frontend needs an actual query benefit.
- `semantic/operations.py`'s current `BoundReader.text_layouts` selects the run's producing ingest
  task and resolves `reused_task_id`; multiple candidate builds refuse. Its existing missing-layout
  and configuration-mismatch reconstruction path does not establish complete source mappings.
- `semantic/text_layouts.py` validates persisted source-bound layouts. `methods/llm/cascade.py`
  prepares frame sentences, token sequences, macro alternatives and quote results. It already uses
  RapidFuzz 3.14.6 `fuzz.partial_ratio_alignment` and `Levenshtein.opcodes`, and selects a fallback
  sentence through `process.extractOne`. `Located` records step, score, multiplicity, fuzzy edits
  and timeouts; it does not carry a full competing-placement explanation.
- `methods/llm/parse.py` applies the cascade to evidence, descriptors, unsupported items and
  phrase leaves. Unlocated quotes fall back to a cited sentence with `coarse=True`, or are dropped
  under the existing typed reason. That behavior is part of a versioned method contract.
- LinkML-derived SQLAlchemy Core 2.1.5 metadata and PostgreSQL remain the instance/query route.
  NetworkX 3.7 and Pydantic 2.14.1 are available native view/boundary tools. Extruct 0.18.0 and
  Trafilatura 2.3.1 are research candidates, not installed product dependency commitments.

The central foundation correction is to query selected products rather than recover their
origins by searching rendered text. Complete partitions and precise repaired-node mappings have
different coverage guarantees. PP-07 consumes those distinctions; an inspection API must expose
unavailable mapping coverage and refuse an exact-origin request it cannot answer.

<a id="PP-07"></a>
## PP-07 — Inspect selected source products and compose attributed views

### Readiness and delivered contract

Begin contract/query design when PP-01 supplies representation identities, occurrence/edge kinds,
coverage/outcome meanings and declared operation recipes. Implement persisted reading when PP-04
supplies actual stored products and a reader pinned to their producing build. HTML selectors and
metadata consume PP-03's qualified structure/encoding products; quote placement consumes PP-05's
source-bound text layouts; mathematical graph consumers use the relevant PP-06 occurrence or
interpretation product. Each slice can proceed when its own inputs work. PP-07 has no dependency
on every capability in those documents finishing first.

Given an explicit run/build/product selection, a request declares its representations, relation
kinds, source range or node set, required fidelity, ordering and requested fields. Return typed
occurrences, edges, mappings and/or derived observations together with their source/build/release
binding, recipe, coverage and diagnostics. A wrong representation, stale selection, unsupported
relation or missing required mapping refuses or yields the specifically declared unavailable
result; an empty list alone cannot stand for incomplete knowledge. Projection contracts come
from PP-01 rather than a second Python interpretation of relation labels.

### A. Source inspection and relational queries

Use SQLAlchemy Core `select`, joins, `exists`, bound parameters and set-shaped requests to fetch
the required populations. Source inspection must support material excluded from canonical text,
synthetic canonical separators, original/decoded/canonical ranges and many-to-many mapping
memberships. Preserve half-open coordinate units and occurrence identity in the response. Range
selection and category/relation filtering belong in the relational access path where meaningful;
loading all source text and every edge to answer a bounded inspection request is not the default.

`Select.cte(recursive=True)` is a candidate for a concrete containment/ancestry traversal. Admit it
only with the selected relation's direction, cycle behavior, scope and termination semantics;
`UNION ALL` over an arbitrary cyclic graph is not a complete traversal recipe. Exact negative
answers require the full relevant universe even when the returned node set is small. Ordering
comes from explicit child/reading positions, with a deterministic tie policy where needed, rather
than row order or object insertion order. Do not persist all paths or all-pairs closure by default.

Generate or reuse Pydantic boundary shapes, recursive models, discriminated variants and reusable
`TypeAdapter` objects from the owned contracts where they fit. Shared/cyclic topology uses node
and edge references; a nested tree is a projection with declared root/containment semantics.
`frozen=True` does not freeze nested mutable attributes, and `model_copy(update=...)` does not
validate changes. Keep owned immutable validated products through consumers that preserve their
premises; do not repeatedly serialize and revalidate unchanged rows merely to cross modules.

Migrate query/export and source-inspection entry points, source frame/packet readers and scope
or binding consumers wherever their access contract changes. Existing canonical-anchor reads may
remain canonical reads; a new original-source answer requires the selected mapping product.
Never graft a parser-specific mapping onto a content-identical shared rendition without its build.

### B. Declared native graph views

Choose NetworkX only when the named operation needs an algorithm such as cycle analysis or
dependency ordering beyond a simpler relational answer. Build `MultiDiGraph` directly from
selected rows/native products. Use occurrence identity for node identity and each structural
relationship occurrence ID as the edge key; add isolates explicitly and preserve parallel edges,
direction, relation kind, endpoint scope, positions and producing product. An RDFLib converter
that keys an edge by predicate can collapse repeated occurrences, so rows → RDF → NetworkX is
not the topology route for this contract.

Each graph operation declares its universe, admitted edge kinds, direction, ordering, allowed
cycles, treatment of alternatives, completeness and mapping of results back to domain IDs.
`strongly_connected_components` and `condensation` are useful only where cycles have a declared
meaning, retaining original member IDs. `lexicographical_topological_sort` applies to a declared
DAG and uses an explicit deterministic tie key. A cycle in a relation declared acyclic is a
typed invalid result, not an excuse to silently discard edges. Generic reachability cannot
establish binding or mathematical implication.

`subgraph_view` and `reverse_view` can avoid copying when their base is stable and remains owned
for the whole operation. Their attributes are shared: they are not independent immutable copies.
An operation permitting edits must own a workspace, validate allowed changes and produce explicit
result mappings before publication. Ordinary derived graph mutation changes no persisted meaning.
Release graph state at its last consumer, avoiding simultaneous rows, nested models, RDF and
NetworkX copies without a distinct use. Output filtering must not prune intermediate nodes
required to compute an exact result. High-degree reference structures use the declared scope and
honest partial/refusal outcomes if an operational limit interrupts the required universe.

### C. Source selectors and embedded declarations

Keep compiled cssselect2 roles as the selected source-convention mechanism. Compile lxml 6.1.3
`etree.XPath` at its actual query/profile lifetime when XPath expresses a concrete query better;
bind values rather than interpolate syntax. Namespace handling and the selected repaired tree
belong to the query recipe. Smart-string parent/text/tail/attribute information can identify an
origin node, but is not an exact source span and can retain an entire tree. Materialize small
owned scalar outputs when retaining the backing tree has no purpose. Parsel is a conditional
selection convenience only if a real consumer removes bespoke selector composition; availability
does not justify another mandatory tree parse or public selection dialect.

Evaluate extruct 0.18.0 for selected embedded declarations: `extruct.extract` with an explicit
`syntaxes` set, base URL and error policy, consuming the existing parsed tree where supported.
Microformats requires raw input; do not assume every extractor shares the tree-input route.
`return_html_node` applies to Microdata, not every syntax. JSON-LD, Microdata and RDFa results
retain their declared syntax, value, source/build, producer and available location evidence.
Resolve relative identifiers using the recorded base-URL recipe. A publisher's declared author,
date or subject is an attributed declaration, not verified domain truth or an admitted claim.
Metadata values need their own origin/coverage status when exact lexical locations are unavailable.

Decide this candidate from representative syntax/error/location cases and the actual observation
consumer. Select the smallest supported syntax subset with qualified shape/location semantics,
or defer unused syntax/candidate with a concrete consumer trigger. Ignored/logged extractor errors
must remain failed/partial coverage, never become evidence that no metadata exists. Preserve raw
declarations independently when parsing their semantics fails. Admission/consolidation consumes
the same attributed evidence boundary as other methods; no direct metadata-to-belief shortcut.

### D. Derived article and metadata views

Assess Trafilatura 2.3.1 only for an explicit main-content consumer. Its `bare_extraction` produces
a `Document` including `body`/`commentsbody`; use that structured result when selected rather than
extracting plain text and guessing which source nodes survived. The narrower
`trafilatura.metadata.extract_metadata` route is a candidate if only heuristic metadata is
requested. Record configuration, comments/metadata selection, extraction implementation and
coverage. These are heuristic derived views, independent of complete original/canonical custody.

A selected article view has its own product/representation and dependency binding. It may omit
navigation, comments or relevant context under its declared recipe; do not replace the canonical
text, segment identities, source profile roles or evidence universe with it. Any location links
use qualified mappings supplied by the actual composition. String resemblance is insufficient to
claim exact origins. A consumer requiring complete source context cannot silently receive this
view. Empty/failed extraction, missing metadata and excluded material have distinct outcomes.

The selection exit is either an implemented, consumer-used derived view with tested attribution
and limits, or a reasoned defer of the optional article/heuristic-metadata capability with a named
future consumer trigger. PP-07's required inspection, attribution and quote behavior remains in
scope whichever outcome wins. Neither deferral can hide PP-02/PP-03's required fidelity work.

### E. Explainable quote placement over shared coordinates

Extend `Cascade`, `PlacementPolicy`, `Located` and `QuoteRecord` coherently, or replace their
method boundary under an explicit new recipe if that is simpler. Inputs are authored quote,
resolved frame/sentence selection, source-bound text/token layout, effective macro context and
placement policy. Output retains the canonical occurrence span, selected sentence, stage,
ambiguity, score/cutoffs, timeout outcomes and the candidate/alignment evidence needed to explain
that decision. An original-source request follows PP-04's selected mapping and carries its
fidelity; it does not relabel a canonical offset as an original offset.

Preserve exact-cited, exact-frame, spacing/macro and token/character distinctions unless their
versioned contract deliberately changes. Reuse prepared candidate strings and quote layouts.
For competing sentence retrieval, evaluate RapidFuzz 3.14.6 `process.extract` with an explicit
`limit`, scorer and `score_cutoff`, or `extract_iter` when cutoff-filtered streaming fits the
consumer. A candidate cap bounds what was examined/returned and cannot establish uniqueness
outside that universe. Keep deterministic tie and cited-sentence preference in the admitted
recipe. Compare these options with the current `extractOne` route using repeated/near-equal
quotes; select richer candidates when the explanation consumer needs them, otherwise preserve
the simpler qualified route and state its narrower ambiguity guarantee.

Use `fuzz.partial_ratio_alignment` for candidate windows and `Levenshtein.opcodes` for native
sequence alignment, storing compact edits/interval witnesses mapped back through the shared token
layout. Long-needle partial alignment is not a guarantee of the unique globally optimal location.
Do not describe a score as exact identity or silently reuse its window as proof of origin.
`process.cpdist` fits already selected pairs if that workload exists; `cdist` is a dense Cartesian
operation, not an index or a reason to compare every quote with every sentence. Native cutoffs,
scope selection and shared normalization should remove unnecessary work before adding concurrency.

Migrate all placements in `methods/llm/parse.py`, authored proposal/golden fixture processing,
packet/source frames and exposed diagnostics together where their payloads change. Preserve
current coarse/drop semantics or explicitly change the method's admitted output/coverage contract
and every consumer. A sentence-only fallback remains coarse; a fuzzy placement remains heuristic.
Any stage, cutoff, tie rule, span snapping or library behavior change that can alter placement
requires a new cascade/method recipe version. Old observations retain their archived version and
coordinates. Parsing-policy changes do not automatically change evaluation/grading policy.

## Integration, failures and completion

PP-07 can deliver source queries before optional article extraction, and graph algorithms only
for the projections that need them. Each delivered slice migrates its actual producers/readers;
PP-10 integrates the selected capability union rather than repairing deferred internal consumers.
Exported RDF/SHACL, if used by a selected consumer, retains occurrence nodes for repeated
assertions and an explicit named-graph scope. Validation selects that graph deliberately rather
than accidentally validating a Dataset union; inference/rules remain separately admitted derived
work. Do not add RDF conversion merely to feed NetworkX.

Scoped acceptance during implementation must distinguish:

| Scenario | Required observable behavior and independent expectation |
|---|---|
| Excluded script, duplicate attributes, implied node and synthetic separator | Inspection returns the selected original/canonical components with correct categories and coverage; exact unavailable origins remain unavailable. Hand-authored source spans challenge the mapping producer. |
| Parallel relation occurrences, isolate, ordered children and cycle | Direct-row and graph answers preserve independent edge IDs, order and isolates; legal cycle analysis differs from acyclic-relation refusal. Expected memberships/order come from a small independently specified graph. |
| Missing product, two content-identical builds or a reused origin | The reader resolves the selected effective origin; ambiguity refuses; a shared rendition never selects provenance implicitly. |
| Relative embedded metadata and malformed syntax | Declaration attribution, base URL, location availability and partial/error coverage survive publication and query; malformed extraction cannot imply absence. |
| Optional article view | Consumer sees an explicitly derived incomplete source view with independent product identity; excluded context remains inspectable through full custody. |
| Repeated quote, typo, macro spelling and non-ASCII normalization | Competing candidates, stage, edit witness, uncertainty and canonical offsets agree with independently annotated examples; ties do not become exact identity. |
| Timeout, coarse fallback and no cited sentence | Existing or deliberately versioned failure/coverage behavior reaches every affected parse consumer and diagnostic/export surface. |

Use targeted Python tests of the changed query/cascade/adapter and native PostgreSQL tests for
actual persisted selection/integrity behavior. Existing test homes include
`tests/llm/test_prepared_cascade.py`, ingest/profile tests and semantic reader/publication tests
under `python/corpus-structure/`; select exact commands from the implemented footprint. Product
tests, measurements and integrated qualification are **not_run** for plan authoring. No latency or
capacity improvement is established by these planned mechanisms; PP-10 owns assembled functional
qualification and any separately justified measurement.

## Mechanism sources and decision limits

The functional review's 2026-10-30 installed/tagged-source findings are the source baseline for
these API choices. At execution, use Context7 first for changed API questions, then the pinned
primary/installed sources; version additions remain deliberate exact pins. Useful precise leads:

- [SQLAlchemy Core selectable/recursive CTEs](https://docs.sqlalchemy.org/en/21/core/selectable.html),
  [lxml XPath and smart strings](https://lxml.de/xpathxslt.html),
  [cssselect2](https://doc.courtbouillon.org/cssselect2/stable/).
- [NetworkX 3.7 MultiDiGraph](https://networkx.org/documentation/stable/reference/classes/multidigraph.html),
  [graph views](https://networkx.org/documentation/stable/reference/classes/graphviews.html),
  [topological ordering](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.lexicographical_topological_sort.html).
- [Extruct 0.18.0 extractor composition](https://github.com/scrapinghub/extruct/blob/v0.18.0/extruct/_extruct.py),
  [Trafilatura extraction API](https://trafilatura.readthedocs.io/en/latest/corefunctions.html),
  [Trafilatura source](https://github.com/adbar/trafilatura).
- [RapidFuzz process retrieval](https://rapidfuzz.github.io/RapidFuzz/Usage/process.html),
  [partial alignment](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html#partial-ratio),
  [Levenshtein opcodes](https://rapidfuzz.github.io/RapidFuzz/Usage/distance/Levenshtein.html#opcodes),
  [Pydantic recursive boundaries](https://docs.pydantic.dev/latest/concepts/forward_annotations/).

Candidate feasibility is resolved within PP-07 before dependent consumers commit to it. Source
fidelity limitations remain owned by the coordinator's PP-02/PP-03 route even if an optional
extraction candidate is deferred; library availability or schema conformance cannot close them.

## Selected implementation mechanisms — 2026-10-30

The coordinator's remaining-scope execution account owns current qualification. The implementation
uses Core range/category predicates, ordered endpoints and a cycle-safe recursive `UNION` for
selected prerequisite closure. Public source inspection/trace and bounded batch exports consume
those selected products. Canonical packet/frame consumers retain their existing canonical
anchor contract; they do not claim original offsets. M09/M11/M13 consume selected text products.
Placement recipe `citation-cascade-2` uses RapidFuzz cutoff-filtered candidate populations,
`partial_ratio_alignment` and Levenshtein edit witnesses while retaining tie, coarse and failure
semantics. The versioned policy participates in the admitted analysis profile.

| Capability | Selected disposition and concrete revisit trigger |
|---|---|
| Source role selection | Retain compiled cssselect2 against the existing repaired tree. A query requiring namespace-aware structural predicates beyond those roles triggers a compiled XPath assessment; no second tree parse is justified now. |
| Parsel selector facade | Deferred: no current caller exposes a selector dialect or needs composition beyond the compiled roles. Revisit when such a caller removes actual duplicated selection logic. |
| Embedded JSON-LD/Microdata/RDFa | Deferred optional observation family: current packs have no publisher-metadata method/output contract. Revisit with a selected attributed-declaration consumer and its supported syntax/base-URL/location contract. Original excluded bytes and source inspection remain available now. |
| Trafilatura article/heuristic metadata | Deferred optional derived view: no current extraction consumer requests a heuristic article subset. Revisit when a named reader needs that subset and can preserve its incomplete-view identity and excluded context. |
| NetworkX source graph | Deferred: current inspection, ordering and tracing questions are bounded relational reads, not graph algorithms. A source topology/cycle-analysis consumer with a declared universe triggers direct MultiDiGraph projection, including isolates and edge occurrence keys. |
| SQLAlchemy ORM navigation | Deferred: no mutable entity-navigation consumer replaces the fixed immutable product/read model. Revisit only with such a consumer; Core/native integrity remains authoritative. |

These are dispositions of conditional candidates, not deferrals of mandatory decomposition,
source attribution, independent edge identity, quote placement or public inspection.
