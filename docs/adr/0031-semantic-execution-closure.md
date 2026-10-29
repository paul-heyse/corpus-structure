---
id: ADR-0031
title: Effective semantic contracts govern protected execution and archive opening
status: accepted
date: 2026-10-29
supersedes: [ADR-0025]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A required workflow needs native patterns or occurrence/context grouping, or an archived boundary cannot be opened faithfully.
---

## Context

SP-I01–SP-I03 address effective model consumption, protected immutable meaning and restricted
admission. The operator accepted archive-backed opening, restricted admission and an explicitly
bounded native profile. Current implementation and qualification remain separately tracked in
[the owning plan](../plans/semantic-model-pivot/model-execution-closure.md).

## Options

1. Recompile every archived read with the current compiler and persist through an administrator.
   This couples retained answers to compiler changes and gives ordinary regeneration unnecessary authority.
2. Introduce a universal workflow engine and general regex/grouping compiler. No required transitioned
   workflow needs these mechanisms, and declarations alone would not connect existing effects.
3. Share effective immutable recipes across actual consumers, preserve versioned archive readers,
   and expose complete protected operations to restricted principals. Selected: more explicit boundary
   and migration work buys localized semantic decisions and preserves old answers without dual writers.

## Decision

Effective LinkML products govern statement/qualification bindings, typed reference positions,
constraint placement, operation phases/results and projection contracts. Ordinary algorithms remain
owned implementations, with their applicability, inputs, results and effects enforced at real boundaries.

This record replaces ADR-0025's mandatory re-preparation on ordinary archive reads with supported
archive-product opening. Full exact verification remains required at persist/replay, activation,
run start and explicit request. Historical compiler-10 readers preserve their recorded validation
ABI, identities and bytes; successful reading never implies permission for new writes or activation.
Byte-producing determinants and runtime/deployment compatibility remain distinct.

This record replaces administrator-backed release persistence/selection in regeneration with a
restricted admission login and protected complete publication/finalization/activation operations.
Intrinsic meaning is closed atomically; deployment-specific SQL/native admission remains a separate
immutable release/physical/deployment product checked live at activation. No broad semantic DML,
publisher membership, generic TEMP or reference access is granted to admission. Runtime purposes
share one declared endpoint, with actual principal capability checks and sequential pool lifetimes.

The supported native integrity profile is structural shape plus selected accepted-value constraints.
Patterns and occurrence/context integrity placements remain explicitly unsupported for native admission.
This deliberately revises the original SP-00 promise; refusal is not implementation of those capabilities.
All supported behavior remains fully model governed. A newly required construct reopens this decision.

ADR-0025's remaining contracts continue: one physical MetaData, frozen forward migrations, protected
staging, same-transaction SERIALIZABLE COPY, exact retry/receipt identity, parent/generation CAS,
no generic writer TEMP, restricted authored SQL, independent SHACL and regenerable asynchronous commit.
ADR-0030's independent references, automated grading, immutable completed results and selected-answer
bindings continue unchanged. Existing runs, grades and MCP processes are not rewritten or restarted.

## Consequences

Protected inference begin/end operations replace caller-owned temporary tables. Meaning checks may
be removed only after immutability discharges them; cumulative state and concurrency checks remain.
New compiler products have deliberate identities, while historical archives remain immutable.
Acceptance of this decision does not establish implementation or native/provider qualification.
