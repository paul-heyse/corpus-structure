---
id: ADR-0002
title: Review architecture through change scenarios and a repository-owned design standard
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§2]
evidence: Implemented
revisit: Reviews miss concrete change-propagation or isolated-testing defects, prescribe abstractions without a credible consumer, or duplicate current finding status across artifacts.
---

## Context

Correct local slices can accumulate architectural problems without a system-level decision. The
template carries a layered design standard (core 3.3): seven foundations, four architectural
judgments and independent correctness/fidelity gates, applied through a
repository binding that owns review cadence and finding disposition.

## Options

1. **Ad-hoc review**: cheapest, but depth and cadence drift and findings lose their owner.
2. **A shared standard synchronized across repositories**: no canonical upstream or update
   contract exists.
3. **Own a copy of the standard here, bound to this repository** (chosen); template updates
   arrive through `copier update` as reviewed diffs.

## Decision

- This repository owns core 3.3 and the review template; `standard.toml` declares versions,
  paths, profiles and the binding.
- FP-01–FP-07 organize assessment. A1–A4 judge change locality, domain meaning,
  composition and qualitative execution-fit assessment independently of the DP/G gates and the code-intelligence profile's CI gates.
- A concrete expected change exposing duplicated decisions, unrelated internals or inseparable
  tests can require revision even when behavior is correct. A supported workload with unjustified
  amplification or a predictably unsuitable physical route can also require revision, using static
  evidence where sufficient. Quantitative speed/capacity claims still need measurements.
- Compare access paths, necessary work, composed library capabilities, locality, working sets,
  reuse, assurance placement, lifecycle/recovery and total machinery against functional intent.
  Semantic ownership does not prescribe physical granularity; safe refusal alone is not fit.
- Reviews are grounded only in the standard and the functional target. ADRs, binding policies
  and other rules are current design: a review lists the rules its recommendations would change,
  and they change only after the operator confirms them in plan creation.
- The binding owns cadence: design/target reviews before substantial stages or §B changes,
  change/target reviews for bounded slices, design/target at integrated stage ends. Effort
  follows risk. Reviews run through a fresh `design-reviewer` subagent, so the author of a change
  is not its reviewer.
- Reviews preserve dated findings. One active plan table owns current execution disposition;
  unscheduled deferrals stay in the source review with a trigger. An accepted decision is
  distinct from implemented and verified closure. No new register, hook or check runner.

## Consequences

Architecture can receive a Revise judgment independently of a correctly implemented slice.
Reviewers need scenario evidence and component ownership, not a fixed amount of prose or probes.
Improved maintainability remains **Proposed** until exercised by actual changes.
