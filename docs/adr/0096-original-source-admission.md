---
id: ADR-0096
title: Original source admission retains factual support without inventing computation
status: accepted
date: 2026-11-13
supersedes: []
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A factual or effectful input cannot be represented without being relabelled as computational evidence or duplicating semantic authority.
---

## Context

DDO-07 must pass an already captured original document into independently declared formal and
NLP operations. Existing published source views have immutable native product, placement,
release/cut and document custody. The first DDO kernel exposes only computation-supported
products through demand bindings. Merely constructing a typed source DTO does not bridge that
admission boundary. Repeating capture or inventing an inference episode would misrepresent
original evidence and can create false independent support.

This realizes the authentic-support target of ADR-0093 and the DDO plan's C3/F03/F13 obligations.
It does not replace their product, computational derivation, currentness or preservation decisions.

## Options

1. **Repeat capture or publish a synthetic computational derivation.** This superficially fits the
   initial kernel, but performs unnecessary work or makes a false evidence claim.
2. **Broaden every derivation into an undifferentiated operation event.** This blurs computation,
   original facts and effects, and changes otherwise useful consumers and independence semantics.
3. **Admit an original fact through an explicit receipt and typed support branch.** Selected.
   A narrow original-source acquisition reuses existing custody owners; ordinary downstream
   computation consumes that support without changing its type or creating a second selector.

The additional support branch has real native/compiler/read integration cost. It purchases an
actual source-to-analysis path, correct lineage and reuse of existing captured originals. It
avoids rehydrating or recapturing an entire document merely to change its execution context.
The initial path is original-source admission; it does not introduce a general plugin/event bus.

## Decision

One declared native original-source admission consumes the exact existing `ExternalSourceRef`,
qualified demand and frozen selectors. Existing published-record/placement and structural-source
custody checks authenticate the original project, release, run/cut, native product, view and
revision. The acquisition derives the source body from stored original facts; a caller-supplied
body or matching digest alone is insufficient. The algorithm receives a narrowed immutable
source representation and no ambient reader.

The target document identity and `original_source` are the persisted document semantic key.
Raw content hash, physical document ID, native product reference and legacy projection digest
retain their own meanings as custody. Clean projection identity excludes task, runtime, recipe
and diagnostic-reference salts. Original atoms, offsets, selectors, reading order and recognition
standing remain exact.

A distinct immutable original-source admission receipt supports the selected semantic product.
The governing model, native input manifests, binding projections, trust closure and result reads
carry an explicit typed original-fact support reference. It is never stored as a computational
`derivation_id` or relabelled in `support_episodes`. Downstream derivations retain both actual
computational premises and actual original-fact support. Source permissions, project boundaries,
pinned read visibility and current revocation checks apply to both branches.

Read/admission replay preserves the original fact and exact receipt custody. Repeated admission
of the same fact does not become independent computational evidence. The new route reuses
existing immutable source capture; production adoption and old-writer retirement remain DDO-11.

## Consequences

Typed source values can feed declared analysis directly without fabricated provenance or repeated
PDF work. This requires coordinated support validation and native reader/publication changes,
not merely a DTO or adapter method. Admission and computation remain separately inspectable.
The [DDO coordinator](../plans/declared-data-operations_2026-11-12.md#remaining-functional-scope-and-next-execution)
owns unfinished implementation and qualification. This decision is accepted target detail,
not a claim of implemented source admission, verified closure or production deployment.
