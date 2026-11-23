---
id: ADR-0155
title: Select PDF capture and recognition custody independently
status: accepted
date: 2026-11-23
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A producer cannot establish its selected execution or an authentic policy remap changes the request identity of an upstream producer whose determining inputs stayed equal.
---

## Context

The Integrated PDF route composes original capture, recognition observations and reconciliation.
Its policy-only remap reran the first two operations. The current release gives all PDF producers
one lowering identity. The generic capture and recognition code inventories have unresolved
executable dependencies, which correctly makes their request identities demand-local. The
operator brought these producer custody prerequisites forward through SBX-09.

[Integrated qualification](../plans/set-based-execution/cutover-and-qualification.md#sbx-columnar-implementation) ·
[Selected executable and material reuse](../plans/domain-model-operability/execution-identity-and-recovery.md)

## Options

A closed Integrated producer could establish exact executable custody for the whole route.
It would include capture, recognition and reconciliation resources in one acquisition.
Changes to reconciliation would have a larger acquisition footprint, and capture reuse would
still require a projection of the actual upstream determinants.

The selected Standard capture already owns a guarded raw producer. Compose that producer with
an independently acquired recognition operation and the existing downstream transformations.
This requires the release and the publication guard to identify the producing scope. It allows
the three operations to retain their present physical owners and evaluate reuse independently.

## Decision

The PDF facet archives the shared record schemas, codecs and helper contracts once. It may
also archive the Standard capture lowering beside the generic transformed-publication
lowering. The capture port selects its own archived producer. PostgreSQL independently
resolves the lowering from the exact producing task and declared operation and verifies the
certificate against the producing release. Historical replay selects the archived lowering
committed by the sealed publication receipt.

Recognition owns its separately acquired executable, renderer, worker, provider resource and
recipe commitments. It retains the authenticated capture episode and exact observation receipt.
Reuse requires complete custody for the selected operation. Capture and recognition can retain
their request identities across an Integrated policy-only change when their inputs and acquired
execution still correspond. Current support, generation, withdrawal and effect checks retain
their existing authority.

## Consequences

The native publication and spool routines select a lowering by producing scope using the
existing task and request relations. Storage tables and shared PDF output meaning stay under
their current owners. Each acquired producer needs functional qualification of its exact
execution or a scoped refusal. The policy remap and historical withdrawal journeys exercise
the composed result. Full PDF certification and replay improvements remain with their
existing later packages.
