# Declared graph projections and NetworkX analysis

**Proposed implementation target · 2026-11-12.** Consumes the
[NetworkX review](../../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md)
at `7c5368faa`. Implements its I01–I07 planning amendments within DDO-00–12; the
[coordinator](../declared-data-operations_2026-11-12.md) alone owns progress and scheduled dispositions.
The operator selected explicit conditional triggers rather than mandatory candidate investigations.
The coordinator's DDO-00–02 receipt records implemented pure typed graph/closure/identity kernels
and their bounded checks. Candidate native snapshots and bounded readiness now have integrated foundations. Real-consumer
integration, public graph explanations and assembled qualification remain open; this companion is not a second progress ledger.

This companion owns shared projection/algorithm contracts. Contracts and compilation owns their
integration into effective definitions and identities; products/support owns native acquisition and
admission; demand execution owns actual readiness; interfaces owns public results. Those owners
link here rather than independently defining graph policy. Apply core 3.3, heuristics,
code-intelligence 1.4 and test-assessment 1.2. Expected benefits are Proposed and qualitative.

**Execution owner · 2026-11-13:** the
[coordinator execution account](../declared-data-operations_2026-11-12.md#audit-repair-execution--2026-11-13)
owns delivered behavior, dated qualification and remaining package scope. This companion keeps
the governing contracts; it does not maintain a second completion ledger.

## Projection contract and physical route — I01

The effective governing model, compiled from declaration-owned and admitted implementation-owned
definitions, contains a typed GraphProjection specification, not arbitrary Python
callbacks, SQL text or a separately edited graph registry. It declares source contracts and exact
selection/snapshot, node/relationship kinds, edge orientation, role/order/multiplicity, stable
identity, unresolved-reference treatment, completeness, attribute/weight interpretation and the
examined universe separately from output filters. An analysis names that projection, semantic
algorithm/parameters, output interpretation and separately admitted execution policy.

| Projection | Meaning and actual consumer | Representation and retained authority |
|---|---|---|
| Semantic-reference closure | DDO-01/02 effective kind/recipe dependencies | DiGraph connectivity plus canonical typed semantic-edge records; legal finite recursive references; inheritance constraints remain compiler-owned |
| Potential producer dependencies | DDO-01/05 validation and DDO-09 potential impact | Declared operation/role occurrences and alternative groups; not proof every possible producer must execute |
| Bound-request precedence | DDO-05/06 selected inputs and actual obligations | Selected occurrence incidence and connectivity; native typed binding evaluates all-of, exact-one, distinctness and closed populations |
| Selected support lineage | DDO-04/09/10 admissibility/currentness and export | Exact products/members/episodes and support roles; native trust/permission rules determine validity |
| Source hierarchy | DDO-07/10/11 original containment/navigation | Original root/parent/order/extent identities; a semantic DAG is not forced into single-parent containment |
| Assessment graph | DDO-08/10 protected structural comparison | Rooted attributed MultiDiGraph/reified assertions and choices; exact mapping semantics below |

Construct graphs from one immutable effective model or coherent native read scope. For runtime
reads, use the existing pinned production read owner with compact typed node/edge rows and indexed
adjacency; no graph-specific durable mirror/table/service is required. Authenticate declared edges
before graph construction. Keep indexed PostgreSQL traversal for selective live queries and indexed
SQLite for detached closure. Materialize a bounded reusable graph where multiple algorithms need it;
release it with its selected input lifetime. Output pagination never truncates the examined closure
silently: return explicit partial/unavailable standing if required acquisition cannot complete.

**Selected NetworkX 3.7 mechanisms:**

- [`DiGraph.add_edge`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/digraph.py)
  creates missing endpoints and updates a single existing edge. Validate endpoints against the declared
  universe first; pre-add isolates. Keep endpoint-pair → original typed occurrence witnesses, since
  connectivity deliberately forgets parallel roles. Hash canonical typed records, never adjacency order.
- [`MultiDiGraph.add_edge`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/multidigraph.py)
  preserves distinct keyed occurrences; reusing a key updates that edge. Use stable semantic occurrence
  keys when exported, not generated local integers. Incidence nodes are appropriate when an operation,
  derivation or n-ary role occurrence is itself meaningful; do not universally lower every edge to nodes.
- [`reverse_view`/`subgraph_view`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/graphviews.py)
  avoid rebuilding adjacency for reverse impact/selected diagnostics, but track the underlying graph.
  Filters bind immutable parameters. [`freeze`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/function.py)
  prevents structural modification only. `G.copy()` copies attribute dictionaries shallowly, sharing
  nested values: own immutable payloads rather than promise snapshot isolation through copying/freezing.
- [`NodeView`, `EdgeView`, degree and multiedge reports](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/reportviews.py)
  provide bounded inspection. Use `in_edges`/`out_edges` and `edges(keys=True,data=True)` when direction
  and occurrence identity matter. Export detached typed results, not live views as DTOs or cursors.

## Shared closure, cycles and partial orders — I02/I03

DDO-02 implements pure topology kernels over authenticated projections. DDO-05/08/09/10 consume
these kernels with their own closure and validity policies; sharing an algorithm does not share all
policies. Existing `evaluate/alignment_preparation.py:52–150` provides the useful SCC/impact pattern,
including unknown/global dependencies and absent lookups, without licensing production use of gold.

1. [`strongly_connected_components` and `condensation`](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/components)
   identify actual strongly connected regions and produce a DAG with `mapping` and `members`.
   A singleton is cyclic only with a self-loop. Component integers are local; retain original internal
   edges and semantic IDs for diagnostics/canonical identity. Legal cyclic type references remain legal;
   unsupported inheritance/execution cycles refuse. Condensation does not compute a semantic fixed point.
2. [`ancestors`/`descendants`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dag.py)
   compute reachability excluding the starting node. Explicitly include roots/components for rooted
   closure and potential impact. Direction differs between prerequisite navigation and downstream impact.
   DDO-09 still stops propagation at equal admissible value/support and discovers never-derived subjects
   through declared population/applicability witnesses, not existing lineage alone.
3. [`bfs_edges`/`dfs_edges` and edge traversal](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/traversal)
   replace private topology work only after source/schema/support authentication. A traversal tree omits
   reconvergent/non-tree edges; use original adjacency or edge traversal when exact export needs all
   occurrences. Preserve row/byte budgets and closure error semantics in their acquisition owner.
4. [`find_cycle`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/cycles.py)
   yields a located witness without enumerating `simple_cycles` or `all_simple_paths`. A bounded
   fewest-hop explanation can use unweighted shortest path/BFS, with original typed edge witnesses.
   [`node_boundary`/`edge_boundary`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/boundary.py)
   explain obligations crossing selected scope; validate requested nodes, preserve direction and reverse
   for incoming boundaries. A boundary is not complete authenticated closure.
5. [`lexicographical_topological_sort(key=...)` and `topological_generations`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dag.py)
   give deterministic presentation and dependency levels. Apply ordering to a DAG/condensation, not a
   raw permitted cyclic reference graph. Generations never become runtime barriers: B finishing can
   admit C while unrelated A at B's level remains active. Native obligations/claims/discovery decide
   readiness and exhaustion, including locked work and backpressure.

**DDO-08 required repair:** `semantic/domain_operations.py:1646–1663` currently drains
`TopologicalSorter` then marks every residual claim cyclic. Replace residual classification with
SCC cycle membership and downstream blockage, preserving independent claims and distinct unavailable
premises. Include self-loop, A↔B→C and unrelated D with independent expected reasons. The source
inspection establishes the defect premise, not a passing reproduction or implemented repair.

## Comparison and inspection contracts — I04/I05

Keep one pure comparison owner consuming the new admitted projection. The current
[`MultiDiGraphMatcher`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/isomorphism/vf2userfunc.py)
callbacks preserve canonical node payloads and typed edge counters/multiplicity. Retain rooted focus,
shared-binder identity and concrete mapping enumeration. Complete slots require isomorphism; partial
positive witnesses require non-induced monomorphism, not induced matching. Expected fields may be
asymmetric, and post-mapping joint-choice/prerequisite checks must still see distinguishing mappings.
Migrate `evaluate/characterization_assessment.py` and `evaluate/task_semantics.py` with their actual
consumers; retain guarded global assignment and independent protected expectations.

For authentic single-parent containment, use
[`is_arborescence`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/tree/recognition.py)
where recognition is needed: directed `is_tree` alone does not guarantee that shape. Retain original
root/order/extents. Required DDO-10 inspection exposes selected members, SCC membership, typed witness
paths and scope boundaries through the shared native/ci/MCP owner. Cursors pin the same selection,
contracts and trust assessment as acquisition. Source-only/partial/failed/empty results remain explicit.
No new graph viewer or rendering dependency is required. Broader hierarchy/support analyses below
are conditional and must not redefine evidence independence or admission.

## Execution and interchange — I06

Call selected dispatchable core algorithms with explicit `backend="networkx"`, so environment
priorities cannot silently select another engine. The
[3.7 dispatch implementation](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/backends.py)
and [configuration](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/configs.py)
separate supported invocation, backend selection, conversion caching and fallback. Algorithm presence
or `.backends` does not prove support for directedness, multiplicity, attributes, dtype or arguments.
Keep global config at bootstrap; context-manager restoration does not make it request-local.
Record result-affecting algorithm parameters under semantic contracts; physical engine provenance
belongs to the execution projection unless it changes the admitted result/numerical interpretation.

Conversion caches live only with the immutable selected projection. Direct attribute mutation can
bypass invalidation; freeze alone is insufficient. No new durable cache authority. Mandatory unsupported
execution refuses; any later optional fallback needs an explicit admitted policy. CPU/GPU graph
acceleration must share existing invocation capacity, not introduce nested unconstrained pools.

Use exact typed row IDs when constructing graphs from native/columnar data. In
[`convert_matrix`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/convert_matrix.py),
sparse conversion sums parallel weights, supplies missing weight 1 and induces subsets from nodelists;
dense default zero can conflate absence and zero weight. Preserve explicit node-index vectors,
isolates, aggregation meaning and original typed records for existing numerical consumers.
`from_pandas_edgelist` may coerce mixed numeric row values; do not route qualified/large integer IDs
through an unsafe numeric representation. No matrix becomes canonical semantic identity.

## Complete capability disposition and revisit conditions

The following is design selection, not a second execution ledger. Each row covers the named feature
families in the review's four coverage tables. Selected mechanisms above are required within their
DDO consumers; the table preserves all remaining alternatives and limits. Conditional/no-current-fit
entries create no pending DDO-12 obligation. Revisit only when the stated consumer exists and is
explicitly selected; then assign implementation/qualification through the coordinator.

| Features and primary source | Disposition, deciding condition and retained limit |
|---|---|
| [Graph classes/factories](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/classes) | Select ordinary DiGraph/MultiDiGraph/incidence above. Dictionary factories/subclasses have no current fit; reconsider a concrete representation constraint. Shared thin-graph attributes cannot encode independent roles. |
| [Relabeling](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/relabel.py), [union/intersection/difference/composition/complement](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/operators) | Conditional private preparation. Establish injectivity/key/attribute collision meaning; noninjective relabeling merges nodes. These are not semantic revision merge or known-absence inference. |
| [Components/attracting/semiconnectedness](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/components), [flow_hierarchy](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/hierarchy.py) | Retain existing weak/strong/undirected components for factor/geometry/guarded assignment. Terminal SCCs, comparability and cyclic-edge summaries are conditional inspection; never demand completion or semantic hierarchy validation. |
| [Transitive closure, antichains, antichain_width, dag_longest_path](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dag.py) | Conditional named all-pairs/dependency-width/depth inspection. `nx.dag.antichain_width` builds transitive closure plus matching; not a hardware concurrency bound. Avoid antichain enumeration routinely. Longest path reads edge weights; node costs require explicit lowering. No duration estimator. |
| [Dijkstra/Bellman–Ford/A*](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/shortest_paths), [beam search](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/traversal/beamsearch.py) | Fewest-hop witness selected above; weighted search conditional on meaningful weights/negative-edge policy. A* caches first heuristic per node and needs valid admissibility/cutoff assumptions. Beam search prunes completeness. Neither establishes missing required work/support. |
| [VF2++](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/isomorphism/vf2pp.py), [ISMAGS/largest common induced subgraphs](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/isomorphism/ismags.py) | Conditional symmetric exact subproblem, no matcher replacement now. 3.7 includes VF2++ subgraph/monomorphism and directed/multigraph ISMAGS support. VF2++ node labels lack arbitrary edge/asymmetric callbacks; ISMAGS partitions require equivalence and pruning must preserve downstream choice distinctions. Require equivalent accepted mappings before substitution. |
| [graphs_equal](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/misc.py), [WL hashing](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/graph_hashing.py), [GED/progressive edit paths](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/similarity.py) | Physical equality helper conditional; canonical typed bytes remain authoritative. WL has no current adoption: multigraph rejection and incomplete fingerprints require an actual candidate-index consumer plus exact verification. GED needs a separate explanation objective/cost policy; default attribute omission and interrupted nonoptimal search cannot establish semantic compatibility. |
| [LCA](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/lowest_common_ancestors.py), [dominators](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dominance.py) | Conditional common-context/bottleneck navigation. Retain indexed ancestry for selective reads; requested tree pairs avoid all pairs. DAG LCA may choose one of several incomparable answers; expose ambiguity. Dominance describes every-path topology, not AND/OR sufficiency or causal necessity. |
| [Reduction](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dag.py), [quotient/contraction](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/minors/contraction.py), [dedensify/SNAP](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/summarization.py) | Conditional grouped display only; require original member/edge expansion. Reduction preserves reachability, not direct roles. Quotient aggregation/views and contraction can erase meaning; dedensify introduces compressor nodes with single-edge-type scope; SNAP resemblance is not identity/support equivalence. |
| [Cuts/articulation/disjoint paths](https://networkx.org/documentation/stable/reference/algorithms/connectivity.html) | Conditional support-fragility product with explicit terminals/projection. Disjoint paths can share authentic sources/providers; AND/OR admissibility loss is not ordinary graph min-cut. Never count them as independent votes. |
| [Bipartite matching/assignment](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/bipartite/matching.py), [max/min-cost flow](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/flow) | Retain unique-positive/distinct-column decomposition with global SciPy fallback. New matching requires a declared exclusive-role allocation, not ordinary two-distinct binding. Flows have no scheduling fit; revisit explicit transport objectives with capacities/demands, multigraph/float/default-infinity checks. |
| [Trees/branchings/arborescence enumeration/counting/sampling/encodings](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/tree) | Recognition selected where containment requires it; optimization/sampling/Prüfer/nested encodings not authoritative hierarchy/support selection. Revisit declared heuristic or fixture use with retained identities/order and objective. |
| [k-factor](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/regular.py), [Lukes](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/community/lukes.py), [Steiner/cover/clique approximations](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/approximation) | No current fit. Revisit a genuine degree-constrained selection, bounded tree partition or approximation objective; never drop required evidence or invent an admission optimization goal. |
| [Bipartite projections/biadjacency/BiRank/clustering/butterflies/redundancy/extendability](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/bipartite) | Conditional affiliation inspection/ranking; typed disconnected sides and intermediaries retained. BiRank needs weights, dual personalization, alpha/beta and convergence. One-mode projection creates new semantics; K2,2 is not independent support. Extendability has no current perfect-matching consumer. |
| [Degree/betweenness/closeness/harmonic/eigenvector/Katz/group/current-flow/load/percolation centralities, prominent_group/voterank](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/centrality), [PageRank/HITS](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/link_analysis) | Conditional triage/representative ranking; flow/diffusion variants have no present consumer. Require a declared projection/objective, weight/direction/convergence and sampling policy. Importance is neither correctness/trust nor actual criticality. |
| [Louvain/Leiden/label propagation/fluid/local/divisive/clique communities, partitions, modularity/CPM/bipartite modularity](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/community), [cut/expansion metrics](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/cuts.py) | Conditional exploratory grouping and partition-quality consumer. Retain membership, seed/resolution/objective; Leiden defaults to CPM, fluid requires justified k, overlapping covers are not partitions. No identity fusion, semantic hierarchy or scheduler independence from communities/scores. |
| [Clustering/transitivity](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/cluster.py), [triadic census/types](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/triads.py), assortativity/reciprocity/rich-club, [cores/trusses](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/core.py), cliques/structural holes/special graph recognition | Conditional topology summaries or genuine shape contracts. Preserve multiedge/direction/projection interpretation; motifs do not prove rules and density cannot prune required low-degree members. No current planarity/chordality/other special-shape requirement. |
| [Link prediction](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/link_prediction.py), [harmonic_function/local_and_global_consistency](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/node_classification.py) | Conditional separate candidate/classification operation with independent evaluation. Unknown is not negative; undirected node classification maps pinned node order and permits only authorized labels. Protected answers never seed production; no NLP replacement selected. |
| [Adjacency/Laplacian/spectral kernels](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/linalg), communicability, [resistance/Kemeny/radius/diameter/barycenter/harmonic distances](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/distance_measures.py), [walks](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/walks.py) | Conditional named numerical/topology product with explicit operators/weights/index/convergence/disconnection. Electrical, walk/null-model/small-world/non-randomness assumptions have no current governing-model fit; walks are not support counts. |
| [D-separation/moralization](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/d_separation.py) | Conditional declared probabilistic factorization only. Provenance/operation DAGs are not automatically Bayesian/causal DAGs; preserve existing finite potentials/constraints. |
| [nx-parallel](https://github.com/networkx/nx-parallel), [nx-cugraph](https://github.com/rapidsai/nx-cugraph), native construction, [backend ecosystem](https://networkx.org/documentation/stable/backends.html) | Core explicit dispatch/cache policy selected above. Accelerators conditional on a supported concrete bulk invocation and whole-route suitability/conformance; no installation now. Custom/ArangoDB/Neptune backends have no current fit; other engines require an actual capability/serious execution risk. No backend registry/name alone establishes parity or speedup. |
| [Numeric/pandas conversion](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/convert_matrix.py), SQL/Arrow acquisition, [node-link JSON](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/readwrite/json_graph/node_link.py), GraphML/GEXF/GML/DOT/edge/adjacency files | Typed acquisition and existing numeric fidelity selected above. Other interchange conditional on a real consumer and qualified codec: endpoint/key field collisions, JSON string keys, nested attributes and omitted isolates matter. Not canonical identity or authenticated export replacement. |
| [UnionFind](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/union_find.py), [MappedQueue](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/mapped_queue.py), [Cuthill–McKee](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/rcm.py), decorators/random-state helpers | Conditional insert-only equivalence, local mutable-priority or sparse/custom algorithm consumers. UnionFind lookup inserts unknowns and representatives are arbitrary; deletion needs rebuild. MappedQueue has no durable/concurrent scheduler contract. No replacement of adequate current components or generated ports. |
| [Generators](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/generators), [layouts](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/drawing/layout.py)/Graphviz | Small path/tree/cycle/diamond/bipartite and deliberate perturbations selected for independent topology controls, I07. Random models conditional with seed/version and independent expected semantics. Layouts conditional for bounded presentation: multipartite/BFS/bipartite ranks or spring/ForceAtlas2/Kamada–Kawai coordinates do not define semantic identity/proximity. |

## Package investigations, migration and qualification — I07

| Owner and question | Settling work and dependent boundary |
|---|---|
| DDO-01/02: can effective declarations preserve every graph role? | Compile real normalized declarations and independent parallel-role/isolate/recursive-kind cases. Select shared typed model integration before generated identity/binding consumers; missing fidelity blocks those consumers, not a fallback digest. |
| DDO-03/04/10: can native acquisition supply one coherent bounded projection? | Inspect generated rows/read contracts and exercise selection/continuation/intermediate closure under native snapshot semantics. Keep selective SQL/SQLite rather than require complete memory materialization. Missing custody/completeness blocks claims of exact closure. |
| DDO-05/08/09: which loops are pure topology? | Migrate actual closure/cycle/impact consumers with their policy checks; inspect _acyclic, authored-claim residuals, exact export worklists and change-reporting callers. Retain authentication and failure semantics. Include never-derived subjects and equal-output stop points. |
| DDO-08/10: does comparison preserve accepted mappings? | Independent root/multiplicity/shared-binder/asymmetric-field/choice cases qualify retained VF2 against new domain projections. No alternative matcher required. |
| DDO-06: is execution policy explicit and supported? | Check selected signatures and typing against NetworkX 3.7 (`types-networkx` currently 3.6.1.20261029). Qualify only selected calls; missing stubs do not prove missing APIs. Unsupported required calls refuse; no ambient fallback. |

Deliver shared projection/identity kernels during DDO-01–03. Runtime acquisition follows actual
DDO-04 native availability; demand, authored claims, impact, inspection and custody migrate with their
own packages. Do not add DDO-13 or a graph-wide stage barrier. Remove private topology machinery only
when its replacement and consumers preserve required behavior. DDO-11 carries exact source/contract /
support closure through adoption, including sealed historical artifacts. DDO-12 incorporates this
scope into its existing final union; optional capabilities above are not blocked required work.

Use independently authored expected sets, bytes, role records and failure reasons for isolates,
parallel/self edges, aliasing, root inclusion, cycles with blocked tails, alternative cycles,
new/removed/absent population members, wrong trust/cursor snapshots, incomplete coverage and source
hierarchy/order. Test C admission while unrelated A remains active; preserve blocked/locked work.
Retain native/ci/actual MCP/export/detached controls and protected source/prediction separation.
Layout/interchange/summarization or alternative-engine/matcher checks apply only if selected later.
No full backend campaign, benchmark, architectural lint or generated semantic oracle is introduced.

**Evidence boundary:** selected contracts are Interface-checked by the source review on 2026-11-12;
this author's focused reinspection confirmed the SCC invalidation pattern and authored-claim residual
path at product source `8c0f4f951`. Production tests, native queries, providers and semantic probes are
**not_run** for plan authoring. Future checks above are obligations, not passing receipts.


## Implementation-reference projections — Python I02/I03

Consumes [implementation facts and slice admission](implementation-contracts-and-fingerprints.md#I02).
Extend the effective model's projection families with lexical-reference, possible-call, resolved
implementation-definition, type-reference and admitted implementation-determinant relations. Preserve
relationship kind, source/analysis provenance, supplying owner, target alternatives and coverage.
Astroid [`lookup`/assignment protocols](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/protocols.py)
and LibCST [scope/qualified-name metadata](https://libcst.readthedocs.io/en/latest/metadata.html)
supply facts with distinct guarantees. None is an authentic data/support or native readiness edge.

Reuse finite canonical typed records and NetworkX closure/SCC mechanisms, retaining original edge
witnesses and root inclusion. A resolved singleton does not certify exhaustive dependency targets;
supported profile and explicit opaque boundaries must justify reusable slice completeness. Cyclic
implementation references are finite graphs, not hash recursion or admitted execution iteration.
Do not create another mirror, scheduler or private canonicalization. Docstrings/annotations/source
positions remain governed by the shared normalization/reflection policy, not arbitrary display filters.
