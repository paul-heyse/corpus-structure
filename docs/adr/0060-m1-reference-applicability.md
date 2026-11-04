---
id: ADR-0060
title: Preserve source-reference provenance across compatible execution successors
status: accepted
date: 2026-11-04
supersedes: [ADR-0057]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: Reference meaning, source closure or comparison semantics cannot be matched without changing the authored premise.
---

## Context

Actual M1 source-only references now bind eleven frozen analysis views and immutable A/B/C
passes. Their source, meaning and coordinate judgments survive a bug repair to trusted runtime
code. The current evaluator nevertheless requires the entire executable release to match.
That couples independent source judgments to unrelated implementation bytes, forcing repeated
authoring during the design phase. The operator explicitly authorizes adjusting requirements
to remove these development frictions while preserving intended behavior and evaluation quality.

View keys, logical source aliases and record identities also include release determinants.
Removing only the release equality would produce false misses or misbound evidence. Retained
native products and projections already provide the physical source correspondence, and the
existing protected evaluation store already binds run, reference set, snapshot and result.
No additional store is needed. The M1 coordinator's F23/F24 retain implementation and quality
obligations separately; accepting this decision establishes none of their closure.

This replacement carries forward every sealed interpretation, native admission, operation reuse,
field-support and fitting decision from ADR-0057. It changes only reference applicability across
implementation successors. ADR-0052's immutable original authoring frames and source judgments,
ADR-0058's literal row-label meaning, ADR-0059's support boundary, all five family quality gates,
origin isolation, prior UM standing, legacy native99/run6 and operational defaults survive.

## Options

1. Keep exact executable equality and reauthor every source judgment after runtime repair.
   Simple validation, but repeated source interpretation adds operator and authoring work
   without changing its premises. It also discourages fixing discovered implementation defects.
2. Copy passes, retag IDs or silently treat references as if authored under the successor.
   Rejected: this loses original custody and misstates authoring and comparison identities.
3. Retain immutable references and explicitly compare them with compatible successor predictions.
   Selected: a narrowly owned comparison projection adds source correspondence work at evaluation,
   reusing admitted products, archived declarations, existing readers and the protected store.
   It avoids repeated parsing/model source work and an independent compatibility registry.

The selected route requires Python/native consumers to agree on correspondence and correctness.
That integration burden buys truthful original provenance and practical iteration. It makes no
performance or capacity claim. Missing or ambiguous correspondence remains a concrete refusal,
not a reason to weaken reference coverage or silently drop units.

## Decision


### Sealed interpretation and reusable preparation

A declared upstream annotation method seals source/profile-bound annotation products through
existing SourceObservationBatch custody. Candidate extraction consumes admitted upstream products
through owned reads. Annotation reuse must bind its actual source/profile/operation inputs,
including relevant spaCy/model libraries, while retaining native source/release and upstream custody.
Use one native operation-dependency projection for orchestration task hashing, Python twin
selection and native origin validation. Scope both declared preparatory operations:
`extract.m1_annotations` binds its source/profile/configuration and linguistic libraries;
`extract.m1_candidates` additionally binds its model/checkpoint, raw pack/context/assembly
configuration and upstream annotation operation. Full release/source/realization identities,
unknown manifest keys and complete immutable run provenance remain significant. Other methods
retain full-binding defaults. Unconsumed downstream scoring/calibration, unrelated policies and
guidelines do not force either preparatory operation to repeat.

`resolve.m1_readings` consumes the exact sealed raw extraction product through the existing
same-view product task edge. It binds finite feature parameters, recomputes interpretation identity
before feature extraction and seals the declared final-event score. Calibration and thresholds
remain outside its producer configuration. Runtime parameter JSON supplies features and protected
acceptance bindings without editing release declarations or source-only reference contracts.
One resolution configuration binds one coherent subset. The independent baseline replays the
finite parameter calculation in Python and native admission/calibration; a future coupled score
needs its own declared native transform and the existing benefit comparison.

Keeping model extraction and scoring in one task would be simpler locally, but every fitted
instance would repeat CPU model work. Splitting them reuses existing owned source products and
keeps expensive extraction stable while preserving exact invalidation of actual inputs. There
is no second cache, scheduler or observation store.
There is no mutable global Doc/context cache or
independent annotation store. Context widening retains exact related-source pins, typed relations,
budgets and unsuccessful retrieval dependencies.

