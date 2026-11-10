---
id: ADR-0075
title: Inspect immutable release products through one shared read boundary
status: accepted
date: 2026-11-10
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
---

## Context

DMC-01/02 need to explain effective model constraints and their authored contributors through
CLI, MCP and retained model candidates. Normalized definitions omit authorship; recompiling
current sources during a historical read would invent provenance. D2 owns preparation and D8
owns transport. The domain-data-model coordinator owns delivery and verification.

## Options

1. Parse current schema files on demand. This is simple but changes historical meaning, repeats
preparation and cannot authenticate the source contributing to an archived release.
2. Make provenance another editable model or reproduce contextual induction in the explorer.
This duplicates semantic authority and requires consumers to reconcile competing definitions.
3. Retain compact declaration references during the existing preparation pass, and compose
those references with immutable effective products through one domain reader. This preserves
source custody and amortizes preparation without requiring a general source-map service.

## Decision

Select option3. Preparation emits version1 `inspection/effective-model.json` through the existing
artifact path. Source references promise supplied module, logical YAML path and source digest;
contributors carry roles and unresolved attribution rather than invented winning locations.
Definitions, boundary recipes and operation products retain executable authority. Semantic
compiler20 distinguishes the new producing contract; archive3 and boundary ABI12 remain intact.
Older readable products expose available effective facts and unavailable new provenance.

One trusted model-bound report serves CLI and read-only MCP. Candidate authoring additionally
retains a digest-bound managed capsule of the existing archive3 products and exact inputs.
Database and detached readers share complete archive authentication before hydration. A capsule
is an inspection delivery container, never another admission mechanism. §B5 authority is unchanged.

## Consequences

Small reads reuse prepared products and demand-built boundary adapters. Retention costs a compact
metadata artifact and, for actual retained candidate inspection, one complete managed capsule.
That copy permits useful inspection after the checkout changes without database publication.
No native migration is required solely by metadata, and execution still needs exact current
preview/admission. Revisit if a real consumer needs exact source-line coordinates or a materially
different archive ABI. Implementation and scoped acceptance are tracked in
[the DMC coordinator](../plans/domain-data-model_2026-11-10.md); acceptance of this decision does
not close its packages.
