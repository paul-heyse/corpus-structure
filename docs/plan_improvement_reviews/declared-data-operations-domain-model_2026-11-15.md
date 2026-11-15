# Declared data operations — the domain model against its own target

**Plan-improvement review · 2026-11-15 · proposals only.** Reviews the
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md) and its eleven
[companions](../plans/declared-data-operations/) against the outcome the coordinator states for
itself:

> a total explicit domain model governing supported products, subjects, operations, input/output
> bindings, applicability, lifecycle/effects/outcomes, demand fulfillment, provenance, reuse and
> change.

The six earlier improvement reviews of this series each started from a library. This one starts
from that sentence and asks, for each of its ten dimensions, how **total**, **explicit** and
**singly owned** the model is in the code now, and what the remaining packages would leave
unchanged. The operator confirmed that executed scope (DDO-00–08) is open to revision.

Nothing here amends the plans, STATUS, ADRs or code, and nothing here lifts the operator's
implementation and test stop or the rich boundary's limits on standing changes and provider runs.
Recommendation IDs `I01`–`I08` are local to this review; cite them as
`declared-data-operations-domain-model_2026-11-15.md#I0n`. They are distinct from the I-numbers
of the earlier reviews.

## Baseline, method and limits

| | |
|---|---|
| Source and plan baseline | `fcc1d6cbe` (main, 2026-11-15), re-checked at `1d551f0ca`, which changes only `semantic/graph_inspection.py`. |
| Relevant uncommitted work | A concurrent agent's NetworkX increment: `evaluate/assessment_graph.py`, `semantic/assessment_graph_contract.py`, `semantic/selected_graph.py`, four test files, two plan companions and an untracked evidence folder. Read as in progress, not as accepted. |
| Standard | Core principles 3.3 with the efficient-architecture heuristics, code-intelligence profile 1.4, test-assessment 1.2 and the repository binding. Used for judgment within the footprint; this is not a diagnostic audit and does not replace a formal design review. |
| Method | Four read-only code maps (model authority and compilation; native realization, demand and lifecycle; provenance, reuse, change and public surfaces; operation families, legacy and tests), each returning `file:line` evidence. The decisive claims behind every recommendation were re-read in source by the reviewer. A fresh-context design reviewer then challenged the draft; five of the eight recommendations were narrowed and one part was withdrawn. See [Challenge](#challenge). |
| Not done | No tests, providers, database work or probes. The PL/pgSQL bodies were read in excerpts. Test structure is known from file-level search and a few files, not from reading every test. Counts come from search and are approximate unless a file and line are given. Absence claims are searches of `python/corpus-structure/src` and would miss dynamic access. |

All paths below are under `python/corpus-structure/src/corpus_structure/` unless they begin with
`docs/` or `tests/`. Every statement about the design is **Interface-checked by source inspection,
2026-11-15**; every recommendation and benefit is **Proposed** and unmeasured.

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

Smaller, well-bounded improvements follow from the same reading: one generic port for the
eighteen families that share a shape ([I04](#I04)), single owners for the read-surface literals
([I06](#I06)), and model-level test assertions made once ([I08](#I08)). Two recommendations
concern delivery: the rich family should be designed as the first instance of the corrected
model ([I05](#I05)), and the coordinator has stopped being usable as a statement of current state
([I07](#I07)).

The set does not change what the series is and adds no package.

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

1. **Subject types become a small declared vocabulary** in the model, each carrying the facts
   consumers branch on: the kind or reference that identifies it, and whether it is a per-source
   or per-document subject, which is the fact `source_discovery` recovers from the spelling.
   Operations reference a declared type; an unknown one is a compilation error.
2. **Applicability and invariant entries resolve or are rejected.** Each names a binding
   predicate (already tagged `impact: eligibility` or `result`) or a declared invariant with an
   enforcement point. Eligibility identity then follows what is enforced, through `binding`.
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
record through the ADR route, with the model version step (v6 to v7) and exact reading of
archived versions that the series already uses. Items 1 and 2 do not need it; items 3 and 4 do.

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

**Uncertainty.** How many of the 72 declarations carry a real, otherwise unrepresented fact in
`precision` or `coverage` was not counted.

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

- **Retire with its mechanism** — run, task and method protocol.
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
sealed archive reading; the legacy lifecycle tables until their operations end.

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
   ordered chain consults, so the type checker reports a fate with no class. The chain itself
   stays ordered; it also tests population and roots.
3. Decide deliberately what a failed, partial or invalid target means for impact, and record
   the table in the change companion.
4. Generate the data-task state literals in the trigger from the protocol, as the fate CHECK
   already is. No runtime table read is needed.
5. For newly admitted definitions, compile each outcome's terminal state into the definition so
   the native `ops.ddo_completion_state` fallback for unmapped outcomes is not consulted. The
   fallback stays for definitions already admitted, which cannot change under their release,
   unless the operator chooses to regenerate them. This item is optional.

**Why here.** DDO-09 and DDO-10 add consumers of exactly these vocabularies: currentness
explanations, public reads and exports.

**Principles.** DP-01, DP-02 (no meaning from an unmatched string), FP-05, DP-19 (partial and
failed distinguishable), CI-04 (unknown is not absent).

**Preserved.** The native functions as transactional authority; the deliberate separation of
binding status, role state and operation-specific outcomes recorded in the contracts companion.
This relates them and does not merge them.

**Closure evidence.** Production code imports the generated types; adding a fate to the
protocol fails type checking until it has a class; independent cases cover a failed and a
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

**Intentional change.** Declarations get shorter. Compiled definitions for existing operations
must be unchanged, which is checkable by comparing them before and after.

**Alternative: leave it.** Each family works. The cost is paid on each new operation of this
shape and on each change to the port contract.

**Closure evidence.** A new CPU-kernel operation is a declaration, a kernel and its tests;
existing compiled definitions are unchanged; the replaced factories go with their mechanism
tests ([I08](#I08)).

**Uncertainty.** Three of the eighteen were read closely. If most need a custom binder, the
benefit is the shared port and the role templates only.

<a id="I05"></a>
### I05 — Design the rich family as the first instance of the corrected model

*Scope and framing recommendation. DDO-09.*

**Current.** The coordinator's rich-consolidation boundary is clear that the remaining
Entity/Claim/Statement/Fact work is "substantive domain work".
`semantic/domain_operations.py` (3,704 lines), `consolidation.py`, `proposals.py` and
`record_interpretation.py` have no data-operation reference beyond one graph import.
Consolidation still runs through the execution model's `evaluate` and `assemble` entries and a
sealed `ops.input_cut`; `CutSelection` (`semantic/demand_results.py:54-85`) and the older cut are
unrelated in code. The queue already puts this first: DDO-10 depends on DDO-09's products, and
STATUS lists the rich contracts as the next owning scope.

Three things are not in that scope as written:

- **Standing is a docstring.** `DdoCandidateInspectionReport` "explicitly has private,
  uncalibrated standing" in prose. The distinction between private, proposed and accepted
  knowledge is the one DDO-09 most needs to be checkable.
- **Two families have no disposition.** `record_policy` and `projection_analysis` have no DDO
  declaration and are not in the cutover companion's family table.
- **A third comparison vocabulary is unaddressed.** `compare_semantic_releases`
  (`semantic/operation_reporting.py:763`) still serves the model CLI beside `change_impact` and
  `source_comparison`.

**Proposed.**

- Write the rich family's design against [I01](#I01): a declared subject type in place of
  `"entity or statement"`, and standing as a declared distinction on the product kinds involved.
- Use one small cut as the design acceptance scenario: a declared consolidation operation over a
  `CutSelection` at **private** standing. Producing accepted standing, running providers or
  converting data stays behind the operator decisions the boundary already requires.
- Give `record_policy` and `projection_analysis` a disposition in the family inventory.
- Decide whether `compare_semantic_releases` retires into the change classification or stays as
  a distinct declared projection.

**Why here.** The plan already owns all of this. The addition is that the rich family is the
scenario that exercises every dimension at once — a subject that is not a source view, authored
and external origins, a policy as a parameter, a cut as a population, standing as a property of
a product — so it is where label fields would do the most damage.

**Principles.** FP-04, DP-02, DP-05 (observations and admitted knowledge separate), §E (do not
reduce the product to convenient fixtures).

**Preserved.** Everything the boundary section preserves: no fabricated task or view aliases,
the consolidation and scientific kernels, independent exclusion and coverage expectations,
sealed historical reads.

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
serve request types; derive the definition-variant map from kind facts in the effective model;
give the native-definitions artifact one typed reader.

**Not proposed.** Declaring read views or context recipes in the model. The model already has
graph projections and `read-projections.yaml`, and the recipes are resolver dispatch; a third
declaration would duplicate them.

**Principles.** DP-01, DP-16 (extension locality).

<a id="I07"></a>
### I07 — Restore the coordinator as a statement of current state

*Execution improvement. The form is an operator decision; do it at a quiet boundary.*

**Current.** The coordinator is 2,380 lines. Its status line is a paragraph. At least five
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
- Move dated receipts and failure narratives to a receipts page beside the plan that cites the
  managed `ci` result identifiers, which already hold the results. Evidence records stay for
  investigations. Nothing is deleted: the plan file stays, Git keeps the earlier text.
- A second small table by target dimension: what is modeled, what is still label or literal,
  and which package closes it. This review's dimension table is a starting point.

**Constraints.** The operator's rule is that plans are never deleted; this keeps the file and
changes its shape, and the operator should confirm the shape. The companions are being edited
by a concurrent increment now, so restructure only when that has landed. Each summary row must
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

**Proposed.** Extend that existing model-wide test to every operation whose profile requires a
factory, and drop the bare per-family line with the factories I04 replaces. Family-specific
expectations stay where they are.

**Principles.** Test-assessment §2 (consolidation that preserves meaning); DP-16
(mechanism-specific tests leave with the mechanism).

## How the recommendations fit together

| | Depends on | Enables | Size and disruption |
|---|---|---|---|
| I01 | Operator and ADR route for items 3–4 | I05 | Items 1–2 moderate and local. Items 3–4 are a model-version step that changes identities once. |
| I02 | — | DDO-11 completion | Small now (classification); the moves are existing scope. |
| I03 | — | DDO-09/10 consumers | Small; mostly typing and one table. |
| I04 | — | I02's moves, I08 | Moderate and mechanical for eighteen families. |
| I05 | I01 items 1–2 | DDO-09 | Framing of existing scope. |
| I06 | — | DDO-10 | Small, inside DDO-10's own migration. |
| I07 | Operator decision on form | every later amendment | Editorial. |
| I08 | I04 | — | Small. |

By consequence, I01 and I02 matter most: they are the difference between a model that is total
and explicit and one that is described as such. By order, I02 and I03 are cheap and independent
and can come first; I01 items 1–2 should precede the rich family's design; I04 can travel with
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
- **The support-graph readers.** Change impact and the selected graph already read the one
  protected export through the selected record index; the remaining path walk is scheduled in
  the graph companion.
- **`effect_support.py`.** It checks the older execution model and leaves with it operation by
  operation; it is not a second opinion to preserve.
- **Legacy twin reuse, `reused_task_id`, run finalization, retained readers.** Correctly
  scheduled for retirement with their consumers.

<a id="separate"></a>
## Separate from this plan

- A typed-payload pass over open `SourceValue` ranges, the hand-coded packet and context shapes
  and `analyzed_scope` bytes. A schema undertaking of its own.
- Splitting `data_operation_compilation.py` (one function of about 960 lines) and
  `data_operation_ports.py` along the model's concepts. Sensible when I01 opens the compiler; its
  value does not depend on this plan.

<a id="challenge"></a>
## Challenge

A fresh-context design reviewer re-checked every claim at `1d551f0ca` and tried to break each
recommendation. Its findings were re-verified in source before being applied.

| | Outcome | What changed |
|---|---|---|
| I01 | Narrowed | The draft called `behavior` a label and said the contracts companion ruled it out. It is the implementation revision for operations without a slice and is re-checked natively; the companion requires it. Prose now leaves the recipe only for slice-owned operations, coverage and precision stay until typed, the ADR-0092 route is named, and the third-party determinant question is added. Subject types and resolving applicability stand. |
| I02 | Stands, corrected | The draft's counts and class sketch were wrong (27 PDF and 15 reference operations, one DDO counterpart), and two absence claims were overstated: the coordinator does state how `approved_implementations` ends, and DDO-00 dispositions exist at population level. The effect table is not an independent check. |
| I03 | Stands, corrected | An exhaustive match does not fit an ordered chain; replaced with a typed partition. Task transitions are generated literals, not a table read. The completion-mapping item is reduced to optional and limited to new definitions. |
| I04 | Narrowed | From "one port for all families" to the eighteen that share `PreparedOriginalCallPort`. Proposals to derive source lists and replace `primary_operations` were dropped; both already do what ADR-0092 requires. |
| I05 | Narrowed | The draft said the rich family was ordered after DDO-10; the queue has the reverse. A proposed vertical that produced accepted knowledge conflicted with the rich boundary; recast as a design scenario at private standing. |
| I06 | Narrowed; one part withdrawn | Declaring read views in the model would duplicate existing projection vocabularies; reduced to single owners for three literals and one typed reader. The proposal to share one support projection was withdrawn: the readers already share the export index. |
| I07 | Stands, corrected | Receipts go to a page citing managed result identifiers, not to evidence records; timing and the operator's stop are stated. |
| I08 | Narrowed | The per-family lines sit beside family-specific expectations; only the bare wiring line moves, into an existing test. |
