# Operation explanations, semantic impact and actionable validation

**Status:** Planned; implementation and verification not_run. **Created:** 2026-11-01.
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
pins. SQLGlot 30.27.0 remains a researched candidate until deliberately added and qualified.

Completion requires all three domain functions and actual CLI/MCP consumers, explicit support
limits, retirement of superseded adapter interpretation, applicable independent controls and the
[assembled integration](integration-adoption-and-qualification.md) journeys. It establishes delivered
operator/agent capabilities, not complete behavioral equivalence, universal dependency knowledge
or improved extraction quality. Benefit measurements are separate if later claimed. No tests,
probes, provider journeys or product changes were performed while authoring this plan.
