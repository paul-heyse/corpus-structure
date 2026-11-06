---
id: ADR-0068
title: Develop and assess corpus structuring on one shared Grinstead–Snell corpus
status: accepted
date: 2026-11-06
supersedes: []
superseded-by: null
design: [§B1, §B5]
evidence: Proposed
revisit: The shared corpus is structured well enough that unseen-source generalization becomes the next practical question.
---

## Context

The operator explicitly replaced separate-book development/fitting/calibration/assessment with
one shared120-page Grinstead–Snell method-development benchmark. The purpose is to establish a
working progressively structured representation, diagnose missing and incorrect distinctions and
relationships, and improve the method. WCE04–05 are delivered; WCE02/06–12 remain implementation
and assessment work. Current test-resolution is complete, independently of WCE qualification.

## Options

1. Shared corpus for construction, fitting, debugging and repeated assessment. This gives direct
   comparisons on the same source opportunities and localizes topic/layout variation.
2. Separate source families and held-out cohorts now. This estimates a different question and
   fragments the available evidence before a working structuring method is established.
3. Wait for complete records before measuring. This hides useful components and failure stages.

## Decision

Use Grinstead–Snell physical191–310 inclusive as one120-page corpus, including the known
normal-density slice. Development, regression, fitting and assessment are activities over this
same population. Existing development/feature-fit custody is appropriate; create no held-out
or independent-origin prerequisite for this mode. Preserve exact sources and prior exposure.
Operation-event fitting is in-sample diagnosis, separate from whole-record algorithms and public
eligibility; numerical validity and genuine class requirements still apply. Scores do not establish
source truth. Assess source-side opportunities and retained output facets separately, including
no-output regions and downstream failures. Obtain an early actual baseline and iterate on its
observed failure mechanisms; final full-scope qualification follows implementation.

Extend ADR-0067's current-only migration to the remaining WCE scope: remove replaced production
bridges, protocols, historical decoders and duplicate semantic paths after replacement verification.
Retain meaningful controls on current contracts, authenticated sources, plans and immutable evidence.
Regenerate insufficient derived data instead of inventing missing evidence.

## Consequences

The shared benchmark establishes observed method behavior on these pages, not generalization.
Group-held-out studies and separate calibration populations are later questions, not readiness gates.
Fitting cannot block useful source-grounded construction. Each operation declares its added structure,
source basis and unavailable/failed/limited outcomes. Original provenance stays distinct from meaning.

The existing WCE coordinator owns current package and finding disposition. This ADR adopts the
operator's decision; it establishes no new implementation, provider or assessment pass. Remaining
contracts, source preparation, actual baseline, independent references, implementation and final
qualification are still required.
