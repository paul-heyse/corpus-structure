---
id: ADR-0080
title: Observe committed source-run identity before source execution
status: superseded
date: 2026-11-10
supersedes: []
superseded-by: ADR-0089
design: [§2]
evidence: Proposed
revisit: A supported consumer needs separately acquired and independently executed source work.
---

## Context

CLD-CA03 identifies initial regeneration source effects occurring after native creation but before
managed association publication. Source execution owns a supervisor connection, resource registry
and native cleanup. D8/ADR-0079 retain separate managed observations and native effect authority.

## Options

1. A synchronous native creation notification exposes actual committed identity while keeping
   source execution and its resources under their existing owner (selected).
2. A finite acquired execution handle transfers configuration, registry, connection/supervisor
   and cleanup obligations to another lifetime. Unlike visual resume, no selected source consumer
   needs acquired-but-unexecuted work; abandonment and one-shot execution add avoidable ownership.
3. Deriving identity later from logs repeats native meaning and cannot establish acquired custody.

## Decision

Source execution accepts an optional one-shot on_created callback with a frozen SourceRunCreated
value containing native run, project and release identity. Invoke after commit and supervisor
adoption, inside existing resource/native cleanup regions and before graph selection or work.
No callback occurs before successful commit. Existing non-observational callers omit it.

The CLI persists association beside acquired storage identity and establishes scoped logging
bindings in its own ExitStack across the source call. Ordinary diagnostic failures are isolated
by that CLI consumer; cancellation propagates through native cleanup. Native execution does not
swallow arbitrary callback bugs or delegate settlement. No callback grants effect permission.

## Consequences

FP-03–06 favor explicit composition, immutable facts and one native lifecycle; FP-07/H2/H25–27
favor preserving the complete resource owner over exporting a live-resource execution handle.
Expected benefits are qualitative, not measured. PostgreSQL commit and filesystem publication
are not crash-atomic: abrupt death between them can leave unavailable association. No inferred
link, outbox, workflow engine or new recovery authority is introduced.

This decision is accepted; implementation and verification remain with the
[CLD coordinator](../plans/cli-and-logging_2026-11-10.md#CLD-CA03). Acceptance alone does not close it.
