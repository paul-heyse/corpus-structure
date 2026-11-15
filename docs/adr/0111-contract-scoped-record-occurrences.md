---
id: ADR-0111
title: Source record occurrence identity follows its consumed family contract
status: accepted
date: 2026-11-15
supersedes: []
superseded-by: null
design: [§B1, §B5]
evidence: Proposed
revisit: A required source occurrence distinction cannot be expressed by the checked family contract, occurrence recipe, original source pin and occurrence anchors.
---

## Context

ADR-0109 authorizes one current domain model and regeneration rather than permanent legacy
interpretation. ADR-0110 binds reading-policy applicability to actual family contracts and reading
recipes while preserving original producer lineage. Rich admission and protected grading exposed
a remaining inconsistency: `record_identity` and `bind_record_candidates` salt source occurrences
with the entire prepared release. A compatible producer cannot retain a valid occurrence across an
unrelated release change without either rejecting it or relabelling its original release.

D1 owns the occurrence/interpretation distinction; D7 owns complete-record grading and policy
application. The DDO coordinator owns implementation and qualification. This record refines their
current target, preserving ADR-0049's qualified records and evidence authority.

## Options

1. Keep the whole-release determinant. Simple locally, but forces unrelated regeneration or a
second historical interpretation path. It contradicts the selected consumed-contract boundary.
2. Use only source pins and anchors. Reuses source occurrences, but loses the typed family meaning
and its declared occurrence recipe when the consumed family contract changes.
3. Use the checked family-field kind contract with the original occurrence determinants. Selected.
It uses the effective model's existing identity authority and requires producer/binder migration,
without another identity registry, compatibility resolver or publication protocol.
4. Include the reading recipe in the occurrence ID. Rejected: different reading interpretations
must still refer to one original occurrence. Exact producer recipes remain in their own receipts.

## Decision

A current SourceRecord occurrence ID uses its actual effective family-field kind-contract identity,
family, occurrence recipe, original primary source pin and sorted occurrence-defining anchor IDs.
The family owner is the checked field-contract declaration referenced by the record, including its
consumed shape/value closure; a local class name or generic SourceRecord wrapper is insufficient.
The producer and pure binder resolve that identity from the actual checked model. No whole-release
fallback, fabricated prepared-release alias or unchecked identity bypass remains.

Reading interpretations retain their actual record ID, fields, evidence and policy basis. Reading
recipes, producer releases, runtime and publication receipts retain their own original attribution.
Compatibility of a current family/reading contract never rewrites those identities or implies that
a changed question, evidence, feature algorithm or policy judgment remains valid.

Existing native support, source custody, currentness, permission, completion and trust checks
remain required. This decision changes occurrence identity determinants; it grants no publication,
evaluation or accepted-knowledge authority.

## Consequences

Compatible releases can reuse occurrences while changed family contracts acquire new identities.
The semantic benefit is Proposed and qualitative; no performance or quality measurement is claimed.
Producer, binder, grading, reading-assertion and rich-admission consumers migrate together. Useful
independent identity/source checks remain; release-salted compatibility code and mechanism tests
retire. Data on the replaced identity basis may require regeneration or faithful explicit conversion;
old products and their attribution are never edited to look newly produced.

Implementation and integrated native/public/protected verification remain open at the
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md). Acceptance of this record does
not close that scope or authorize persistent deployment, activation, reset or conversion.
