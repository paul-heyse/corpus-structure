# Diagnostic correction and qualified graph workflows

**Accepted implementation design and selected mechanisms, 2026-11-10.** This supporting plan owns the design
and delivery instructions for DMC-11, DMC-12 and DMC-14. The [series coordinator](../domain-data-model_2026-11-10.md)
owns authorization, execution state, investigation dispositions, formal review points and
assembled acceptance. Package identifiers below describe work, not a second progress register.
Execution follows completed PTD-11 and precedes production milestone two, as the coordinator
specifies. Authoring this plan performs no production implementation or probe.

## Inputs and authority

The inspected baseline is `8e69e2b5f`, with concurrent PTD-11 documentation and test work preserved.
During authoring, `dfe77f5a3` landed PTD-11 review/native-test work; its final campaign remained
pending. DMC-00 must consume PTD-11's completed handoff rather than treating that commit as it.
The source propositions are [O09, O10 and O13](../../functional_reviews/domain-data-model/validation-and-graph-analysis.md),
plus discovery [DDM-07/08 and graph capability branches](../../library_leverage/libraries/domain-data-model/briefings/qualified-graphs.md).
The review's library baseline is jsonschema4.26.0/referencing0.37.0, RDFLib7.6.0 and
pySHACL0.40.1; later-release overview addenda are leads, not qualification of these versions.

[D2](../../design/D2-schema-and-guidelines.md) owns admitted model meaning and lowerings;
[D8](../../design/D8-agent-and-query-interfaces.md) owns located reports and bounded read interfaces;
[D1](../../design/D1-knowledge-representation.md) and
[D5](../../design/D5-consolidation-identity-confidence.md) own assertion meaning and production
inference. [ADR-0069](../../adr/0069-cli-operations-custody.md) owns invocation custody. Proposed
diagnostic extensions fit those responsibilities. New executable model syntax or production
entailment, rules, imports or mutation must follow the coordinator's explicit decision route.

The focused foundation assessment uses core3.3, its efficient-architecture companion and
code-intelligence1.4. The relevant constraints are one scoped semantic authority, typed fidelity,
qualified relationship identity, explicit unknown/partial states, pinned evidence and work shaped
to the requested operation. This is plan design, not a refreshed broad audit or a formal review.

## Baseline and intended division of responsibility

In [ontology.py](../../../python/corpus-structure/src/corpus_structure/semantic/ontology.py),
`validate_graph` obtains a real pySHACL report, returns its canonical bytes in `GraphValidation`,
and extracts focus, path, shape, component, severity and joined messages. Its selected profile is
inference none, advanced false, imports false and no mutation. Shape loading, execution failure
and data nonconformance are distinct. `GraphDiagnostic.path` stringifies the RDF node; a blank
node label cannot explain a composite path.

[operation_reporting.py](../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py)
projects located observations, placing a report hash in `original_report` for graphs. Other
branches use that same string field for inline JSON or engine/exception markers. Those forms
have different custody guarantees. PTD-11's validation-v3 dependency occurrence pages describe
projection dependencies; they are not subsidiary JSON errors or complete graph-report detail.

Prepared JSON validators already exist. `PreparedPayloadFamily._validated_row` in
[pdf_payloads.py](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_payloads.py)
collects sorted errors and passes only the first path/message through `_error`.
`NativeMapping.validate` in
[pdf_records.py](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_records.py)
similarly turns its selected error into `NativeMappingError`. Improving only the reporting
function would lose errors already flattened at these boundaries. Native mapping's finite-value,
reference-profile and semantic closure checks remain separate obligations.

The target preserves compact refusal and adds a requested correction view derived from the
actual execution evidence. The report owner owns presentation and custody references; the
validator owner owns execution and its error structure. Neither diagnoses by rerunning each
field nor recreates yesterday's error under today's release. The shared DMC-01 effective-model
inspection contract supplies immutable provenance: module, logical definition path and source
digest, with contribution/origin information when available. Missing provenance in an older
archive is unknown, not reconstructed from the current workspace. Runtime input paths, schema
definition addresses, source locations and graph terms stay separately typed.

