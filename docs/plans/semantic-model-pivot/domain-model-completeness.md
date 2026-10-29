# Complete domain model and executable contracts

**Status:** SP-C01 implemented; SP-C02 contract products and admission refusal implemented, admission closure pending required enforcement · **Created:** 2026-10-29 · **Proposed implementation target.**
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

Compiler 7 retains semantic-1 and adds explicit semantic-2 inputs through composed_dependencies.
Execution inputs/products are archived independently of the domain extraction namespace. The
conditional profile uses native LinkML rule fragments and the same strict Pydantic boundaries;
unsupported branches refuse. jsonschema 4.26.0 is now a direct product pin; no transitive versions
changed. Exact archives, generation CAS and baseline publication remain intact.

SP-C02 activation checks trusted execution identity and required capabilities. New native
migration semantic_0022 blocks semantic-2 realization construction, including the authenticated
source-project initializer. Composed archive persistence also checks that this fence is enabled;
a server without it cannot store a new composed archive and expose it to an old write path.
This is admission refusal, not the future SP-C03 transition enforcement implementation.

SP-C02 admission closure remains blocked by required execution.lifecycle.v1 and, for conditional
rules, conditional_rules_native enforcement. Contract consumers can use compiled definitions;
no permission flag or graph-generation success authorizes an unenforced release. Current runtime
transition adoption, scientific outcomes and analytical projections remain SP-C03–SP-C05.
Operational bootstrap/default selection was not changed. Scoped receipts are in coordinator §10.
