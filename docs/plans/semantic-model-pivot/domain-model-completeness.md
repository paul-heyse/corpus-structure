# Complete domain model and executable contracts

**Status:** SP-C01 definitions/products implemented; effective behavioral and SP-C02 admission/lowering closure partial (completion audit below) · **Created/Revised:** 2026-10-29.
[Coordinator](../semantic-model-pivot_2026-10-29.md#10-domain-model-completeness-integration)
owns current package state, queue and opportunity disposition. This document owns SP-C01/SP-C02
and the shared definitions consumed by [realization](domain-model-realization.md).

## 1. Input, scope and preservation

Consume the [completeness review](../../functional_reviews/semantic-domain-model-completeness_2026-10-29.md)
and [target model](../../functional_reviews/semantic-domain-model-completeness_2026-10-29_target-model.md)
at dcc5e0b, reconciled with the current working tree. Its O01–O07 are selected for planning.
References to those opportunities use the review path, not an ambiguous bare O-number.

The review addresses transitioned SP-00–SP-05 and delivered SP-06/SP-07 behavior. These packages
strengthen that implementation; SP-08 later consumes the stronger contracts. They do not classify
unfinished legacy paths as defects or absorb unrelated phase-0 scope. Existing implemented
profiles and passing receipts remain intact. The coordinator distinguishes them from new work.

Preserve release/realization-scoped identities; independent source occurrences; exact values,
qualifications and source context; known-input lineage; source-grounded finite proofs; immutable
archives and completed results; parent-plus-generation activation; protected PostgreSQL
publication; one snapshot and local analytical resource ownership. Reasons, evidence and
confidence remain outside proposition/group identity where the target specifies.

The intended result is a model that governs existing behavior. More annotations, a complete
schema diagram or generated JSON Schema alone do not deliver it.

## 2. Foundation assessment and selected design

The review's source inspection remains applicable to the planning baseline; inspect intervening
source changes at execution start. Core 3.3, efficient-architecture heuristics 1.0 and profile 1.4
apply through standard.toml. This is focused plan assessment, without another diagnostic audit.

| Existing foundation | Reuse and required extension |
|---|---|
| model/semantic core, agent and observation modules | Reuse typed values and report/proposal boundaries; add missing operational, decision and projection concepts and their connections. Raw source payloads may remain generic where no domain decision depends on their interior. |
| physical.yaml and semantic.metadata | Keep fixed storage and shared Core metadata. Lift semantic relationship/state meaning into typed logical contracts; physical SQL annotations remain a lowering, not a parallel definition. |
| semantic.types/prepare | Reuse immutable inputs, normalized products and bounded pure-preparation cache. Add execution compatibility, relationship/operation descriptors and required invariant resolution. |
| semantic.releases | Preserve exact archive/reconstruction and activation; include new model products without reinterpreting older archives under new defaults. |
| operations, domain_operations, inference and native routines | Preserve owned algorithms and strong existing fences; connect them to complete contracts through SP-C03/SP-C04. |
| query, analytics and arrow_publication | Preserve native snapshots, strict reconstruction and protected COPY; consume named projection/input/result contracts through SP-C05. |

### One model with explicit semantic scopes

Trusted execution definitions are LinkML-authored and code-versioned. They own operational
lifecycles, privileged invariants, implementation bindings and physical projection compatibility.
Immutable semantic releases own domain meanings, vocabulary/ontology snapshots, scientific rules
and analytical interpretation. A bound operation names both compatible revisions. Domain data
cannot replace the trusted execution definitions or publish privileged code.

Use a small typed LinkML companion for ConceptDefinition, RelationshipDefinition,
LifecycleDefinition, TransitionDefinition, OperationContract, InvariantDefinition,
ImplementationBinding and ProjectionContract. These conceptual names do not require a separate
runtime registry/table for each. Finite trusted contract instances and release-authored policies
are validated data, not a new YAML grammar or universal workflow language.

Ordinary functions own source placement, identity, mathematical comparison and proof algorithms.
Each material function has a resolved contract specifying typed inputs, applicability, outputs,
effects, outcomes and dependencies. Invocation references resolve to approved implementations;
no import-by-string or arbitrary authored Python/SQL execution is introduced.

### Required connected definitions

Carry the target companion §§2–5 into executable definitions, retaining these coverage families:

| Family | Connections the definitions must expose |
|---|---|
| Interpretation | Bundles/artifacts, dependency snapshots, preparation result, archived release, execution compatibility and project activation |
| Execution | Project/realization, immutable run binding, method/configuration, typed task unit, invocation/attempt/holder/lease and fresh/reused origin |
| Source and agent work | Original/rendition/build/segment/span, provider/source frame, source reports and inputs, packet/read obligations, held submission and terminal result |
| Measurement | Metric definition, typed subject scope, exact value/detail and producing method/operation/input context; measured values remain separate from fact truth and source coverage |
| Cut and result | Effective completed origins, nonfinal/final cut, sealing, publication receipts, completed output relationship and immutable replay |
| Knowledge | Entities/memberships, exact recursive values, typed roles, qualifiers/conditions/scope, occurrences/facts and evidence/support |
| Decisions and inference | Selection, typed assessment targets/counterparts, alternatives, rule/version/direct premises and verified input lineage |
| Read and coverage | Snapshot handles, occurrence/fact/accepted projection, outcome-domain translations, knowledge versus page completeness and explanation |
| Analytics | Captured versus candidate input, projection/arithmetic profile, owned scope, borrowed/detached result and append/snapshot-derived publication |

Every relationship declares typed endpoint roles, direction, contextual cardinality, identity,
qualification, ordering/multiplicity, unresolved endpoints and authorization requirements.
All persisted entity/fact/occurrence/group references are release/realization-qualified.
Alternative-group identity uses distinct unordered fact membership; reasons remain provenance.

State is composed. Run status, sealing and completed-output relationship; task status, current
attempt and held progress; source coverage; scientific assessment; and analysis lifetime remain
independent dimensions with explicit valid combinations. source_ready is a response outcome,
held is a submission disposition, and a completed-result seal is a relationship/predicate.
Do not invent dormant retirement/recovery capabilities from unused physical state strings.

### Invariants and execution placement

Local constraints use supported LinkML metamodel expressions and strict boundary validation.
Relational/lifecycle constraints use owned typed predicates and existing Core/native boundaries.
An invariant records its subject, scope, failure code, required semantics and enforcing route.
The same meaning must not be independently reimplemented in Python, SQL and SHACL.

For shared lifecycle checks, derive finite allowed-edge predicates from the trusted transition
definitions. Named specialized guard/effect kernels retain ordinary implementations and resolved
contracts. Python preflight may invoke the shared native/Core guard rather than maintain another
interpreter. Procedural transaction effects remain owned native operations where appropriate.

No generic rule-to-SQL compiler is implied. The compiler admits supported constructs, composes
existing capabilities and refuses required semantics with no faithful realization.

<a id="SP-C01"></a>
## 3. SP-C01 — Connected definitions and owned behavioral contracts

**Input:** delivered semantic foundation and review target; current ADR/DESIGN owners.
**Owner:** logical model and contract integration.

Author and validate the trusted companion types/instances and missing logical concepts using
LinkML SchemaView and existing normalization patterns. Define the relationships, state dimensions,
allowed transitions, operation results and cross-object invariants for every family above.
Keep local module organization discretionary; preserve one semantic owner for each definition.

Link the current owned operations and report families to their definitions. Distinguish binding
identity, implementation identity, physical projection revision and full provenance. Define
closed code-owned outcome sets versus release-authored domain sets; valuesets can supply reusable
vocabularies without granting external vocabularies lifecycle authority.

Resolve four execution choices before dependent compiler work:

- Trusted lifecycle/operation definitions change with application code; scientific policy remains
  immutable release-authored data. Both participate in the compatible operation binding.
- Specialized algorithm contracts resolve to ordinary owned functions; only mechanical finite
  state/predicate lowering is generated.
- Writable versus sealed evaluated output is defined through the completed-result relationship
  and a shared predicate, avoiding a separately mutable seal flag.
- Definition references are typed/scoped and resolved; annotations cannot silently substitute
  for a relationship, invariant or implementation.

Update enduring architectural owners for adopted contract clarifications during execution.
Use the coordinator's decision-impact route if a real change to an accepted rule is required;
do not edit accepted ADRs in place.

**Completion:** normalized definitions can be loaded and referenced by the preparation boundary;
independent examples distinguish qualified repeated/n-ary relations, valid/invalid composed
state and unresolved contract references. Each material transitioned operation has an owner and
contract. This establishes definitions, not their complete runtime adoption; SP-C02–SP-C05 own it.

<a id="SP-C02"></a>
## 4. SP-C02 — Compilation, invariant admission and compatible bindings

**Input:** SP-C01 normalized contracts; existing SP-01 preparation and SP-02 archive/activation.
**Owner:** semantic compiler, boundary and release integration.

There are two readiness milestones, not two new package IDs:

- **Contract products:** working normalization, descriptors, boundary adapters and declared
  implementation requirements are available to SP-C03–SP-C05. This does not claim an admissible
  release or permit unresolved required semantics to activate.
- **Admission closure:** each required implementation/lowering and its actual native/graph
  enforcing boundary is available, then archive/load/activation establishes the compatible
  admitted binding. Relevant SP-C03–SP-C05 implementation slices supply those prerequisites.

Consumers depend on the milestone they use, not completion of all SP-C02. No public partial-release
mode or substitute runtime interpretation is introduced.

Extend the existing prepared binding with normalized relationship/operation/lifecycle descriptors,
strict result adapters, resolved invariant/implementation references and execution/projection
compatibility. Generate or build stable envelopes and dynamic boundaries from those definitions;
do not hand-author parallel Pydantic domain meanings. Resolve settings once at entry points;
resource settings cannot change admitted semantic policy.

Archive the exact new authored inputs and derived products. Include result-affecting execution
model/compiler/policy identities in preparation/reuse dependencies. Preserve current exact
manifest and relational-projection validation on reload; cached pure preparation does not cache
database authorization/state. New product semantics require a deliberate compiler/profile
revision, never reinterpretation under compiler 6 or mutation of historical products.

Activation verifies compatible trusted execution/projection capability and required native
admission before the existing parent/generation CAS. Old bound realizations/runs retain their
definitions. Unsupported archived compiler versions refuse under the established policy; no
historical upcaster or dual-write framework is required.

### Required bounded design investigation

Inspect the installed LinkML/runtime 1.12.1 local-rule semantics and the repository's actual
Pydantic adapter construction before extending the admitted profile. Native JSON Schema and
SHACL generators have unequal rule coverage; successful generation is not evidence of enforcement.

For the constraints needed by the modeled workflows, resolve each to a faithful local validator,
shared Core/native predicate or scoped graph constraint. Reuse native class/slot expressions
where supported. A required unimplemented branch must refuse, not be silently dropped.
Do not broaden admission merely by deleting the current unsupported-construct list.

Persisted-state integrity and transactional authorization retain an enforcing native route.
Graph validation may cross-check the declared state or enforce a graph-specific contract; it
cannot substitute for the publisher's required native check or concurrent transition guard.

**Decision output:** a supported construct/placement description within the prepared-profile
contract, concrete lowering owners and explicit unsupported diagnostics. This is not a new
alignment checker or independent capability ledger. Required behavior cannot be deferred solely
by labeling it unsupported; implement its faithful alternative before claiming completion.

**Completion:** the actual preparation/archive/activation path consumes SP-C01 definitions;
unresolved implementations, incompatible execution revisions and silently weakened required rules
refuse. A supported conditional/relational example reaches its real enforcing boundary. Exact
archive corruption and existing semantic integrity controls retain their purpose.

## 5. Mechanisms, investigations and execution fit

Selected: LinkML SchemaView/typed metamodel definitions, existing Pydantic create_model/TypeAdapter
boundaries, immutable prepared products, Core predicates, exact archives and current admission.
Sources and exact-version limits are retained in
[review §6](../../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#6-library-selections-and-boundaries),
[LinkML](../../libraries/linkml.md), [Pydantic](../../libraries/pydantic.md) and
[valuesets](../../libraries/valuesets.md). Context7 precedes primary/installed source lookup when
implementation needs consequential API details; prior review research need not be repeated
without changed premises.

Compile stable definitions once per binding, cross boundaries in validated batches and preserve
optimizer-visible predicates. Richer logical structure does not require a table, transaction,
job or persisted event for every concept. Known source/skew scenarios include many observations
supporting one fact, high-degree references, repeated attempts and shared prepared releases.
Keep direct provenance compact and validate only the necessary declared closure.

SP-C01/SP-C02 must be usable foundations for the
[realization packages](domain-model-realization.md), not isolated declarative artifacts.
SP-C03/SP-C04/SP-C05 adopt the contract products in current operations and supply the enforcing
implementations required for admission closure; SP-08 later adopts them in the
remaining consumer surface. The coordinator owns their readiness and opportunity disposition.

## 6. Planned verification and publication boundary

Use targeted model/compiler/contract tests when implementing these capabilities: independently
specified endpoint/cardinality/context/identity cases; invalid cross-references and composed
state; strict JSON/Python missingness; required-rule refusal; wrong execution compatibility;
archive corruption; and old binding unaffected by project activation. Consumer checks can share
production validators; tests of a validator/model retain independent expectations.

These are planned checks. This document was authored from source/review/primary-library evidence;
it does not claim new product checks or changed package completion. Existing passing receipts
stand. SP-10 owns assembled-series qualification, expanded through the acceptance plan.

## Execution checkpoint (2026-10-29)

Implemented source: trusted contracts.yaml and execution-model.yaml, normalized immutable
contract products, reference/state/implementation-owner validation and an eight-entry pure cache.
The catalog contains 101 concepts, 43 relationships, 37 operations, 7 lifecycle definitions,
24 invariants and 8 projections, including measurements and distinct outcome translations.
These counts describe this catalog, not an automatic proof of semantic completeness.

Compiler 8 retains semantic-1 and explicit semantic-2 inputs through composed_dependencies.
Execution inputs/products are archived independently of the domain extraction namespace. Native
LinkML conditional fragments compile to a finite presence/absence/choice IR enforced by strict
Pydantic boundaries and protected native publication; unsupported required branches refuse.
jsonschema 4.26.0 and cattrs 26.2.1 are direct product pins, with no transitive versions moved.
cattrs normalizes existing frozen contract dataclasses; it does not replace LinkML/Pydantic
semantic validation. Exact archives, generation CAS and baseline publication remain intact.

SP-C03–SP-C05 now supply the required lifecycle, conditional, domain and projection implementations.
Frozen revisions semantic_0023–0026 extend, rather than alter, earlier migration history.
Admission requires exact trusted execution/model/native/physical compatibility and real restricted
principal privileges. Existing authored-SQL artifacts and fatal diagnostic policy are checked
natively as well as at activation. There is no permission flag for missing enforcement.
Composed source/MCP completion through final cut, accepted query/explanation and private-result
atomicity passed against the final admitted binding. Supported native binary inference admission
includes inverse, symmetric, transitive and subtype lifting; scalar/wrong-scope profiles refuse.

The [realization checkpoint](domain-model-realization.md#7-implemented-mechanisms-2026-10-29)
retains concrete runtime/library choices. Coordinator §10 owns receipts and opportunity closure.
Earlier compiler-7 receipts retain their original boundary; they are not relabeled as compiler-8
results. Operational bootstrap/default selection remains unchanged. SP-08–SP-10 retain later
adoption, regeneration/cutover and assembled qualification.

## Completion audit (2026-10-29)

**Definitions and contract products are implemented; full behavioral/admission closure is
partial at `ad4593f`.** The [series audit](../semantic-model-pivot_2026-10-29.md#13-completion-audit-2026-10-29)
owns the current finding dispositions. Catalog counts describe an inventory, not completion.

The clarified target is complete model governance with **zero disconnected behavior**. An
ordinary implementation can remain handwritten, but its actual applicability, typed inputs and
outcomes, invariants, effects and dependencies must be connected to the authoritative model.
Implementation-name registration or an attested function body alone does not establish that
connection. No exception class or diagnostic-only substitute for a missing connection is adopted.
Model-centered identification and remediation of divergence remain part of reaching that target;
the CLI/code-generation mechanism is later design work, not implemented by this audit.

| Accepted item | Current determination and evidence |
|---|---|
| SP-C01 complete conceptual families and typed companion | Definitions implemented in contracts/execution-model LinkML: interpretation, source/execution, measurement, cut/result, knowledge, decisions, coverage and analytics. New reference concepts are included. Runtime adoption remains independently assessed. |
| Relationship endpoint roles, scope/cardinality, identity, qualification, ordering and unresolved authorization | Definitions and cross-reference validation implemented in `semantic/contracts.py:418–490`; general physical/query/graph realizations preserve these distinctions. Explicit statement binding remains CA-01. |
| Independent composed states, allowed transitions and typed outcome domains | Definitions implemented. All 38 ordinary finite transition tuples match the frozen native projection at this baseline; two reference lifecycle edges use protected reference routines. Operation result mismatches remain CA-04 and maintained correspondence CA-06. |
| Trusted execution versus release-authored scientific/domain policy | Implemented separation and immutable composed identities; domain data cannot install privileged code. This separation does not permit an unconnected predicate in either scope. |
| Every material operation has a resolved, effective contract and implementation | Partial: approved imported callables and catalog cross-references resolve, but CA-01 and CA-04 show actual applicability/result disagreement. All 49 current catalog operations received a source-level coupling account in the audit; the name inventory is not itself assurance. |
| Completed-result relationship defines sealing/writability; no duplicate mutable seal authority | Implemented native completed-output and deferred atomic-result protections, preserving independent run/task/source dimensions. |
| SP-C02 normalized immutable descriptors and strict boundary products | Implemented substantial products; CA-02 applies accepted-only conditional rules to submitted Python objects. CA-04 has actual result types/outcomes that differ from declarations. |
| Exact archive of authored/derived execution products and deliberate compiler identity | Implemented archive2/composed products, compiler 10/execution compiler 2 and exact reload comparisons. Older unsupported compiler products refuse instead of changing meaning. |
| Settings and cache cannot replace policy/authorization | Implemented separation; settings acceptance accounting remains CA-09. Pure caches do not cache current database state or privileges. |
| Required implementation/lowering and native/graph enforcement before activation | Partial under CA-01/CA-02/CA-05/CA-06: real deployment/capability checks exist, but they do not resolve all behavioral correspondence. Preparation alone is not admission closure. |
| Finite LinkML conditional lowering investigation | Delivered supported grammar and explicit refusals. The accepted-value scope discrepancy is a concrete incomplete lowering, not justification for removing that construct. |
| Consumer adoption, old binding preservation and conditional/relational demonstration | Existing composed/native/graph journeys retain their scoped credit. Current full adoption is partial; the fresh statement run fails and additional source-established gaps remain. |
| Proactive model-centered identification/remediation of disconnected behavior | Remaining completion work under CA-06, explicitly clarified during this audit. Existing unresolved-reference, capability, archive and native-drift diagnostics are useful but do not close actual predicate/result parity. No universal interpreter, proof engine or new generic alignment gate is required. |

For the six model/persistence operation routes: `prepare`, `activate`, `admit` and `publish`
consume real model products but remain partial at the identified seams; `archive` and `reload`
are implemented for exact preservation/reconstruction. Other operation accounts are owned by
realization and consumer sections. cattrs is a strict frozen-product adapter; LinkML/Pydantic
remain semantic/ingress owners. attrs/msgspec, linkml-map, alternate graph stores and
LinkML-Datalog remain reasoned candidate/deferred choices, not missing dependencies.

## Improvement integration (2026-10-29)

**Planned amendment; no new implementation or qualification claim.** Contract products must govern actual result constructors, validation placement, enforcing composition and projection attribution. Name/hash correspondence alone does not close admission. Normalize once, archive effective products and derive finite native consumers. New product compatibility and compiler-10 preservation are explicit transition prerequisites.

Additional packages SP-I01/SP-I02/SP-I04 are defined in
[model-execution closure](model-execution-closure.md),
[release/consumer consolidation](release-and-consumer-consolidation.md) and
[qualification infrastructure](qualification-infrastructure.md). The
[coordinator §14](../semantic-model-pivot_2026-10-29.md#14-improvement-integration-2026-10-29)
owns their queue, selection and dependencies. Earlier target/checkpoint prose retains its
historical binding until the scheduled successor decisions and implementation establish the
amendment. CA IDs and scoped passing receipts remain unchanged; the new package definitions
supply corrective work rather than another mutable findings ledger.