<a id="DMC-11"></a>

## DMC-11 — Actionable correction detail and honest report custody

### Result and request flow

A caller validates one supplied input or graph under a bound release and operation. Default
output remains the compact outcome. A detail request selects relevant observations and bounds
the correction view by returned items, nested depth and encoded bytes. These are explicit
presentation limits; exceeding one marks detail incomplete without changing the original
conformance/refusal result. If execution itself stops at a work limit, the operation's assessed
coverage is separately incomplete. Do not call a first-error refusal a complete error inventory.

Build one operation-local evidence collection at the existing validation boundary. In compact
mode it may keep the present first-error evaluation behavior. In requested detail mode, consume
the prepared validator's `iter_errors` once with an explicit examination limit, retain the
original yielded errors through formatting, and expose `absolute_path`, `absolute_schema_path`,
keyword, message and nested `context`. A bounded collection must report that later errors were
not examined. Expensive individual validator work is not preempted merely by bounding yielded
errors; keep existing input/work limits and refuse a claimed comprehensive mode that cannot
honor its declared operation bounds. No per-field second validation pass follows.

Keep subsidiary `oneOf`/`anyOf` causes attached to their parent/branch rather than pretending
all alternatives apply. Preserve same-path/same-keyword multiplicity and numeric array indices;
escape JSON Pointer segments only when rendering. Use message/cause metadata without embedding
entire input objects, secret values or arbitrary exception objects in reports. Expected/actual
values are opt-in, bounded and governed by the existing redaction rules. A location remains
useful when the actual value is withheld. Known native finite/reference/closure failures can
join the view under their own typed category; they are not relabelled as JSON Schema failures.

For graphs, parse/query the already produced report graph once for the requested detail.
Expose `sh:value`, `sh:sourceConstraint`, subsidiary `sh:detail`, and structured `sh:resultPath`
alongside existing focus/shape/component/severity facts. Preserve RDF term kind, datatype and
language when present. Do not promise message language that the engine has already normalized.
Use a visited set and limits for nested detail and RDF lists so cyclic/malformed report
structures cannot cause infinite rendering. Unsupported paths return a located unsupported
representation plus the original-report reference, not a fabricated predicate.

