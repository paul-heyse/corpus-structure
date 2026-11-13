# Declared data operations — corrected target contracts and storage

**Proposed · recommendation-audit synthesis2026-11-12**, original8f35f1d07,
product source8c0f4f951. The [principal](../design_review_declared-data-operations_2026-11-12.md)
owns the complete target, F01–F14, C1–C7, RC01–RC09 and overall judgment.
This page specifies the resulting contracts; the [audit companion](../audits/design_review_declared-data-operations_2026-11-12_audit.md)
owns changes to the original. No implementation or schema change is made by this document.

## Governing declaration and compilation

Extend the composed operation model with typed profiles, not an independently authoritative
sibling declaration. Existing OperationContract/call bindings already have inputs/results,
cardinality, effects, transitions and outcomes (semantic/contracts.py:670–716). The total model
covers data derivation, discovery, selection, authored input, external work, publication,
consolidation and governed read/evaluation behavior. Different profiles need not all be memoized
or scheduled as data producers.

| Owned part | Required meaning |
|---|---|
| Definition revision | Stable operation identity; complete subject/input/output/state/effect/validity contract |
| Subject binding | Immutable original source/context/actual analyzed scope; distinct from which subjects a demand requests |
| Input role | Semantic kind contract, subject relation/selector, order/multiplicity/cardinality, alternatives/optional behavior, acceptable outcomes/coverage and support requirements |
| Output role | Typed product/result bundle, member roles/cardinality, discovery population and no-product outcomes |
| Applicability | Typed relational predicates; closed population required for negation/all-members claims; unknown remains unknown |
| Recipe | Behavior revision, semantic parameters/assets, provider/numerical policy, interpretation/coverage contracts and all result-affecting binding semantics |
| Effects/lifecycle | Authorized capabilities, fulfillment/idempotency, preparation/submission/publication/recovery/retirement outcomes |
| Implementation | Admitted algorithm/provider, supported capabilities and limits, typed invocation/result forms |

Compile complete definition revision, result-recipe fingerprint, eligibility/binding revision
and execution binding from this one authority. Eligibility-only widening preserves the recipe
only where result meaning, scope, input/support, required effects and validity are unchanged.
Operation ordinals name immutable fingerprints; they are not another manual version source.

Generate operation-shaped typed ports and fixed relational projections. A selector adapter may
execute the declared query; it cannot define its own applicability or input digest. Inputs arrive
as admitted bindings, not an ambient Reader permitting undeclared semantic reads. Preserve useful
batch/stream/preparation/cancellation capabilities without a process or task per semantic concept.
Specialized predicates/algorithms remain explicit domain operations, not arbitrary effect programs.

## Identity and canonicalization

| Identity | Contract |
|---|---|
| Semantic kind | Effective normalized contract plus declared semantic dependency closure, including inheritance/invariants/relations/coverage/numerics |
| Semantic product | Kind-contract fingerprint + immutable subject/context identity + canonical semantic body digest |
| Stored artifact | Exact byte encoding/archive digest, mapped to semantic identity; byte equality alone proves no source truth |
| Logical computation request | Recipe + subject + exact role-labeled value/support/population inputs + requested replicate |
| Derivation execution | Authentic production episode under that request; independently attributed runtime/task/attempt/outcome/output support |
| Demand/use | Frozen requested obligation and exact selected fulfillment/support/fate |
| Runtime | Executable artifact identity separately linked to release-bound execution attestation |

Domain-tagged, versioned encodings resolve defaults and typed numeric/precision semantics;
retain role, ordering and multiplicity and distinguish absent from present-empty. Normalize only
explicit sets. Do not derive identity from reader fields, arbitrary row order or the entire release.
Do not embed producing version/task/runtime recursively in semantic layer bodies. Meaningful
source coordinates, native schemes, coverage and choices remain. Local IDs qualify through the
product and avoid hash self-reference. Distinct evidence episodes never merge into extra votes.

