# Actionable validation, portable contracts and graph research

**Proposed functional judgments, 2026-11-10.** [Shared baseline](../domain-data-model_2026-11-10.md).
Sources: discovery [graphs](../../library_leverage/libraries/domain-data-model/briefings/qualified-graphs.md)
and [portable contracts](../../library_leverage/libraries/domain-data-model/briefings/portable-contracts-and-settings.md).

<a id="O09"></a>

## O09 — A bounded correction view over actual validator evidence

**Recommend.** A model author or agent currently receives a selected JSON failure or flattened
graph diagnostic. For a nested union, several invalid fields or a composite graph path, the
first message can be insufficient to decide what to correct. The proposed workflow requests
repair-oriented detail through the existing validation/result interface, follows a source/schema
location, sees subsidiary causes and revalidates after correction. Ordinary refusal remains compact.

[ontology.py](../../../python/corpus-structure/src/corpus_structure/semantic/ontology.py) retains
full canonical RDF in GraphValidation, extracts focus/path/shape/component/severity/message and
distinguishes invalid shape, engine failure and nonconformance.
[operation_reporting.py](../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py)
turns those into located observations with original-report digest. This digest alone is not
retrievable report custody. Current dirty v3 dependency pages supply projection analysis detail,
not nested JSON causes or complete graph details; build on its established report boundary
without calling those scopes equivalent.

**Mechanism and composition.** jsonschema `iter_errors`, nested `context`, structural paths,
validator keyword and causes can supply an explicitly bounded correction view without
revalidating per field. Graph detail can read `sh:value`, `sh:sourceConstraint`, `sh:detail`
and structured `sh:resultPath` from the actual report graph. Preserve engine-specific evidence
and location types in the shared report envelope. A caller-owned report can be rendered directly;
if later retrieval is promised, retain the bytes under existing result custody with an actual
resolvable reference and declared lifetime. Do not invent a parallel diagnostics archive.

**Compared alternatives.** Keep first-error refusal when no correction is requested; expose the
raw engine report to expert research consumers; or add a separate diagnostics subsystem. Prefer
an opt-in existing-owner view: it serves both an agent and the operator while preserving compact
ordinary calls. `ErrorTree` loses same-path/keyword multiplicity and is not a replacement for
original errors. A graph path blank-node identifier is not a readable path. Report generation
can normalize message language, so do not promise lossless original-language retention.

**Delivery and limits.** A union error shows branch causes rather than claiming all branches
apply; repeated keyword errors survive where requested; graph detail identifies the offending
value and path under the right release; failed validator execution stays distinct from invalid
data; truncation reports incomplete detail; an expired raw report is unavailable rather than
recreated under today's semantics. Retain independently authored invalid examples. No diagnostic
field proves scientific support, and a complete error list need not imply complete source coverage.

<a id="O10"></a>

## O10 — Relationship navigation and reusable conformance vocabulary

**Conditional on a selected richer relationship/navigation workflow.** An operator or research
agent could traverse a declared qualified relationship, inspect its member path and apply the
same meaning in graph conformance. A model author could reuse one parameterized invariant
across related shapes. This is useful prospective functionality even before several duplicated
queries exist; it does not justify abstracting the current two unique queries on its own.

RDFLib `Path`, `parse_shacl_path` and `build_shacl_path` can connect traversal, shape construction
and report display for a bounded grammar. LinkML relationship roles can inform its model-owned
definition where they faithfully represent the application's qualified facts. pySHACL native
`sh:ConstraintComponent`, parameter bindings and ASK/SELECT validators can express recurring
conformance with engine targeting/reporting. Custom component discovery occurs outside the
advanced branch in selected pySHACL; `advanced=False` does not prohibit every custom component.

**Alternatives and choice.** Keep direct-predicate Turtle/Core shapes for simple constraints;
use explicit SPARQL queries for genuinely unique invariants; use a supported path/component only
when it carries the declared relationship without another private interpreter. Do not equate
relationship graph connectivity with a supported assertion or infer occurrence identity from endpoints.

Installed RDFLib7.6.0 path construction can return an unencoded blank node for unknown Path
subclasses. Explicitly admit predicate/sequence/inverse/alternative/repetition forms and reject
unsupported grammar such as NegatedPath. pySHACL's SPARQL restrictions and absent shapes-graph
support constrain candidate components. Focus/shape selection does not compute affected closure;
Dataset validation uses a union. The required semantic universe must remain explicit.

