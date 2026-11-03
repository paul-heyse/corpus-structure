# Operation explanations, semantic impact and actionable validation

> Current execution (2026-11-03): implementation is integrated under
> [ADR-0047](../../adr/0047-current-only-domain-runtime.md); the
> [coordinator checkpoint](../unified-domain-model_2026-11-01.md#current-execution-checkpoint--2026-11-02)
> owns current disposition and open acceptance. Historical compatibility/repair statements below
> retain their dated baseline; obsolete runtime formats are retired, while current archive custody
> and query compatibility remain supported. Final assembled qualification is open.

**Status:** Implementation integrated; current-only targeted closeout and assembled acceptance remain with the coordinator. **Created:** 2026-11-01.
**Target maturity:** Proposed. The [coordinator](../unified-domain-model_2026-11-01.md) owns
package state, source disposition and assembled acceptance. This companion owns UM-11–UM-13
and delivers selected review opportunities [O01](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#O01),
[O02](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#O02) and
[O03](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#O03).
These capabilities are selected for delivery, not merely retained as future ideas.

## 1. Baseline, consumers and foundation assessment

Planning uses review revision `370f0643`, its three applicability accounts and identified current
source seams. Concurrent PDF/native source and evidence are evolving context. This series neither
waits for all PDF work to finish nor claims its qualification; later baseline reconciliation is a
separate update. Paths below are relative to `python/corpus-structure/src/corpus_structure/`.

`semantic/contracts.py:297–407` already represents invariants, implementation bindings, operations,
result dimensions and projection contracts; `bound_execution_model` resolves an exact archived
product. Existing owner-specific native/operation checks decide actual applicability and effects.
The new capability exposes their meaning and observations rather than inventing another executor.

The release already retains normalized definitions, execution products and projection dependencies.
These can explain declared change impact, but do not prove arbitrary Python or PostgreSQL behavior
equivalence. The semantic contract owner must identify which dependencies are complete and which
cannot be settled from declared products.

Existing preparation diagnostics, Pydantic validation errors, JSON Schema located errors and
`semantic/ontology.py:722–770` graph diagnostics carry different evidence. Their composition can
improve actionability without collapsing invalid data, invalid shapes, failed evaluation and
unassessed coverage. Keep the underlying validators and independent native enforcement.

## 2. Public domain contracts and delivery surfaces

Use typed request/result contracts under the existing semantic and serving owners. Conceptual
product names below express meaning; they do not require a new registry, service or persistence
object for every report. Static request/result declarations follow UM-03's generation rules.

| Capability | Input and result meaning | Delivery surface |
|---|---|---|
| Operation explanation | Exact supported release, declared operation and optional typed subject/context; declared inputs/results/effects plus checks classified applicable, unavailable or unresolved. | Add `ci schema explain-operation OPERATION --release RELEASE --json` with subject/context options and an MCP `explain_operation` tool using the same domain function. Human CLI rendering is a projection of that result. |
| Semantic impact | Two supported immutable release references; classified normalized changes and affected declared consumers, with unknown impact explicit. | Add `ci schema diff BEFORE AFTER --json` and MCP `compare_semantic_releases`, backed by one domain comparison. |
| Located validation | Existing validation invocation/result plus exact source/model/operation binding; located observations retaining original cause and enforcement scope. | Extend current schema-check and validation/refusal JSON results and MCP failure/report surfaces. Provide a shared report reader/renderer; do not introduce a parallel validation command or a new validator. |

Reports bind the release/model and operation/query/projection revisions they interpret. A CLI or
MCP adapter does not independently reconstruct applicability, assign a semantic-diff policy or
translate all validator failures into one Boolean. Old unsupported product shapes refuse explicitly;
missing analysis is not an empty successful report.

## 3. UM-11 — Explain operation applicability

**Required input:** UM-02's invariant observability and owner bindings; UM-03's request/result
contracts where generated invocation is exposed. Static descriptions can be prepared from existing
exact contracts before all live check evaluators exist. UM-04 supplies consistent serving pins.

**Delivered behavior:** an operator or agent can see what a declared operation consumes, produces,
requires and may change, and why it is currently unavailable or unresolved for the supplied subject.
Every declared operation can expose its static contract. Live applicability initially covers the
maintained read, analysis and publication families; an operation without a qualified live evaluator
returns unresolved rather than claiming a false availability verdict.

Compose `OperationContract.applicability`, dependencies, transitions, result dimensions and
`ImplementationBinding` with the existing owner-specific checks. Use the same resolved release
and trusted implementation compatibility as actual invocation. Checks report a stable model/contract
reference, evaluated scope, relevant expected/actual fact and reason. Do not interpret prose
invariant descriptions as executable predicates. Avoid exposing private storage details when a
model-level missing prerequisite explains the outcome.

The result is an observation at a stated input/state revision. It never authorizes later effects.
The protected operation still rechecks current mutable state, owner, input revision and privileges
atomically. A response that says applicable cannot bypass a refusal after another writer changes
state. Pure contract inspection performs no provider work and no publication/adoption effects.

**Concrete library role:** LinkML effective definitions and normalized execution products supply
concept/property/operation meaning; prepared Pydantic models and `TypeAdapter` validate typed
subject/context input. Existing SQLAlchemy query functions inspect needed state through one owned
snapshot. No graph rule engine or universal function-name dispatcher is added. This composition
lets another frontend consume the same answer without duplicating policy.

**Migration and acceptance:** wire both actual CLI and MCP adapters to the domain function, remove
adapter-local prerequisite explanations where superseded, and preserve raw failure causes.
Exercise available, missing prerequisite and unresolved evaluator cases; a changed implementation
binding; wrong-release subject; and stale preflight followed by native refusal. Assert no mutation
or provider execution from read-only explanation. Independent expected reasons must follow the
contract rather than call the explanation function to manufacture expected output.

## 4. UM-12 — Explain semantic changes and declared consumer impact

**Required input:** UM-01's explicit comparison projection, UM-02's invariant contract, UM-03's
operation products and UM-05's projection dependencies for affected scopes. UM-08 can add qualified
SQLGlot projection analysis; other normalized-change reporting does not wait for that whole package.

**Delivered behavior:** compare supported normalized releases and distinguish added, removed,
changed and unassessable definitions. Show the changed contract/property/result/invariant/projection
and the consumers whose declared dependencies intersect that change. Keep exact producing model
references and a reason for impact classification. Stable bytes or syntax alone are not proof of
behavioral equivalence; unchanged declared products mean only unchanged examined definitions.

Use existing normalized definitions and dependency products rather than YAML line differences or
a general semantic-diff language. A changed comparison role can affect scientific grouping without
changing full fact identity; a result optionality change can affect generated clients; a changed
invariant implementation can alter admission. Preserve those different consequences. Unknown or
incomplete consumer dependencies produce unknown impact with an explicit scope, not “no impact.”

**Concrete SQLGlot role:** for the first companion-family consumer, derive `MappingSchema` and
admitted helper return metadata from the same model/native signatures. Construct `exp` nodes from
the single projection recipe, run strict `qualify(..., dialect="postgres",
validate_qualify_columns=True)`, then `annotate_types` and `lineage`. Persist or reuse only the
prepared model-identified dependency product appropriate to its immutable lifetime. SQLGlot's
runtime SQL types are not static domain types or PostgreSQL overload authority. Its column lineage
supports a projection impact explanation; it does not replace semantic dependencies, source
assertion provenance, native authorization or O02's conservative unknown handling.

Consume UM-08's dependency kinds, not only output-value lineage. A WHERE-only property, join key,
group/order expression or bound helper can affect the answer without changing its output-field
lineage. Supported nested model-owned sources use UM-08's pinned expansion and scope profile;
incomplete structure or missing source coverage remains visible in impact output. The comparison
does not invent its own expansion, name resolution or type interpretation.

**UM-I12 — Impact integration:** consume UM-08-I1's qualified projection-analysis profile and
verify that a changed dependency and an incomplete/unknown result survive the actual impact
report and CLI/MCP presentation. UM-08 owns SQLGlot/PostgreSQL feasibility and supported scope;
this package does not repeat it. If that result limits coverage, preserve the limitation in the
consumer result and keep any unmet capability obligation open. Do not silently drop O02 or make
SQLGlot a second editable query/schema owner.

**Migration and acceptance:** both CLI and MCP consume one comparison result. Test an added
qualifier, changed comparison role, changed result dimension/nullability, invariant implementation
and projection field/path. Include unchanged examined products and intentionally incomplete
consumer dependencies. Expected impacted consumers must be independently specified. Verify that
ordinary report generation does not require a live provider, mutate releases or rebuild every
immutable compiled artifact. Wire its result into compatibility/regeneration advice without
making the report itself an authorization to activate or migrate.

## 5. UM-13 — Actionable validation across representations

**Required input:** UM-02's observable failure contract and UM-03's typed report shapes. Existing
validators are usable inputs before all native rewrites finish. UM-04 pins served report meaning;
UM-06/UM-07 must preserve the same failure distinctions when their enforcement changes.

**Delivered behavior:** an operator/agent receives a located observation identifying model/release,
concept or relationship, exact input/member path, operation, enforcement scope, source diagnostic
and remedy category. Keep these meanings separate: invalid supplied data, invalid schema/shape,
state violation/nonconformance, validator execution failure and unassessed coverage. Preserve the
original native code/SQLSTATE or validator report reference as cause; do not fabricate a domain
invariant code for an unmapped native failure. Native message text remains descriptive.

For generated projection analysis, consume UM-08's model/member origins, structural diagnostics
and available SQL positions. AST transformations can lose text spans, so a stable model path is
the required fallback. Report an opaque/unsupported construct as incomplete or refused analysis,
never as successful validation; SQL comments/directives cannot establish an enforcement promise.

Compose existing production validators and reports. Pydantic 2.14.1 `ValidationError.errors()`
provides typed boundary locations and categories. JSONSchema 4.26 reusable validators with checked
schemas, explicit `referencing.Registry` and `iter_errors` supply draft/resource-qualified paths;
schema annotations do not execute transformation or every custom format. Preparation diagnostics
retain the authored source/contract reference. RDFLib `Graph` resources preserve assertion/report
identity and pySHACL 0.40.1 `validate` returns conformance plus an RDF report; retain focus node,
path, source shape/constraint, severity and actual execution configuration.

Graph conformance remains relative to the complete supplied universe. Keep inference, advanced
rules, imports and mutation explicitly disabled unless a separately qualified operation selects
them. Dataset union is not isolation; focus-node filtering does not establish complete incremental
impact analysis. Reusable parameterized SPARQL components are a candidate only for genuinely
repeated graph constraints. This package adds mappings/rendering, not a common truth evaluator or
another semantic-validation engine. Raw reports remain available through their existing custody.

**Migration and acceptance:** replace adapter-local flattening in maintained schema-check,
operation/refusal, graph-validation and CLI/MCP consumers with the typed report projection.
Keep existing wire compatibility only where maintained consumers require it; intentional changes
must be versioned with the generated result contract. Exercise invalid scalar/nested input,
missing/null/unsupported distinction, cross-record or relationship failure, invalid shape,
validator infrastructure failure and explicitly unassessed scope. Check exact member/occurrence
paths and that separate causes remain distinguishable through the actual served response.

### Published document explanations, impact and failures

Use the [UM-02 invariant](semantic-contracts-and-policies.md#published-document-address-invariant)
and [UM-05 binding](relational-implementations-and-projections.md#published-document-consumers)
as a required O01–O03 integration case. Explain separately whether the exact document is published,
its selected source views/context are prepared, rendering has a qualified region/original, and the
invoked consumer realization supports that address contract. Qualified checks reuse actual owners;
an unimplemented evaluator reports unresolved. Read-only explanation performs no inference or
repair, and native effects still recheck current owner/state and resolved bindings atomically.

Impact reporting includes declared relationship targets, composite endpoint correspondence,
selection membership/order and projection implementation/recipe dependencies. A changed FK target
or selection predicate can affect consumers without changing output-column types or document
content identity. Distinguish physical realization changes from changed domain meaning, and retain
unknown dependencies. SQLGlot supplies only its qualified query coverage; model/native relationship
facts supply enforcement dependencies, without another catalog or behavior interpreter.

Located diagnostics retain product/model/operation references, section or region coordinates,
enforcement scope and named native constraint/guard identity. A consumer-preparation failure after
successful publication must not be reported as invalid document content. Classify incompatible
realization versus invalid address only when supported by admitted bindings and actual evidence;
unmapped errors retain native cause/effect knowledge. Recovery advice identifies preparing consumers
from the retained pin, rather than rerunning OCR by default. Full domain error promises and CLI/MCP
delivery remain UM-02/11/13 obligations, not implied by preserving an error message.

## 6. Integration and completion

[Semantic contracts](semantic-contracts-and-policies.md) own meaning and observability;
[typed operations](typed-domain-operations.md) own generated signatures/report types;
[relational projections](relational-implementations-and-projections.md) own the shared expression
recipe; [query compatibility](query-compatibility-and-serving.md) owns serving implementation pins.
This companion owns useful interpretation and explanation, not authority over execution effects.

The [semantic assessment](../../library_leverage/libraries/unified-model-semantics_2026-11-01.md),
[boundary assessment](../../library_leverage/libraries/unified-model-boundaries_2026-11-01.md) and
[PostgreSQL assessment](../../library_leverage/libraries/unified-model-postgresql_2026-11-01.md)
retain source/tagged evidence. Use exact supported versions rather than crediting fixes from newer
addenda: pySHACL 0.40.2, Pydantic 2.14.2 and settings 2.16.2 are separate from researched installed
pins. SQLGlot 30.27.0 is installed exactly; current recipe analysis is bounded-tested, with selected source-composition scope still open.

Completion requires all three domain functions and actual CLI/MCP consumers, explicit support
limits, retirement of superseded adapter interpretation, applicable independent controls and the
[assembled integration](integration-adoption-and-qualification.md) journeys. It establishes delivered
operator/agent capabilities, not complete behavioral equivalence, universal dependency knowledge
or improved extraction quality. Benefit measurements are separate if later claimed. No tests,
probes, provider journeys or product changes were performed while authoring this plan.

## Execution checkpoint — 2026-11-02

**Implemented, bounded tested:** `model/semantic/operation-reports.yaml` is a trusted LinkML
source, supplying the actual prepared Pydantic report schemas used by domain functions and
FastMCP output schemas. Always-present report arrays permit zero members through authored
`value_presence: PRESENT`, distinct from the existing required/nonempty convention. Reports
identify their schema digest; normalized operation meaning comes from the exact archived model.

`semantic.operation_reporting` supplies shared explanation, normalized semantic comparison and
located validator/native projections. CLI `schema explain-operation` / `schema diff` and MCP
`explain_operation` / `compare_semantic_releases` call these functions. Operation inspection
preserves unresolved checks; native admission observation uses the existing protected check in a
savepoint and grants no later effect authority. Publication-pin lookup uses the existing owner.
Pydantic, JSON Schema, graph shape, graph execution and admitted/unmapped native failures remain
distinct; original diagnostics/SQLSTATE/constraint and raw graph-report references are retained.
CLI/MCP refusal rendering now uses the same located report alongside existing error information.

Semantic impact consumes archived qualified projection products, including non-output relational
changes, declared native/export consumers, expression/model origins and helper limitations.
Absent/unsupported archives remain unknown or explicitly refused. A changed implementation digest
is not labeled behaviorally equivalent. The library realization and product lifetime are recorded
in the [relational companion](relational-implementations-and-projections.md#execution-evidence--2026-11-02).

Focused reporting/analysis passed12 cases and retained-product impact passed4 cases, with an
8-case affected expression/product union subsequently passing. Scoped warning-inclusive Pyrefly
and Ruff passed for root-owned report/analysis/CLI/refusal files. These are component results;
actual native CLI/MCP positive/refusal/stale-state journeys, full maintained validation-consumer
closure and UM-11/12/13 assembled acceptance remain required. No provider or scientific quality
claim follows from these report controls.

**Tested, bounded actual adapters:** the actual PostgreSQL archive → CLI explanation/diff →
FastMCP explanation/diff journey passed as part of17 report/analysis controls on2026-11-02
(`build/test-receipts/um-actual-reports-00003.jsonl`). The native admission refusal on the older
head remained explicit; that pass does not establish positive admission to the new native head.
The earlier invalid numeric output-schema failure is retained. Shared boundary construction now
uses integer/float numeric bounds, with integer ceilings/floors preserving fractional thresholds;
Decimal value validation/serialization remains exact. Nine numeric/presence controls passed.

MCP registration reads the generated `model/semantic/operation-report-schemas.json` product,
identified by the closed source schema, compiler/boundary and library versions. The output schema
comes from the same prepared adapters as actual reports. This avoids executing ontology/Arrow
preparation simply to list tools; cold registration passed. A missing/stale artifact refuses with
an actionable generator command, `uv run python -m corpus_structure.semantic.operation_reporting`.
There is no current-schema fallback or second editable report schema. The source acquisition
helper `trusted_execution_schema()` supplies schema bytes without provider/implementation loading.

Published subjects reuse the modeled product pin with optional run/section/region context; snapshot
subjects reuse the retained `CaptureSnapshotBinding`. Read-only observations use existing owners
for publication, selected views, exact regions and source realization/revision. Original digest
metadata is reported separately from byte availability; explanation does not fetch the PDF or
rasterize it. Missing live evaluators remain explicit.

Subject observation follows the exact bound operation's existing context concepts: a
`SnapshotBinding` input selects snapshot inspection; a `SourceView` input/result selects published
document context. Mixed or other concepts refuse a supplied live subject while preserving static
inspection. Operation names and generic PDF product pins do not determine the observer. This
keeps recognition observations from being misreported as unavailable document publications.

**Tested, bounded forward-head consumers (2026-11-02):** actual small PostgreSQL publication
followed by CLI/MCP inspection distinguishes a published pin from an unprepared source context,
then observes available context after real source-view preparation. A missing exact pin remains
unavailable. Invalid task input reaches both adapters as `invalid_input` at `/task_id`.
This case passed in `build/test-receipts/um11-13-native-reports-00001`; the same receipt retains
two stale test expectations, corrected in the following affected-case run. The two actual
archive/report adapter cases passed in `um11-13-native-reports-00002`: native84 admits the
retained operation, and a changed retained coverage predicate reports its WHERE dependency,
qualified native/export consumers and helper-body unknowns through CLI and MCP. No provider,
publication effect or arbitrary archived Python is executed by these observations.

Semantic comparison now includes declared concepts, relationships, lifecycle/state composition,
transitions, effects, outcome domains/translations, native guards, analysis profiles, parser
adapters and required capabilities. Consumer edges from both compared releases are retained;
removing a dependency does not erase the old consumer from impact. Projection, invariant and
transition declarations supply the existing connections; undeclared closure remains unknown.
The independent relationship/lifecycle/removed-edge control and affected report/analysis unit
union passed16 cases (`build/test-receipts/um12-contract-edge-impact-00001.jsonl`). These
are bounded checks, not assembled UM-11–13 or complete-plan qualification.

An absent family in an incomplete archived analysis is unassessed, not a removed projection.
The retained unsupported-physical-profile control verifies this distinction (four affected
product/impact cases passed in `build/test-receipts/um12-unknown-not-absent-00001.jsonl`).

**Implemented and tested, bounded review repairs (2026-11-02):** changed normalized definitions
now expose typed `members` with stable member paths and lossless before/after `SourceValue`
facts. Added/removed members distinguish absence from explicit null; ordered collection changes
retain order and multiplicity. Named-member matching applies only where the complete ordered
identity sequence is unchanged; membership changes retain the actual before/after sequence so
insertion/removal positions cannot disappear. Report schemas import the existing observations
model rather than introduce another value representation. The independent report/product unit
union passed22 cases (`build/test-receipts/um-report-review-repairs-unit-00002.jsonl`).
Three subsequent independent insertion/removal-position cases passed in
`build/test-receipts/um-report-ordered-membership-00001.jsonl`; scoped Pyrefly and Ruff passed.

Qualified native diagnostics preserve an available operation release and exact invariant model
without requiring a separately supplied preparation object; contradictory supplied bindings refuse.
Live prerequisite observers translate only named absence and expected native admission refusals.
Malformed result admission, semantic incompatibility and infrastructure failures propagate to their
existing located diagnostic boundary. They are not reported as a missing document/region.

The actual retained compiler20 task10 release also passed static CLI inspection and explicit
CLI/MCP refusal of the absent retained `PublishedDocumentSubject`, with actionable static/new-release
advice ([archive subject evidence](../../design_review/evidence/2026-11-02_um-archive-subject/README.md),
`um.archived-subject-23`, current compiler23 reader). This read-only check did not migrate or
republish the operational book.
Current native property-difference presentation and the actual composite-address diagnostic remain
in the coordinated final native consumer selection; these unit/archive results do not replace it.

## Completion audit — 2026-11-02

**Baseline:** `fb84eb8f`; independent source/consumer and library-mechanism inspection, with no new
product tests, provider runs or database mutations. The coordinator owns all current disposition.

Actual CLI/MCP explanations/diffs, regeneration advice and located graph/native/boundary reports consume shared model products. Known release/model/operation context is retained. Class/helper impact and unsupported live evaluators remain explicitly unknown/unresolved. No newly confirmed material implementation gap in UM-11–13; optional I05 and further qualified observer coverage do not establish universal dependency knowledge. Actual acceptance remains open at UM-CA10.

See the [coordinator audit](../unified-domain-model_2026-11-01.md#completion-audit--2026-11-02)
for combined judgment, UM-CA evidence and remaining obligations. Library tables above retain their
accepted mechanisms and limits. New improvement proposals are separately published and unadopted.

## Test-architecture reconciliation — 2026-11-02

**Selected amendment:** Current implementation and qualification are owned by the coordinator.
TA foundations retain their declared scope; their completion does not itself qualify UM.

**Selected extension planned: [review I01](../../plan_improvement_reviews/unified-domain-model-test-architecture_2026-11-02.md#I01), coordinator UM-TA02.**
Extend `compare_semantic_releases` to compare released `operation/alias-policy.json` by profile
and full class IRI. Reuse the compiled product, existing `_changed_members` and generated
SemanticImpactReport. Separate normalization changes (including rewrite order) from origin-only
provenance changes; added/removed policy and missing/incompatible profile remain explicit.
Do not parse live pack YAML or treat absent unknown policy as an empty supported policy.

Use existing versioned model/implementation dependency bindings to identify actual entity-mapping
and semantic-alignment consumer kinds; do not invent operation IDs for non-operation consumers
or maintain a parallel editable registry. Unknown dynamic closure remains unknown. Feed the
same result into CLI/MCP diff and regeneration advice. If report contracts change, generate and
admit their versioned schema through the existing forward route; frozen revisions stay immutable.

Independent alias-only, ordered-rewrite, origin-only, added/removed and unknown-profile cases
must reach actual served reports/advice with unchanged class shapes. Keep producing-release
meaning stable. I05/I06 custody/runtime corrections precede claims relying on those respective
boundaries; TA's single accepted stdio tool journey does not qualify all O01/O02/O03 consumers.