A provider profile has compiled semantic inference-recipe and complete execution/admission
projections. Current NativeProfile includes runtime/thread fields: hashing it whole contradicts
thread-independent reuse. Preserve requested/observed profile and actual numerical/batch evidence;
CUDA/dtype guarantees are not weakened by the identity split. See principal RC08.

## Retained records and responsibilities

| Record/projection | Consumer |
|---|---|
| Operation definitions/recipes/kind contracts | Compiler, typed ports, admission, explanations and release comparison |
| Discovery/population product | Subject expansion, exact membership, empty/partial/negative dependency meaning |
| Logical request reservation + fenced attempts | One live producer, concurrent-demand coalescing, safe takeover and replicate separation |
| Semantic products/member projections | Analytics and retained reads, independent of producing execution identity |
| Derivation and role-qualified input/output/support | Reuse, attribution, dependency analysis and independently retained observations |
| DemandUse / demand-result selection | Each requested target's fate, selected exact support, reuse reporting, resume and downstream cuts |
| Revocation with reason/scope | Current admissibility without destroying shared content or rewriting historical evidence |
| Cut selection / consumed bindings | Per-run consolidation and currentness relative to an explicit target |
| Completion intent/receipt and frozen build custody | Exact uncertain-commit replay and authorized adoption without repeated inference |

Supersession/currentness are relative queries, not a mutable latest product pointer. Serving
pins the demand-result/cut selection, contracts, source and support closure across calls,
resources, continuation, export and detached replay. Reference-source release, prediction selection
and grading recipe remain separate; protected labels cannot become ordinary planner inputs.

## Execution, admission and change

Resolve typed inputs from declarations; register tasks after immutable bindings exist. Indexed
set operations and demand-scoped frontiers avoid all-operations × all-history scans. Preserve
closed aggregate populations, source coverage, explicit producer selection and bounded fan-out.
Physical grouping/fusion/preparation is independent of semantic granularity.

One fenced publication commits product/projection/derivation/receipt/fulfillment coherently.
Known rollback and uncertain commit differ; uncertain replay uses the exact completion intent.
Uncertain physical submission retains custody until drain, reports executor failure and cannot
become permanent temporary backpressure. Revocation and final admission have serialized ordering.
Actual closure is modeled; absent registered edges do not establish independence.

Cross-release admission checks kind compatibility plus original scope/source custody, acceptable
coverage/outcome, selected support/alternatives, permissions and trust. Compatible content never
launders a revoked observation. Rebinding equivalent trusted support is explicit and allowed only
where the consumer's contract permits it. Changed support can invalidate an unchanged payload.

Change reporting combines old/new typed declarations, demand/discovery universe and actual
reverse lineage. Newly applicable/unseen subjects and changed optional/absent memberships matter.
Potential impact differs from proven staleness; propagation stops at substitutable value/support.
Reads explain update need without scheduling execution or repeating upstream interpretation.

## Replacement and preservation

C2/C3 establish the contracts/records before C1 removes conservative reuse conditions.
C4 replaces name-based scheduling and adapter-owned selection. C5–C7 consume the same admission
and change semantics. Replace all callers of old task-keyed refs and run membership, including
zero-output reports, evaluation, serving, exports and original-source authentication.

Regenerate disposable derived products through a preservation-aware forward cutover. Preserve
original source custody, protected reference definitions/labels, required completed snapshots,
receipts/evidence and their reference closure. Immutable migration files alone do not preserve
instances. Named correspondence exists only for actual retained consumers; it cannot relabel
an incompatible historical contract. No blanket database reset or deletion is implied.

PDF open/frozen builds retain source/recipe/schema/profile premises, sealed union and replay
receipts. Adoption authenticates equivalence and transfers custody under a newly fenced attempt;
changing the build key alone does not authorize adoption. Consolidation remains per run but is
fully modeled, as are external-agent packets and effectful actions. The principal §7 supplies
independent acceptance countercases; layout/index mechanics follow these contracts in planning.