Run bounded interpretation over reconciled candidates before sealing their private task result.
Retain the actual decisions/universe, factors, constraints, dependence groups, dependencies,
limits, numerical outcome and whole-record event scores. Private standing stays candidate.
A changed countercandidate, context, ontology or fitted feature instance recomputes the affected
component through ordinary task dependencies; it never amends an earlier completed cut.

### Source-reading graph meaning and public admission

Use five scoped source-reading graph classes beneath an ordinary `SourceReading` entity:
DefinitionReading, QualifiedAssertionReading, MeasurementReading, TableAssertionReading and
FormulaContextReading. Their role correspondence is mechanically derived from the same effective
family declarations, rather than a separately authored family schema. Reading identity binds the
release, record occurrence and interpretation, with no global label merge.

Each role yields a declared source-reading predicate with an inlined graph-safe stateful value.
Use the existing field state/kind and domain classification vocabularies; retain literal text,
exact decimal lexical spelling, ordered pieces, native pointers and transformation information.
Nonpresent roles assert their reading state, not an invented scientific value. These graph values
have no SourceRecordProduct ancestry and introduce no general graph regex engine. Author polarity,
modality, conditions and scope remain reading fields. The graph assertion that a reading has a
particular field uses explicit core assertion qualification; it does not assert the underlying
scientific proposition. Mapping a reading into mathematical entities is a separate future adapter.

Prepare field assertions outside the publication transaction. The existing domain-policy result
carries whole-record admission alongside ordinary fact selections. Ordinary rule success cannot
upgrade a provisional record; every record-produced fact is capped by its record admission.
Acceptance requires complete released role/evidence obligations and the evaluated applicable
family policy or validated deterministic proof witnesses. An exact enumerator is not such a proof.

Public record projection applies an explicit admission overlay to immutable private interpretations.
Native reconstruction checks the allowed overlay, exact policy instance and complete assertion
membership. Extend finite linkage from record/interpretation to assertion fact, source occurrence,
field and evidence sets. Source support authenticates origin task → sealed record → field/set →
anchor directly; no fabricated Agent batch, observation ID or citation is permitted. Existing
attribute-specific evidence guards and private-product graph fences remain enforced.

`consolidate_cut` remains the sole public boundary. Source publication, finite inference and terminal
run settlement remain atomic. A failed record cannot publish successful individual fields as an
accepted whole record. Candidate/rejected/limited dispositions remain queryable and exportable.

### Fitted instance and calibration authority

The release owns the algorithm/feature/parameter contract. Canonical immutable run dependencies
carry one typed `record_acceptance` instance: algorithm version, family/subset applicability,
feature signature, finite parameters, calibration map/standing, thresholds, conditioning assumptions,
training/evaluation provenance and content digest. Algorithm policy version remains distinct from
instance digest. Configuration alone grants no evaluated standing.

The `statistics-reading-occurrence-2` policy distinguishes decoder group anchors from occurrence
identity. Definition uses primary term and defining-clause anchors; assertion uses primary subject,
predicate and object; measurement uses primary referent, property and original value; table uses
its native table and data-cell identities. Required unavailable primary locations remain unresolved.
Compatible clauses sharing a predicate or numeric string therefore retain separate occurrences.
Formula binding occurrence uses `formula-symbol-first-use-1`: the complete primary formula
anchor plus its first exact primary use of the declared symbol. Related declaration anchors
supply evidence only. Compatible distinct bindings have distinct records; conflicting readings
of one binding remain alternatives. A formula-only record is reserved for no explicit binding.
Unlocated or ambiguous bindings remain unresolved coverage, never fabricated anchors. Existing
anchor-membership identity and one accepted interpretation per occurrence remain unchanged.

Use regularized grouped feature fitting through scikit-learn LogisticRegression, retaining the
finite coefficients/intercept and the declared feature order rather than a pickled executable.
These are supervised binary full-reading correctness scores, not structured-likelihood fits.
Any interpreter use treats them as declared compatibility potentials, without an LLR or independent
vote claim. Production coupling requires the M1-09 fixed-universe benefit comparison; merely
exercising a template does not authorize its factors. Calibrate the whole-record event after
constraints/coupling rather than relabelling prefit field confidence.
A separately fitted final-event sigmoid map consumes held-out final-event scores; its assumptions,
class support, convergence and diagnostics remain explicit. Numerical fitting is not a quality
certificate. Insufficient labels retain provisional standing and cannot license acceptance.