**Delivery and trigger.** Select one real navigation or repeated-invariant consumer and show
its readable path, qualified parallel occurrences, ordering and malformed/unsupported-path
refusal. Verify independent known answers for the chosen component. New admitted relationship
syntax needs faithful lowering/profile decisions; no general SHACL-AF or entailment change follows.

<a id="O11"></a>

## O11 — Self-contained contracts for independent tooling

**Conditional; retain current finite local schemas by default.** An independent research script
or client could obtain the exact release's portable input/output contract, validate offline,
and explain a failure against retained definition addresses. This can complement existing
detached Arrow exchange with schema-aware tooling, rather than exporting another instance store.

The project already prepares local checked validators in pdf_payloads/pdf_records, uses
`evolve` for branch mapping and retains producing schema bytes in pdf_contracts. The prospective
capability is a consumer-oriented package with explicit dialect, resource identity, supported
semantics and source/release custody—not simply adding a Registry it already uses.
`ci schema derive` and `compile --out` already export manifests, source snapshots and model
artifacts. The additional proposition is a selected independent consumer's closed contract
package, not introducing portable export where none existed.

Pydantic `TypeAdapter.json_schemas`/shared definitions and validation/serialization modes can
derive mechanical contracts. jsonschema `Registry`/`Resource`, anchors and explicit specifications
can close the resource package offline. Package only required registered resources; reject
unavailable references and unsupported dialect/vocabulary instead of silently using fallback.
Native PDF mapping's narrower local-reference profile remains separate from general JSON Schema.

**Alternatives.** Link the existing standalone schemas; export raw source modules for expert
authors; generate an SDK or OpenAPI description. Prefer standalone retained schemas until an
independent consumer needs multi-resource composition. A JSON Schema package does not promise
Pydantic custom-validator parity, reference integrity, scientific support or native enforcement.
Dynamic references and unevaluated regions are appropriate only if their actual consumer needs
and selected dialect are supported. Rust/PyO3 or generated language types are later options for
a concrete consumer, with structural versus executable fidelity declared.

**Delivery and trigger.** Name the independent tool, disconnect it from the original environment
and validate known valid/invalid variants under the package's stated scope. Cover external
reference refusal, required resources, input/output differences and unknown dialects. Prior
Arrow transfer success is not evidence for this new schema consumer. No general SDK/server or
cross-language generation is selected merely because a generator exists.

<a id="O13"></a>

## O13 — Reproducible derived graph views for research

**Conditional research extension.** A researcher could inspect a declared bounded relation view,
compare two projections semantically and explore candidate consequences without changing
accepted source assertions. Example: compare identity-exclusion or concept-neighborhood views
under two pinned declaration sets, distinguishing changed asserted edges from derived reachability.

Start from the existing qualified projection and explicit relation universe. RDFLib prepared
SPARQL/`initBindings`, CONSTRUCT and `rdflib.compare` can supply a disposable query/diff route.
Native paths or a graph algorithm library may fit traversal better; choose the complete operation
according to semantics and data movement. OWL-RL, SHACL rules/functions and Datalog are alternatives
only when their entailment/recursion contract matches the proposed question.

**Preferred boundary.** Preserve asserted/derived identity, premise witnesses, model assumptions,
complete/partial outcomes and exact release inputs. Rebuild disposable derived graphs when useful
instead of introducing persistent truth maintenance. Production native inference/publication stays
with its owner. Additive SHACL iteration does not establish deletion-aware maintenance or an
arbitrary common fixed point. Independent graph comparison is not canonical archive-byte identity.

**Alternatives and revisit.** Existing typed SQL/query/export may already answer the question;
prefer it if graph hydration adds no capability. Alternate stores, remote SPARQL, RDF Patch,
JSON-LD/HTML, NetworkX and visualization deserve consideration for a named research/interchange
activity, but no second authoritative store or service is recommended. Select a concrete question
and admitted semantic profile before deeper backend work.

**Delivery.** Known-answer views retain isolates, parallel edges, unresolved endpoints, cycles
and qualification. An output filter must not shrink a required traversal universe. Bounded
interruption stays partial; semantic comparison scopes blank nodes correctly. Neither graph
similarity nor entailment may silently acquire scientific standing. Expected usefulness remains
Proposed; no graph probe, performance result or compatibility experiment was run here.
