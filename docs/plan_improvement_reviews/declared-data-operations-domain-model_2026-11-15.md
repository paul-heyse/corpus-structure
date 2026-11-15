# Declared data operations — the domain model against its own target

**Audited plan-improvement review · 2026-11-15 · proposals only.** Reviews the
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md) and its eleven
[companions](../plans/declared-data-operations/) against the outcome the coordinator states for
itself:

> a total explicit domain model governing supported products, subjects, operations, input/output
> bindings, applicability, lifecycle/effects/outcomes, demand fulfillment, provenance, reuse and
> change.

**Revision attribution.** The coordinating auditor independently revised the review at
`51cd9774d` on 2026-11-15, incorporating a fresh read-only reviewer’s contributions and the
operator’s subsequent migration/retirement direction. The original is recoverable from that commit.
The [audit companion](../design_review/reviews/audits/declared-data-operations-domain-model_2026-11-15_audit.md)
owns recommendation dispositions and changes in judgment; this document presents the integrated
recommendations. The original reviewer is not represented as endorsing the revision.

The six earlier improvement reviews of this series each started from a library. This one starts
from that sentence and asks, for each of its ten dimensions, how **total**, **explicit** and
**singly owned** the model is in the code now, and what the remaining packages would leave
unchanged. The operator confirmed that executed scope (DDO-00–08) is open to revision.

Nothing here amends the plans, STATUS execution claims, ADRs or code. No tests, provider runs,
data conversion, standing changes or destructive operations are authorized. Recommendation IDs
`I01`–`I09` are local to this review; earlier source finding IDs and their plan owners remain intact.

## Baseline, method and limits

| | |
|---|---|
| Original review | Exact input `51cd9774d`; originally inspected product `fcc1d6cbe`/`1d551f0ca`. |
| Audit source and plan baseline | `51cd9774d`, including completed NetworkX integration through `6b017902f` and reader-lifetime/cache corrections. The earlier description of that work as unaccepted/concurrent is superseded. |
| Concurrent work | Untracked nx-cugraph-cu13 overview is unrelated and unmodified. No product edits during this audit. |
| Standard | Core3.3, efficient-architecture heuristics1.0, code-intelligence1.4, test-assessment1.2 and repository binding. Judgment within this footprint, not a broad diagnostic or completion audit. |
| Method | Independent source inspection of model/compiler/identity, source discovery, opaque dependencies, lifecycle/change classification and public readers; fresh read-only reviewer investigates legacy operations, shared ports, rich contracts and tests. Decisive evidence is reconciled by the coordinator. |
| Limits | No tests, providers, database queries or probes. No exhaustive data-migration feasibility claim. Historical counts are orientation, not current completion quotas. Negative search results do not prove absence of dynamic consumers. |

Current-source observations are **Interface-checked by source inspection · 2026-11-15**.
Recommendations and benefits are **Proposed**, qualitative and unmeasured. Earlier test receipts
keep their original dates and scope and establish no implementation of these recommendations.

## Operator direction and adoption premise

The operator explicitly requires freedom from legacy code, while preferring useful data migration
when it can produce faithful target-native records. Historical readability/editability, old identifiers
and previously implemented compatibility are not target constraints. This applies to old execution
protocols and also to the recently implemented v2–v5 readers. It does not require deleting old data.

Migration may preserve meaning that the available evidence actually establishes. Where changed
inputs, outputs, context or question basis invalidate a recorded model response, regenerate or
reassess it; do not turn transport success into semantic equivalence. Migration work must not require
permanent old readers, old writers or an ongoing dual-model service, or hold the target architecture
hostage. I09 specifies the amendment and decision routes. Current provenance, trust, concurrency and
independent evaluation guarantees still apply to newly produced results.

## Combined judgment

The relational core of the model is real and governs behavior. Roles, cardinality, collection,
presence, support requirements and the sixteen-operator binding expression are typed
(`semantic/data_operation_model.py:87-197`), compiled once, lowered to SQL and re-validated
natively. Definition, recipe, eligibility, kind and implementation-slice identities are separate
and derived. Demand, obligation, request, derivation, support, revocation and population are
native relations with one coalescing point (`ops.attach_data_request`). On **bindings, demand
fulfillment, provenance and reuse** the target is substantially met for the operations that are
in the model, and the remaining packages are aimed correctly.

The model falls short of its own sentence in three ways that the remaining packages, implemented
exactly as written, would not correct:

