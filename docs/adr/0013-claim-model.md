---
id: ADR-0013
title: "Every fact is one claim form: subject, predicate, object, typed qualifiers, evidence, supports and status"
status: superseded
date: 2026-10-28
supersedes: []
superseded-by: ADR-0024
design: [§B1]
evidence: Tested
---

## Context

The product builds a structured representation of what a set of documents states, for any domain
(DESIGN §1.1); statistics is the calibration domain. The old repository kept meaning in Python
classes: `evidence/model.py` held 10,059 lines and 277 classes, and one distinction ("governing
association") cost 24 classes, 12 tables and three migrations
([design rationale](../design/rationale.md) §2). Every later choice depends on one representation
for knowledge: the schema compilers (D2 §7), consolidation (D5), storage (D3), queries (D8) and
evaluation by alignment (D7 §5).

## Options

1. **A statement model** after Wikidata: a claim is a subject, a predicate, an object (an entity or
   a typed value) and qualifiers, with references and a rank. Variation lives in typed qualifiers,
   the value union and the condition tree, not in new tables or classes.
2. **RDF triples with reification or n-ary relation patterns.** Standard, but qualifiers, evidence
   and statuses on statements are verbose and awkward to query.
3. **Event-centric models everywhere.** They over-reify; most facts have a natural subject.
4. **Property graphs without qualifiers.** They lose conditions and modality, which are what keep a
   premise from reading as a fact.
5. **Per-type classes and tables** (the old repository's path). Every distinction becomes a code,
   codec and migration change.

## Decision

Option 1, as D1 states it:

- **The claim** is subject, predicate, object or typed value (D1 §6), qualifiers, evidence spans,
  supports, status and establishment (D1 §5). Core qualifiers apply in every domain (`modality`,
  `polarity`, `statement`, `conditions`, `scope`, …); schema qualifiers are declared per predicate.
- **Conditions** are a typed JSON tree with escape leaves (`phrase`, `unsupported`), so a claim is
  never presented as unconditional when its source conditioned it (D1 §7).
- **Symbol bindings** are a value-level map, the general form of "which symbol supplies which
  parameter under which premise" (D1 §6.1).
- **Reification** happens only when a fact has several equal participants, must be referred to as a
  thing, or recurs as one identity (D1 §5.4). Statements are reified, so theorems keep their
  premises, conclusions and proofs together.
- **Relations between claims** are typed claim links; relations between statements are ordinary
  claims with statement subjects. Claims stay first-order.
- **Keys** are hashes of canonical JSON of meaning-bearing parts (D1 §10.1), with formula values
  keyed by their token form (ADR-0012).

## Consequences

- A new distinction is a schema edit plus a migration mapping, never a new class or table. Every
  method's output, goldens and agent proposals share the form, so evaluation is alignment (D7 §5).
- **Tested:** S0 and S0-R2 annotators expressed the twelve core units and six held-out units in
  this form. 35 gaps were found, 11 of them in the schema; none required a different model
  (records `s0.gaps`, `s0r2.scores`).
- **Not yet built:** the phase 0 series implements it in `core` (the phase 0 plan,
  foundations).
- **Revisit** if a domain's facts repeatedly need several co-equal subjects that the reification
  rule turns into entities, or if the condition tree cannot carry a construct a second domain needs.

## Amendments

- 2026-10-28: the S0-R2 evidence cited above is now record `s0r2.scores-ir2`, which supersedes `s0r2.scores` (instrument revision I-R2; figures unchanged). No decision changed.
