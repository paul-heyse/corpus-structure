# M1 record assembly and bounded interpretation

**Target: Proposed; mixed implementation maturity · reconciled 2026-11-04.** This companion
owns the detailed design and completion conditions for M1-08/09/10. The
[coordinator](../first-production-milestone_2026-11-03.md) owns current package state,
dependencies, findings and assembled acceptance. Foundation notes retain their stated source
and receipt context; the coordinator owns the current integrated implementation and selected
verification. Remaining targets below are not blanket claims that every listed capability is
unimplemented. Whole-M1 qualification remains open.

**Execution baseline, 2026-11-04:** selected AC acceptance remains bounded to71a78774/native105.
Subsequent M1 native107–129, actual CPU publication/reuse/recovery, independent source-only references
and candidate consumer results have their own receipts in the coordinator. Actual development
quality fails and no fitted acceptance policy exists. Preserve those separate implementation,
functional and quality boundaries; no whole M1 package is complete.

## Target and existing seams

Deliver faithful, qualified source records for statistics-first English release populations:
definitions/concepts, qualified local assertions, measurements/comparisons, table assertions and
formula/symbol context. A record reads the source under a released guideline; it does not certify
scientific truth, causal validity or a proof. Ordered procedures remain shadow output.
The target develops [WP3/WP4](../../target-pipeline-design/first-production-milestone.md#delivery-and-exit-evidence)
and [O03/O04](../../functional_reviews/m1-target-design_2026-11-03.md#O03).

The existing [consolidation `assemble`](../../../python/corpus-structure/src/corpus_structure/semantic/consolidation.py)
lowers typed source values into facts and separate source occurrences; its selected facts are
policy selections, not confidence cutoffs. Existing
[publication rows](../../../python/corpus-structure/src/corpus_structure/semantic/publication.py)
include occurrence evidence, evidence roles, assessments, alternatives and derivation premises.
These are foundations to extend under M1-02/M1-03, rather than five independent stores.
[`derive`](../../../python/corpus-structure/src/corpus_structure/semantic/inference.py) computes
finite rule closure over admitted premises. `semantic/record_interpretation.py` already supplies the distinct bounded domain operation
`interpret_records` with three templates. Complete its producer/policy integration: routing uncertain candidates through `derive` would conflate
interpretation with established entailment. D1/D2 own meanings; D4 owns method realization;
[D5](../../design/D5-consolidation-identity-confidence.md) owns interpretation, source identity
and publication policy. The coordinator schedules durable authority changes before dependent work.

The [shared record/evidence contract](semantic-contracts-and-evidence.md) must govern assembly,
publication and evaluation. It contains stable
occurrence identity, family, field roles and states, role-labelled anchor sets, original versus
normalized versus derived values, qualification, coherent alternatives and acceptance standing.
Present, unstated, inapplicable and unresolved are distinct. Unresolved carries reason and available
alternatives; required meaning-changing unresolved roles prohibit full-record acceptance. An
operation failure, skipped route or `not_run` is not a field state. Native `ABSENT` and forced
cardinality do not decide whether the source stated a role.

<a id="M1-08"></a>
## M1-08 — Five deterministic family assemblers

**Remaining target.** Reuse `methods/record_assembly.py` common assembly, native table/formula
grouping and candidate reconciliation; consume M1-03 bound candidate observations/evidence,
[M1-05 typed contexts](linguistic-preparation-and-source-contexts.md) and the implemented
[M1-07 CPU producer profile](gliner-execution-and-cpu-runtime.md).
M1-02 must supply the released family roles, field states
and occurrence identity recipe. M1-01 supplies guideline conventions before assemblers decide
what constitutes a complete record. An agreed interface permits early fixture development; an
actual producer and coordinate mapping are required before claiming assembled integration.

Finish the existing five-family operations around common located candidates and domain-specific
attachment rules, using retained wrong-association outcomes as counterevidence to shape-valid success.
Use native GLiNER natural grouping with an explicit anchor and native same-field assignment where
the selected pack supports it. Deterministic span assembly is the baseline comparator and the
route for established keys; do not recreate native within-group matching as a second generic
framework. A decoder's grouped result remains a proposal. Outer assembly owns cross-context
identity, qualification, scope, inherited notes and whole-record completeness.

| Family | Assembly and meaningful failure |
| --- | --- |
| Definitions/concepts | Pair separately anchored term and defining passage; preserve aliases, local sense and explicit hierarchy/instance relation. A reused term resolves under source scope or remains alternative. Lexical similarity cannot authorize a global ontology merge. |
| Qualified local assertions | Join explicitly typed relations/frames to local arguments, then attach polarity, modality, attribution, quantification, conditions, exceptions and time/scope. A detached “may” or exception is a full-record failure, even if subject/relation/object match. |
| Measurements/comparisons | Join referent/property/value/unit/value-role/comparator/bounds/uncertainty and applicable condition. Preserve exact numeric string and source role; a converted value is a derivation with premises and rule, not extracted text. Distinguish mean, SD, sample size, rated and delivered values. |
| Table assertions | Use native row keys, cell identity, full header paths and declared unit/note inheritance. Retain blanks and missing states; refuse ambiguous header or note attachment as unresolved. A shared header or condition remains reusable across records. |
| Formula/symbol context | Link native formula occurrence to independently addressed declarations, meanings and assumptions. Symbol spelling alone cannot cross section scope. Nearby prose is not formula-coordinate evidence, and formula context establishes no theorem proof. |

A source record can lower to multiple domain assertions while retaining record identity and role
membership. Preserve separate occurrences with equal text and qualifications; fact equivalence
may group qualified meanings under existing identity policy but cannot erase provenance or record
structure. The statistics example “Group A: mean 12, SD 3; Group B: mean 10, SD 2” must retain two
groups, distinct mean/dispersion roles and unstated sample sizes. A shared population note may
support both records without violating native scalar exclusivity.

Perform set joins over typed candidate relations in existing owned analytical scopes, projecting
only needed columns. Keep source addresses, exact numerics and state tags through Arrow/DuckDB
transport. Partition on relevant scope/join keys before comparing pairs; a small final record
count does not justify a whole-corpus Python Cartesian join. Keep buffers alive through lazy
consumption and complete or abort results before engine reuse. Model calls and uncertain solving
remain outside publication transactions.

The output is a complete deterministic candidate record, a supported partial/candidate record or
an explicit unresolved/rejected disposition, with dependencies and family coverage. No-output
units still contribute routing and gap outcomes. Local pure assembly does not publish or move
the selected result pointer. M1-11 consumes these outputs through the common policy boundary.

Focused verification must independently specify expected roles, qualifiers and anchors from
sources. Cover duplicate strings at different positions, nested spans, discontinuous evidence,
blank cells, header/note inheritance, repeated symbols under changed scope and required missing
roles. Reuse production structural validators for consumers, but do not compute expected readings
with the assembler being tested. Finish M1-08 when each family has a usable deterministic route,
actual bound producer/context integration and located candidates on retained sources. Release
precision, provider quality and all-family adoption remain M1-13/M1-14 obligations.

AC integration changes the assembly inputs without granting scientific authority. Consume the
released behavioral roles and complete RuleValue ABI2, and retain attribute-specific evidence for
each qualifier. Typed identity outcomes must remain visible; storage representatives do not
choose the class display or scientific-view representative. Persist operation-owned reasons on
actual assessments and verify their consumer presentation. AC improvement I01 supplies the
nondefault/producer-bound integration cases; it does not replace independent source readings.

<a id="M1-09"></a>
## M1-09 — Three bounded interpretation templates

**Remaining target.** The pure numerical operation is implemented. Finish actual producer and
acceptance integration after the M1-08 deterministic baseline can expose actual ambiguity and provide
a fixed candidate comparison. Develop numerical fixtures alongside M1-02/M1-03 contracts. Enable
coupling for a supported template only after comparison with deterministic joins and a fitted
independent/stacking baseline demonstrates worthwhile complete-record gain or error reduction.
M1-13 supplies independent development references; it does not take reference answers from these
predictions. Sparse fitting evidence keeps scores provisional and never licenses invented factors.

The logical table template's `row_identity` decision remains distinct from the statistics source
role `row_label` (ADR-0058). Required native table/cell custody supplies structural row membership;
a quoted label is separately inspected source content. Missing native row-header metadata never
becomes an unstated author label. Dense contexts consume complete bounded row/cell targets and
canonical rich-header child pieces; unconsumed middle text and synthetic separators supply no
literal evidence. Current bounded preparation/assembly evidence is in the coordinator.

The templates are value–property–referent–condition; mention identity–type–relation; and table
header–row identity–cell value–unit–note. Definitions/formula records reuse these decisions with
their native contexts. Do not build a universal solver language or corpus-wide latent-truth model.
Use the existing `InterpretationRequest` / `InterpretationResult` operation whose input names
decisions, finite candidate domains, factor
scopes, hard constraints, policy/ontology inputs, search settings and all computation dependencies.
Every uncertain decision retains unresolved and a reason; identity also permits genuine local/new.
Search scope, exclusions, candidate truncation and retrieval limits are part of its result.

Use assignment-relative hard constraints. Structural invariants can be hard; unit/type constraints
are hard only under the meanings selected in that assignment. Typical values and uncertain ontology
expectations are soft or diagnostic. In the pressure challenge, both `2 bar` and OCR's `2 h`
survive until unit meaning, antecedent and condition scope are jointly evaluated. A preferred OCR
duration cannot pre-prune the pressure interpretation. Preserve delivered/rated flow distinctions
and the modal “may” and “below this pressure” qualification on cavitation.

The implemented numerical baseline is [M1 numerical realization](../../target-pipeline-design/mathematics.md#m1-numerical-realization):
bounded NumPy assignment blocks with SciPy `special.logsumexp`. Declare real factor/dependence scopes
before component partitioning; `networkx.connected_components` can identify independent components.
Shared release metadata alone creates no coupling. Begin with a configurable 65,536-state guard
plus time/memory limits, admitting work through M1-06. This is a supported computational limit,
not evidence that actual M1 component sizes fit it.

Evaluate feasibility and sum log potentials over complete retained support. Hard-zero/infeasible
states may carry negative-infinity log weight or an explicit feasibility mask. Reject NaN,
positive infinity and other invalid model inputs; do not reject a legitimate hard zero as a
numerical failure. Empty positive feasible support returns infeasible; no
uniform distribution or successful empty extraction substitutes. For record event `Phi`, compute
`exp(logsumexp(weights[Phi]) - logsumexp(weights))`. Include every meaning-changing qualifier in
the event; assignments satisfying duplicate derivations count once. Normalize before selecting a
few displayed coherent alternatives. Never multiply field marginals, normalize only the displayed
list or replace an event sum with MAP. Record scores are conditional on the declared retained
candidate model. Missing candidates have unknown omitted mass, independently measured by capture
recall; they are not automatically assigned a calibrated unresolved probability.

Return coherent alternatives, event score/probability standing, useful marginals, exactness relative
to the declared model, examined search and limit/feasibility diagnostics. Numerical failure,
infeasibility, cancellation and resource limit remain different outcomes. No silent splitting,
approximate fallback or partial component becomes accepted output.

Independent numerical expectations must include a hand-calculated tiny joint/event distribution,
duplicated derivations, impossible support, hard-zero feasibility, variable/state permutations,
extreme log weights and MAP-versus-event disagreement. Test limits separately from semantic
empty results. Comparison evidence must hold the candidate universe fixed when attributing gains
to coupling, and recompute dependent candidates for end-to-end effects. Actual CPU execution and
provider extraction remain separate from pure numerical checks.

### Conditional inference investigations (O09)

Trigger pgmpy investigation only when measured repeated factorized queries or enumerated component
work make a factorized route useful. Compare supported `DiscreteMarkovNetwork`/`DiscreteFactor`
with variable elimination or junction-tree inference; inspect the selected version, ordering,
hard zeros, finite positive partition, normalization and intermediate factor size. A full joint
request may recreate enumeration's size. Qualify stability against the independent numerical
cases before substitution. Select adopt/route/revise/defer/reject from complete-route evidence;
the baseline remains runnable without pgmpy.

Z3, SciPy `milp` or CVXPY are candidates only for a demonstrated constraint/best-assignment problem.
They do not supply posterior normalization or marginals by themselves. Approximation needs an
explicit result/error policy and evidence for the supported subset. Pyro requires a separately
justified learned model. These investigations neither add dependencies nor change inference
semantics automatically; the coordinator owns their current disposition.

<a id="M1-10"></a>
## M1-10 — Acceptance, calibration, dependence and invalidation

**Remaining target, not established by the pure operation.** Consume M1-09 template results, deterministic proofs from M1-08 and independently
authored M1-13 development/fitting references. Author the acceptance contract early so producers
retain necessary dependencies; complete fitted acceptance after there are sufficient held-out
labels. M1-11 must not publish model-resolved output as accepted merely because a shape validator
or an exact enumerator succeeds.

Keep author modality, reading confidence, source reliability and corpus support distinct. Group
correlated observations by common checkpoint/head/encoder, passage, windows, OCR and derivation.
Do not count schema re-decoding or repeated windows as independent evidence. Fit grouped features
or regularized stacking where labels support it; a conservative representative-feature policy
must name its assumptions and remain provisional when fitting is insufficient. The prototype's
uniform effective-count discount is a heuristic, not the M1 calibration method.

A binary calibrated posterior may become an LLR feature by subtracting the matching calibration
prior log-odds only under matching conditioning assumptions. Candidate-versus-rest scores do not
define a coherent changing-candidate multiclass distribution. Calibrate final record-event
predictions after constraints and coupling; head calibration cannot be assumed to survive added
factors. Use explicit source-group-separated development, feature-fitting, final-event calibration
and final-assessment partitions. Evaluator-authorized fitting uses only the isolated fitting
labels through the protected route; feature fitting does not consume calibration/final labels,
and production extraction receives neither reference answers nor evaluator credentials. Freeze the
family acceptance threshold before final assessment. The utility threshold `c/(c+v)` explains a
decision model; 0.75 is illustrative and is not the release threshold.

Deterministic acceptance requires validated premises and proof witnesses. Model-resolved acceptance
requires the evaluated family policy. Expose provisional score and decision status until empirical
calibration is established. Retain rejected candidates and useful partial records for inspection;
they do not satisfy full-record precision/recall by dropping a failed qualifier.

Separate derivation lineage from computation dependencies. A rule witness lists premises that
establish a result; invalidation also includes consumed counterevidence, rejected alternatives,
failed retrieval, ontology/calibration/policy versions and contexts influencing candidate selection.
Withdrawal recomputes the affected interpretation component and descendants, potentially increasing
a winner's probability. Setting a premise to zero in fixed lineage is not that recomputation.
Bind interpretation reuse to these complete dependencies through the existing reuse owner; do not
add a second cache or lease system.

Qualification cases withdraw a rejected alternative, change a table note, change ontology or
acceptance policy, duplicate a window and interrupt before publication. Verify selective recomputation,
retained immutable observations and idempotent resume. Independent references determine whether
the resulting readings and acceptance decisions are faithful. Few independent source groups,
even with many records, can leave calibration or generalization unestablished. The selected
finite-cut precision gate follows ADR-0053 and the evaluation companion’s census/SRS procedure;
few origins alone do not invalidate that bound.

M1-10 supplies M1-11 acceptance standing, component dependencies and replay scope. M1-14 owns
final threshold/gate evidence and operating/adoption claims. Corpus-wide truth probability,
conformal coverage, learned EVI escalation and exhaustive stream attribution remain conditional
follow-ons with their own assumptions, rather than requirements for this package.

## Completion and evidence limits

Completion here means implemented family assembly and interpretation contracts, migrated producer/
publication inputs, focused independent checks, explicit unsupported/limited outcomes and complete
invalidation dependencies. It does not mean the five families are released. The coordinator owns
the combined required qualification union and final source applicability. During future execution,
run focused functional checks after coherent slices; broad qualification follows complete functional
scope under M1-14. This revision performed source inspection only. Existing assembly and pure numerical receipts
remain bounded at their original source; new runtime, model, numerical,
calibration and consumer checks are **not_run**.

The [AC improvement review](../../plan_improvement_reviews/audit-closure_2026-11-03.md) I01–I03
and [AC completion audit](../audit-closure_2026-11-03.md#12-completion-audit--claimed-integrated-slices)
constrain the reused foundation. The coordinator alone owns their M1 dependency impact and
current evidence applicability. New checks are selected for unresolved obligations; historical
passes are not promoted to final-source or whole-milestone qualification.
