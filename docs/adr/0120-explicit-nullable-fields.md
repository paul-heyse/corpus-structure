---
id: ADR-0120
title: Explicit nullable fields preserve null separately from absence
status: accepted
date: 2026-11-16
supersedes: []
superseded-by: null
design: [§B1, §B4]
evidence: Proposed
revisit: A maintained JSON product requires a null distinction that cannot be represented by explicit whole-field nullability without weakening identity or native source authority.
---

## Context

The actual selected-context E5 provider journey fails before inference because curated targets
are project-owned: their original-source field is explicitly null. The LinkML-derived boundary
permits omission of the optional string but rejects null. Scalar product references similarly use
an explicit null member address. Omitting these context fields would break authentic native packet
identity. Substituting a string sentinel would change domain meaning. DDO-SI-22 in the
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md#current-consumer-integration-and-discovered-defects--2026-11-16)
owns implementation and actual qualification; this decision alone establishes neither.

[D2](../design/D2-schema-and-guidelines.md#effective-operation-compilation-and-authoring)
owns effective property declarations and their boundary compilation. Missing, null and a populated
value must remain distinct through preparation, identity, archive opening and native JSON Schema.

## Options

1. Make every optional field nullable. LinkML's JSON Schema generator offers a global null option,
   but this would weaken unrelated boundaries and merge independent presence/value decisions.
2. Move contextual products to separately authored nominal JSON schemas. This can represent null,
   but replaces their existing prepared adapters and role kinds or duplicates the effective model.
   It expands the migration without removing the missing representational responsibility.
3. Add explicit opt-in whole-field nullability to the effective property contract. Selected.
   LinkML annotations carry the additional distinction; Pydantic's native union and JSON Schema
   support realize it. The small compiler extension keeps one declaration and one validation path.
   Required presence, collection members, identity and source authority remain separate constraints.

## Decision

`cs:nullable` explicitly declares whether a whole field may contain null. Omission remains governed
by required presence and the existing MISSING representation. Nonnullable fields retain strict
null refusal. Nullable collection fields permit a null collection, not null elements. Annotation
values are checked; nullability cannot silently weaken an identity determinant.

The effective property definition, preparation, boundary recipe, archived products and emitted
JSON Schema preserve this distinction. Ordinary Pydantic unions perform validation; no alternate
validator or producer-specific normalization rewrites null to absence. Initially annotate only
the contextual target/vector/product-reference fields whose project-owned source or scalar-member
address actually permits null. Source-only carrier and primary-input pins remain nonnullable.
The native packet's original-source field remains required-present even when source-free.

Issue compiler24 and boundary ABI13 for the changed compiled products. Current native guards and
archive readers enforce the new interpretation; older data can remain inert or regenerate. No
compiler23 compatibility interpreter or default injection supplies current authority. Immutable
registered migration bytes remain unchanged; the normal successor captures the source change.

## Consequences

Project-owned targets and scalar addresses can preserve exact current meaning without a sentinel
or special encoder branch. The opt-in compiler property adds a maintained declaration responsibility
and requires source recapture/current archive qualification. Existing strict default behavior and
presence semantics remain useful independent verification targets. This is a semantic correction,
with no numerical performance claim or additional runtime coordination mechanism.

Required evidence includes absent/null/value distinctions, required-nullable fields, collection
boundaries, identity refusal, archive fidelity/current-only interpretation, native admission and the
three actual configured E5 selected-context recipes. The coordinator retains these open obligations
until their real source-qualified results settle.
