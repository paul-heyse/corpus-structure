---
id: ADR-0085
title: Retain authentic native batch observations under explicit numerical semantics
status: accepted
date: 2026-11-11
supersedes: []
superseded-by: null
design: [§B1, §B2, §B5]
evidence: Proposed
revisit: A supported consumer requires byte-reproducible fresh inference or stronger threshold stability, or actual production-pack qualification reveals an attribution or inference-contract failure.
---

## Context

ADR-0084 requires BEP-06-I3 to choose a truthful inference-identity rule before cross-region
batching. The [actual CPU panel](../design_review/evidence/2026-11-11_book-provider-batches/README.md)
retains three original contexts requested singly, mixed, reordered and regrouped. In this bounded
panel HanLP/D1 responses were exact; GLiNER retained labels/text/extents/cardinality while native
confidence changed by up to2.384185791015625e-7. The panel uses a statistic-entity schema, not the
complete production cue/classification packs, and supplies no universal equivalence or threshold
stability guarantee. Actual production-pack qualification remains required before cutover.

GLiNER confidence is native probabilistic evidence, not calibrated truth or a bitwise-repeatable
scientific quantity. Existing classification selects using the actual returned unrounded score
against the declared threshold; retained proposals remain private. The project has established no
bitwise reproducibility promise for fresh native inference. I3 therefore requires a consequential
precision/determinism contract choice rather than automatic byte equality. This selection falls
within approved RC04/I3; no additional operator rule reversal is introduced. The
[ready-coordination review](../design_review/reviews/design_review_book-ready-coordination_2026-11-11.md#qualified-native-numerical-semantics)
owns the independent judgment; the [BEP coordinator](../plans/book-processing-efficiency-and-parallelism_2026-11-11.md)
owns actual qualification and remaining work.

## Options

1. Declare qualified native-float32 batched observation semantics and preserve exact actual
   responses plus batch provenance (selected). Logical request identity includes the governing
   numerical/inference policy; actual grouping is authenticated computation provenance. This
   fits probabilistic evidence and preserves independent ready progress without promising an
   unsupported fresh-run equality guarantee.
2. Freeze exact cross-region cohorts before task registration. Cohort identity would become a
   logical determinant, coupling fast work to slow members and extending configuration/lifecycle
   coordination. It would establish which population ran, not numerical determinism by itself.
   Select this if a supported future contract actually requires that population as a determinant.
3. Use deterministic within-logical-task batching and leave cross-region GLiNER batching open.
   This is the fallback if production-pack qualification cannot establish the selected contract,
   but is unnecessary solely because a native confidence differs in its final floating digits.

## Decision

**Proposed accepted inference target.** The released CPU policy declares native float32 batching
with numerical nondeterminism. Retain every actual score without rounding or normalization and
retain the actual complete batch commitment, member ordinal/digest, raw answer and effective
profile. Keep original thresholds and apply them to the actual unrounded returned values.
Numerical nondeterminism may include a threshold/decoder-tie boundary changing selected labels or
spans. Do not promise invariant selections, universal closeness, a numerical epsilon or byte-equal
fresh inference across batching/order/regrouping.

The logical request means an admissible authentic observation under its exact source/context,
pack, options, artifacts/runtime/device and governing qualified inference policy. Reuse selects
an authentic retained observation satisfying that contract, not a forecast of the bytes a fresh
execution would produce. Its original actual batch provenance remains inspectable and is never
rewritten. Physical cohort membership is not an additional logical determinant within this
qualified policy. No cross-context leakage, source-coordinate reinterpretation or semantic
family/context omission is permitted by numerical nondeterminism.

Record this meaning explicitly in released model-observation policy, with affected producer and
operation versions under ADR-0084's migration route. It is not an invisible physical-setting
change. Authenticate that policy selection through batch header and effective runtime checks.
Historical v1 products retain original read-only meaning and acquire no retrospective numerical
or batching equivalence claim. Consumers continue using exact retained observations/pins.

Actual CPU cue and classification packs must qualify before coalescing cutover. Qualification
checks proper requested pack/options, exact member scatter/source positions, faithful raw-score
retention and threshold/reduction behavior, including mixed-size/reordered inputs and invalid
members. It cannot establish universal threshold stability. CUDA and changed device/precision
profiles require their own later qualification; this CPU decision does not extend to them.

## Consequences

Independent ready work need not acquire artificial cohort barriers to preserve truthful
probabilistic evidence. Exact stored scores, observed selected alternatives and batch provenance
remain reconstructible. Two authentic executions of one logical request can differ within the
declared native numerical contract; existing exact retained identity still distinguishes their
actual products. A consumer needing stronger reproducibility must ask for a stronger policy,
not treat retained raw confidence as a deterministic quantity.

The observed panel maximum is evidence only for that panel and never a global tolerance or new
acceptance threshold. No provider-family coverage, production-pack qualification, accuracy,
measured performance or full-book completion is claimed. If actual pack investigation exposes an
unsupported native path or attribution failure, do not label it numerical variation: repair it or
keep that provider's batching obligation open. ADR-0084's exact-cohort route remains available
outside this qualified contract. No source/family truncation, book restart, publication-limit
repair or protected-reference input is authorized.
