---
id: ADR-0090
title: Persist source operation lineage in native run options
status: accepted
date: 2026-11-12
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A supported operation must span independently authorized application invocations or needs mutable durable state beyond its existing native runs.
---

## Context

BEP-E13 requires existing status/result reports to distinguish actual operation capture, primary
characterization, analysis and settled views. Original source pins identify their original producer.
A new capture can reuse those pins; a current demand can reuse a view produced by an older demand.
Neither source origin nor final product ownership therefore identifies all runs in the current
application operation. Reporting a guessed grouping would misrepresent native execution.

ADR-0088 selects the explicit source application contract and ADR-0089 preserves notification and
logging custody. [BEP's findings table](../plans/book-processing-efficiency-and-parallelism_2026-11-11.md#execution-findings)
owns delivery and qualification. This decision establishes the missing lineage meaning, not another
progress store or a change to original-product/task identity.

## Options

1. Infer operation membership from product/source origins. This needs no new field but merges
   distinct invocations when products are reused and cannot identify a current capture.
2. Keep grouping only in managed CLI results. This works while that receipt exists, but omits
   direct Python callers, interrupted work before final delivery and retained native status.
3. Add one explicit operation link to existing immutable native run options (selected). The
   application supplies the same identifier to actual participating runs at creation; existing
   native queries can join it without another lifecycle owner or cross-store atomicity claim.
4. Create a mutable operation table and coordinator record. That could support independently
   resumed multi-invocation workflows, but this invocation-owned composition has no such consumer.
   It adds settlement and recovery responsibility unnecessarily.

## Decision

**Proposed accepted target · 2026-11-12; implementation/qualification tracked by BEP.**
A typed versioned SourceOperationLink records one UUID, a capture/primary/analytical role and the
actual capture run when known. The application creates the UUID once, outside serialized request
intent and semantic determinants. Native capture, every actual primary child and analytics carry
that same operation identity in existing immutable run options. SourceOperationResult exposes it.
No fabricated control run or mutable registry is created. Ordinary native task/claim/publication
and supervisor authority remain with their existing owners.

CharacterizationOperation keeps this link separately from its frozen semantic demand. A new
standalone primary demand can own an operation identity while actual capture association is unknown.
Recovery carries an existing anchor's recorded link exactly; historical missing associations stay
unknown. Do not retrofit identity into old records or infer current capture from original custody.
Readers scope joins by recorded operation, project and semantic release; original producer pins
and their provenance remain distinct from current invocation membership.

General source-run options carry operation metadata and characterization anchor/region/stage
metadata together. They do not choose workflow, replace typed application intent, or confer effects.
Existing reports expose capture, regional/family and final-view readiness separately, retaining
bounded detail and explicit unknown/unavailable activity where native state does not establish it.
An absent observation or expired managed receipt never proves absent provider work.

## Consequences

FP-01/04/05 and H19/H22 favor explicit operation meaning at native creation over reconstructing it
from incidental producers or duplicating progress custody. This adds a small immutable link per
actual run and a bounded report read over native runs; it needs no new table or separate store. Protected metadata-reader extensions use the normal forward routine revision.
The functional requirement is honest native operation reporting, not runtime cost accounting.

New links cover newly created runs only. Historical anchors still support their recorded child
aggregate with unknown enclosing capture/analysis association. Durable independent workflow
resumption would reopen the decision. Implementation, actual native lineage/report checks and
assembled qualification remain open in BEP-E13; accepted rationale alone closes no finding.
