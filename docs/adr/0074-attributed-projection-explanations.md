---
id: ADR-0074
title: Retain attributed projection occurrences and frozen model-change explanations
status: accepted
date: 2026-11-09
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
---

## Context

PTD-04/05/09 require useful explanations of value, membership and ordering dependencies and
candidate native changes. Existing analysis reduces dependencies to sets; SQLGlot lineage also
deduplicates equal expressions. Existing candidate inspection does not expose frozen operations.

## Options

1. Extend set summaries and rely on current lineage callbacks. This cannot preserve repeated
occurrences or distinguish historical unavailable detail from known absence.
2. Author another provenance graph/compiler and reconstruct old detail during reads. This adds
competing authority and incorrectly changes historical meaning.
3. Capture bounded checked-recipe occurrences at preparation, retaining local edges and archived
source facts, and render current summaries/reports from them. This preserves multiplicity without
expanding all paths or duplicating native catalog authority.

## Decision

Choose option3. Stable occurrence identity follows recipe/source identity and structural role,
with separate value, membership and ordering relations and explicit unknown boundaries. SQLGlot
continues qualification/type support; checked helper signatures do not imply known body meaning.
Analysis v3 writes and v2/v3 readers preserve historical unavailable detail without reanalysis.
Semantic compiler19 retains18 reading. Current-only production regenerates affected products.

Model-change SQL diagnostics retain original source/coordinates and remain inspectable after a
failed preparation. Failure diagnostics do not authorize effects. Native operation explanation
reads exact frozen candidate facts, retaining overload identity, ordering, owners and ACLs.
The explicit Alembic walk remains: its privilege context and global ordering remain necessary
under public Rewriter traversal, so callback conversion would add machinery without removing work.

## Consequences

Operator explanations gain attributed, bounded detail. Preparation owns its extra retained facts;
inspection does not execute submitted queries or reconstruct historical evidence from current code.
No richer SQL language, arbitrary equivalence claim or new migration engine follows. The
[PTD coordinator](../plans/postgresql-typed-domain_2026-11-09.md) owns implementation and verification.
Revisit if a selected language extension needs new occurrence roles or a native transform becomes
independently simpler under public traversal.
