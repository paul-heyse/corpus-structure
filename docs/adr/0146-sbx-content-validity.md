---
id: ADR-0146
title: Key validity by rule and evaluated content
status: accepted
date: 2026-11-21
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A supported validator cannot declare a sound bounded premise or required proof lookup would become recursive.
---

## Context

Current whole-body validation receipts are tied to release and validator identity, while
consumers often validate the same bytes again. A rule can remain true when unrelated release
facts change. The operator accepted declared rules and content-addressed proofs and confirmed
projection-based reuse.

[Rules and proofs owner](../plans/set-based-execution/populations-rules-and-proofs.md) ·
[Independent review F03](../design_review/reviews/design_review_sbx-revision-a-identity-and-authority_2026-11-21.md#F03)

## Options

1. Revalidate every whole product under each release. This is straightforward but repeats
   checks after changes outside the validator's read set.
2. Retain the current release-wide receipt and add ad hoc exceptions. This preserves broad
   invalidation and creates consumer-specific validity decisions.
3. Declare each rule and key its immutable proof by rule fingerprint and complete evaluated
   premise. Existing proofs match whenever both facts remain equal.

## Decision

The model declares rule form, scope and the fields the checker reads. PostgreSQL evaluates
supported forms at admission and the common establish routine evaluates missing proofs for
retained content. Attested rules bind the determining checker identity and the actual input
projection supplied to it. An unavailable checker determinant refuses publication.

Store proof facts by rule fingerprint and evaluated premise. Derive that premise from every
observed content group, membership, order, placement and external pinned fact. A relative
content digest can establish a content-only rule. A rule that reads absolute placement or
ordering includes its separately authenticated commitment. Unknown reads conservatively widen
the premise. The fingerprint captures the rule's model and checker determinants separately.

Required proofs are checked at binding after selected inputs are known, outside the native
support-validity fixpoint. Current authority, revocation, selected support and publication
fences remain independent premises. Consumers rely on their bound required rules.

## Consequences

Proof reuse can cross releases whose determining rules and content agree. New rule tables,
evaluators and binding checks land together in Revision A. SBX-02 owns the generic mechanism
and SBX-04 migrates current validators and removes the old receipt path. Neither package is
implemented by acceptance of this record. Revisit when an attested validator cannot expose a
sound premise, or a proposed proof dependency would make binding recursively depend on its
own validity conclusion.
