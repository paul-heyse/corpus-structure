---
id: ADR-0144
title: Store homogeneous populations as declared partitions
status: accepted
date: 2026-11-21
supersedes: []
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A supported consumer needs token-level database joins or source correspondence cannot establish stable partition keys.
---

## Context

Tokens, sentences and HanLP populations are duplicated as nested data and individually
wrapped members. Their immediate consumers operate on blocks. Whole-product identities and
absolute source offsets propagate changes through facts that a downstream consumer may never
read. The operator confirmed partitioned populations, relative offsets, role-relative body
references, one reference carrier and read-projection request identity on 2026-11-21.

[Partition contract](../plans/set-based-execution/populations-rules-and-proofs.md) ·
[Reference and key contract](../plans/set-based-execution/references-and-projection-keys.md) ·
[Independent identity and authority review](../design_review/reviews/design_review_sbx-revision-a-identity-and-authority_2026-11-21.md)

## Options

1. Keep each population in a whole-product list. This is simple to serialize but makes keyed
   access and proof premises depend on the entire population.
2. Store one typed database row per item. This enables token-level SQL joins, while adding
   physical shapes and reconstruction work for consumers that currently need blocks.
3. Store declared partitions once with keyed access and group digests. This matches the
   observed input unit and supports narrower changes while preserving tagged value fidelity.

## Decision

Choose declared partitions for homogeneous collections. LinkML effective slots declare the
unit, key, order, item address and field groups. Python and generated native programs consume
that same compiled contract. PostgreSQL recomputes submitted partition and group digests,
roots and counts before atomic product admission. Disclosure inherits the parent product and
acquired selection.

Partition bodies contain relative item spans and stable local content. Absolute placement and
ordinal order have a separate authenticated commitment under the product header. A move under
a known stable key preserves relative content identity, while an order- or placement-sensitive
read includes those changing facts in its projection. Block-relative coordinates alone do not
establish correspondence across renamed source pointers.

A consumer's request input identity is the digest of its declared read projection. The kernel
receives only that projection. Its current use records the selected inputs and the derivation
records the original equivalent inputs. One reference carrier describes whole products,
identified members and partition addresses. Body references name a declared input role and an
address and resolve through the producing derivation's inputs. Multiple input occurrences need
a declared discriminator or unique address. Product indexes and rich support references retain
the explicit variants specified by the reference owner.

Identified graph members and the four currently bound member kinds retain their individually
addressed unit. Canonical identity encoding preserves absence, null and supported numeric
meaning in both languages.

## Consequences

The representation can avoid per-token packet storage and broad downstream re-keying. It
requires coordinated compiler, admission, reference and consumer changes and regeneration at
Revision A. SBX-01 delivers the generic capability, SBX-03 converts the first populations,
SBX-05 implements references and SBX-06 implements projection keys. Each retains its actual
acceptance in the coordinator. Unknown dependencies conservatively widen the read premise.
Revisit if a real database consumer needs token-level joins or stable block correspondence
cannot be established for its supported source edits.
