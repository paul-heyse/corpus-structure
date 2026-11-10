# Effective semantic declarations and their consumers

**Source-inspected discovery, 2026-11-10; benefits Proposed.** Shared baseline and limits:
[briefing](../briefing.md). Capability territory:
[LinkML](../../../../libraries/data_model/linkml.md).

## Present foundation

[prepare.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/prepare.py)
closes supplied imports, rejects unsupported required constructs and normalizes effective
definitions. [boundary.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/boundary.py)
realizes those definitions as strict Pydantic models. The release index, native requirements,
conditional fragments and immutable archive already make this considerably more than
schema-to-documentation generation. Native LinkML support and actual executable support
remain different facts: `_UNSUPPORTED` and the allowed profile are deliberate admission boundaries.

[operation_call_generation.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/operation_call_generation.py)
also prepares a supplied multi-module SchemaView, normalizes source attribute ranges/URIs,
then maps effective ranges to native call kinds. Its current dirty changes add correspondence
checks. That path is evidence of meaningful reuse and also a concrete place to investigate
whether normalized preparation facts can serve more than one compiler.

<a id="ddm-01"></a>

## DDM-01 — Broaden effective-model consumption

**Status:** adopted capability; candidate underuse across consumers, not a proven missing compiler.
`SchemaView.class_induced_slots`, `induced_slot`, `type_ancestors`, controlled `importmap`,
reusable slots/mixins and generator extensions can keep inheritance, range, requiredness,
aliases and constraints connected to the authored model.

**Broader use and value:** trace selected call/report/record consumers that reconstruct these
facts, and provide genuinely shared facts through the existing compiled product or accessor.
A change to a semantic range should update its mechanical representations through that owner;
consumers retain their distinct operation policy. This is especially promising where domain,
execution and physical declarations meet generated calls, rather than adding another schema registry.

**Defeater and retain case:** physical native kinds, runtime binding and semantic ranges can
legitimately differ. Combining their preparation must preserve source-relative URI authority,
closed imports, duplicate refusal and conjunctive constraints. A common helper that erases those
differences would be worse than separate explicit compilers.

**Next question:** which facts in operation-call source preparation are identical to release
preparation facts, and which exist specifically to bind physical inputs? Follow one changed
enum/range and one class-valued result through both products before proposing consolidation.

The [LinkML account](../../linkml/README.md) supplies installed1.12.1 observations: generators
can mutate inputs; native derived-schema materialization can change bound/pattern semantics;
missing import-map entries can fall back to ambient resolution. Those are preserved limits,
not reasons to abandon native induction or silently remove local safeguards.

<a id="ddm-02"></a>

## DDM-02 — Express richer relationships and value structure once

**Status:** unused/conditional declaration territory in the inspected current source schemas.
The overview describes `represents_relationship`, `relational_role`, subproperty/inverse
characteristics, disjointness, `unique_keys`, ordered/unique collections, explicit presence,
quantity kinds and units. These provide a richer language than unrelated primitive fields.

**Broader use and value:** first-class relationship roles could connect attributed source
relationships to generated boundary, native and graph projections. Collection/presence
declarations could govern membership ordering and omitted/empty distinctions where behavior
already depends on them. Unit and quantity-kind metadata could inform scientific value contracts
without making unit conversion an implicit parser side effect.

**Defeater and retain case:** changing authored syntax alone establishes no enforcement.
The present application already preserves qualified relation identity through owned contracts;
a replacement must retain endpoint kind, role, direction, multiplicity, context, exact occurrences
and competing interpretations. Optional descriptive axioms can remain descriptive. Independent
native guards are useful enforcement mirrors, not duplicates to delete mechanically.

**Next question:** which existing relationship or measurement requires the same semantics to
be authored in several places, and does the native metamodel construct preserve them in every
required lowering? Start from one real qualified relationship, not a universal graph redesign.

## Wider territory and stopping conditions

LinkML arrays, typed extras, conditional rules/classification, inference, linting,
documentation/API/language generators, grammar generation, Rust/PyO3, YARRRML and companion
Map/Datalog/store capabilities remain useful discovery territory. Native generator output
is not automatically equivalent to this project's strict runtime. The dated
[unified semantics assessment](../../unified-model-semantics_2026-11-01.md) identifies
Map/Datalog fidelity and execution limits; reuse those questions before extending research.

Rust/PyO3 deserves further attention when an actual cross-language consumer can retire a maintained
representation. API/documentation generation deserves attention when it can serve current operator
or agent contract discovery. Generic storage and workflow frameworks have no established new
consumer here. Broad availability is retained in [coverage](../coverage.md), without scheduling
adoption or treating supported-profile refusal as a diagnosed defect.
