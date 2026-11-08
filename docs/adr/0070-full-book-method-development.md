---
id: ADR-0070
title: Use the whole Grinstead–Snell book for method development
status: accepted
date: 2026-11-07
supersedes: [ADR-0068]
superseded-by: null
design: [§B1, §B5]
evidence: Proposed
revisit: The full-book benchmark is structured well enough that unseen-source generalization becomes the next practical question.
---

## Context

The operator expanded the existing Grinstead–Snell method-development benchmark
from physical pages 191–310 to the whole book. The additional chapters expose
more structural forms and cross-chapter relationships for diagnosis. The original
parent has 518 physical pages and SHA-256
`763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`.

## Options

1. Keep the 120-page window. It provides inexpensive repeatable controls and
   narrower evidence about layout, terminology and relationships.
2. Process the full parent as one native document, then batch downstream work
   by its natural source scope. This preserves the book hierarchy and lets
   section-level work and reads stay bounded.
3. Convert independent page ranges. This bounds conversion attempts at the cost
   of disjoint native identity and lost document-wide organization.

## Decision

Use physical pages 1–518 as one shared source for development, fitting, debugging,
regression and repeated assessment. Preserve original source custody, exact page
coverage and prior exposure. Convert the authenticated whole parent as one
native product and bound later work and delivery by exact selected scope. Keep
the original 120-page runs and evidence at their recorded extent.

Keep ADR-0067's current-only producer and consumer migration. Regenerate
insufficient derived data, preserve authenticated historical products and
receipts, and keep source-side opportunities separate from output assessments.
In-sample event fitting retains independent label and numerical requirements
and remains separate from public eligibility.

## Consequences

The full book enlarges the diagnostic population and preserves its one exposed
origin. Separate calibration and unseen-origin performance remain later questions.
The [NCE coordinator](../plans/next-corpus-enrichment_2026-11-07.md) owns current
execution and qualification. The [WCE coordinator](../plans/witnessed-corpus-enrichment_2026-11-05.md)
continues to own its historical 120-page implementation and evidence.
