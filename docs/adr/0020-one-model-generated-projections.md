---
id: ADR-0020
title: One LinkML model is the authority; every representation is a governed projection
status: superseded
date: 2026-10-28
supersedes: [ADR-0017]
superseded-by: ADR-0024
design: [§B5]
evidence: Proposed
revisit: Probe Q-1 and its fallback emitter both leave a hand-kept mirror; the physical overlay grows a second physical vocabulary that mirrors SQLAlchemy; LinkML's introspection (`SchemaView`) blocks a compiler; or a domain needs logical inference over the schema.
---

## Context

ADR-0017 made a domain a LinkML pack compiled into every consumer and divided ownership by
artifact kind: the pack owns the domain vocabulary; hand-written Pydantic models in `core` own the
domain-independent D1 shapes, with `core.yaml` as their contract-tested mirror; `vocab.py` holds
the operational closed sets by hand, "one string enum per list", mirroring D3's CHECK lists; and
D3's DDL text was to be hand-ported into `core/db` as the specification of migration 0001. S4
showed the pack compiles to every consumer (records `s4.*`).

The [domain-model alignment review](../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md)
(decision Revise; R01, R05, rule changes RC01, RC03, RC04) found that this division leaves the
model short of the core §1 MUST (FP-04, A2): closed sets, defaults, the core qualifier list, key
roles, member behaviour and cross-field invariants are each written by hand in two to six places
(Python `Literal`s, `vocab.py`, `core.yaml`, `keys.py`, Pydantic validators, D3's DDL and design
prose), with no derivation between most of them ([DA-001](../design_review/audit/semantic-model-and-authority.md#da-001),
DA-002, DA-003, DA-011, DA-012, F01). D2 §6 and §9 inline copies of the pack files that already
differ from the S4 files (DA-011). A business pack's statement kinds, modality and identifier
qualifiers would need core edits (A3).

The expected changes are the audit's S1–S9: a new qualifier, kind or vocabulary member; a new
invariant; a business pack (DESIGN §1.3); a canonical-form fix. Nothing is stored yet: P0-F-1,
P0-F-2a, P0-I-0 and P0-F-2b are built in `core/`, and the pack compilers (P0-S-1) and migration 0001
(P0-F-4) are next, so this is the cheapest point to move authority. The operator accepted RC01,
RC03 and RC04 on 2026-10-28 ([coordinator §9.2](../plans/phase-0_2026-10-28.md#92-rule-changes-of-the-domain-model-alignment-review),
decisions 1 and 18).

Owners amended: DESIGN §B5; D2 §2, §3, §6, §9; D3 header, §1, §6.2; D9 §1. Consumers: the `core`
shapes, keys and locators; the `schema` compilers; `core/db` and Alembic; every SQL reader; the
annotator reference; the JSON Schemas served to agents.

## Options

1. **Keep every form and extend the mirror contract test to every enum, default, qualifier and
   invariant** (the simplest viable alternative; the audit's lead). Least new code, and each copy
   is checked. But every change is still an edit in four to six places, each a writable source
   (DP-01), held together by a reconciliation protocol whose cost recurs with every change. It is
   rejected as the target and kept as the **interim guard** for whatever is not yet generated.
2. **The current split** (ADR-0017 as accepted: Pydantic shapes, LinkML vocabulary, `vocab.py` →
   CHECKs, D3's DDL hand-ported). The A2 gap above; rejected.
3. **Pydantic as the one authority** for the core shapes and operational sets, with `core.yaml`
   and the pack bridge generated from Python, and hand-written `MetaData`. One edit for a core fact,
   but two authoring languages joined by generated bridges, member properties as Python metadata,
   and a change classification (ADR-0022) over two introspection APIs. The pack must stay LinkML
   (ADR-0017's reasons stand: authors and models read YAML; it generates to several targets), so
   LinkML is the only language that sees core and domain facts together. Rejected as the
   authority; it survives only as the **fallback for shape structure** if probe Q-1 fails.
4. **Hand-written `MetaData` for the operational tables**, with vocabularies and invariants
   generated. Less compiler work, but the D1 ↔ D3 restatement of the knowledge tables remains.
   Rejected for knowledge tables; acceptable for purely operational tables only if the overlay
   sprawls (the revisit trigger).
5. **LinkML's own generators as they are.** On 1.12.1 `gen-pydantic` emits a plain `Union` with no
   discriminator, `Optional` defaulting to `None` and unfrozen models; `gen-sqltables` emits native
   enums, no CHECKs and no JSONB, and Alembic's PostgreSQL implementation does not compare enum
   values; `gen-json-schema` emits draft 2019-09 and drops predicate slots (Interface-checked in
   installed sources, 2026-10-28; S4). Rejected.
6. **One LinkML model in three modules, own compilers over `SchemaView`, a hand-written physical
   overlay, behaviour in hand-written functions** (chosen). The compilers are a deliberate bespoke
   projection rule set over a library's introspection (DP-13), not generic capability rebuilt.

Option 6 costs more than option 1 in compilers and generated files (the plan's indicative size is
about 1,500 product lines). It retains what option 1 cannot: one declaration per fact, so a change
is one edit plus regeneration and the copies cannot drift, and one introspection API for every
compiler and for change classification.

## Decision

**The corpus-structure model is the single authority for structure and meaning.** It is LinkML in
three modules:

- **`core`**: values, condition nodes, bindings, items per form, evidence, segment kinds, qualifier
  specifications, closed sets with member properties, the key-scheme declaration and
  `ExternalReference`;
- **`system`**: the classes of `meta`, `ops`, `kb` and `eval` with their closed sets, invariants,
  relationships and payload classes, the source-profile class and the `EmbeddingSpec`;
- **the domain packs**, unchanged in form.

`core` and `system` live in `python/corpus-structure/src/corpus_structure/model/` and change with
code releases; together they are the **model revision** (ADR-0022). Packs stay in `domains/` and
are data; each is a **schema version**. Packs combined in one project compile into one schema
version, with local names checked unique at compile.

**What the pack owns** (kept from ADR-0017): the domain vocabulary, meaning classes, predicates,
qualifiers, enums, identity and extraction hints, so a description edit is a new schema version.
What changes is that the core vocabulary, the member properties, the qualifier specifications, the
lifecycle of each closed set and the shapes join the same model instead of living in code.

**Every consequential fact is declared once**, in native LinkML where it can be and otherwise in
the `ci:` declarations of D2 §3: closed-set members and their lifecycle (`static` sets enforced by
CHECK, `schema_version` sets extendable by packs and enforced per version), member properties,
defaults, qualifier specifications, cross-field invariants of the templated kinds, relationships,
relational placement and the class of each stored value. Each project annotation must have a named
consumer; the model loader's declaration check refuses one that has none.

**Every representation is generated** by compilers in `schema/` that are pure functions of
`SchemaView` and their own version, or is the hand-written physical overlay. Generated files that
`core` imports are checked in, never edited, and each has a drift test.

- **Stage A** (now): the vocabularies with member-property sets, qualifier specifications,
  defaults, the local ↔ prefixed name tables, SQL-literal constants and templated invariant
  validators, generated into `core/_model/`; `core/vocab.py` is generated at its existing path.
- **Stage B** (after probe Q-1): the shape structure (discriminated `t` and `op` unions, a named
  recursive `Condition`, the authored and stored forms, `MISSING` defaults, frozen models, prefixed
  aliases) is generated too. **Or, if Q-1 fails, the fallback:** the shapes stay hand-written and
  `core.yaml`'s shape classes are emitted from their `model_fields` by an own emitter. Either way no
  hand-kept mirror remains. Until then the mirror contract test is extended to every shape fact
  Stage A does not generate. Q-1 selects the variant; it does not reopen this decision.
- `core` keeps its runtime dependencies (Pydantic and `regex`); LinkML is needed only by `schema`
  and the generators. Per-predicate batch branches stay `create_model` over `SchemaView`, as
  per-version compiled artifacts.

**The relational projection** (RC03). SQLAlchemy `MetaData` is generated from the model into the
checked-in `core/db/_tables.py` and drives Alembic: system classes are tables, scalar slots columns;
static closed sets are `text` with digest-named CHECKs; schema-version-scoped sets are per-version
member rows referenced by composite FKs; single-valued references are FKs and multivalued or nested
ones edge tables; invariant templates become CHECKs beside their generated validators; nested values
are typed JSONB under the payload-schema registry (ADR-0022). One hand-written **physical overlay**,
`core/db/overlay.py`, owns every access-path choice (indexes and partial predicates, the BM25 and
HNSW indexes, views, the extension assertion), binds by name to generated tables and fails at import
on a missing name; the model declares no physical layout. Migration 0001 is generated once from the
generated `MetaData` plus the overlay and then frozen. D3's DDL is no longer the authority: the
S6-tested DDL is the reference that the first generation is compared against (a pglast-normalized
port check, probe Q-3), after which D3 cites the generated renderings. The same-run invariants
INV-03 and INV-08 are enforced by FK or, if probe Q-4 chooses it, in the bulk-write primitives with
a test per invariant; the edge tables stand either way.

**Interchange projections.** Arrow schemas for every table and payload class with `cs.*` field
metadata, JSON Schemas carrying a versioned `$id`, and DuckDB types are generated from the same
model. Agreement among projections generated from one model is **derivation conformance**, not
independent assurance; each contract names its independent semantic controls.

**Design text cites, it does not copy.** D2 and D3 cite the model and pack files and the generated
renderings by path and revision and keep only explanatory prose. Behaviour (canonical forms, keys,
locators, frames, the quote cascade, consolidation, queries) stays in ordinary domain functions over
the generated types; the model holds what things are and which rules apply, never algorithms.

**Replaced from ADR-0017:** its clause that hand-written Pydantic models own the core shapes with
`core.yaml` as their mirror. **Carried forward:** the pack owns the domain vocabulary; native LinkML
replaces `ci:` annotations wherever it carries the meaning; the batch JSON Schema is built from
Pydantic models generated per predicate, not by `gen-json-schema` (D2 §7.3); every consumer of a
pack is compiled from one source; its revisit trigger on logical inference.

## Consequences

- **Easier:** a qualifier, kind, vocabulary member or invariant is one declaration plus
  regeneration (S1, S2, S3/S7, S4 of the review); a business pack adds statement kinds, a modality
  with `attribution_identifying`, key roles and case policy by declaration alone (A3; the toy pack
  is the check); the D1 ↔ D3 restatement and D2's pack copies disappear; consumers stop testing
  literal kind subsets and restating defaults.
- **Harder:** the compilers are product code that must keep pace with LinkML releases (pinned:
  linkml-runtime 1.12.1, linkml 1.12.1 dev); generated modules are checked in with drift tests;
  Stage B carries generator risk, bounded by the fallback; the overlay must stay physical, or the
  revisit trigger applies.
- **Evidence:** the LinkML generator gaps and the `SchemaView` helpers are Interface-checked
  (installed LinkML 1.12.1, 2026-10-28); the pack's compilation to every consumer is Tested (S4,
  2026-10-28, records `s4.pack-lint`, `s4.batch-validation`); whether permissible-value `in_subset`
  passes `linkml-lint` and reads back is probe Q-2 (otherwise the `ci:properties` fallback, D2 §3).
  The rest is Proposed.
- **Not yet built:** the model modules, loader, declaration check and Stage A (P0-M-1); the
  relational compiler and overlay (P0-M-2); the interchange projections (P0-M-3); Stage B or its
  fallback (P0-M-5); probes Q-1 to Q-4. Disposition of DA-002, DA-003, DA-011, DA-012 and F01 is
  in the [phase 0 coordinator's §11](../plans/phase-0_2026-10-28.md#11-findings-disposition);
  acceptance of this record closes none of them.
- **Revisit** (front matter).
