---
id: ADR-0023
title: Identity is declared: qualifier key roles, canonical forms by range, case policy and a versioned key scheme
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§B1]
evidence: Proposed
revisit: A pack needs a key role that the three roles and a member-property condition cannot express, or the outgoing scheme's key functions cannot be kept callable to compute a carry-over map (probe Q-6), or scheme changes become frequent enough that cross-scheme comparisons dominate run diffs and carried judgments.
---

## Context

ADR-0013 makes keys hashes of the canonical JSON of a claim's meaning-bearing parts (DESIGN §B1,
D1 §10.1), and ADR-0019 settles which parts of evidence identity are meaning-bearing. Neither
declares which **qualifier** parts are identity, how a value is put in canonical form, or how the
key function itself changes. Under the design and the code at `6f31f75`, code decides all three:

- **Key roles are hard-coded.** `claim_parts` encodes "attribution is identity under `cited`" with
  the literal member name (`keys.py:63-66`), and D1 §5.2, D1 §10.1, D5 §5.4–§5.5 and consolidation's
  slot and conflict rules each restate the rule. A business pack cannot add a modality under which
  attribution identifies without a core edit (DA-001).
- **Canonical form is chosen by JSON shape.** `canonical_qualifier` tests the shape of a value
  (`keys.py:432-462`), so a map entry `{"ref": "Smith"}` under a string range is read as an entity
  reference, and nothing declares how a business identifier such as `ORG-101` is compared (DA-001).
- **Case is erased everywhere.** The text form casefolds every label and literal, while symbols
  keep case (`symbol_form`). A `RandomVariable` labelled by its defining expression, or a
  `FamilyParameter` whose canonical name falls back to a symbol, keys `X` like `x` and `\Sigma`
  like `\sigma`, which are different mathematical objects (DA-008).
- **The key function has no version.** Any canonical-form fix is an unannounced key migration,
  which orphans judgments (D5 §7.3) and cross-run diffs, and D1 §10.1 forbids fixtures to pin key
  values, so a drift in a dependency, the Unicode tables or dump behaviour is detectable only by
  review (DA-009, key-scheme part; RC07).
- **Locator limits are incomplete.** D1 §10.3 omits the first-sentence ordinal shift within an
  anchor (DA-014).