The relied-on jsonschema contract is [structured ValidationError and context](https://python-jsonschema.readthedocs.io/en/v4.26.0/errors/)
and [4.26.0 validator iteration/evolution](https://github.com/python-jsonschema/jsonschema/blob/v4.26.0/jsonschema/validators.py).
`ErrorTree` is a convenience index, not the evidence owner: its same-path/keyword indexing can
overwrite multiplicity. Graph fields follow [SHACL validation results](https://www.w3.org/TR/shacl/#results)
and the selected [pySHACL report construction](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/constraints/constraint_component.py).
Discovery's installed-source observations qualify these choices; execution rechecks only changed
or uncertain contracts if the selected dependency release differs.

### Direct delivery, retention and failure

Direct detail is the default and requires no retained invocation. A caller holding
`GraphValidation` or original JSON errors can request the bounded view within that call. No
managed reference is advertised for ephemeral evidence. Caller-directed `compile --out` remains
an explicit export; a filesystem export path is not silently converted into managed custody.

When the operator requests later retrieval, extend the existing compile/check command's
operation with `ResultStore.operation`, `Invocation.publish` and the existing result inspection
route in [cli/managed.py](../../../python/corpus-structure/src/corpus_structure/cli/managed.py).
Compile/check currently use direct refusal/output paths, so this is a real integration slice,
not an assumption that their results are already retained. Retention selects this wrapping;
ordinary direct compile/check should not gain mandatory result-store setup. Reuse the owning
operation and its result ID; do not introduce a separate archive, daemon or diagnostic registry.

Publish one named diagnostic-report artifact containing the bound report envelope and exact
available engine evidence, with engine/version, release/model binding, schema digest, detail
scope, coverage, media type and content digest. Artifact structure can group distinct engine
bytes without copying the graph into each observation. A graph report is the actual retained
canonical bytes; JSON evidence is a structured capture of actual error paths/context, not a
pickled exception and not a rerun. A typed reference names result ID, artifact role and the
specific evidence member/digest. Retrieval authenticates bytes through the existing managed
reader and keeps the original binding; it never resolves a mutable current release.

Evolve the report schema at its existing model owner in
[operation-reports.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/operation-reports.yaml).
Distinguish inline evidence, a nonretrievable diagnostic marker/digest and a managed retained
reference. A marker can help correlation but cannot be followed. Version the affected report
contract and generated schemas together; preserve the archived-v2/v3 reader's stated limits.
Older `original_report` strings stay legacy/unknown custody unless an actual retained artifact
establishes more. Do not guess from a `sha256:` prefix or invent legacy report contents.

Capture detail before mapping wrappers flatten it and before `failure_boundary` turns the
exception into process exit. For retained failures, publish the available evidence and settle
the failed/refused operation receipt before translating to the existing CLI outcome. Invalid
data must not become a successful invocation merely because its report was written. Invalid
shape, validator execution failure, nonconformance, incomplete examination and missing archived
detail remain different outcomes. A report-publication failure preserves the original cause
and discloses that retrieval was not established. Cancellation keeps an interrupted receipt
and any safely published evidence without claiming completion. Managed role authentication,
holds and expiry remain ADR-0069's: unheld successes one day; failures/interruption one week.
An expired artifact is unavailable, not an invitation to rerun validation under new inputs.

### Integration and replacement

Migrate schema compile/check, `validation_failure_report`, `graph_validation_report`, the JSON
mapping wrappers that feed them, and CLI failure rendering as one selected flow. Keep the
existing shared application report consumable by CLI/MCP adapters; migrate any registered
report-schema consumers actually affected by its version. Inspect callers of the affected
wrappers before changing exception payloads. A wrapper can carry the original library error
internally without making public consumers depend on validator internals.

Remove redundant string-only evidence production and independent detail extraction in migrated
paths. Retain compact summaries as presentations of the same facts. Keep archive readers only
for real historical contracts; add no compatibility mode for an unconsumed interim schema.
Do not replace PTD-11 dependency pages or their separate completeness fields. Move enduring
report/custody meaning into D8 and the report model when implemented; the plan is not runtime
schema authority.

### Prerequisites and acceptance

DMC-01 must have delivered its inspection/provenance slice, including archived absence semantics,
before diagnostics claim definition-source links. Plain input/error detail does not wait for
unrelated vocabulary or archive-conversion work. Completed PTD-11 supplies the final dependency
report schema that this package must extend without collision. Coordinate edits to
`operation_reporting.py`, report YAML/generated schemas, `cli/schema.py` and `cli/failures.py`.
No dependency on DMC-12's optional richer navigation is needed to display an existing report
path: DMC-11 can use the bounded path reader described below without admitting new model syntax.

Acceptance uses independently authored valid/invalid inputs and known error expectations:

- A nested union exposes branch causes and two independent bad fields without asserting all
  alternatives apply; two same-path/keyword failures remain distinct. Compact refusal still
  supplies a useful selected message, and no extra validation pass runs merely for formatting.
- Wrapper-produced PDF/native errors retain locations and structured causes when requested;
  finite-value, reference-profile and semantic-closure failures preserve their own meanings.
- A SHACL case with an offending typed value, source constraint, nested detail and composite
  path yields readable terms. Cyclic detail/list data terminates with explicit incomplete or
  malformed detail. Shape failure, engine failure and ordinary nonconformance remain separate.
- Item/depth/byte and examined-error limits expose their actual coverage. Complete compact
  conformance does not imply complete detailed evidence, and truncated evidence does not alter
  conformance. A high-degree report does not force all report content into each observation.
- Direct detail works with no result-store artifact. Explicit retention retrieves identical
  bytes under the original release/model; failed and interrupted invocations keep their true
  receipt and expiry. Expiry, corruption, role mismatch and unavailable legacy detail refuse
  honestly. Withheld input/credential values never appear in the report or failure envelope.
- Two source modules with the same local name retain distinct DMC-01 provenance; an older
  archive missing source detail stays unknown after the working model changes.

Targeted tests belong at the report/validator/CLI capability endpoint; broad qualification waits
for the series boundary. These are planned checks, not results reported as passed.

<a id="DMC-12"></a>

## DMC-I06 decision obligation and DMC-12 — Selected navigation/constraint delivery

DMC-I06 has two separately decidable branches: a relationship/navigation consumer and recurring
conformance vocabulary. Resolve them from DMC-01's actual effective relationship inventory and
the first correction/authoring journey. A useful candidate is explaining the member path of an
already qualified occurrence while preserving its qualifiers and collection position. The
selection record must name an actual relationship, starting point, required traversal universe,
returned occurrence identity and user action. Do not select a generic graph browser solely
because native path APIs exist.

For a selected path, use RDFLib `Path` composition and
[`parse_shacl_path`/`build_shacl_path`](https://github.com/RDFLib/rdflib/blob/7.6.0/rdflib/extras/shacl.py)
to share the admitted structural meaning between traversal, shape construction and display.
Explicitly admit predicate, sequence, inverse, alternative and the required zero/one/more
repetition forms; exclude `NegatedPath` and unknown subclasses. The installed builder can emit
an unencoded blank node for unknown path subclasses, so application admission must precede
encoding. Do not implement a second general path interpreter. Validate RDF list structure and
round-trip the selected grammar; do not broaden LinkML/native support merely by rendering it.

For recurring constraints, inspect the two current `_qualified_shape_triples` SPARQL checks
and selected new invariants for actual semantic equivalence under parameter changes. Keep
unique queries explicit. When repetition is real, use pySHACL's
[`sh:ConstraintComponent` and parameterized validators](https://www.w3.org/TR/shacl/#sparql-constraint-components)
with ASK/SELECT reporting and the selected
[component implementation](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/constraints/sparql/sparql_based_constraint_components.py).
Respect the selected engine's restrictions on MINUS, VALUES, SERVICE and `$shapesGraph`.
Custom component discovery is not equivalent to enabling SHACL-AF: `advanced=False` alone is
not a blanket prohibition. The admitted component's semantic profile, targeting and lowerings
still require their owning decision. No ordinary entailment/import/mutation profile change is
assumed.

Settle each branch by source inspection and one representative scenario; use a bounded retained
probe only if actual engine behavior remains consequentially uncertain. Outcomes are selected
delivery with its consumer and grammar, or retained direct-predicate/Core/unique-SPARQL behavior
with a concrete reason and revisit trigger. Merely writing an investigation summary cannot
complete selected DMC-12 delivery.

DMC-12 consumes only the DMC-01 relationship/provenance slice and DMC-11 report-path contract it
actually needs. A new supported declaration additionally waits for its faithful compiler/native
lowering package; a display-only path reader does not. Migrate the selected navigation command,
generated shape and diagnostic presentation together, removing their private RDF-list/path
encoders and duplicate equivalent invariant queries where replaced. Adjacent query/read owners
retain closure and snapshot responsibility. Dataset union and focus/shape selection do not
compute provenance isolation or affected closure.

Acceptance challenges forward/inverse/alternative/repeated paths, ordered members, parallel
qualified occurrences with identical endpoints, unresolved targets, unsupported/malformed paths
and independently known conforming/nonconforming component cases. Output filters must not
remove intermediate traversal nodes; operational work interruption stays partial. A bounded
requested relation/depth scope may be complete within that declared scope. Avoid materializing
all paths to produce a small witness list; reuse the prepared path/shape within the selected
release lifetime. These properties establish correctness and credible execution fit, not a
quantified performance improvement.

<a id="DMC-14"></a>

## DMC-I06 graph research decision and DMC-14 — Selected reproducible view

The research branch asks a precise question: can a declared view comparison or derived relation
answer a selected model/research question that existing typed SQL/query/export cannot answer
as directly? A candidate is comparing qualified identity-exclusion or concept-neighborhood views
under two immutable declaration sets. Selection must name the question, input snapshots,
relation universe, direction, multiplicity, asserted/derived distinction, witnesses, assumptions
and complete/partial contract. An example is not automatic selection of that research activity.

Compare complete operation routes in this order of relevance, without a compulsory API tour:

| Question shape | Candidate mechanism and decisive boundary |
| --- | --- |
| Existing relational selection or comparison | Keep typed SQL/query/export when it already supplies the needed semantics; avoid hydrating a second graph for equivalent filtering. |
| Explicit graph selection/view | RDFLib [`prepareQuery` and `initBindings`, CONSTRUCT](https://rdflib.readthedocs.io/en/7.6.0/apidocs/rdflib.plugins.sparql/) over the bound qualified projection; prepare stable queries once per operation/release, supply values separately. |
| Semantic RDF comparison | [`rdflib.compare.to_isomorphic`/`graph_diff`](https://rdflib.readthedocs.io/en/7.6.0/apidocs/rdflib.compare/), with the two graphs' blank-node scope explicit. Semantic equivalence is different from RDFC-1.0 archive-byte identity. |
| Topology/algorithm not supplied by the existing route | Native paths or a suitable NetworkX graph type, preserving node inventory and edge identities. A simple graph that merges parallel occurrences is unsuitable. Compare selected-data transfer plus algorithm work, not API appearance. |
| Entailed or recursive consequences | OWL-RL, SHACL rules/functions/JS or a Datalog engine only after naming the inference profile, recursion, termination/limit, premise eligibility and retraction/rebuild contract. No engine is selected by this plan in advance of that question. |

The last row is a bounded research-engine decision, not production authorization. Native
publication/inference keeps its current owner. Distinguish conformance, derivation, ontology
entailment, heuristic similarity and scientific support in the output. Additive SHACL rule
iteration does not promise arbitrary common fixed points or deletion-aware maintenance; consult
[SHACL-AF rule semantics](https://www.w3.org/TR/shacl-af/#rules) and the selected engine's actual
tagged source only if the chosen question needs it. Compare recomputation of a disposable view
with persistent maintenance; prefer disposable recomputation unless a real research lifetime
requires more.

DMC-I06 also disposes the related alternatives against the same consumer: alternate RDF stores
(RDF4J/GraphDB/Oxigraph), remote SPARQL, events/RDF Patch, JSON-LD/HTML/server interchange,
visualization and `Describer`/`infixowl`. Coordinate OAK federation/native OWL/subsetting or
source investigation with DMC-I09 in the [tooling plan](independent-consumers-and-configuration.md#DMC-16);
that branch owns domain-specific taxon/enrichment/plugin fit, reusing this graph decision.
Select only a capability that resolves the named query/interchange or authoring
problem. Remote acquisition requires exact captured inputs and effects; a store flag, patch
marker or graph type does not supply PostgreSQL transaction/custody semantics. Domain-specific
research must preserve suggestion versus selected meaning. Retain current query/export/source facilities with
a concrete trigger where no additional value is established. No second authoritative store,
ambient ontology service or generic research backend framework follows.

If selected, DMC-14 delivers one usable command/application research flow through existing
read/export/result owners: bind inputs, construct the declared view, perform the chosen analysis,
return bounded findings/witnesses and optionally retain a reproducible result. Capture exact
release/source digests, engine/method version, parameters and unavailable assumptions; immutable
inputs are reused across pages/retrieval. Derived graphs are disposable and never update
assertions. New release input produces a new result; an interrupted frontier records partiality
and cannot be compared as a complete view without explicit qualification. Remove a superseded
one-off script or private projection if this selected flow replaces it; existing independent
query behavior remains its own consumer.

DMC-14 needs the DMC-01 projection/meaning slice and selected query binding, and DMC-11 only when
using its detailed/retained report interface. DMC-12 is a dependency only if the chosen view uses
its newly admitted path/component. Vocabulary source preparation from the terminology packages
is a dependency only for a selected concept view; it is not required for identity-exclusion
research. Resolve the semantic/engine decision before downstream consumer implementation.

Acceptance uses manually known views with isolates, parallel edges, self-loops, reconvergent
paths, cycles, unresolved endpoints, shuffled input order and blank nodes from distinct source
scopes. Asserted edge changes and derived consequences remain distinguishable with premise
witnesses. Repeated execution under identical captured inputs yields semantically equivalent
results under the declared method, without asserting identical arbitrary blank-node labels.
Changed definitions, lost evidence, unsupported semantics and resource interruption are visible.
Test a high-degree frontier against examined-work/intermediate/byte bounds as well as output;
a small response or hop bound alone does not establish fit. No benchmark is required absent a
serious unresolved regression risk, and no numeric speed claim is made.

## Closure and evidence boundary

DMC-11 closes only after the actual repair/retrieval journey and migrated consumers work.
DMC-12/DMC-14 close after either their selected consumer is delivered and verified or the
coordinator records a justified retained branch with its concrete revisit trigger. DMC-I06 retains
separate outcomes for navigation, components, research engines and related interchange/tooling;
choosing one does not silently dispose the others. Formal review timing, rule-change approval,
overall package state and the required verification union remain in the coordinator. DMC-00
owns the due target-review route and DMC-17 owns assembled review/qualification.

Implementation will run scope-appropriate compile checks and targeted `uv run ci test -- PATH`
at coherent endpoints, followed by the coordinator's complete-scope `uv run ci test` and
`uv run ci check` accounting. Publication uses `uv run ci docs check`. No functional tests,
native/provider probes or performance experiments were run to author this document: **not_run**.
The target and benefits remain **Proposed, 2026-11-10**.


## Selected execution · 2026-11-10

**Accepted target; Proposed until qualified.** DMC11 defaults to safe messages and withheld input
values, with explicit raw-evidence opt-in. Preserve actual errors in-call, serialize bounded facts,
and distinguish safe presentation from original engine bytes. Managed retention is optional and
uses leased reads with content-digest verification. Safe/raw, assessment/inventory/render and
projection-dependency coverage are separately represented. Raw report messages themselves can
contain input, so withholding only an instance field is insufficient.

I06/DMC12 selects structural SHACL path display through admitted RDFLib forms, bounded before
recursive parsing. Existing occurrence-witness native walks retain their fact IDs and work bounds.
Retain the two unique SPARQL invariants/Core checks; revisit a parameterized component only when
the same invariant actually repeats under parameter changes. No richer executable model syntax,
SHACL-AF/JS, OWL-RL or Datalog engine is selected.

DMC14 selects a read-only pinned exclusion comparison under the same semantic release and
compatible operation version. Match authenticated observation key/local declaration ID, preserve
parallel declarations and unmatched/incomparable cases, and separate source declaration/evidence
changes from resolution bindings. Typed scoped SQL selects before hydration. Snapshot-generated
RDF identities are not semantic comparison keys. Partial populations cannot establish absence.
Optional managed retention captures this reproducible result without changing assertions.

Prepared SPARQL/CONSTRUCT and semantic RDF comparison remain alternatives for a genuinely RDF-shaped
external/view question; NetworkX awaits a named topology algorithm preserving occurrence identity.
Rules/OWL/Datalog await named entailment/recursion/premise/rebuild semantics. Alternate stores,
remote endpoints and patch/events await an actual store/exchange and recovery lifetime. JSON-LD,
HTML/server, Describer/infixowl and visualization await named interchange/presentation/OWL authoring
needs. Existing typed reads, export and disposable recomputation serve the selected question.
Coordinator owns dispositions and accepted evidence; these retained choices are not claims that
those libraries lack the capabilities.