1. **Several named dimensions are labels, not model.** Subject, applicability, invariants,
   coverage and precision are free strings on the operation record. They enter identity hashes
   and archives, and nothing evaluates them. One of them is compared by spelling in generic code
   ([I01](#I01)).
2. **There are two operation models and no stated end for the second.** About ninety operations
   are in the DDO model; ninety-eight are in the older execution model, with its own contracts,
   effect table, lifecycle tables and generated call layer. The two cannot be combined in one
   release. The plan accepts composing them (F01) and schedules retirement by mechanism, but no
   package says what becomes of each remaining operation ([I02](#I02)).
3. **Lifecycle vocabularies are declared once and then respelled.** The generated fate types have
   no production importer, and the change classifier reads fate as a bare string ([I03](#I03)).

Smaller, well-bounded improvements follow from the same reading: shared prepared-kernel execution where
capabilities genuinely match ([I04](#I04)), single owners for the read-surface literals
([I06](#I06)), and model-level test assertions made once ([I08](#I08)). Two recommendations
concern delivery: the rich family should complete the corrected
model ([I05](#I05)), and the coordinator has stopped being usable as a statement of current state
([I07](#I07)).

The set keeps the DDO functional target and package structure. I09 materially replaces the
preservation-led adoption premise; it is not merely a cleanup or an assertion that existing data can
be converted without loss.

### The ten dimensions

| Dimension | Judgment | Where |
|---|---|---|
| Products | **Mostly met.** Kinds are LinkML or Python classes with derived contracts and member kinds. The packet and context shapes are hand-coded beside the schema (`semantic/data_operation_ports.py:206-267`); `analyzed_scope` and `coverage` on a bound member are untyped canonical bytes. | [Separate](#separate) |
| Subjects | **Not met.** A subject is a string with nine observed spellings; one is compared literally in generic discovery code. | [I01](#I01) |
| Operations | **Split.** One effective model for about ninety operations; a second model for ninety-eight. | [I02](#I02) |
| Input/output bindings | **Met.** Typed, closed, compiled once, lowered once, re-validated natively by an independent interpreter on purpose. | — |
| Applicability | **Not met as named.** Real eligibility lives in binding predicates tagged `impact: eligibility`. The field called `applicability` is a label that only enters a hash. | [I01](#I01) |
| Lifecycle, effects, outcomes | **Partly met.** Declared per operation and checked natively, but fates and task states are respelled by hand and the generated types are unused. | [I03](#I03) |
| Demand fulfillment | **Met** for modeled operations. `ops.task` as the physical attempt is an accepted choice and is sound. | — |
| Provenance | **Met.** Native relations, a typed support-reference union, and one protected export that the readers share. | — |
| Reuse | **Met** for modeled operations; legacy twin reuse is correctly scheduled for retirement. One open question about third-party numerical determinants. | [I01](#I01) |
| Change | **Partly met.** Seven impact states computed by a hand-ordered classifier over a string fate; the rich path and an older release diff sit outside it. | [I03](#I03), [I05](#I05) |

## Recommendations

<a id="I01"></a>
### I01 — Declare subject types, and make applicability and invariants resolve to something enforced

*Alignment opportunity with one observed defect. Reopens DDO-01/02; consumed by DDO-05 and
DDO-09. Carries a proposed rule impact on ADR-0092.*

**Current.** `EffectiveOperation` (`semantic/data_operation_model.py:338-367`) has eleven
free-text fields, and compilation checks only that they are non-empty
(`semantic/data_operation_compilation.py:1654-1680`). In the 72 authored declarations they read,
for example, `"applicability": ["retained-source-intervals-and-parent-layout"]`,
`"coverage": "exact-selected-source-and-context"` and
`"precision": "original-native-half-open-extents"`. A search of the source tree finds no code
that reads an operation's `applicability`, `invariants`, `coverage` or `precision` to decide
anything. Where the conditions they name are enforced, they are enforced by the binding
expression, by native admission or by the algorithm. They are nevertheless identity: `recipe`
hashes `subject`, `context`, `invariants`, `coverage`, `precision` and `behavior`; `eligibility`
hashes `applicability` (`data_operation_model.py:369-423`).

Two of these fields need separate treatment.

- **`behavior` is a real determinant for some operations.** Where an operation has no
  implementation slice, `behavior` *is* its implementation revision
  (`semantic/data_operation_storage.py:853-861`), and native admission re-checks it
  (`semantic/sql/data_operations.sql:1725`). For the generated native `data.*` operations it is a
  derived digest of the function body (`data_operation_storage.py:389`). The contracts companion
  requires this ("The result recipe names behavior revision"). For an implementation-owned Python
  operation, however, the slice already carries the revision, and the same companion says such a
  change reaches the recipe "without a manual version bump". There the hashed prose sentence is a
  second, hand-kept token: rewording it invalidates reuse, and a real change does not need it.
- **`precision` may be the only trace of a numerical contract.** Values such as
  `captured-cpu-normalized-float32-encoder` or a named NumPy/SciPy numerical behavior describe
  third-party computation. The closed-source frontend records no library version or distribution
  identity (none appears in `semantic/python_operation_sources.py`). If nothing else in the
  recipe carries it, the label is the determinant, and it changes only when an author edits it.

Subject has the same shape with a sharper consequence. `subject` is a string with nine spellings
(`original-source-view` 32, `original-document` 13, `selected-native-source` 7,
`actual-focus-source` 4, five singletons including the literal `"entity or statement"`). The
concrete occurrence, `SubjectContext`, is properly typed. The subject *type* it is an occurrence
of is declared nowhere, and nothing relates a subject type to the kinds that can stand for it.

**Observed defect.** Generic discovery code decides fan-in by comparing the spelling:
`operation.subject != "original-source-view"` at
`semantic/data_operation_source_discovery.py:42` and `:57`. A declaration that names the same
subject differently, or a new subject type with the same fan-in meaning, silently gets different
discovery relations.

**Proposed.**

1. **Declare subject identity and scope relations** consumed by discovery and binding. Operations
   reference checked subject definitions; unknown references fail compilation. Derive fan-in from
   declared role/subject/population relations where sufficient; add only the missing domain fact.
   Per-source/per-document flags alone are not a general subject model for rich entities/statements.
   Preserve the distinct typed `SubjectContext` occurrence and original-source association.
2. **Applicability and invariant entries resolve or become explicit documentation.** References
   name an existing binding predicate, schema constraint, native admission policy or operation-owned
   invariant with a captured enforcement owner. Unresolved executable claims fail compilation.
   Do not create a second invariant registry, force scientific/kernel invariants into relational
   predicates, or call prose enforced. Identity must include the actual enforcement semantics and
   relevant parameters, not just the binding reference string.
3. **Prose leaves the recipe only for slice-owned operations.** Keep `behavior` as the revision
   wherever it is one today (no implementation slice, external executors, generated native
   operations). For operations with an admitted slice, move the descriptive sentence out of
   `recipe` and `definition`.
4. **Coverage and precision stay in the recipe until each has a typed home.** Give numerical
   policy a typed declaration (the contracts companion already assigns device class, dtype,
   backend and numerical policy to the semantic inference recipe), then retire the label per
   operation. Do not remove a label that is the only carrier of a fact.
5. **Settle the third-party determinant question** as part of this work: whether a change in
   a numerical library that an operation depends on reaches its recipe by any route other than
   an edited label. If it does not, that is a gap under the current design as much as under this
   proposal, and it is larger than the label question.

**Why here.** DDO-01/02 own this representation, and DDO-09 is about to define the rich family's
subject (today literally `"entity or statement"`), "accepted-knowledge standing" and "policy
universe" against it. Defined as more labels, those are the distinctions F08, F09 and F11 exist
to make checkable.

**Rule impact (proposal).** ADR-0092 builds identities from "complete effective semantic
records" with colocated facts supplying "numerical meaning". Changing which fields enter the
recipe is a change to that decision. It needs operator confirmation and a successor or amending
record through the ADR route, with a new current model encoding where required. I09 removes any obligation to retain old
encoding readers. Typed subject/enforcement changes also require checking ADR-0092’s identity
and authority implications; they are not pre-exempted from the decision route.

**Principles.** §1 semantic-model-first; DP-02 (roles and scopes are types or checked
references); DP-03 ("schema metadata is not enforcement"); DP-04 and DP-09 (identity and reuse
from declared result-affecting inputs); DP-11 (precision is a contract); §G "The schema enforces
it" and "Everything is generic".

**Preserved.** Roles, bindings, support, effects, transitions and the five identity domains.
Conservative invalidation: no field leaves the recipe unless the fact it names is carried by a
role, a binding predicate, a parameter, an asset or the implementation slice.

**Alternative: keep every label as a conservative determinant.** Safe in one direction, since an
edited label forces recomputation. It invalidates on wording, stays silent on real change, and
leaves subject and applicability unrepresented. Items 1 and 2 are worth doing even if the
operator keeps the recipe composition exactly as it is.

**Closure evidence.** `source_discovery` contains no subject spelling; an independent case shows
two subject types with the same fan-in class discover identically; compilation rejects an
applicability or invariant entry that resolves to nothing; for a slice-owned operation an edit
to descriptive prose leaves recipe and eligibility unchanged; a typed numerical-policy change
reaches the recipe.

**Uncertainty.** Exact coverage/precision and numerical-boundary adequacy remain a per-operation
preparation task. Current evidence supports the correction, not a complete inventory of missing
numerical determinants. No label is removed before its meaningful replacement is accounted for.

<a id="I02"></a>
### I02 — State the end of the second operation model, operation by operation

*Missing concretization of an accepted obligation (F01). DDO-08–11.*

**Current.** `model/semantic/execution-model.yaml` (14,654 lines) declares 98 operations and 99
implementations, with its own concepts, lifecycles, transitions, outcome domains, effect
definitions and native guards. It compiles through `semantic/contracts.py` (`OperationContract`,
`:689`) into the generated `semantic/_operation_calls.py` (10,762 lines). Beside it sit a
hand-written import registry (`approved_implementations`, `contracts.py:320`) and a hand-written
effect table keyed by operation (`semantic/effect_support.py`). The DDO compiler refuses to
combine the two (`semantic/composed.py:128-131`). The word `applicability` means invariant
identifiers in one model and labels in the other.

The plan covers part of this. The contracts companion states the target: "Existing
database/protocol contracts and data-operation profiles reference that definition rather than
authoring parallel applicability or effect policies." ADR-0092 keeps the older protocols until
their callers move. The coordinator names the remaining consumers of `approved_implementations`
and `source_dependencies` and says when they go. The DDO-00 consumer reconciliation gives the
101 then-declared operations a disposition as a population. The retirement tables are organized
by mechanism.

What is missing is the end state for each operation that is still there. By name, 27 of the 98
concern PDF staging, build and publication, and 15 are `reference_*`; of the latter only the
reference snapshot has a DDO counterpart today. The rest are run, task, method, cut and
supervision protocol. Commit `69df0eb72` shows the working pattern: moving region rendering to a
DDO declaration removed its entries from `execution-model.yaml`, `effect_support.py` and
`_operation_calls.py` together.

**Proposed.** Add to the coordinator one disposition per remaining execution-model operation,
with its owning package, in three classes:

- **Retire with its mechanism** — obsolete run/method scheduling and publication semantics;
  distinguish physical attempt/lease/fencing behavior that remains required by current DDO.
- **Move into the DDO model** — operations whose meaning survives: PDF staging and build,
  reference authoring and evaluation, `capture_cut` with consolidation.
- **Remain as native protocol**, if any do — entering the effective model the way the generated
  `data.*` operations already do (`native_operation_declarations`,
  `semantic/data_operation_storage.py:318-395`).

Then name the end state in DDO-11's completion statement: one effective model, with
`OperationContract`, its compiler, the effect table, the import registry and the generated call
facade gone or reduced to that one generated frontend, and the mutual-exclusion guard removed.

**Why here.** "One target authority" is the coordinator's own definition of complete. Without a
per-operation end state DDO-11 can retire every listed mechanism and still leave a second
catalog with live members. The work now is classification; the moves are existing scope.

**Principles.** FP-04, DP-01 (G1: two independently mutable definitions of what an operation
is), DP-16 (a replaced path does not survive).

**Preserved.** ADR-0092's transitional guard for live legacy consumers; frozen migrations;
target-required physical attempt/fencing behavior. Legacy lifecycle tables and sealed readers
are not protected merely by historical consumers; I09 permits migration or regeneration instead.

**Alternative: leave it to DDO-11.** This repeats what the completion audit corrected once
already (CA-07, a retirement row citing code that no longer existed).

**Closure evidence.** Every execution-model operation has a recorded class and owner; DDO-11's
criteria name the retired modules; the compiler no longer needs the guard.

<a id="I03"></a>
### I03 — Use the generated fate types where code branches on fate, and partition the classifier

*Alignment opportunity with one coverage gap. DDO-03/04 (executed), DDO-06, DDO-09.*

**Current.**

- **Fates.** The protocol YAML owns three fate lists, generated into
  `semantic/_data_operation_fates.py`, a SQL list and a physical CHECK. The generated Python
  module is imported only by its generator (`semantic/typed_generation.py:82-89`) and one test.
  The strings are spelled as literals where behavior depends on them: `BindingStatus`
  (`semantic/data_operation_bindings.py:45-53`), fate sets in
  `semantic/data_operation_demands.py`, and the impact classifier. The planner already writes a
  binding status straight into a recorded fate (`data_operation_demands.py:866-872`), so the
  relation between the two vocabularies exists and is untyped.
- **Impact.** `classify_change_impact` (`semantic/change_impact.py:169-298`) takes
  `SelectionEvidence.fate` as `str` and names five target fates. A target that is `failed`,
  `partial`, `invalid`, `known-absent`, `not-applicable` or `awaiting-inputs` falls through to
  `changed_declared_dependency` or `insufficient_selected_or_population_evidence`. Its
  "not settled" set lists `unavailable`, which an earlier branch always catches. A new fate is
  silently "unknown".
- **Attempt states.** The data-task branch of `ops.guard_execution_task` hard-codes its legal
  transitions (`semantic/sql/execution_guards.sql:1-27`).

**Proposed.**

1. Type fate-carrying values with the generated `Literal`s, choosing the right one of the three
   (recordable, historical, visible) at each site, and type the binding-status-to-fate step.
2. Partition the visible fates explicitly in the classifier: a table from fate to its class
   (settled-fulfilled, settled-not-produced, not-settled, unavailable, cancelled) that the
   ordered chain consults. A `dict[VisibleFate, Class]` constrains keys but does not establish
   totality. Use an exhaustive typed discriminator with an unreachable remainder, or an exact-key
   conformance check against the authoritative vocabulary. Keep independent expected classifications;
   generated cases alone do not establish their meaning. The chain stays ordered because it also
   tests population, roots and native evidence.
3. Decide deliberately what a failed, partial or invalid target means for impact, and record
   the table in the change companion.
4. Generate the data-task state literals in the trigger from the protocol, as the fate CHECK
   already is. No runtime table read is needed.
5. For newly admitted definitions, compile each outcome's terminal state into the definition so
   the native `ops.ddo_completion_state` fallback for unmapped outcomes is not consulted. Fallback
   removal is part of the target: supported outcomes have explicit terminal mappings or a deliberate
   refusal. Already admitted old definitions are migration/regeneration inputs under I09, not a
   permanent reason for fallback. Releasing changed definitions is distinct from mutating an old
   result in place.

**Why here.** DDO-09 and DDO-10 add consumers of exactly these vocabularies: currentness
explanations, public reads and exports.

**Principles.** DP-01, DP-02 (no meaning from an unmatched string), FP-05, DP-19 (partial and
failed distinguishable), CI-04 (unknown is not absent).

**Preserved.** The native functions as transactional authority; the deliberate separation of
binding status, role state and operation-specific outcomes recorded in the contracts companion.
This relates them and does not merge them.

**Closure evidence.** Production code imports the generated types; a missing fate class is detected by the
chosen exhaustive discriminator or exact-key check; independent cases cover a failed and a
partial target.

<a id="I04"></a>
### I04 — One generic prepared-kernel port for the families that share the shape

*Alignment opportunity. Reopens DDO-07/08 mechanics for eighteen families.*

**Current.** There are 33 `resolve_*_port` factories. Eighteen modules build the shared
`PreparedOriginalCallPort`; the other fifteen build their own port classes from frozen
execution-custody records (PDF capture and transforms, learned primary providers,
characterization, HanLP, formal, sentence and discovery families) and differ for real reasons.

Among the eighteen, each family repeats:

- an `acquire_port` static method that forwards its seven arguments
  (`methods/clause_classification_declared.py:357-372`);
- a factory that looks up the operation, compares its id with the class dictionary and
  constructs the port with the family's assets, sources and function tuple
  (`semantic/clause_products.py:666-700`);
- a `*_profile_assets` function that differs between families by a name, a version string and
  a file list (`semantic/clause_products.py:42-52` against `semantic/predicate_products.py:46-56`);
- a `*CallPlan` class with the same verify, bind and plan sequence.

The differences inside this group are also real: the structural family binds `project` in place
of `context` and requires exactly one hydrated selection; the definition family dispatches two
operations to two kernels; the contextual encoder acquires a model from custody and carries two
assets. Separately, role declarations repeat one support block and one field-projection map
(`"projection": "selected-input"` appears 626 times across the source tree).

The coordinator already records one instance of this as "an improvement opportunity, not a new
completion defect".

**Proposed.**

Extend/extract the existing `PreparedOriginalCallPort` responsibility rather than create another
port authority. It already owns signature checks, verification, ingress, CPU evidence and completion
(`data_operation_prepared_call.py:28–166`). Clause/definition plans repeat physical bind/submit/wrap
work; structural acquisition requires exactly one governing selection and binds project instead of
context (`declared_structural_calls.py:482–510`). Contextual encoding authenticates native frames and
model custody (`contextual_encoder.py:364–432`). Share physical execution while family-owned captured
preparation retains those differences. No arbitrary binder DSL, implicit imports or dispatch registry.

- One generic CPU-kernel port and plan, configured from the declaration with the kernel or
  kernels, an argument binder (default: declared roles to kernel parameters, which the compiler
  already cross-checks) and any extra assets. A family keeps a custom plan where it does
  something the generic one cannot.
- Named defaults or templates for the recurring role support block and selected-input
  projection, expanded and inspectable at compilation.
- Leave the fifteen custody-bound ports, the explicitly supplied source sets and
  `primary_operations` as they are. The supplied source set is the closed-source universe
  ADR-0092 requires, and target closure already belongs to the model.

**Why here.** The remaining moves from the execution model ([I02](#I02)) and the rich family
([I05](#I05)) will add operations of this shape.

**Principles.** DP-06 (author structure once), DP-16 and §E (one declaration and any genuinely
new implementation), A3.

**Preserved.** Kernels, role and kind lists, context policies and product schemas. Closed-source
acquisition, CPU ownership, cancellation and receipts.

**Intentional change.** Declarations get shorter. Role, subject, binding, outcome and numerical meaning must retain independently checked
behavior where the refactor claims equivalence. Captured prepared-factory source and implementation
slice changes can legitimately change definition/recipe identities. Compare effective projections
and explain identity changes; do not preserve wrappers to manufacture digest equality.

**Alternative: leave it.** Each family works. The cost is paid on each new operation of this
shape and on each change to the port contract.

**Closure evidence.** A new CPU-kernel operation is a declaration, a kernel and its tests;
semantic projections retain required behavior and identity changes are accounted for; the replaced factories go with their mechanism
tests ([I08](#I08)).

**Coverage limit.** Common clause/definition and distinct structural/contextual preparations were
read closely; not all eighteen plans were read end to end. If most need a custom binder, the
benefit is the shared port and the role templates only.

<a id="I05"></a>
### I05 — Complete the rich family against the corrected model

*Scope and framing recommendation. DDO-09.*

**Current.** The coordinator's rich-consolidation boundary is clear that the remaining
Entity/Claim/Statement/Fact work is "substantive domain work".
`semantic/domain_operations.py` (3,704 lines), `consolidation.py`, `proposals.py` and
`record_interpretation.py` have no data-operation reference beyond one graph import.
Consolidation still runs through the execution model's `evaluate` and `assemble` entries and a
sealed `ops.input_cut`; `CutSelection` (`semantic/demand_results.py:54-85`) and the older cut are
unrelated in code. The queue already puts this first: DDO-10 depends on DDO-09's products, and
STATUS lists the rich contracts as the next owning scope.

Three boundaries need explicit integration:

- **Existing private standing is enforced.** `model/semantic/data-operation-candidate-inspection.yaml:48`
  requires `private_uncalibrated_candidates`; `declared_candidate_products.py:135–144` constructs
  and validates it, and `reading_resolution_products.py:114` checks it before use. Preserve this
  working boundary. The remaining question is the rich Entity/Claim/Statement/Fact contracts and
  their explicit standing/admission transitions, not adding a second standing system.
- **Two families have no disposition.** `record_policy` and `projection_analysis` have no DDO
  declaration and are not in the cutover companion's family table.
- **A third comparison vocabulary is unaddressed.** `compare_semantic_releases`
  (`semantic/operation_reporting.py:763`) still serves the model CLI beside `change_impact` and
  `source_comparison`.

**Proposed.**

- Write the rich family's design against [I01](#I01): a declared subject type in place of
  `"entity or statement"`, and standing as a declared distinction on the product kinds involved.
- Start with one small cut as a discriminating design scenario: a declared consolidation operation over a
  `CutSelection` at **private** standing. Producing accepted standing, running providers or
  converting data remains outside this audit. Also specify an accepted-standing admission case and
  refusal with missing/ambiguous evidence: the private case alone cannot establish complete rich
  contracts. `CutSelection` supplies native read/trust pins, not all rich policy, alternatives,
  known-fact and population meaning; substituting its ID for `ops.input_cut` is insufficient.
- Give `record_policy` and `projection_analysis` a disposition in the family inventory.
- Replace or retire the actual callers of `compare_semantic_releases`: it opens both sides with
  `bound_execution_model` (`operation_reporting.py:784–807`) and has CLI model/schema and MCP callers.
  Migrate useful structural model-difference explanations into the target model. Keep that question
  distinct from subject-relative native currentness and source-code drift; one catch-all classifier
  would lose meaning. Its old implementation retires with the execution model.

**Why here.** The plan already owns all of this. The addition is that the rich family is the
scenario that exercises every dimension at once — a subject that is not a source view, authored
and external origins, a policy as a parameter, a cut as a population, standing as a property of
a product — so it is where label fields would do the most damage.

**Principles.** FP-04, DP-02, DP-05 (observations and admitted knowledge separate), §E (do not
reduce the product to convenient fixtures).

**Preserved.** Required domain guarantees: no fabricated task or view aliases,
the consolidation and scientific kernels, independent exclusion and coverage expectations,
target-native provenance. Historical read obligations are reconsidered under I09.

**Uncertainty.** The reviewer did not read `domain_operations.py` in full. The claim is about
representation, not about how the conversion should be decomposed.

<a id="I06"></a>
### I06 — One owner for each read-surface literal

*Small alignment opportunity inside open scope. DDO-10.*

**Current.** Three sets of names are spelled twice:

- the five demand views: owned by `DemandQueryRequest.view`
  (`semantic/demand_queries.py:20`) and repeated in `cli/selected_results.py:15-20`;
- the three context recipes: owned by `ContextRecipe` (`methods/contextual_query.py:36`) and
  repeated in `serve/demand_context.py:42`;
- the definition variants: a hand map from three variant names to kind identifiers at
  `serve/characterization.py:642-646`. This is the one place where adding a product kind needs a
  surface edit; the five demand views are generic over kinds.

Four modules also read the `data_operation_native_definitions.json` release artifact by hand
(`evaluate/selected_references.py:33`, `serve/characterization.py:638`,
`serve/demand_export.py:342`, `semantic/data_operation_storage.py:918`).

**Proposed.** As DDO-10 migrates these call sites: import the owning `Literal` in the CLI and
serve request types; derive the definition-variant map only after the effective model owns an explicit variant-to-kind
association, with missing/ambiguous associations rejected. A kind name or IRI suffix is not that
association. Give the native-definitions artifact one authenticated typed reader that checks artifact
uniqueness and its model binding, reused by admission, serving, evaluation and export. Preserve each
consumer’s actual acquired cut, permission and nominal-kind checks.

**Not proposed.** Declaring read views or context recipes in the model. The model already has
graph projections and `read-projections.yaml`, and the recipes are resolver dispatch; a third
declaration would duplicate them.

**Principles.** DP-01, DP-16 (extension locality).

<a id="I07"></a>
### I07 — Restore the coordinator as a statement of current state

*Execution improvement. Proposed amendment; no coordinator restructuring in this review.*

**Current.** The coordinator is 2,435 lines. Its status line is a paragraph. At least five
sections say they hold the current account ("This section owns current execution disposition",
"This is the one current account for the selected increment", "This table owns current
disposition", the execution queue, the completion-and-next-action section), and later sections
supersede earlier ones in place. Most of the text is dated receipts: commands, result
identifiers and failure narratives. A reader resuming work has to reconstruct which statements
still hold; this review had to.

There is a second cost. The plan's unit of completion is the package, and packages now carry
four layers of amendment. Nothing in the plan tracks completion against the ten dimensions of
its own target, which is why the gaps in I01–I03 are not visible in it.

**Proposed.**

- One current-state table at the top: per package, what is implemented, what is open, the
  owning findings, and where the receipts are. One short status line.
- Consolidate dated receipts into clearly secondary sections of the existing coordinator, citing
  managed result IDs and retaining exact source/context limits and unresolved failures. Do not add
  a receipts page without a concrete retrieval need. Remove superseded current-state claims rather
  than leave several sections announcing authority. Git preserves earlier wording; plans/evidence
  remain under the repository retention rule.
- A second small table by target dimension: what is modeled, what is still label or literal,
  and which package closes it. This review's dimension table is a starting point.

**Constraints.** The operator's rule is that plans are never deleted; this keeps the file and
changes its shape, and the operator should confirm the shape. The NetworkX increment has now landed; reacquire current authorship before restructuring. Each summary row must
keep the words "scoped" and "bounded" where they apply and cite the receipt that carries the
exact source and context limits.

**Principles.** DP-01 applied to the plan, FP-06, and the repository's "keep a current working
set" agreement.

<a id="I08"></a>
### I08 — Move only the generic wiring assertion to one model-wide test

*Small test alignment; part of I04. Coverage is file-level with two files read.*

**Current.** `operation.capabilities.prepared_factory is not None` is asserted in eight test
files. In the files read, that line sits beside expectations that belong to the family: output
witness counts and `consumer_selection` in `tests/semantic/test_declared_structural_calls.py:55-64`,
profile, preparation, entrypoint and effects in the PDF capture test.
`tests/semantic/test_primary_operations.py:58-66` already resolves every factory in the primary
profile.

**Proposed.** Reuse/consolidate the existing model-wide acquisition checks: the broader
`tests/semantic/test_downstream_profile_acquisition.py:77–112` already resolves actual factories
against an independently expected operation population. Extend its responsibility to all factory-
requiring profiles rather than automatically widening a second primary-only loop. Preserve an
independently specified population expectation; merely iterating whatever the compiler emits cannot
find missing operations. Remove only redundant callable-presence assertions with the replaced
factories. Keep source-mismatch, resource-custody, binding-refusal and domain expectations such as
`test_predicate_products.py:54–73`. No test deletion follows just because it mentions a factory.

**Principles.** Test-assessment §2 (consolidation that preserves meaning); DP-16
(mechanism-specific tests leave with the mechanism).

<a id="I09"></a>
### I09 — Remove preservation as a reason for permanent legacy architecture

*Operator-directed change of premise, with concrete integration obligations. DDO-00–12; especially
DDO-09–11. Proposed implementation, not authorization to mutate data.*

**Current.** The preservation companion defaults to sealed retention of originals, references,
completed results and unsettled work, then requires exact old-reader/recovery closure before
retirement. ADR-0095 explicitly rejected reset/regeneration because of those consumers.
`data_operation_model.py:24–28,808–870,1027–1100` and
`data_operation_admission.py:37–64` implement exact v2–v5 interpretation alongside current v6;
`graph_inspection.py:356–374,475–538` branches for historical-unavailable views. Those are sound
implementations of the prior commitment, not defects in that increment. The operator has now
changed the commitment: freeing the target from legacy code is more valuable than guaranteed access
to all generated historical state, while faithful migration remains desirable.

**Proposed target.** One supported operation model, encoding family and set of target-native
read/write/evaluation interfaces. Multiple releases/results within that supported basis can retain
normal provenance and currentness; eliminating obsolete schema interpreters does not eliminate
history as a domain concept. No permanent execution-model compiler, version decoder, task/view alias,
legacy source-interface fallback, historical writer or migration-only import survives solely for
old data. Trace actual CLI/MCP/export/reference/fixture callers and frozen-schema imports, not just
the obvious version constants.

**Data transition.** For each affected population, choose the least machinery that preserves useful
meaning: direct target-native import when source/evidence/bindings are sufficient; regeneration when
they are not; or inert retention/disposal when no useful target consumer remains. This is a finite
adoption decision, not a new permanent registry. A converter is one-time tooling with an explicit
removal point, outside normal serving/execution. Test its intended correspondence and reject missing
facts rather than fabricate task/run IDs or accepted standing. Legacy-produced judgments whose
question/context/input-output basis changed must be reassessed, even if their payload converts.
Preserving a claim as an attributed old observation never certifies it as a new target answer.

**Adoption.** Finish target contracts and migrate maintained callers first; fence old writers at the
actual switch. Do not turn data-conversion completion into an architectural dependency. Use a clean
supported database baseline if retaining the old upgrade chain would retain legacy dependencies;
otherwise use a bounded forward change. Decide that physical route from the actual required schema
and imported populations during plan revision. This review does not prescribe rewriting frozen
migrations in place or operating against a live database. Preserve native authorization, leases,
uncertain-commit handling and source fidelity for new work; their continuing value is independent
of historical compatibility.

**Alternatives.** Permanent sealed readers retain the architecture the operator rejects. Mandatory
deletion wastes useful convertible data. Migrating everything before target delivery makes old
representations govern the redesign. Prefer faithful selective import plus regeneration, with a
complete code-retirement endpoint and no historical-data completeness requirement.

**Decision impacts.** Revise the adoption/preservation commitment through a successor to ADR-0095;
reconcile affected clauses of ADR-0092, compact/archive ADR-0098/0105 and source/graph ADR-0107/0108,
plus DESIGN B5 and affected D-doc owners. Do not supersede unrelated identity/trust/graph decisions
wholesale. Accepted records remain immutable; current plans remain authority until revised. Operator
intent is explicit here; this audit adds no repeated approval request for that direction.

**Closure evidence for later execution.** Current-source installation and native/public/evaluation
flows work with no legacy imports; old encodings are explicitly unsupported without a fallback;
selected migrated records are admitted and consumed under target contracts; changed-basis judgments
are new assessments; regenerated populations have honest coverage; obsolete code/config/grants/tests
and any one-time converter are retired. Existing independent domain expectations remain useful.
Git, retained plans/evidence and original failed receipts do not require runnable old application code.

**Principles.** FP-01/04/07, DP-16, CI-02/06/12 and heuristics H1/H24/H25/H28: preserve needed meaning
and assurance, remove compatibility work that no longer purchases a required capability.

## How the recommendations fit together

| | Depends on | Enables | Size and disruption |
|---|---|---|---|
| I01 | Subject/enforcement and determinant contracts; ADR reconciliation | I05 | Scope depends on actual representation gaps; identity changes must be explained, not suppressed. |
| I02 | — | DDO-11 completion | Small now (classification); the moves are existing scope. |
| I03 | Native protocol/outcome owners | DDO-09/10 consumers | Typing plus deliberate classification and generated native transitions; exact effort not established. |
| I04 | Verified shared capabilities | I02's moves, I08 | Avoid assuming all eighteen are mechanically identical. |
| I05 | I01 items 1–2 | DDO-09 | Framing of existing scope. |
| I06 | — | DDO-10 | Small, inside DDO-10's own migration. |
| I07 | Current ownership reconciliation | every later amendment | Simplify the existing coordinator; no automatic new receipts document. |
| I08 | I04 | — | Bounded test consolidation; semantic expectations stay independent. |
| I09 | Operator direction; successor decision/target contracts | Complete code retirement | Selective migration/regeneration, without permanent historical support or a migration-wide blocker. |

By consequence, I01 and I02 matter most: they are the difference between a model that is total
and explicit and one that is described as such. By order, I02 and I03 can be prepared together without waiting for rich-family implementation; I09 changes adoption assumptions before detailed migration design;
I01 subject/enforcement work should precede rich-family integration; I04 can travel with
the first execution-model move.

## Judged sound and left alone

- **Two binding interpreters** (SQLAlchemy lowering and the PL/pgSQL interpreter). Deliberate
  independent native validation, recorded in the contracts companion.
- **`ops.task` as the physical attempt.** Accepted in the products and demand companions; a
  request-state machine would be a second authority.
- **Python and native request identity computed twice and compared.** An equality check across
  a trust boundary.
- **The Python and native completion functions.** They answer different questions: which outcome
  a normal return reports, and which terminal state a reported outcome maps to.
- **The support-graph readers.** Change impact and selected graphs share the protected selected
  record index. The completed NetworkX increment now owns the shared topology realization; no
  repeat migration is scheduled by this review.
- **`effect_support.py`.** It checks the older execution model and leaves with it operation by
  operation; it is not a second opinion to preserve.
- **Legacy twin reuse, `reused_task_id`, run finalization.** Retire with maintained callers. Old
  data does not require replacement historical readers; apply I09.

<a id="separate"></a>
## Separate from this plan

- A universal typed-payload rewrite remains separate. However, typed subject scope, rich evidence,
  standing, policy/cut and consumer variant associations required by I01/I05/I06 belong in this
  amendment. Canonical bytes or dictionary shapes cannot substitute for those missing contracts.
- Splitting `data_operation_compilation.py` (one function of about 960 lines) and
  `data_operation_ports.py` along the model's concepts. Sensible when I01 opens the compiler; its
  value does not depend on this plan.

## Evidence limits and next decision

This audit changes recommendations only. The coordinator still owns F01–F14/C1–C7 and CA dispositions;
no recommendation disposition closes a product finding. The companion records the original eight
recommendations and audit changes. Plan revision should incorporate I01–I09 together, reconcile the
preservation decisions, and specify target-native consumer/retirement acceptance before execution.
