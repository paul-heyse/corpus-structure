---
id: ADR-0035
title: One interpretation authority governs prepared analytical representations
status: accepted
date: 2026-10-30
supersedes: [ADR-0012]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A required analytical interpretation cannot be expressed by the admitted context and demand profile.
---

## Context

Production-efficiency PE-00/PE-01 establish shared analytical contracts before optimizing
recognition, comparison, data movement and invocation preparation. ADR-0012's requirement for
one physical grammar prevents comparing physical frontends even when they preserve one
interpretation authority. Independent context translations also give identical notation different
meanings across source readers, rule projections and scientific comparisons.

The operator accepted RC01–RC04 for planning and authorized their execution on2026-10-30.
The [production-efficiency coordinator](../plans/production-efficiency_2026-10-30.md) owns
implementation and qualification; acceptance here establishes no performance claim.

## Options

1. Retain one grammar and independent adapters. This minimizes immediate changes but couples
   every demanded product to full interpretation and leaves symbol-role drift across consumers.
2. Introduce a universal workflow, cache and intermediate-representation service. This centralizes
   mechanisms but adds persistence, lifecycle and scheduling responsibilities without a consumer.
3. Compile bounded context, demand, result and dependency contracts from the existing trusted
   LinkML products; admit physical implementations beneath that authority. Selected: explicit
   boundaries permit useful preparation without repeated compilation or a second semantic owner.

## Decision

One admitted interpretation model governs supported physical recognizers and structural frontends.
PE-02 selects and qualifies any replacement; the existing grammar remains the implementation
until then. No deterministic fast path may silently resolve ambiguity or weaken supported semantics.

Source-local symbol-role declarations are separate from resolved entity attachment. Their scope,
source custody, evidence and profile/rule authority determine applicability. Source reading cannot
consume downstream M13 conclusions circularly. Pure kernels receive immutable prepared projections;
release/profile support is resolved at a valid batch boundary, without SQL per span. Native effects
retain current snapshot, authority, fencing and complete-publication checks.

RC02 permits explicitly versioned segmentation with new rendition and anchor identities; it never
reinterprets old source coordinates. RC03 permits logical skipped-invocation identity before packet
rendering while retaining source/configuration/policy identity, skipped population and reasons.
RC04 permits resident and detached spooled capture under identical exact-value, complete-spine,
atomic-completeness and snapshot-custody obligations. Physical availability remains explicit:
accepting these targets does not implement a segmenter, packetless scheduler or spool.

ADR-0012's other decisions survive: token normalization over the effective macro table determines
keys independently of parsing; the token/tree correspondence case remains inspectable. Source facts,
selectors, delimiters and rendering conventions remain profile data. Quote location retains exact,
spacing, macro-expanded and aligned fuzzy steps with source offsets, word-boundary snapping and
step/edit evidence. Prose constructs retain pack-owned spaCy Matcher patterns and
DependencyMatcher where attachment matters. No fuzzy identity, recursive-regex math or pynini
adoption follows. SymPy's parser coupling remains pinned and subject to its existing hold.

ADR-0031/0033/0034 continue to govern protected execution, archive reading and PostgreSQL lifecycle
authority. Semantic variation uses immutable release rows where supported. Code-owned executable
support is independent of authored declarations. Historical archives retain explicit readers and
do not gain current write capabilities or new meanings through defaults.

## Consequences

Context and preparation become shared inputs to real consumers. This adds bounded schema,
normalization and compatibility work; it avoids a new workflow engine, persistent cache registry
or per-item authority lookup. PE-01 establishes interfaces and adoption around current algorithms;
PE-02–PE-12 own algorithm changes and assembled qualification. Quantitative benefit needs measurement.
