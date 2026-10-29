# Complete domain-model realization in transitioned operations

**Status:** SP-C03/SP-C04/SP-C05 substantially implemented; required current behavioral/graph closure partial (completion audit below) · **Created/Revised:** 2026-10-29.
[Coordinator](../semantic-model-pivot_2026-10-29.md#10-domain-model-completeness-integration)
owns current state, queue and opportunity disposition. This document owns SP-C03–SP-C05 and
consumes [SP-C01/SP-C02 contracts](domain-model-completeness.md).

## 1. Scope and capability dependencies

Realize the [completeness review O01–O07](../../functional_reviews/semantic-domain-model-completeness_2026-10-29.md)
and [target](../../functional_reviews/semantic-domain-model-completeness_2026-10-29_target-model.md)
on the transitioned SP-00–SP-07 implementation. Preserve its existing mechanisms and passing
receipts; the implementation checkpoint below records the added scope. Remaining legacy migration stays SP-08; regeneration
and default cutover stay SP-09; assembled acceptance stays SP-10.

SP-C01 supplies agreed definitions; SP-C02's contract-products milestone supplies working
adapters, descriptors and implementation requirements. SP-C03–SP-C05 provide actual enforcing
implementations before SP-C02 admission closure can activate the corresponding binding.
Independent source/consumer design can begin from settled contracts.
Integrated native/consumer claims require the working product. Package independence does not
permit concurrent edits to shared model declarations, compiler products or migration surfaces.

### Foundation assessment

Current operations and native migrations already implement substantial guards: immutable
bindings, successful completion protection, terminal immutability, effective-origin reuse,
final-cut barriers, source custody, proof grounding and exact replay. Reuse them. The additional
work makes the full allowed behavior and its outcome domains explicit and authoritative.

Existing domain algorithms and one DuckDB scope remain appropriate. The candidate input used by
consolidation and the captured database packet need distinct provenance contracts, not different
engines. Current optional Arrow revision fencing needs explicit append/derived intent types.
Current source/semantic coverage sets need an owned translation rather than forwarded strings.
These are grounded extension seams, not new runtime failure claims.

<a id="SP-C03"></a>
## 2. SP-C03 — Model-governed lifecycle and native publication

**Input:** SP-C02 contract products and current SP-02/SP-03/SP-06/SP-07 native routes.
**Owner:** orchestration/operations and protected database integration.

Make actual project/release/realization construction, scheduling, claiming, agent submission,
cut sealing, cancellation, publication and result replay consume the trusted contracts.
Derive finite allowed-edge/combination checks from those definitions. Use SQLAlchemy Core
guarded DML with expected state/attempt/binding and RETURNING; native triggers/protected routines
enforce the same contract for every supported writer. Local shape checks and relational/current
state authorization remain distinct enforcement responsibilities.

Keep one semantic predicate owner. If a native invariant cannot be faithfully evaluated locally,
preflight calls its shared Core/native guard instead of maintaining an approximate Python copy.
Specialized procedural effects remain owned native functions with resolved contracts.
Do not build a generic workflow engine, arbitrary transition interpreter or second retry owner.

| Operation | Required realized behavior |
|---|---|
| Release/project/realization | Exact archive and compatible activation; parent plus generation CAS; empty project/release-bound realization construction; no rebinding of existing work |
| Run and task creation | Immutable full dependencies; typed unit/configuration applicability; explicit pending/awaiting-agent/reused/skipped construction and reasons |
| Claim/reclaim | Atomic eligible selection, incremented attempt, holder and reclaim deadline; a deadline permits reclaim but does not independently create another owner |
| Agent hold/completion | First uncertain result held durably; clean first or subsequent submission completes as appropriate; current packet/attempt authorizes effects; held is not a task status |
| Source completion | Protected result/report/rendition writes and terminal task outcome agree; protocol completion never implies accepted knowledge |
| Cuts | Nonfinal cut remains an observation selection; final cut captures effective completed origins and seals into consolidation only after live source work is terminal |
| Fail/cancel | Coordinated run/task locking; terminal run and active-task cancellation; diagnostics/held progress retained; stale completion refused |
| Publish/finish | Exact source/proof receipts and result/run completion commit atomically; native evidence and grounding authorization remain mandatory |
| Replay | Matching immutable identity/content returns its exact result before mutable-input checks could reinterpret it; conflicting content refuses |

Model run status with sealing/result relationships and task status with attempt/submission
dimensions. Enforce the target's valid combinations, not just status string membership.
Use the completed EvaluationResult relationship to define output sealing/writability; avoid a
second independently editable seal flag. Do not add unsupported transitions for dormant
physical availability strings.

Deploy changed constraints/routines through a new frozen Alembic revision; do not edit historical
SQL revisions. Preserve restricted application principals, publisher ownership, fixed staging,
safe search paths and caller-owned SERIALIZABLE transactions. psycopg/pgpq operate on that
connection; the existing publication owner retains whole-transaction retry and uncertain-commit
receipt lookup. The single psycopg pool/SQLAlchemy NullPool route remains.

**Completion:** actual migrated CLI/MCP/source-operation callers use typed contracts and outcomes;
illegal nonterminal transitions and malformed attempt ownership refuse at the native boundary.
Independent claim/reclaim, completion versus seal/cancel, held resubmission, direct-write denial,
rollback, exact replay and content-conflict cases preserve their intended semantics.
Later untransitioned callers remain SP-08, not a reason to postpone adoption in current callers.

<a id="SP-C04"></a>
## 3. SP-C04 — Typed outcomes, decisions and qualified domain behavior

**Input:** SP-C02 contract products and existing source/consolidation/inference operations.
SP-C03 native publication is required for integrated publication claims, not pure policy work.
**Owner:** producer/domain-policy/inference and current explanation integration.

Replace independently interpreted outcome strings with the distinct modeled domains: task
protocol, submission disposition, source coverage, semantic coverage, scientific assessment,
transaction result and query knowledge/completeness. Use release-derived strict discriminated
types and resolved method/report contracts. Preserve raw source evidence where appropriate;
promote fields to typed references when decisions depend on them.

Migrate current measurement producers and their transitioned readers with these method/report
contracts. Metric definition, typed subject scope, value/detail and producing operation/binding
remain explicit relationships. Preserve existing mathematical/source measurements; do not invent
new metrics, reinterpret them as scientific truth or expand to unfinished evaluation consumers.

The shared coverage mapping preserves complete/partial/failed and maps source unknown/unsupported
to semantic unanalysed with the originating code, reason and required capability. Complete
coverage is retained only for the same family/scope when transformation obligations are met.
Transport done may include refused semantic content; it cannot manufacture accepted facts.

Give assessments typed subject/counterpart/context references, rule/operation/version and
uncertainty. Move machine-significant references out of reason text while retaining readable
explanation. Keep selection contextual and alternatives compact: group identity is unordered
distinct fact membership within release/realization; several reasons attach to that same group.

Retain owned identity, source placement and numerical/symbolic algorithms. Their model contracts
state applicability, exact frozen math contexts/constants, supported restrictions, precision,
uncertainty and effects. Use the existing typed rule-engine Context/input definitions where
compatible; no transaction lifecycle or scientific truth is delegated to rule-engine.

Qualified inference consumes exact snapshot/rule identity and the declared eligible fact
projection. Preserve positive source-supported asserted/defined seeds and grounded derived
premises, identical compatible qualification, finite conclusion identity and compact direct
proofs. Negative assertions, suppositions and unsupported readings remain represented without
becoming positive premises. Native publication checks actual grounding and authorization.

Migrate the already-transitioned source/agent boundary, consolidation, inference and query/explain
consumers alongside these changes. Explain decision targets, alternatives, source/input lineage,
rules and direct premises within the bound realization. Do not defer required adoption to SP-08.

**Completion:** the real source → final cut → decision/inference → publication → current
explanation path uses the contracts. Independent cases distinguish refused content from failed
transport, unknown/unsupported from absence, equivalent/different/undecided science, conditional
multiple values, repeated occurrences, two causes for one group, incompatible contexts, cyclic
proofs and old input lineage without copied occurrences. No prior result is regraded; grading
and adjudication remain automated.

<a id="SP-C05"></a>
## 4. SP-C05 — Faithful projections, semantic validation and analytical lifetimes

**Input:** SP-C02 contract products; working SP-04/SP-05 kernels and relevant SP-C04
decision outputs. Native derived-publication integration consumes SP-C03.
**Owner:** graph/projection/query and interchange/analytics integration.

### Graph and relation validation

Define each projection's source model/binding, node/relation kinds, universe, context, collection
semantics, precision, allowed omission, completeness and lifetime. Build only the required
validation closure, including referenced nodes; output filtering cannot narrow required inputs.

Use existing RDFLib Graph/Dataset interoperability and native LinkML/PyOxigraph canonicalization.
SHACL Core paths, comparisons and qualified cardinalities plus selected SPARQL constraints can
validate rich relations. Before/after transition records can expose immutable/state comparisons
without a persisted event ledger or whole-corpus copies.

Qualification, occurrence identity, evidence/support and proofs remain explicit nodes/relations.
A qualified rdf:Statement does not entail its bare triple. RDF set cardinality does not count
duplicate reports; ordered/bag collections retain member identity/positions. Default conformance
keeps inference none and external imports/mutation disabled. Graph conformance cannot authorize
a concurrent PostgreSQL transition.

### Analytical and read contracts

Separate CapturedPacket from CandidateInput while sharing AnalysisScope. Capture identifies
one PostgreSQL snapshot and declared projection; a candidate input identifies its cut/source
and decision universe. Copying Arrow metadata does not establish provenance or row scope.
Query adapters and continuation checks consume those same defined projections and bindings.

Separate AppendPublication from SnapshotDerivedPublication. The latter requires exact source
release/realization/revision and operation/projection identity; changed input yields
recompute-required. Both use protected immutable staging and existing exact receipt replay.
Do not make a snapshot-dependent operation's safety rely on remembering an optional revision.

Preserve exact source/canonical numeric representations and the accepted DECIMAL(38,scale),
HALF_EVEN analytical profile with explicit rounding/overflow outcomes. Wider Arrow types or RDF
literal transport do not establish a wider coherent arithmetic contract.

AnalysisScope owns the DuckDB connection, child connections, registrations, readers and scratch.
Its lifecycle combines input kind and open/closed scope. Multiple borrowed and detached results
can coexist; result lifetime is per result, not an exclusive state of the scope. Borrowed handles
refuse after close; materialized results can detach. Idempotent close attempts every owned
teardown, retains individual failures and repropagates cancellation after settlement. Resource
limits, response completeness and declared analysis universe remain separate.

**Completion:** current graph/query/analytical consumers use named contracts; captured and
candidate input cannot be mislabeled, snapshot-derived publication cannot omit its fence, and
qualified duplicates/roles/context/decimal boundaries survive each promised projection.
Independent wrong-scope, stale revision, missing related node, metadata loss, borrowed-reader
closure and cleanup-failure cases exercise the real boundaries.

<a id="library-dispositions"></a>
## 5. Bounded investigations and library dispositions

Current selections and precise source limits are retained in
[review §6](../../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#6-library-selections-and-boundaries).
These investigations are design work inside their owning packages, not installation mandates.

| Mechanism | Package and decision question | Default, exit and dependency |
|---|---|---|
| Shared guard lowering | SP-C03: how do finite definitions and owned Core/native predicates cover all supported writers? | Existing Core/protected functions remain. Settle the predicate owner and failure semantics before deploying a transition; no parallel interpreter. |
| Native conditional-rule coverage | SP-C02/SP-C03: compiled finite presence/absence/choice branches | Implemented from native LinkML JSON Schema fragments, including inherited aliases and whole-rule scopes. Unsupported required grammar refuses; strict local errors retain keyword and instance/schema paths. |
| cattrs / attrs / msgspec | Shared contract representation | Selected cattrs 26.2.1 for strict structure/unstructure of existing frozen dataclasses, with primitive hooks and extra-key refusal. LinkML/Pydantic remain semantic/ingress owners. attrs and msgspec add no required capability here; deferred until a concrete consumer needs them. |
| Direct PySHACL/PyOxigraph Store | SP-C05: do selected graph constraints preserve result semantics, graph context and numeric requirements? | RDFLib remains the supported baseline. Adopt direct Store only after relevant conformance; no assumed speedup or new persistent authority. |
| linkml-map | SP-C05: is there an actual current mapping consumer whose complete shape semantics its supported transformer preserves? | Candidate only. If justified, select an exact version and strict TransformationSpecification/ObjectTransformer route, explicit join/unit/collection behavior and independent target validation. Otherwise retain owned projection functions. SQLCompiler is not assumed to implement the full mapping language. |
| Oxrdflib | Deferred: a required consumer specifically needs RDFLib's Oxigraph-backed store interface and direct native PySHACL input is insufficient | Revisit with that consumer. Qualify fallback/transaction behavior then; no completeness dependency now. |
| linkml-datalog | Deferred: required inference exceeds the selected qualified finite SQL profile | Revisit only with a faithful numeric, qualification, occurrence, grounding and proof contract. No automatic dereification or adoption of the package's narrower semantics. |

Selected mechanisms include Core update/where/returning and locks; psycopg COPY on the caller's
transaction; pglast AST/dependency analysis followed by restricted PostgreSQL binding; immutable
Alembic revisions; strict Pydantic boundaries; release-scoped rule-engine Context; PyArrow schemas,
safe conversions and RecordBatchReader; DuckDB registered relations and owned readers; pgpq
write_header/write_batch/finish into protected staging. Linked
[PostgreSQL](postgresql-and-publication.md), [analytics](interchange-and-analytics.md) and
[model](domain-model-completeness.md) owners retain their detailed composition.

Assess workload fit qualitatively: shared preparation, narrow relational predicates, many supports
per fact, high-degree references, finite closure, bulk crossings and bounded scope cleanup.
Keep provenance compact; avoid repeated full graph reconstruction, gratuitous materialization,
per-item database calls or another state service. No new instrumentation, cost model, alignment
lint, benchmark campaign or proof ledger is scheduled.

## 6. Integration and acceptance

SP-C03–SP-C05 must connect their actual producer/operation/read consumers as they land. SP-08
adopts these products for the remaining surface; it does not own fixing unadopted transitioned
callers. SP-09 regenerates with the composed model; SP-10 qualifies the required combined union.
The coordinator owns the qualified review-opportunity crosswalk and current package state.

During product execution, run meaningful targeted checks for changed behavior at coherent
capability boundaries. Existing passing type/test receipts remain valid; lint-only changes do
not trigger repeated type checking or tests. Final series qualification and native scenario
ownership are in [regeneration and acceptance](regeneration-and-acceptance.md).

## 7. Implemented mechanisms (2026-10-29)

**Implemented; scoped Tested.** Compiler 8 / execution compiler 2 archive the finite conditional
IR, native guard bindings and named projection products. The exact supported execution binding
is `execution:ba807ea0f3d649f0e59a29033a03209d3e19ab2c5769882cd97b73a82103fc78`.
No arbitrary native symbols or authored executable imports are admitted. Static outcome domains
are checked against the trusted catalog. cattrs is a direct exact pin; the lock adds no new
transitive versions. Its canonical unstructuring preserves the existing wire representation.

- **SP-C03:** frozen revisions `semantic_0023`–`0026` deploy finite lifecycle and conditional
  guards, protected renew/release and terminal effects, method unit/configuration contracts,
  completed-result relationships and compatible native admission. CLI/MCP/orchestration use
  frozen strict result DTOs. Held evidence survives cancellation/reclaim. A deferred native
  constraint prevents committing private evaluated output without its completed result.
- **SP-C04:** release-compiled coverage lowering preserves source code/reason/capability;
  assessment subject/counterpart/context and comparison tier are typed. Explicit packaged metric
  definitions bind producing methods and source schemas. Protected result insertion materializes
  measurements in one set-based native operation; source position preserves duplicate bag members.
  Direct late insertion/mutation refuses. Readers expose exact source values and producing binding.
  Consolidation and inference use candidate inputs and explicit derived-publication intent.
- **SP-C05:** captured/candidate projections carry distinct provenance. Derived publication
  requires the exact source binding/revision plus operation/projection and retains replay before
  stale-source checks. Qualified graph closure includes referenced nodes, reified nested values,
  collection positions and nulls; selected shapes augment the core contract. RDFLib remains the
  supported PySHACL input, inference/imports/mutation disabled. No current mapping consumer
  justified linkml-map or a direct-store backend change. Borrowed DuckDB/Arrow handles enforce
  scope lifetime; detached values survive. Cleanup attempts every owned resource, including
  child cursors, and preserves cancellation after settlement.

`semantic_0026` replaces the blanket `0022` refusal only for a faithfully enforced binding.
Admission checks exact function/trigger definitions, owners/configuration, positive restricted
EXECUTE/SELECT privileges and denied privileged writes, the current physical model and existing
SQL-admission artifacts. Archived SQL admission runs inside activation's existing savepoint before
native admission/CAS. Fatal archived diagnostic policy matches Python. These checks are set-based;
no additional registry, event service, alignment gate or proof ledger was introduced.

Semantic-1 remains supported. Existing methods without unit/schema metadata remain explicitly
unresolved and cannot run under semantic-2; no metadata was fabricated or backfilled. The finite
conditional and qualified binary-inference profiles remain deliberate support boundaries, not
claims of arbitrary LinkML or ontology execution. Source algorithms and mathematical policies
retain their existing meaning. Grading/adjudication remain automated; no prior result was regraded.

The coordinator §10 owns exact passing, failed and superseding receipts. Native checks used owned
fresh databases. The operational database remains at `semantic_0005`; no default deployment,
cutover or enclosing SP-10 qualification occurred.

## Completion audit (2026-10-29)

**Substantial realization; current SP-C03/SP-C04/SP-C05 closure is partial at `ad4593f`.**
Existing scoped passing receipts stand. The [series audit](../semantic-model-pivot_2026-10-29.md#13-completion-audit-2026-10-29)
owns CA-01–CA-06 and the combined current conclusion. This corrects unconditional earlier
current-consumer closure; dated implementation receipts are not new qualification.

| Accepted item | Current determination and evidence |
|---|---|
| SP-C03 compatible archive/activation, empty construction and immutable bindings | Mechanisms implemented; explicit statement operation meaning at admission remains CA-01. Existing project/release/input relationships are not rebound. |
| Typed method/unit/configuration and initial task/reuse/skipped construction | Implemented native method contract and guarded scheduling with reasons; actual configured dependencies govern reuse. |
| Claim/reclaim/lease/holder/attempt and held progress | Implemented atomic selection, ownership, renewal/release and durable held diagnostics. Actual hold helper/result contract mismatch remains CA-04. |
| Source completion, terminal effects and measurements | Protected effects implemented; valid dynamic statement publication remains CA-01 and source synthesis remains within that finding. |
| Nonfinal/final cuts, effective origins and sealing barrier | Implemented native cut selection and terminal-source barrier. Source readiness is not completed scientific output; its contract must say so (CA-04). |
| Coordinated fail/cancel and stale/late completion denial | Implemented locking, terminal immutability and retained held/diagnostic state. |
| Publish/finish/result relationship and exact replay | Atomic source/proof/result transaction and replay-before-mutable-input checks implemented; valid statement journey remains partial. |
| Finite allowed edges/shared owner and frozen native projection | All 38 modeled ordinary edges match current frozen tuples. Retained model-to-projection comparison/regeneration remains CA-06; body attestation is not that comparison. No actual edge drift is alleged. |
| One protected SERIALIZABLE/retry/receipt owner and restricted writers | Implemented; no parallel workflow/state service or validation-flag bypass was found in current routes. |
| SP-C04 distinct protocol/submission/source/semantic/scientific/query outcomes | Distinctions and source→semantic conversion implemented, including unknown/unsupported→unanalysed with reason/capability. Three operation/result alternative mismatches remain CA-04. |
| Refused content versus failed transport and missing knowledge | Implemented source report/coverage semantics. Named serving can still assert false absence under CA-03, so the complete consumer contract is not closed. |
| Existing measurement relationships and duplicate bag members | Implemented typed metric/source/operation bindings and protected set-based materialization; source positions preserve multiplicity. No new metrics or truth inference were added. |
| Typed assessments, counterparts/context/tier and compact alternatives | Implemented fields/FKs/guards and unordered-distinct group identity; reasons stay provenance. Scientific operation alternatives remain CA-04. |
| Source placement, identity, exact numerical/symbolic policy and qualified inference | General algorithms are connected to bound inputs/rules/context; literal statement range/member assumptions remain CA-01. Finite grounded proofs retain their independent controls. |
| Existing source/agent/consolidation/inference/explanation adoption | Partial, not work that can all be reassigned to SP-08. CA-01/CA-02/CA-04 affect the already-transitioned path. |
| SP-C05 named graph contract, closure, qualified duplicates and positional collections | Closure/reification mechanisms implemented; the public graph projection accepts a nonempty caller-supplied ID without resolving the declared graph contract (CA-05). |
| SHACL settings and PostgreSQL authority | Implemented RDFLib baseline, inference/imports/mutation disabled and scoped supplied/core shapes. Graph conformance does not authorize native transitions. |
| Captured/candidate provenance and explicit analysis universe | Implemented distinct DTOs and actual snapshot/cut use; neither copied metadata nor output focus fabricates provenance. |
| Append/snapshot-derived publication and replay/stale revision | Implemented disjoint intents, mandatory source/operation/projection fence and recompute-required, preserving exact completed replay. |
| Exact analytical arithmetic, borrowed/detached values and all-resource cleanup | Implemented selected DECIMAL(38,scale)/HALF_EVEN boundary, exact lexical preservation, lifetime guards, child-resource cleanup and cancellation settlement. |
| Optional graph/mapping/representation investigations | Delivered dispositions: RDFLib/owned projections retained, cattrs selected; no current consumer required other candidate backends/libraries. No missing installation is inferred. |

### Actual operation coupling

The catalog's ordinary operation implementations remain concrete functions, not a generic
interpreter. Their behavior was traced beyond `owner:symbol` declarations:

- Construction/method/scheduling/claim/renew/release/end-run consume immutable bindings and native
  lifecycle predicates; register/read-original/store/read-rendition consume typed source custody.
- Completion/bind-report consume actual result/report/measurement contracts and protected effects.
  `hold_submission` is partial under CA-04: the bound helper returns `proceed`, while its catalog
  alternatives describe a different submission stage.
- `make_packet` and `check_submission` consume archived boundary models, exact frame/read obligations
  and attempt ownership. `assemble`/`resolve_identity` consume release properties, scoped references,
  keys and eligible evidence-backed exclusions; CA-01 remains at source statement applicability.
- `execute_source` is partial under CA-04: the bound implementation returns a readiness report while
  the catalog names completed task results. `evaluate` consumes the cut/binding and publishes
  atomically but remains partial under CA-01/CA-02. `scientific_policy` consumes released rules and
  exact context, but emits assessment alternatives not declared by its operation (CA-04).
- `derive` and `publish_inference` consume declared eligible rules/context and native source-grounded
  direct proofs. Iterative Core fixed-point insertion is a justified replacement for a recursive
  CTE: finite semantic identity and compact proofs retain the promised closure/termination.
- Graph/read/analytical/reference operation accounts are in the consumer and analytics owners.
  Hashing a projection description or resolving a function name does not by itself settle parity.

No disconnected-behavior exception is accepted. Current safeguards and independent tests remain
useful; CA-06 carries the model-centered detection/remediation work without prescribing the later
CLI/code-generation mechanism or adding a universal behavior interpreter.

## Improvement integration (2026-10-29)

**Planned amendment; no new implementation or qualification claim.** Migrate actual source/session/native enforcing boundaries with the corrected contracts. Preserve readiness, protocol, hold, scientific and transaction dimensions. Resolve graph contracts before closure/SHACL. Keep qualified source/proof authorization, immutable replay and borrowed/detached lifetimes while consolidating surviving algorithms and native bindings.

Additional packages SP-I01/SP-I02/SP-I03/SP-I06/SP-I07 are defined in
[model-execution closure](model-execution-closure.md),
[release/consumer consolidation](release-and-consumer-consolidation.md) and
[qualification infrastructure](qualification-infrastructure.md). The
[coordinator §14](../semantic-model-pivot_2026-10-29.md#14-improvement-integration-2026-10-29)
owns their queue, selection and dependencies. Earlier target/checkpoint prose retains its
historical binding until the scheduled successor decisions and implementation establish the
amendment. CA IDs and scoped passing receipts remain unchanged; the new package definitions
supply corrective work rather than another mutable findings ledger.