Feature fitting consumes only the existing protected feature-fit route. Do not widen that principal
to calibration or final assessment. A narrow evaluator-authorized calibration operation consumes a
frozen feature-instance digest and final_event_calibration references. Fit a predeclared complete
eligible/scored event frame, including low-score and unaccepted candidates, with no-output/source
coverage accounted separately. Do not derive calibration solely from accepted publication selections.
Native custody binds the exact frozen candidate/score membership; independent evaluator readings
establish whole-reading correctness. Its typed product extends the
released record evaluation report and uses existing immutable `eval.reference_evaluation` result,
reference snapshot and content digest. Native validation checks actual partition, completed
prediction/source closure, frozen feature instance, finite parameters, algorithm/family contract,
threshold procedure and parameter digest. Ordinary grading keeps its limited quality claim.

Production receives parameters and evidence identities, never labels. Native run admission and
publication check the exact evaluator-authorized instance. Final grading verifies the frozen
instance as well as algorithm version. Freeze the authoring release and exact source frames before A/B/C. Preserve those immutable
identities when a compatible implementation successor is evaluated as specified below. Freeze
feature parameters before calibration and the calibrated instance/thresholds before final assessment.
No implicit reference relocation or old-release payload rebinding is introduced.

### Reference applicability across implementation successors

Original reference sets, source-ready cuts, frames, passes, authored bytes, origin assignments,
record/interpretation identities and content digests remain immutable under their authoring
release. A new evaluation binds both that reference release and the actual completed prediction
release/run/cut. It never executes a predecessor or copies/rebinds an authored payload.

The supported strict source-occurrence comparison contract determines applicability. Compare
the exact consumed family/role/value/state/requiredness/occurrence and source-coordinate
declarations, frozen guideline text/digest and policy versions, with a named supported comparison
semantic version. Changes to those premises require new applicable references or an explicitly
revised comparison contract; equality of arbitrary version strings alone grants no compatibility.
Unrelated execution implementation bytes need not match. The trusted current comparison
implementation remains responsible for the supported semantics and independent expectations.

For each primary and related reference view, require exactly one view selected by the actual
prediction run with identical retained native product task/key/digest, document/content custody,
placement/section/membership/analysis eligibility, recipe and complete physical projection.
Validate each side with its own release/run/coordinates. Require a bijection over the frozen
source closure, retain empty/no-output units, and refuse missing, ambiguous or changed sources.
New view IDs, keys and logical aliases appear in explicit correspondence alongside original
identities. They never replace the frame's original values.

Only after independent validation derive comparison-only anchor, evidence-set and occurrence
keys from the authenticated physical correspondence. Preserve precision, coordinate space, native
pointer, extents, source spelling, recognition and binding semantics; compare fields with the
existing strict meaning rules. Original literal piece sequences remain exact. Preserve both
original record/interpretation IDs in matches and diagnostics, and retain the one accepted
interpretation per occurrence rule. No new production record identity or paraphrase equivalence
is introduced.

Grading, native gap evidence, complete policy-event frames and full-reading correctness must
consume that same correspondence. The evaluation store/snapshot remains the authority. Feature
and calibration products bind the actual prediction release/candidate universe and comparison
provenance. Changed prediction code still requires new predictions and affected fitting and
calibration; no old accepted instance inherits applicability from compatible source references.

## Consequences

Implementation can improve while unchanged source judgments retain their truthful original
provenance. Source/semantic/comparison changes remain visible applicability boundaries rather
than incidental runtime equality. The existing reference store and operation principals retain
their roles; no pass-copy API, generic compatibility registry or new review gate is introduced.

**Accepted target, Proposed implementation (2026-11-04).** Python/native correspondence,
generated reports, protected fitting/admission and same-/cross-release refusal controls remain
to be implemented and verified. The [M1 coordinator](../plans/first-production-milestone_2026-11-03.md)
owns F24 and all unchanged quality/resource/release obligations. Existing references/grades
retain their actual frozen contracts until the compatible successor path is implemented.

## Amendments

2026-11-04 — Changed-boundary review clarified the unchanged source-scope obligation:
correspondence preserves the original frozen anchor allowlist and scope extents. For anchor-only
frames, derive a counterpart reference anchor identity from the authenticated prediction
descriptor and exact source correspondence solely for membership comparison. An anchor need not
occur in an authored record; never widen the frame to a whole corresponding view. The required
bijection covers the frozen closure, not unrelated additional selected prediction views. This
clarifies the existing immutable-frame decision and introduces no broader compatibility claim.
