---
id: ADR-0086
title: Run current D1 characterization on CUDA with explicit BF16 provenance
status: accepted
date: 2026-11-11
supersedes: []
superseded-by: null
design: [§B1, §B2, §B5]
evidence: Proposed
revisit: The required CUDA/BF16 runtime or custody cannot qualify actual D1 work, or another explicitly selected inference profile is required.
---

## Context

The operator explicitly directed D1 always to use CUDA as its default/current execution route,
with no CPU fallback. This replaces the tentative uncommitted600second CPU deadline correction
following two actual120second D1 inference timeouts in the captured-prose integration attempt.
Those CPU failures remain diagnostic evidence; neither longer deadlines nor CPU batch panels
establish CUDA qualification. Scoped D1 CUDA qualification is authorized now within BEP-04–06
and the necessary07a slice. Other CUDA/provider/final-count investigations remain with07b.

The existing native D1 loader selects torch.bfloat16 for CUDA and checks BF16 support. Thus this
is a result-affecting device/precision profile, not an invisible placement optimization. ADR-0084
requires such profiles to have truthful identity and actual qualification. ADR-0085 defines
qualified native numerical observation semantics; its CPU evidence remains scoped to its original
profile and supports neither CPU/GPU equivalence nor CUDA passage. The
[ready-execution review](../design_review/reviews/design_review_book-ready-coordination_2026-11-11.md#required-d1-cuda-bf16-target)
owns the bounded target judgment; the [BEP coordinator](../plans/book-processing-efficiency-and-parallelism_2026-11-11.md)
owns implementation, actual evidence and remaining obligations.

## Options

1. Keep CPU D1 and extend its deadline. This preserves the former device but conflicts with the
   operator's current requirement and does not establish practical completion merely by allowing
   more waiting. The tentative600second branch is not selected.
2. Prefer CUDA but fall back silently to CPU. This obscures precision/runtime provenance and
   can restore the original execution-fit problem while presenting the wrong profile.
3. Require CUDA/BF16 for all current D1 authoring/execution and qualify that exact profile
   (selected). It uses the available native loader/device-custody mechanisms and makes missing
   prerequisites explicit. Historical authentic CPU observations remain readable as CPU evidence.

## Decision

**Proposed accepted target.** Current D1 defaults and authoring interfaces select CUDA only.
Current native admission/loader paths reject CPU selection, missing CUDA or unavailable BF16
support before inference; no implicit CPU fallback or extended CPU-timeout route remains.
Standalone/current managed D1 operations follow the same rule. Historical read-only CPU products
retain original provenance and contracts; they are not rewritten or treated as CUDA results.

The selected D1 inference profile is CUDA bfloat16 under the exact frozen runtime/artifacts/model,
source context, offered questions/candidates and supported native batch policy. Device/precision
is reflected in current configuration/released provider policy, request/resident compatibility and
actual startup/model metadata. Validate executed CUDA/BF16 correspondence, not merely a requested
device string. Runtime-only code provenance cannot substitute for the released inference profile.

Release-owned batch numerical policy is provider/device scoped: GLiNER's selected CPU profile
retains float32 semantics while current D1 declares CUDA/BF16 explicitly. Keep this policy outside
native API inference kwargs. Both preserve unrounded actual scores, unchanged thresholds, actual
batch/member provenance and honest numerical nondeterminism, including possible threshold/tie
selection changes. No universal epsilon, byte-reproducibility or CPU/GPU output-equivalence promise
is introduced. Changed policies/affected operations retain their explicit version/identity route;
old authentic contracts remain readable without retroactive equivalence claims.

Use existing explicit GPU/device custody and its persistent lane owner. Acquisition may suspend
the existing Nemotron resident through the established handoff; stop/teardown must restore custody
under that same owner, including cancellation and startup failure. Preserve one active native
exchange, bounded pending state, exact member attribution, fast active checks, claim renewal and
native settlement. Keep supported D1 set attention/set_size16 and complete original contexts;
no smaller request, rounding, retry policy or new scheduler is selected to mask a failure.

Actual scoped CUDA qualification must establish hardware/runtime/BF16 support, executed metadata,
source-aligned current question/batch behavior, member attribution and required custody/lifecycle
plus DB-backed integration obligations. CPU receipts do not satisfy those checks. The coordinator
may use focused current D1 cases; this decision does not initiate an unrelated provider-wide CUDA
campaign. Missing prerequisites remain explicit failures/blocks rather than successful empty
coverage or CPU fallback.

## Consequences

The current D1 route has one selected execution profile with truthful precision/provenance and
available GPU acceleration. GPU custody and profile-specific actual evidence become immediate
obligations. The speculative600second CPU policy is removed; original timeout attempts remain
unchanged diagnostic records. Existing operation boundaries, exact source, private proposal
standing, native task fences and historical CPU read obligations remain.

Acceptance records the operator-selected target, not actual CUDA implementation/qualification,
performance or full-book completion. It extends ADR-0084/0085 with the current selected profile
without editing their accepted records or retroactively broadening their evidence. The separate
run610 publication-size limit, other07b device choices, final counts and BEP-09 remain open.
