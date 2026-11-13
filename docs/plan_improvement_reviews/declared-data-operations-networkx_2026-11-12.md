# NetworkX improvements to the declared-data-operations redesign

**Proposed recommendations ·2026-11-12.** Reviews the complete remaining DDO-00–12 change
footprint at 264c5f47c1c5a2a5fd428f510da27fad49102f6d:
[coordinator](../plans/declared-data-operations_2026-11-12.md) and its seven supporting plans.
All packages remain unimplemented. Product source 8c0f4f951 is unchanged. Root synthesis with
bounded independent library/representation and dependency-design contributions; no plan amendment
or production adoption is made by this review.

The root read all 2,694 lines of the [NetworkX reference](../libraries/scientific_compute/networkx.md),
including the complete advanced addendum. Its operator-owned working-copy SHA256 is
0d801decfc5ee475533a24377088508585d02c7044aa97cff3b8b077d5669da7. It is uncommitted input,
not silently included in this publication. NetworkX 3.7 is installed and exactly selected; namespace and
signature inspection and contract analysis use that version's source and primary documentation. Overview
examples and function names are leads, not guarantees of complete feature/backend compatibility.

Applied core 3.3, efficient-architecture heuristics, code-intelligence 1.4, test-assessment 1.2 and
repository binding. This is a plan-improvement inquiry, not a new broad diagnostic audit or an
implementation-completion audit. F01–F14/C1–C7 and accepted RC01–09 retain their DDO owner.
Other plans supply no scope or qualification prerequisite.

## Combined result

NetworkX can take a fuller role in the proposed model's **derived graph computations**, including
runtime demand/support and preservation projections. The current compile-time-only wording is
unnecessarily narrow. Its domain model, persisted bindings, authorization, completeness, choice
compatibility and publication remain governed by the declared contracts and native kernel.
NetworkX is not itself a typed schema, a transaction manager or an AND/OR sufficiency interpreter.

Recommend I01–I06 as coherent amendments; I07 adds focused qualification/inspection support.
Optional analytics and acceleration receive explicit conditional or no-current-fit judgments below.
The strongest gains are one faithful projection contract, reusable dependency/closure algorithms,
better explanations and fewer private traversals. Broad adoption of every graph algorithm would
add machinery without strengthening the model. No numerical throughput or memory gain is claimed.

## Current footprint and useful strengths

Paths in this section are relative to python/corpus-structure/src/corpus_structure/.

| Owner | Observed contract and review significance |
|---|---|
| evaluate/alignment_preparation.py:52–150 | CandidateComparisons already uses SCC condensation/descendants for invalidation, including changed components, absent lookups and conservative unknown/global dependencies. Reuse this pattern's semantics rather than assuming no graph invalidation foundation exists. |
| evaluate/characterization_assessment.py:301–350 | Rooted MultiDiGraphMatcher preserves canonical node payload, edge meaning/multiplicity and shared identity; direct label-only replacement could weaken assessment. |
| evaluate/task_semantics.py:1267–1505 | Reified assertions/choices and role edges; exact complete slots versus monomorphism; downstream joint-choice checks consume actual mappings. |
| semantic/characterization.py:281,395,724,842 | Private DFS and typed layer/choice/reading closure coexist with archived-release/source validation. Topology can be delegated; authentication and semantic support cannot be dropped. |
| serve/review_bundle.py:1360 onward | Exact closure is a bounded authenticated worklist over declared predecessor types, not arbitrary JSON-reference crawling. |
| ingest/pdf_hierarchy.py:131,408; serve/selected_source.py:756 | Ordered source hierarchy, exact native pointers, direct/descendant membership and detached custody exceed plain graph reachability. |
| semantic/record_interpretation.py:450–499 | A connectivity-only factor-scope star is adequate because actual potentials and inference semantics remain elsewhere; do not force a richer physical graph here. |
| ingest/pdf_candidates.py:261–330 | Existing shape-intersection components compose with spatial indexing. No replacement is justified solely by more graph APIs existing. |

The planned [compiler](../plans/declared-data-operations/contracts-and-compilation.md) already selects
DiGraph plus separate semantic edges/SCCs, while [change](../plans/declared-data-operations/change-reuse-and-consolidation.md),
[demand](../plans/declared-data-operations/demand-planning-and-execution.md),
[storage/support](../plans/declared-data-operations/products-and-support.md),
[interfaces](../plans/declared-data-operations/interfaces-and-evaluation.md) and
[preservation](../plans/declared-data-operations/preservation-adoption-and-qualification.md)
need runtime and retained projection semantics. Those are the integration boundaries below.

<a id="I01"></a>
## I01 — Declare reusable, snapshot-bound graph projections

**Recommend · DDO-01–04/09/10; FP-04/05, DP-04/07/09, CI-03/05/13.** Add a shared typed
GraphProjection specification to the governing model: source snapshot/selection and contracts,
node and relationship kinds, orientation, identity, role/order/multiplicity, isolates/unresolved
endpoints, input universe versus output selector, completeness and attribute/weight meaning.
An algorithm invocation names that projection, parameters and result contract. These are model
facts, not independently edited graph settings or a second registry of operation policy.

Choose the physical view for the question from the same admitted records; do not always build both. A DiGraph connectivity projection
supports reachability/SCC/DAG algorithms, with explicit endpoint-to-semantic-edge witness mapping.
A keyed MultiDiGraph or operation/derivation incidence projection retains role multiplicity and
n-ary bindings for assessment and support inspection. Keep typed canonical semantic-edge records;
never canonically serialize NetworkX iteration order, component numbers or incidental attribute dicts.
Include isolated declarations and validate every referenced node instead of inventing an untyped
node when add_edge auto-creates it. Compare direct MultiDiGraph use per algorithm; it is not a
universal replacement for typed persistence or the already adequate connectivity projection.