Source: the domain-model alignment review
([R02](../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r02),
[target model §8](../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md#8-identity-model)),
rule changes [RC07](../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#rc07)
and [RC08](../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#rc08), which
the operator accepted on 2026-10-28 (phase 0 coordinator §9.2, decision 20). Owners: D1 §5.2, §6.2,
§10.1, §10.3. Consumers: the key function and canonical forms (foundations), pack qualifier
declarations (schema and rules), slots, fusion and conflict detection (D5 §5.3–§5.5), the rule view
(`validate`), runs (D3 §4, D6) and judgments (D5 §7.3) that record a scheme, and run comparison in
evaluation (D7). The current implementation is the code above; nothing of the target is built.

## Options

1. **Keep code-decided roles and forms, with a contract test** (the simplest viable alternative).
   `keys.py` keeps the role rule and the shape test; a contract test checks that D1's qualifier table,
   consolidation's slots and the rule view agree with it. It costs least now, but the test checks two
   hand-kept copies against each other, not that a new pack qualifier or range is canonicalized
   correctly; every pack modality that should identify attribution is a core edit; case stays a code
   decision; and without a scheme a key drift stays invisible. The cost recurs with each pack, which
   rules it out for a design whose first goal is new domains without new code (D1 §1).
2. **Declared identity, with the scheme number hashed into every key.** Roles, forms and case are
   declared as in option 3, and keys carry their scheme inside the hash. Mixing schemes becomes
   impossible, but every scheme change moves every key, including a fix that changes no output for
   most inputs, orphaning every judgment and every cross-run diff (DP-04, DP-09).
3. **Declared identity, with the scheme recorded beside keys, conformance vectors and a carry-over
   map** (chosen). Each qualifier's key role, conditional role, canonical form by range and case
   policy are model declarations compiled into one `KeySchema`; the scheme is recorded beside the
   keys it governs; a scheme change ships a carry-over map. Unchanged inputs keep their keys across
   a scheme change, and readers compare keys within one scheme or through the map.

For case alone, folding everywhere (today) merges distinct mathematical objects, and preserving
everywhere splits prose variants ("Normal distribution", "normal distribution") that label
normalization exists to merge; a declared policy per string-ranged slot and per class label keeps
both properties.

Option 3 adds a specification type, one compiled lookup and per-scheme vectors, beside a key function
that exists anyway. In exchange keys, slots, conflicts and the rule view read one input, a pack
changes identity by declaration, and a key change is announced and mapped rather than silent. Its
benefit over option 2 is that judgments and diffs survive scheme fixes that leave most outputs
unchanged.

## Decision

- **A `QualifierSpec` per qualifier, core and pack alike.** It declares the qualifier's range, its
  default, its **key role** (`identity`: it enters the claim key; `meaning`: it stays out of the key
  but a disagreement makes alternatives; `inert`), an optional **role condition** naming a member
  property under which the role becomes `identity`, its **canonical form by declared range**, its
  **case policy** and its store placement. The contract's fields are those of
  [model and projections §3.2](../plans/phase-0/model-and-projections.md#32-stage-a-generation-m1).
  Core specifications are generated from the `core` model; a pack declares `ci:key_role` on a
  qualifier slot, or its existing `ci:identity_qualifiers` list is compiled into the same
  specification. `statement` stays a key part of its own, beside the qualifiers (D1 §10.1).
- **Conditional roles are member properties.** Attribution is `meaning`, and `identity` when the
  claim's modality has the `attribution_identifying` property (core: `{cited}`). `ClaimModality` is
  schema-version-scoped: core members plus pack members, each with its member properties
  (`premise_forming`, `attribution_identifying`, `conflict_bearing`), so a pack modality under which
  attribution identifies needs only its declaration. No member name is written in the key function.
- **Canonical form is chosen by declared range**, never by the value's shape: token form for formulas
  and sets (ADR-0012), text form for text and phrases, NFC with collapsed whitespace and the declared
  case for string identifiers, `{enum, v}` verbatim for enums, the resolved key after a kind check for
  entity references, recursion for intervals, the entry's value range for map entries, the canonical
  decimal for numbers, verbatim for dates and booleans (D1 §6.2).
- **Case policy** (`ci:case`: `fold` or `preserve`) is declared on string-ranged slots and on class
  labels. `fold` is the default for prose; `preserve` applies to the labels of classes declared
  math-bearing (`RandomVariable`) and to literal identity slots whose fallback is a symbol
  (`FamilyParameter.canonical_name`). Symbols keep case, as they already do.
- **`KeySchema` is compiled from these specifications** (core from the model, pack from its compiled
  lookup), and the key function, consolidation's slots and conflict detection, and the rule view read
  it and restate nothing.
- **The key scheme is versioned beside keys, never inside them.** The model declares
  `ci:key_scheme: N`; each run records the scheme of its keys, and each judgment target records the
  scheme of the key it names. Readers compare keys only within one scheme, or through a carry-over map.
- **Each scheme has a conformance vector**: hand-authored inputs (values of every range form,
  condition trees, entities with identity, statements on a small rendition, an external reference)
  with their expected keys pinned, computed independently of the code under test. A change to any
  output fails until the scheme moves. Fixture tests still compare key equalities, never values.
- **A scheme change is a key-bearing change** (ADR-0022's class): it ships a new scheme number, a new
  conformance vector and a **carry-over map** (old key → new key, translation T8), computed by keying
  the stored authored inputs under both schemes. A key whose input is unavailable is reported, never
  guessed. Cross-run comparisons, carried judgments and reference-run key reuse go through the map
  when schemes differ.
- **Stability limits are stated** (D1 §10.3): locator regeneration, the first-sentence ordinal shift
  within an anchor, and key-derivation changes, which are handled only through schemes and carry-over.

This extends ADR-0019 and refines ADR-0013's keys clause; it supersedes neither, and ADR-0012's token
form is unchanged.

## Consequences

- **Easier:** a pack adds a qualifier, a modality under which attribution identifies, or a
  case-sensitive identifier by declaration, with no core edit; keys, slots, conflicts and the rule view
  cannot disagree about identity, because they read one compiled input; a key drift from a dependency
  or a canonical-form fix fails the vector instead of passing silently; a scheme fix moves only the
  keys whose outputs change, and judgments and diffs follow the map.
- **Harder:** every qualifier needs a specification, and the declaration check refuses a member
  property no consumer reads; the outgoing scheme's key functions must stay callable long enough to
  compute a carry-over map (probe Q-6 settles a frozen module per scheme against a map computed by the
  outgoing release); vectors are hand-authored per scheme; every reader that compares keys checks the
  schemes first.
- **Limits:** carry-over covers keys whose authored inputs are stored; others are reported. Scheme 1
  is frozen only after the token form is final (`s5.keys-property`) and the typed dispatch and
  specifications are in.
- **Evidence:** Proposed. The defects are confirmed by source reading at `6f31f75`
  (`keys.py:63-66`, `:432-462`) and by the audit's scratch probe (2026-10-28, not retained).
- **Not yet built:** the generated core specifications (model and projections, M1); pack
  specifications and `ci:key_role` (schema and rules, S1); `KeySchema`, case policy, canonical form by
  range, `carry_over` and the ordinal-shift test (foundations, F2d); scheme 1 frozen with vector v1
  (F2e); the scheme recorded on runs (orchestration, O1) and judgment targets (evaluation, E1), and
  comparison through the map (E2b); consolidation reading `KeySchema` (C1). Disposition of DA-001,
  DA-008, DA-009 (scheme) and DA-014 is in the phase 0 coordinator's §11
  ([phase 0 plan](../plans/phase-0_2026-10-28.md#11-findings-disposition)); acceptance of this record
  closes none of them.
