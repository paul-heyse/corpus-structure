---
id: ADR-0053
title: Use GPT-6.1 Sol for M1 reference authoring and adjudication
status: accepted
date: 2026-11-03
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
revisit: The selected Sol model is unavailable or cannot produce the released five-family reference contract.
---

## Context

The operator selected GPT-6.1 Sol instead of Claude Code for all M1 reference passes and
approved qualification through a nondefault release. M1 has a distinct source-record reference
protocol under ADR-0052. The legacy Sonnet/Claude author configuration in ADR-0011 remains a
historical/legacy protocol choice; M1 requires an explicit replacement profile.

## Options

1. Keep Claude authoring and use Sol only as adjudicator. Rejected by operator selection.
2. Replace the complete reference workflow and numerical scorer. Unnecessary: the existing
   source packets, immutable passes and deterministic evaluator already own these responsibilities.
3. Use fresh Sol A/B/C sessions through the existing reference lifecycle. Selected: changes
   model configuration and delivery adapters while retaining one reference and scoring authority.

## Decision

M1 source-record passes A, B and adjudication C use `gpt-6.1-sol` at high reasoning effort.
A and B receive the versioned source packet, guideline and released output contract in fresh
contexts. C receives source, both retained passes and their disagreement, and records reasons.
Record model, actor/session identity, exact submitted bytes and existing source/policy bindings.
The coordinator registers answers through the existing reference operations. Numerical grading
continues in the deterministic protected evaluator; Sol does not invent precision/recall results.

The operator trusts session independence. Add no special isolation infrastructure or independence
checks. Existing native reference/fitting contracts remain unchanged. M1 extraction remains the
CPU GLiNER route, with no general LLM extraction fallback. Legacy grades and authoring profiles
are not rewritten. Model unavailability is reported rather than silently substituting Claude.

M1 qualification uses at least 90% candidate capture, at least 97% accepted full-record precision,
a one-sided 95% lower bound of at least 95%, and at least 70% accepted full-record recall for each
of the five released supported subsets. Confidence methodology and source-group sufficiency are
frozen before final assessment; the descriptive ratio bootstrap is not a release certificate.
The operator permits additional suitable statistics sources when the local collection is insufficient.
The operator subsequently selected qualification of a frozen held-out cut. Freeze that finite source
population before final labels and keep source-origin separation from development/fitting/calibration.
Assess all source units, including no-output units, for recall/capture; precision may use a census or
a predeclared uniform sample without replacement from the complete finite accepted-record frame.
Exact hypergeometric test inversion supplies the latter's one-sided bound. Retain the numerical
targets unchanged. A census supplies the exact finite-cut precision; neither route establishes
unseen-origin performance. Group bootstrap remains descriptive and is not relabelled as this bound.

## Consequences

Reference preparation can proceed before successful extraction using existing source-only packets.
No second reference store, scorer or agent service is required. Actual Sol authoring/adjudication,
new entry-point integration, native grading and full release evidence remain M1-13/14 work.
Decision acceptance supplies no tested reference result, calibrated output or default adoption.
