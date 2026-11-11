---
id: ADR-0082
title: Select active analyses independently of retained dependency closure
status: accepted
date: 2026-11-11
supersedes: []
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A consumer requires selecting different interpretation revisions for different source regions within one layer.
---

## Context

TC-03–09 execution exposed a distinction within ADR-0081's immutable enriched-document
contract. Reusing raw contextual provider observations after a rule change requires retaining
their original layer and dependencies. Selecting all those dependencies as current interpretations
would also select obsolete hypotheses. Re-running the providers avoids that ambiguity but defeats
the accepted separation of inference and pure interpretation. D1 owns selection meaning, D6 the
frozen execution inputs and D8 live/detached reads. The TC coordinator owns implementation acceptance.

## Options

1. Treat every dependency as selected analysis. This is the smallest representation, but
   confuses cited evidence with adopted meaning and combines incompatible rule revisions.
2. Exclude dependencies from the view. This simplifies selection but loses the explicit original
   closure needed by validation and portable replay, or forces a second closure inventory.
3. Retain the complete closure and select active layers explicitly within the same immutable
   view (selected). One additional pin subset preserves provenance and permits ordinary indexed
   readers and existing method configurations to select the appropriate analytical population.

## Decision

**Proposed accepted target.** `EnrichedDocumentView.layers` retains the complete dependency
closure. `active_layers` selects the analytical population from that closure; it contains distinct
exact pins and is nonempty for analytical views. Coverage is supported by active layers. Archived
views without this field retain their original all-layers selection meaning under their own
released contract. No mutable latest selection or implicit winner by producer timestamp is added.

Consumer binding freezes active pins into existing `characterization_layers` configurations.
Default annotation/term/membership reads use active layers; explicit layer inspection may inspect
provenance dependencies. Export preserves the full closure. Validation may traverse dependencies
without using their interpretations as model candidates or evaluator context.

A new demand replaces a producer's previous active output only after obtaining its exact
configuration-matching result. It retains dependencies separately. Pure contextual refreshes may
select original raw provider layers through a separate frozen evidence port, with exact source,
token population, provider/runtime/artifact, language, device and focal-context correspondence.
Current hypotheses are generated from explicitly selected semantic inputs, never from all cited
raw-layer dependencies. Multiple rival compatible populations require explicit selection.

## Consequences

FP-01/02/04 and CI-02/04 favor explicit selection authority. H12/13/19 favor reusing unchanged
provider evidence while recomputing affected interpretation. The additional pin subset reaches
composition, native enforcement, reader selection, detached replay and execution configuration;
that bounded integration is preferable to a parallel selection service or repeated inference.
No performance magnitude is claimed. Full-profile production remains bounded by natural source
units; this decision adds no scheduler or per-annotation lifecycle.

Implementation is in progress on2026-11-11; focused composition/context/inspection tests passed25
cases in `eebb9ce8b09543fbbf9b40485b7313e1`. Native and integrated acceptance remain open in the
[TC coordinator](../plans/text-characterization_2026-11-10.md). Acceptance records the decision,
not completed implementation or qualification.