Build each owned graph from one immutable effective model or selected native snapshot. Release it
after its useful analysis lifetime; reuse by complete projection identity where useful. Do not keep
a live full-database NetworkX mirror. Preserve original node/member IDs and explicit incidence;
one-mode bipartite projections are additional analyses, not neutral representations of support.

Use `subgraph_view`/`reverse_view` and reporting views inside that private lifetime when they preserve
the required universe. Filters bind immutable parameters; they cannot read changing latest state.
`freeze` protects topology only; shallow copies/views share nested attributes. Keep attributes
immutable/owned and export detached typed values; make an explicit independent copy only for a real
mutation consumer. Do not build deep chains of repeatedly evaluated views.
[Classes/views](https://networkx.org/documentation/stable/reference/classes/index.html),
[freeze](https://networkx.org/documentation/stable/reference/generated/networkx.classes.function.freeze.html),
[relabeling](https://networkx.org/documentation/stable/reference/generated/networkx.relabel.relabel_nodes.html).

Acceptance challenges: parallel roles with same endpoints, an isolate, unresolved endpoint,
repeated spelling with distinct source identity, live attribute aliasing, view/source mutation,
noninjective relabeling and matrix/index remapping. A valid projection must preserve the declared
meaning, not merely yield the same untyped node count.

<a id="I02"></a>
## I02 — Share topology kernels while retaining semantic closure policies

**Recommend · DDO-02/05/09–11; DP-08/10/13/16, CI-04/05/11.** Use `ancestors`, `descendants`,
BFS/DFS/edge traversal and SCC decomposition over I01 projections for rooted contract closure,
reverse change impact and exact retained-reference/preservation navigation. Include the changed
root/component itself: descendants excludes it. Traverse declared predecessor relationships only;
a generic recursive scan of JSON keys would fabricate dependencies.

The owning declaration determines permissible role transitions, selected alternatives, source /
contract/trust scope and population completeness. Acquisition authenticates each selected product
and maintains existing row/byte/custody bounds. The library supplies adjacency and traversal, not
those decisions. Retain role-qualified witness edges and reason codes for included/excluded members.
Disconnected/missing evidence remains explicit. Use a single bounded witness path for an explanation
where sufficient, not all_simple_paths or a globally materialized closure. Edge traversal, rather
than only a BFS tree, is needed when parallel/non-tree relationships are part of the result.

For large live queries retain PostgreSQL indexed/recursive set operations where locality and native
admission favor them; an in-memory projection is useful when several topology algorithms reuse a
bounded selected graph. Detached closure may use its existing indexed SQLite source. Compare whole
acquisition/materialization/analysis/rejoin, not isolated BFS time. Replace private topology loops
such as _acyclic only when their semantic owner and error/custody behavior have migrated.
[Traversal](https://networkx.org/documentation/stable/reference/algorithms/traversal.html),
[DAG reachability](https://networkx.org/documentation/stable/reference/algorithms/dag.html).

Acceptance: diamond/reconvergent dependencies, cyclic type graph, selected versus retained layers,
missing upstream member, a newly present previously absent input, cross-page references and filtered
output whose required intermediate nodes lie outside the returned scope. Use independently specified
expected memberships and diagnostic witnesses, including incomplete/refused outcomes.

<a id="I03"></a>
## I03 — Analyze declared and bound dependency graphs separately

**Recommend · DDO-01/02/05/06/08/09/10; FP-03/07, DP-12/19/20, H22.** Compile a potential dependency
graph for model validation and a frozen bound-request incidence graph for actual selected demands.
Label their different universes. Optional/alternative producers can create cycles in a potential
graph that do not occur in the selected binding; neither projection can silently define validity
for the other. Native relational sufficiency still resolves exact-one/all-of/alternative/coverage
requirements. A plain reachability edge cannot encode them all.

Use SCC + condensation + stable lexical topological ordering for compilation and impact diagnostics.
Preserve original SCC members and internal witnesses; condensation does not solve a fixed point or
make an unsupported execution cycle valid. Use find_cycle for a bounded error witness instead of
exhaustive simple-cycle enumeration. Sorted semantic IDs provide reproducible presentation; NetworkX
component IDs and arbitrary valid topological orders are not semantic identities.

Use topological_generations for structural explanations and revealing overbroad barriers; do not
enumerate all antichains during normal planning. The live frontier replenishes whenever actual
prerequisites settle, without a generation barrier. `dag.antichain_width` is an optional exact structural diagnostic, not an admission limit:
its implementation uses transitive closure and matching. Unweighted DAG longest paths explain structural depth. Weighted paths
require declared edge weights, or an explicit lowering of node costs to edge weights; measured
durations are not invented estimates. No new numerical cost model or mandatory instrumentation is proposed.
[SCC/condensation](https://networkx.org/documentation/stable/reference/algorithms/component.html),
[antichain_width](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.antichain_width.html).

**Observed diagnostic defect, source-inspected 2026-11-12:**
`semantic/domain_operations.py:1646–1663` drains `TopologicalSorter` and labels every residual
source claim “cyclic source claim reference.” A downstream acyclic claim blocked by a cycle is
also residual. DDO-08 migrates this exact authored-claim path: distinguish SCC cycle members
(including singleton self-loops) from descendants blocked by cyclic premises, and retain independent
publishable claims and partial coverage. This is a proposed repair, not a reproduced test result.
The existing CandidateComparisons composition already supplies a useful implementation pattern.

For DDO-09, descendants produce potential-impact candidates, not an eager stale-all rule. Recheck
admissibility/substitution and stop propagation at equal admissible value/support. Newly applicable
subjects, absent-to-present inputs and closed-population deletions need their declared discovery
witnesses; existing lineage cannot reveal never-derived subjects.

Acceptance: self-loop, cycle with an acyclic downstream tail and unrelated component, valid recursive
type, unsupported bound cycle, selected alternative removing
a potential cycle, independent ready work at different depths, delayed discovery, all parents needed,
partial population and a locked/running producer. No graph-empty result can establish demand exhaustion.

<a id="I04"></a>
## I04 — Make structural comparison an explicit family of contracts

**Recommend · DDO-02/08/10/12; DP-04/08/11/23, CI-02/06/12.** Preserve distinct comparison modes:
identity-sensitive equality, exact rooted attributed isomorphism, required-pattern monomorphism,
induced matching and optional explanatory edit correspondence. Each declares its projection,
semantic attributes, edge multiplicity and completeness. Existing MultiDiGraphMatcher with canonical
edge counters remains the selected baseline for typed assessment; retain asymmetric partial expected
fields and post-mapping joint-choice evaluation. Do not remove useful independent controls.

VF2++/ISMAGS features genuinely exist in 3.7, but their contracts are not drop-in equivalents of these
callbacks. Evaluate them only for a compatible declared subproblem. Symmetry pruning must preserve
any mapping distinctions used by downstream choice checks. WL hashes can prefilter a supported
simple attributed projection; they are neither canonical product IDs nor proof of isomorphism and
must never replace DDO-02's semantic identity. graphs_equal is identity-sensitive utility equality,
not validation of arbitrary nested application semantics.

Largest common subgraphs and bounded graph-edit paths can enrich developer explanations of changed
contract structure. Keep mappings proposed, anchored and cost-policy-relative; a timeout/best-found
result is not an optimum or reviewed migration correspondence. Native semantic member diffs remain
authoritative change facts. Structural absence in an incomplete projection is not semantic absence.
[Isomorphism](https://networkx.org/documentation/stable/reference/algorithms/isomorphism.html),
[graph hashing](https://networkx.org/documentation/stable/reference/algorithms/graph_hashing.html),
[edit paths](https://networkx.org/documentation/stable/reference/algorithms/similarity.html).

Acceptance: reordered local IDs, same topology/different role, duplicate parallel edges, shared versus
split binder, induced versus noninduced triangle, partial expected fields, crossed choice prerequisites,
symmetric mappings distinguished by joint queries, and an interrupted edit search with explicit limits.

<a id="I05"></a>
## I05 — Explain hierarchy, support and reductions without erasing evidence

**Recommend bounded paths/member explanations; other analyses conditional · DDO-05/09–11; DP-07/21, CI-01/04/09.** Reuse declared
incidence and document-hierarchy projections for common ancestry, component/member summaries,
dependency paths and support-overlap explanations. Preserve ordered source pointers and original
context; tree recognition, arborescence and DAG ancestry have different contracts. A DAG LCA can
return one of several incomparable answers; report the complete required set through an explicit
owned selection or expose ambiguity, rather than promoting one library result to unique shared context.

Expose SCC member/witness mappings when reporting dependency diagnostics. A grouped display consumer
may additionally justify quotient or transitive-reduction projections with mappings back to original
members/edges; no new display is required for core delivery. Keep original direct dependency/support relationships authoritative.
Reduction preserves reachability, not a meaningful direct role, attributes, weight or independent
support. dedensify/SNAP are conditional summaries only where their encoding/reconstruction contract
matches the selected edge families; never run ordinary support algorithms on compressor nodes by
assuming they are original entities.

Cuts, articulation points, dominators and disjoint paths can expose structural choke points in a
specified support graph. They do not prove causal necessity, trust independence or sufficient support
in an AND/OR system. Native binding/trust evaluation owns those meanings. Bipartite projections,
butterflies and overlap/redundancy measures can report shared sources without creating additional
independent votes. One-mode clique expansion is unnecessary when the two-mode question suffices.
[LCA](https://networkx.org/documentation/stable/reference/algorithms/lowest_common_ancestors.html),
[dominance](https://networkx.org/documentation/stable/reference/algorithms/dominance.html),
[reduction](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.transitive_reduction.html),
[summarization](https://networkx.org/documentation/stable/reference/algorithms/summarization.html).

Acceptance: multiple DAG LCAs, disconnected source roots, opposite edge direction, parallel support
from one origin, alternative versus joint support, retained direct edge removed by display reduction,
and a quotient with exact member/witness expansion. Preserve partial/unexamined scope and stable pins.

<a id="I06"></a>
## I06 — Give graph execution and interchange explicit lifecycle contracts

**Recommend native policy now; acceleration conditional · DDO-03/06/09/10; DP-09/15/18/20.**
Declare backend/capability choice per graph operation and pin it with the execution projection.
For admitted core invocations, explicit `backend="networkx"` prevents ambient backend priorities from
redirecting the call. Optional fallback must be an admitted execution policy; a mandatory unsupported
invocation is unavailable/refused. These are execution-profile facts, not new semantic recipe salts
unless the numerical/result interpretation actually changes.
Keep NetworkX global configuration out of concurrent request mutation. A backend conversion cache
is not a semantic cache or automatically synchronized replica. Own immutable graph snapshots and
conversion lifetime; direct attribute mutation can bypass cache invalidation. Explicitly qualify
fallback, graph/attribute support, algorithm semantics and result mapping.

Core 3.7 is installed; optional accelerated backend adoption needs a concrete supported operation,
exact selected package/environment, conformance and a plausible complete-workload route. Compare
explicit dispatch with backend-native graph construction and conversion amortization. CPU parallel
work must share admission with existing pools; GPU graph work must share capacity with NLP providers.
NLP CUDA defaults do not establish graph-backend coverage or benefit. No backend installation,
new generic backend or automatic hardware-driven policy is selected by this review.

Native SQL/typed records stay durable authority. Import exact semantic node/edge IDs explicitly;
pandas numeric coercion or integer relabeling cannot define them. Matrix/sparse operations retain
nodelist/index mapping, isolates, missing versus zero edges, aggregation and parallel-edge loss.
GraphML/GEXF/DOT/node-link are optional derived interchange/display formats, not a replacement for
canonical domain serialization. Nested attributes, IDs and endpoint keys need an explicitly qualified
roundtrip. Use authenticated selected closure and source/support metadata, not protected labels.
[Backend contract](https://networkx.org/documentation/stable/reference/backends.html),
[conversion](https://networkx.org/documentation/stable/reference/convert.html),
[read/write](https://networkx.org/documentation/stable/reference/readwrite/index.html).

Observed environment, 2026-11-12: core 3.7; algorithm/generator/class backend priorities empty;
conversion caching enabled; fallback disabled. Only the `nx_loopback` test backend entry point is
present, with no backend-info entries. Neither nx-parallel nor nx-cugraph execution is established.
This observation is not evidence of throughput, backend parity or hardware saturation.

Acceptance: native fallback/refusal, mixed unsupported attributes, immutable snapshot reuse versus
stale cached conversion, zero/nonedge and multiedge conversion, exact large integer IDs, absent
isolates, pinned node ordering and result/continuation reuse across incompatible projections.

<a id="I07"></a>
## I07 — Use revealing graph fixtures and inspectable results

**Recommend · DDO-01–12; DP-06/13/21/23, CI-12.** Use path/cycle/tree/diamond/bipartite generators
and deliberate perturbations to build bounded independent semantic cases. Generators supply topology,
not correct role/coverage/trust expectations. Keep expected canonical bytes/memberships and invalid
outcomes independently authored. Record seed/version when random perturbations are useful; avoid
claiming cross-version exact randomness or an architecture-lint framework.

Expose model-derived graph results through the existing pinned native/ci/MCP inspection contract.
Optional multipartite/BFS/spring or Graphviz layouts can render a selected dependency/support view
with original IDs and expandable evidence; coordinates do not define identity or ordering. Prefer
one bounded result plus node coordinates to a new rendering service. No new visualization dependency
is required for core planning/qualification. Reuse actual graph-assessment protection in DDO-10/12,
not merely tests that compute expected closure through the same NetworkX operation.
[Generators](https://networkx.org/documentation/stable/reference/generators.html),
[layout/drawing](https://networkx.org/documentation/stable/reference/drawing.html).

## Adoption order, interactions and authority

Settle I01's projection and ownership contract during DDO-01–03. I02/I03 then supply shared graph
kernels for compiler and actual bound-runtime projections, designed alongside native query/admission.
I04 consumes these projections while preserving independent assessment. I05/I07 add bounded inspectable
results through DDO-10 and preservation checks in DDO-11. I06 applies wherever a graph algorithm
executes; optional acceleration does not block core delivery. These recommendations are coherent
amendments, not seven new mandatory services or stages.

Revising compile-time-only wording is a proposed mechanism change, not removal of PostgreSQL
transactional authority. RC01–09 remain accepted; this review approves no new rule change. Any new
choice that actually changes their guarantees must use the existing decision route. DDO owns
scheduled findings and qualification. Broader analytics/optimization opportunities below remain
separate unless a concrete integration consumer is selected; existence of an API is not scope.

## Feature coverage and selected-version judgments

The tables cover the families shortlisted from both parts of the supplied overview and the related
alternatives that could change their selection. **Recommend** means a proposed amendment to remaining
DDO work, not adoption. **Retain** preserves an adequate mechanism. **Conditional** names the concrete
consumer/contract that would earn an extension; it is not deferred mandatory scope. **No current fit**
means the inspected footprint supplies no justified consumer, not that the library lacks the feature.
All judgments are **Proposed**. Selected-version API/source inspection is **Interface-checked,
2026-11-12**; no algorithm-output equivalence or performance qualification is implied.

Links below target upstream 3.7 source where version-sensitive. Stable documentation links in I01–I07
were checked against the selected 3.7 contract. Installed source paths are relative to
`.venv/lib/python3.14/site-packages/networkx/`. The `types-networkx` stub is
3.6.1.20261029; newly selected 3.7 APIs need ordinary typing integration checks during implementation,
not an assumption that a missing stub or top-level export means the implementation is absent.

### Representation, closure and dependency algorithms

| Capability and primary source | Judgment, actual use and decisive contract |
|---|---|
| [Graph/DiGraph](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/classes), keyed MultiGraph/MultiDiGraph | **Retain/select, I01.** Compiler connectivity uses DiGraph plus canonical typed edge records; assessment uses MultiDiGraph. Repeated simple edges update one record; keyed multiedges retain occurrences, but reusing a key updates one edge. Generated integer keys cannot become semantic IDs. Add isolates and validate endpoints before insertion. |
| [Incidence/bipartite structure](https://networkx.org/documentation/stable/reference/algorithms/bipartite.html) | **Recommend, I01/I03**, where operation, derivation or role occurrences are themselves meaningful. Explicit typed sides, occurrence identity and conjunction/alternative groups retain n-ary meaning. A bipartite attribute is convention, not validation. No universal edge-to-node lowering: compiler connectivity does not need it. |
| [Node/edge/degree reporting views](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/reportviews.py) | **Recommend bounded use, I01/I07.** Degree, directional edges and `edges(keys=True,data=True)` expose the selected projection. Views remain live; emit detached typed results within the owned snapshot. Degree counts can count occurrences rather than unique neighbors; name the intended measure. |
| [Subgraph/reverse/filter views](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/graphviews.py), [copies/freeze](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/function.py) | **Recommend ownership contract, I01.** Reuse private immutable adjacency for reverse impact and selected closure. `freeze` leaves attributes mutable; independent shallow graph copies still share nested values. Top-level `nx.to_directed`/`to_undirected` return views, unlike ordinary default graph-method copies. No revision snapshot through a live view. |
| [Dictionary factories/subclasses](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/graph.py) | **No current fit.** Storage customization does not establish typed identity or immutability. Shared thin-graph edge dictionaries are unsuitable for distinct role attributes. Ordinary compact immutable payloads suffice; reconsider only a concrete representation constraint. |
| [Relabeling](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/relabel.py), [graph algebra/operators](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/operators) | **Conditional private preparation.** Preserve qualified IDs and explicit mappings. Noninjective relabeling merges nodes and may change multiedge keys; composition can overwrite shared attributes. Union/intersection/difference/complement are graph operations, not semantic revision merge, absence or trust logic. |
| [SCC/condensation](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/components) | **Recommend, I02/I03.** Closure, canonical finite references, impact and precise authored-claim diagnostics. SCC membership distinguishes cycle members from downstream blockage; include a singleton self-loop. Condensation preserves a member mapping, but drops internal edges/attributes; component integer IDs are local. |
| [Connected/weak/strong components](https://networkx.org/documentation/stable/reference/algorithms/component.html) | **Retain existing connectivity consumers.** Factor-scope connectivity, geometry candidates and guarded assignment decomposition already use appropriate components. Operation independence additionally requires all declared constraints; disconnected projection alone is insufficient when omitted globals/cross-component choices exist. |
| [Attracting components, semiconnectedness](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/components), [flow hierarchy](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/hierarchy.py) | **Conditional topology inspection only.** Terminal SCCs can describe sinks in a pinned dependency graph; semiconnectedness describes comparability and flow hierarchy cyclic-edge prevalence. None proves demand completion, successful terminal output, admissible hierarchy or a valid iteration contract. No mandatory DDO operation selected. |
| [Ancestors/descendants/transitive closure](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dag.py) | **Recommend rooted reachability, I02/I03.** Include roots themselves; reverse orientation explicitly for impact. Materialize full transitive closure only for a real all-pairs consumer. Native selective traversal and unknown/absence witnesses remain meaningful alternatives. |
| [BFS/DFS/edge traversal](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/traversal) | **Recommend, I02.** Replace topology bookkeeping over authenticated adjacency, not acquisition/custody policy. Tree traversal alone omits non-tree/parallel relationships needed by exact export. Selected result bounds must not erase required intermediate nodes. |
| [Shortest paths](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/shortest_paths), simple paths/cycle witnesses | **Recommend one bounded explanatory path where sufficient.** Unweighted BFS is adequate for fewest-hop explanations. Weighted Dijkstra/Bellman–Ford require a declared weight interpretation/negative-weight policy. Prefer located `find_cycle` plus SCC membership to enumerating all cycles/paths; no all-pairs computation merely for one explanation. |
| [A*](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/shortest_paths/astar.py), [beam search](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/traversal/beamsearch.py) | **No current exact-closure fit; conditional heuristic candidate search.** A* caches the first node heuristic; admissibility/cutoff assumptions must hold. Beam pruning loses completeness. Neither can establish that required support, export closure or executable work is absent. |
| [Node/edge boundaries](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/boundary.py) | **Recommend bounded explanation, I02/I05.** Show obligations crossing selected/affected scope, retaining role witnesses and direction. Incoming boundary needs reversed orientation; validate requested nodes because absent nbunch members may be ignored. A boundary is not complete authenticated closure. |
| [Topological sort/generations](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dag.py) | **Recommend, I03.** Stable semantic key for `lexicographical_topological_sort`; generations are explainable levels. Native readiness admits C after B even while unrelated A in the same generation runs. Never schedule generation barriers or infer exhaustion from no currently claimable node. |
| [Antichains/antichain_width](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.antichain_width.html) | **Conditional on-demand structure diagnostic.** Selected namespace is `nx.dag.antichain_width`; implementation builds transitive closure then bipartite matching. Width describes incomparable dependencies, not feasible CPU/GPU/provider concurrency. Do not enumerate all antichains or add width to routine admission. |
| [DAG longest paths](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dag.py) | **Conditional explanation, I03.** Unweighted depth is structural; a runtime critical path requires meaningful declared weights and scope. Supply deterministic topological order when ties are observable. No synthetic duration estimator or new cost-accounting machinery. |

### Comparison, hierarchy, support and restricted optimization

| Capability and primary source | Judgment, actual use and decisive contract |
|---|---|
| [VF2 attributed GraphMatcher/MultiDiGraphMatcher](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/isomorphism/vf2userfunc.py) | **Retain, I04.** Root/focus, canonical node meaning, typed edge counters, multiplicity, shared binders, expected-field asymmetry and mapping-dependent joint choices all matter. Complete-slot isomorphism differs from non-induced witness monomorphism and induced matching. Migrate the domain projection without weakening these contracts. |
| [VF2++](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/isomorphism/vf2pp.py) | **Conditional exact symmetric subproblem; no direct replacement.** 3.7 has whole-graph, induced-subgraph and monomorphism APIs. Public matching uses one node-label attribute/default, not arbitrary node/edge callbacks. Faithful incidence lowering could encode exact labels but adds conversion/lifting and does not reproduce asymmetric expected-field matching. |
| [ISMAGS and largest common induced subgraphs](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/isomorphism/ismags.py) | **Conditional, no scoring replacement selected.** 3.7 supports directed/multigraph handling and monomorphism. Its partitions require equivalence-compatible matching; partial expected fields are asymmetric. Symmetry pruning is safe only if downstream choice checks are invariant under suppressed mappings. Keep full VF2 mappings unless equivalent acceptance is established. |
| [graphs_equal](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/misc.py) | **Conditional physical regression helper.** `networkx.utils.graphs_equal` compares actual IDs/keys, adjacency and attributes, with no bijection search. DDO-02 still compares canonical typed semantic bytes; arbitrary nested payload equality remains the domain owner's contract. |
| [WL graph/subgraph hashes](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/graph_hashing.py) | **No current adoption.** Potential future candidate prefilter, followed by exact comparison, for a supported simple attributed projection. Selected implementation rejects multigraphs; label/direction/iteration/version changes affect fingerprints. Equal hashes are not isomorphism, canonical identity or an admissible reuse proof. |
| [Graph edit distance/progressive edit paths](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/similarity.py) | **Conditional separate explanation feature.** Costs/callbacks define similarity; defaults can ignore attributes. Exact search is hard and interrupted best-found paths are not certified minima. Stable-ID member diffs plus typed dependency witnesses already answer DDO-09 change; no GED requirement added. |
| [Tree/arborescence recognition](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/tree/recognition.py), rooted-tree encodings/composition | **Select real containment checks, I05.** Directed `is_tree` does not guarantee the single-parent directed shape of `is_arborescence`. Preserve root, order and role semantics. Prüfer/nested-tuple encodings and tree composition do not replace ordered source identity or arbitrary DAG contracts; no new encoding selected. |
| [Tree/DAG lowest common ancestor](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/lowest_common_ancestors.py) | **Conditional common-context/navigation consumer, I05.** Retain indexed ancestry for current selective reads. Tree all-pairs API accepts requested pairs; avoid all pairs when unnecessary. DAG LCA returns one possible lowest ancestor; expose ambiguity or explicitly own complete-set selection when several incomparable answers exist. |
| [Dominators](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dominance.py) | **Conditional bottleneck explanation, I05.** A declared root/synthetic root plus `immediate_dominators` describes every-path structure. It does not prove all-of sufficiency, permission, causal necessity or necessity under omitted alternatives. No mandatory dominance service. |
| [Transitive reduction](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.transitive_reduction.html), [quotient/contraction](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/minors/contraction.py) | **Conditional display simplification, I05.** DAG reduction preserves reachability, not direct semantic roles/attributes. Quotient defaults can aggregate weights and retain subgraph views; contraction merges members. Keep original members, semantic edges and expansion mapping; never use a reduction as the governing support/recipe graph. |
| [dedensify/SNAP aggregation](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/summarization.py) | **No current core adoption; conditional bounded grouped display.** Dedensify introduces compressor nodes and documents a single-edge-type scope. SNAP groups selected attributes/connectivity, not authenticated identity. Require faithful decoding/drill-down before use; compression cannot create new evidence votes or discard custody. |
| [Cuts/articulation/connectivity/disjoint paths](https://networkx.org/documentation/stable/reference/algorithms/connectivity.html) | **Conditional support-fragility product, I05.** State structural projection and terminal sets. Graph-disjoint paths may share source/provider/episode; ordinary min-cut in AND/OR incidence is not automatically minimum admissibility-defeating revocations. Preserve independent trust and binding validation. |
| [Bipartite matching/full assignment](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/bipartite/matching.py) | **Retain existing guarded decomposition; conditional new allocation rule.** Two-distinct/exact-cardinality bindings remain relational predicates. Use matching only when the declared rule truly assigns exclusive role slots. Full weighted matching delegates to SciPy and does not subsume optional-match ambiguity. Existing independent_assignment requires distinct unique positive maxima, otherwise global assignment. |
| [Max flow/min-cost flow](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/flow) | **No current DDO-06 adoption.** Simultaneous byte/count/device/residency/lifetime/fencing and uncertain submission are not a single-commodity flow problem. A future declared transport/assignment operation could use explicit costs/capacities/demands, checking infinity defaults, multigraph restrictions and float cautions. No invented optimization objective. |
| [Spanning trees/branchings/arborescence iteration](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/tree), counting/sampling | **No authoritative hierarchy/support selection.** Optimizing or sampling a tree deletes valid relationships. Conditional declared heuristic structure or fixture use needs its own objective and retained originals; tree counts do not measure independent evidence. |
| [k-factor/regular subgraphs](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/regular.py), [Lukes partitioning](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/community/lukes.py), [approximations](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/approximation) | **No current fit.** Degree-constrained subgraph selection, capacity-bounded tree partitioning, Steiner/cover/clique approximations solve specific objectives absent from current bindings/admission. They must not invent grouping, drop required evidence or masquerade as exact support. Revisit only an explicit product allocation/selection problem with those assumptions. |

### Two-mode analysis, network science and numerical possibilities

These are screened opportunities, not required DDO delivery. They are useful possible declared
operations because the full domain model makes their inputs and result interpretation explicit.
Their principal work introduces new analytics rather than repairing the shared graph contract.

| Capability and primary source | Judgment and selection condition |
|---|---|
| [Bipartite projection/biadjacency](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/bipartite) | **Conditional source/derivation/operation affiliation inspection.** Supply typed sides, including disconnected populations. Weighted/collaboration/overlap projections have different meanings; retain intermediary identities. Prefer original two-mode analysis when it answers the question without clique expansion. |
| [BiRank](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/bipartite) | **Promising conditional two-population ranking.** A named candidate/review prioritization product can rank both sides directly. Declare weights, personalization for both populations, alpha/beta, convergence and node/result mapping. Ranking does not establish trust or independent evidence. |
| Bipartite [clustering/butterflies/redundancy/extendability](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/bipartite) | **Conditional repeated-affiliation diagnostics**, preserving actual member/source identity. A K2,2 motif may arise from one source, so it is not support independence. `maximal_extendability` concerns perfect-matching robustness; **no current fit** to DDO bindings. |
| [Degree, betweenness, closeness/harmonic centrality](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/centrality) | **Conditional DDO-10 triage.** Fan-in/out or connectors in a declared projection can orient inspection. Sampled measures retain sampling policy/seed where meaningful. Actual impact is qualified traversal, not centrality; structural centrality is not execution criticality. |
| Eigenvector/Katz/PageRank/HITS; current-flow/load/percolation centrality | **Conditional exploratory ranking only** for the first group; **no current consumer** for the latter flow/diffusion models. Specify direction, weight, personalization and convergence. Do not translate importance into correctness, causality or source trust. [Centrality](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/centrality), [link analysis](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/link_analysis). |
| Group centrality, prominent_group, voterank | **Conditional representative inspection**, with an explicit structural objective. No replacement for qualified coverage or independent evidence selection. [Centrality source](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/centrality). |
| [Louvain/Leiden/modularity/label propagation](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/community) | **Conditional exploratory grouping.** Do not fuse semantic identities or derive scheduler independence. Retain membership, seed/resolution/objective. Leiden 3.7 defaults to CPM, so modularity comparisons require a common explicit metric. Partition levels are analytical, not authored semantic hierarchy. |
| Fluid/local/divisive/clique communities, louvain_partitions/leiden_partitions | **Conditional specific inspection product**, no routine execution use. Fluid communities need a justified k; source expansion has a local scope; divisive methods need a declared rule; overlapping clique cover is not a partition. Retain original members. [Community source](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/community). |
| [Cut/expansion metrics](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/cuts.py), modularity/CPM/bipartite modularity | **Conditional assessment of an adopted partition product.** Objective and projection define score meaning. Conductance/cut ratio/coverage are not semantic coherence, support completeness or actual execution isolation. Do not add a score-driven partition policy to admission. |
| [Clustering/transitivity](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/cluster.py), assortativity/reciprocity/rich-club, triadic_census/triads_by_type | **Conditional structural summaries.** State direction/multiedge reduction and projection artifacts. Use census for counts, concrete typed occurrences for instance inspection. A feed-forward triad is not proof of a domain rule. [Triads](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/triads.py). |
| [Cores](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/core.py), cliques/trusses/structural holes and special graph recognition | **Exploratory cohesion/shape or genuine declared constraint only.** Dense cores cannot justify pruning required low-degree members. Planarity, chordality, interval/other special shape checks earn use only when the domain actually promises that shape; none is required by the current governing model. |
| [Link prediction](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/link_prediction.py) | **Conditional separate candidate-generation operation.** Jaccard/Adamic–Adar/resource allocation/preferential attachment score specified relations; negative versus unknown is explicit. Independent semantic evaluation is required. No candidate becomes an admitted fact merely from its score. |
| [harmonic_function/local_and_global_consistency](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/node_classification.py) | **Conditional separate classification baseline.** Undirected graph semantics and permitted labels are prerequisites; map output through pinned node order. Protected answers cannot seed production. No current NLP-provider replacement selected. |
| [Adjacency/Laplacian/spectral kernels](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/linalg), communicability | **Conditional named numerical operation.** Delegate graph linear algebra to NetworkX/SciPy with an explicit operator, row/column identities, weights, disconnected scope and convergence. Do not lower ordinary typed readiness to matrices without a numerical consumer. |
| [Resistance/Kemeny/distance measures](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/distance_measures.py) | **No current electrical/random-walk-model fit.** Conductance and walk dynamics are additional assumptions. Radius/diameter/eccentricity/barycenter/harmonic distance can be optional topology summaries under declared disconnection/weight semantics, not domain centrality or demand completion. |
| [D-separation](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/d_separation.py), moralization | **Conditional explicit probabilistic model only.** Provenance/operation DAGs do not imply Bayesian factorization or causal structure. Keep existing finite-interpretation potentials/constraints authoritative; topology cannot certify evidence independence without the appropriate model. |
| [Walks](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/walks.py), random-walk/small-world/non-randomness models | **No current semantic/execution requirement.** A future dynamics/null-model research product must name its assumptions and permitted observations. Walk counts are not unique support counts. No mandatory simulation campaign. |

### Execution, interchange, extension and verification support

| Capability and primary source | Judgment, integration and decisive condition |
|---|---|
| [Core/backend dispatch/config/introspection](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/backends.py), [configs](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/configs.py) | **Recommend explicit core policy, I06.** Per-invocation admission names algorithm/projection and result parameters; `backend="networkx"` selects native execution. Registered names or `.backends` discovery do not establish support for graph class, attributes, dtype or options. Keep global configuration at bootstrap, outside concurrent requests. |
| [nx-parallel](https://github.com/networkx/nx-parallel), [nx-cugraph](https://github.com/rapidsai/nx-cugraph), backend-native construction | **Conditional concrete bulk operation; no installation now.** Qualify actual invocation and complete extraction/conversion/result route. Reuse invocation-wide CPU/device admission instead of nested unbounded pools. Native construction may avoid conversions but must support the full consumer sequence. No performance claim follows from backend availability or low device utilization. |
| Backend conversion caches/fallback | **Recommend lifecycle and explicit policy, I06.** Direct attribute-dictionary mutation may bypass conversion invalidation; freeze is insufficient. Reuse only under immutable selected projection ownership, and retire caches with it. Optional fallback must satisfy admitted numerical/resource behavior; mandatory unsupported engine refuses. No second durable reuse authority. [Dispatch source](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/backends.py). |
| Custom/ArangoDB/Neptune/other engine backend | **No current fit.** DDO needs native transactional operations plus pure algorithms, not a backend wrapper that recasts PostgreSQL demand execution as a graph call. Consider graph-tool/igraph/other engines only for a concrete capability or serious execution risk, preserving typed projection/result meaning. [Backend ecosystem](https://networkx.org/documentation/stable/backends.html). |
| [NumPy/SciPy conversion](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/convert_matrix.py) | **Retain numerical consumers with explicit mapping, I06.** Sparse conversion sums parallel weights, uses default weight 1 and subsets induce a graph; dense default zero can conflate zero-weight and absent edges. Preserve ordered ID vectors and typed records. A matrix is not the canonical domain representation. |
| pandas/SQL/Arrow boundaries | **Recommend direct typed-row construction where graph computation earns it, I01/I06.** `from_pandas_edgelist` can coerce mixed numeric row values; preserve exact qualified/large integer IDs and isolates separately. Columnar/native filtering owns acquisition, NetworkX owns selected graph algorithms; no full native-to-Python-to-native data detour without a consumer. [Conversions](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/convert_matrix.py). |
| [Node-link JSON](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/readwrite/json_graph/node_link.py), GraphML/GEXF/GML/DOT/edge/adjacency formats | **Conditional derived interchange, I06.** Preserve direction, occurrence keys and field codecs; node-link reserved source/target/key fields can overwrite same-named attributes and JSON keys are strings. Edge lists can omit isolates; rich/nested attributes need a qualified codec. No replacement for authenticated DDO export or canonical semantic encoding. |
| [UnionFind](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/union_find.py) | **Conditional insert-only equivalence accumulation.** Lookup inserts unknown elements; representatives are arbitrary and are not canonical IDs. Revocation needs rebuild/another algorithm. No replacement for adequate existing connected_components or for nontransitive similarity matching. |
| [MappedQueue](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/mapped_queue.py) | **No current scheduling fit.** Useful for a real local mutable-priority algorithm with unique elements, removals and deterministic comparable priorities. It provides neither durable claims nor concurrent admission; do not build a second ready scheduler. |
| [Cuthill–McKee](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/rcm.py), decorators/random-state helpers | **Conditional numerical/custom-algorithm use.** Ordering earns use for a real sparse operation; decorators help a genuine NetworkX-compatible algorithm. Neither is a framework for DDO operation ports or generic scheduling optimization. |
| [Generators/perturbations](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/generators) | **Recommend selective independent shape controls, I07.** Explicit isolates, diamond, skew, disconnected, cycle/self-loop and duplicate-role cases reveal actual risks. Seeded random/block models are conditional, with independent semantic expectations. No random campaign, benchmark or generated gold from production. |
| [Layouts](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/drawing/layout.py)/Graphviz | **Conditional DDO-10 presentation.** Multipartite/bipartite/BFS ranks are useful dependency explanations; spring/ForceAtlas2/Kamada–Kawai are optional coordinates, not semantic proximity. Keep ID expansion and pinned scope; no mandatory dashboard, plotting dependency or layout-driven identity. |

## Validation account and remaining decisions

**Interface-checked, 2026-11-12:** root and three bounded contributors inspected the DDO coordinator
and seven companions, the decisive compiler/runtime/assessment/custody consumers above, and installed
NetworkX 3.7 sources. Representation/matching, dependency design and backend/analytics received
independent focused contributions. The root integrated disagreements: retain simple connectivity
plus typed semantic records rather than universally require MultiDiGraph/incidence; allow runtime
snapshot algorithms without creating another scheduler; preserve VF2 semantics despite newer APIs.

Executed read-only checks:

- **passed:** `uv run python -c 'import networkx; print(networkx.__version__); print(networkx.__file__)'`;
  selected implementation is 3.7.
- **passed:** `uv run python -` read-only namespace/signature inspection and backend configuration /
  entry-point inventory. This located `nx.dag.antichain_width` and `networkx.utils.graphs_equal`,
  checked selected algorithm signatures, and established the installed backend inventory in I06.
  These checks exercised inspection only, not algorithm semantics or optional backend execution.
- **not_run:** product/native/provider tests, database queries, performance experiments and semantic
  probes. Consequential questions here were resolved by source contracts and actual consumer
  requirements. No measured performance, full comparison equivalence or current runtime correctness
  is claimed. No new probe artifact or evidence record is warranted for routine source inspection.

For precise source contracts, inspected loci include `classes/digraph.py:676–745`,
`classes/multidigraph.py:427–520`, `classes/graph.py:1591–1665`, `classes/function.py:198–244`,
`algorithms/isomorphism/vf2pp.py:185–454`, `algorithms/isomorphism/ismags.py:560–645,978–1010`,
`algorithms/graph_hashing.py:71–120`, `algorithms/similarity.py:39–110`,
`algorithms/minors/contraction.py:99–196,325–461`, `algorithms/summarization.py:70–106,408–464`,
`readwrite/json_graph/node_link.py:108–140`, `convert_matrix.py:520–550,893–970`,
`algorithms/dag.py:177–224`, `algorithms/boundary.py:1–145`, and the linked dispatch/config source.
Source behavior is evidence for the selected version, not a promise for future releases.

Implementation qualification, if these amendments are adopted, belongs in existing DDO packages:
use the acceptance challenges at I01–I07 with independent expected memberships/bytes/roles and
mapping-sensitive choice outcomes. Adopted backend paths require actual package/conformance checks;
unselected optional analytics do not become blocked final obligations. Preserve native admission,
unknown/completeness, independent protected assessment and existing preservation requirements.

The next decision is whether to integrate I01–I07 into DDO, with optional portions explicitly
selected or left conditional. No separate graph service, registry, new audit cadence, capacity
estimator or broad analytics subsystem is needed. The proposed total domain model remains the
single semantic authority; NetworkX executes declared, faithful projections of it.
