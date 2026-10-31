---
id: ADR-0037
title: Publish immutable parsing layers under explicit capability demands
status: superseded
date: 2026-10-30
supersedes: []
superseded-by: ADR-0038
design: [§B4, §B5]
evidence: Proposed
revisit: A required parsing capability cannot retain product-qualified custody or a weak demand still performs stronger interpretation.
---

## Context

ADR-0036's source products now preserve original/decoded/canonical custody. PP-05–PP-10
require later text, interpretation and assessment results without mutating their source build.
The original store admits one HTML product per ingest task, and the current mathematical reading
can construct SymPy values during ambiguity resolution. Neither is a sufficient boundary for
explicit deferred requests. The [coordinator](../plans/parsing-pipeline_2026-10-30.md) owns
implementation and qualification; this decision adds to ADR-0036, preserving rendition identity,
canonical evidence, archived meanings and independent automated evaluation.

## Options

1. Add mutable fields to the original HTML manifest and a lazy flag around the existing reader.
   This is the smallest edit, but overwrites custody and leaves hidden symbolic construction.
2. Add separate mathematical stores, scheduler and generic cache service. This isolates code but
   duplicates identity, dependency, lifecycle and publication decisions across consumers.
3. Extend shared product contracts with immutable layers and explicit capability prerequisites.
   Selected. Native libraries retain their useful operation-owned representations, while source,
   text, interpretation and assessment products share reference and publication semantics.

## Decision

Products have producing-task/key/content identity and explicit root source-build custody.
Derived products append qualified dependencies and endpoints rather than modifying a completed
source product. Preserve old payload bytes/digests through supported historical root readers;
forward migrations deploy new contracts without modifying frozen revisions.

Separate lexical, structural, syntax, contextual interpretation, native symbolic construction and
named assessments. Weak demands do not invoke stronger kernels. Keep existing method IDs with
explicit new method/payload versions and migrate all consumers of changed promises together.
SymPy remains the native mathematical engine, not the source-occurrence authority. Preserve
unknowns, alternatives, binder identities, definedness and scoped assumptions.

Use pylatexenc 3.0b2 only for requested structural work: its explicit parsing-state controls retain
current percent/dollar semantics. Keep the total scanner and token-form identity. Retain Lark
1.3.1/SymPy 1.14.0; private native objects are operation-owned rather than an executable persisted
ABI. Reuse prepared inputs at actual validity lifetimes and retain main-thread deadlines.

Existing restricted publication seals coherent product sets atomically after pure preparation.
Historical reads grant no new-write authority. Source inspection/exports and placement explanation
consume pinned products and qualified coordinates; fuzzy placement is never exact source origin.

## Consequences

Additional normalized product/dependency rows and forward migration work buy independent deferred
results, stable custody and one selection mechanism. Explicit stage separation removes unnecessary
stronger work and permits reuse without collapsing source occurrences. It requires migrating
methods, native support, readers and direct mathematical callers coherently. No quantitative
speed or storage improvement is claimed. Original operational data remains intact; adoption uses
a fresh realization after qualification. Implementation and acceptance remain tracked in PP-05–PP-10.
