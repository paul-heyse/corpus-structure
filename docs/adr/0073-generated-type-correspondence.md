---
id: ADR-0073
title: Derive static relational types from explicit semantic correspondence
status: accepted
date: 2026-11-09
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
---

## Context

PTD-01 and functional opportunity O01 require selected Core columns, calls and companion
results to preserve released semantic distinctions. Operation calls already declare nominal
anchors; primitive-only column rendering loses those distinctions. Some model fields lack a
value-source projection even though their identifier correspondence is known.

## Options

1. Keep primitive columns and hand-annotate consumers. This is locally simple but duplicates
semantic knowledge and makes declaration changes propagate inconsistently.
2. Reuse `cp:source` for every type correspondence. Its value-projection semantics can replace
local constraints and create inherited self-references where only a type correspondence exists.
3. Resolve explicit semantic correspondences once and supply the same facts to every selected
renderer. This adds a narrow annotation but keeps semantic ownership and consumer evolution together.

## Decision

Choose option 3. Existing execution-call semantic identifiers remain nominal naming authority.
`cp:type_source` is an explicit qualified type correspondence; it does not redirect the local
value projection or replace local nullability, representation, defaults or constraints. Reject
cycles, incompatible representations and conflicting anchors. Generic fields remain generic.

Generate selected calls, columns and companion materializers from shared resolved facts. Use
SQLAlchemy Named/TypedColumns/with_cols and narrowed protocols; retain existing Core objects.
NewType and these static surfaces do not establish runtime nominal or general SQL-operator
validation. Existing runtime constraints and SQL/JSON null distinctions remain authoritative.

Typed artifact identity includes semantic, physical and renderer determinants. Preserve the
existing runtime identity policy; relevant model bytes can legitimately change source identities.

## Consequences

The selected workload gains declaration-driven distinctions without per-row hydration or a second
identifier registry. Runtime validation and native admission keep their existing responsibilities.
Generation must reject contradictory correspondences and migrate affected callers together.
Implementation and qualification are owned by [PTD-01](../plans/postgresql-typed-domain_2026-11-09.md#PTD-01);
acceptance of this decision alone does not close O01. Revisit if a required consumer cannot be
expressed through an explicit compatible correspondence or needs runtime nominal validation.
