---
id: ADR-0099
title: PDF capture retains original assets and sealed publication under genuine demand claims
status: accepted
date: 2026-11-13
supersedes: []
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A PDF source action needs fabricated legacy run custody or cannot retain its actual sealed publisher separately from later admission.
---

## Context

DDO-07 includes PDF capture, not only analysis of already published SourceViews. ADR-0096's
existing-view factual admission is insufficient for a document that has not yet been captured.
Existing PDF staging also assumes every task has a legacy run. Target DDO releases correctly
exclude legacy execution-model products, so importing that model or fabricating a run would
reintroduce the authority being replaced.

The DDO coordinator owns implementation, pending native integration and DDO-11 adoption. The
existing-view factual support contract in ADR-0096 remains in force.

## Options

1. Recreate legacy runs, execution registries and source references around DDO requests. This
   would make task authority, declaration correspondence and recovery depend on synthetic facts.
2. Build a second PDF conversion/publication pipeline. This duplicates substantial native schema,
   streaming, validation and recovery behavior and separates future fixes from existing consumers.
3. Reuse the actual PDF owner under a genuine demand claim, with an explicit original-asset
   input and PDF-domain contract facet. Selected. Narrow context/call correspondence changes
   preserve the existing converter, staging, record validation and native publication ownership.

## Decision

An `OriginalDocumentRef` is a distinct original-source reference branch authenticated against the
persisted project/document semantic key, MIME, content hash and retained immutable source bytes.
It is not an `ExternalSourceRef` with fabricated cut, view, run or published-product fields. The
source URI remains custody. The capture operation's recipe/configuration belongs to the operation
and its actual assets, not to original-fact identity. Generic factual support/trust rules preserve
this branch without a synthetic computational episode.

PDF native staging accepts either its actual legacy task/run context or a genuine DDO task,
request generation, current claim and live demand interest. The DDO branch has no legacy run;
the modeled staging `run_id` is nullable for that reason. Private current-owner and publication
checks continue to enforce the task attempt, holder, scope and exact native PDF contracts.
A frozen PDF-domain facet is derived from the actual PDF owner's declarations, native calls and
implementation bindings; it authorizes only those actions. A broad capability flag or copied
legacy execution model cannot grant arbitrary native action authority.

A sealed PDF publication retains its actual publisher task, attempt, holder and validated product
custody. A later current DDO attempt may adopt the exact already-sealed result; its admission
fence and the original sealed publisher remain separate facts. Retaining or replaying that
publication does not perform another conversion or create an independent vote. The common
completion envelope must bind this actual PDF execution receipt to the native publication proof.

Invocation-owned NLP residency can suspend for actual PDF GPU work. Accepted NLP calls drain,
actual host processes retire and their existing capacity/sleep lease releases before the PDF
owner borrows capacity. Later NLP work can acquire a new host generation. Unproven host or PDF
retirement quarantines ownership and byte credit; successful NLP teardown cannot prove PDF death.
No global lock serializes independent NLP CUDA submissions. Physical configuration, including
an actual local service endpoint, stays explicit and separate from product meaning.

## Consequences

The target preserves one PDF implementation and authentic source, claim and publication lineage.
It requires coordinated context, generated-call, native guard and execution-envelope integration;
DTO preparation alone cannot establish a working source pipeline. The actual source asset,
sealed result and later demand admission remain independently inspectable without duplicate
conversion or fake recovery records.

Raw-original DTO and context foundation controls and bounded physical retirement/handoff controls
passed on 2026-11-13. Actual raw-source-to-runless-stage, PDF-domain facet, sealed-receipt replay
and complete source-to-analysis qualification remain in execution. The persistent database is
unchanged; accepting this target does not deploy a migration or close DDO-07.
