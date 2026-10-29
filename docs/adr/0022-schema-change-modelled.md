---
id: ADR-0022
title: Schema change is modelled: revisions, a payload-schema registry and change records with compatibility classes
status: superseded
date: 2026-10-28
supersedes: []
superseded-by: ADR-0024
design: [§B5]
evidence: Proposed
revisit: A change PostgreSQL enforces or reads is wanted on the no-migration route; a real change fits none of the compatibility classes; readers come to carry upcast chains across many payload versions; or a pack change needs a data rewrite of authored artifacts.
---

## Context

Before this record, change was only partly modelled. D2 §8 classified pack changes as additive or
breaking, with a YAML mapping for breaking ones; `meta.schema_version.migration` held that mapping;
the schema-version hash covered `core.yaml` as a mirror. The core contracts, the key scheme, stored
payloads and derived artifacts carried no version, so a reader could only interpret a stored payload
under the current defaults ([DA-009](../design_review/audit/semantic-model-and-authority.md#da-009)).
Source profiles named schema vocabulary outside every schema version (DA-010). Re-location rewrote a
golden pass's citation frame in place, under results that had already scored it. D2 and D3 kept
copies of contracts with no version (DA-011).

The operator asked whether a structured schema could evolve without migrations. The
[domain-model alignment review](../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md)
answered in [§4.6](../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#callout):
sound for one class of data (immutable, versioned payloads that no constraint, key, index or query
reads, and their Parquet and DuckDB projections); unsound as a general route. It recommended R06:
change becomes part of the model. The operator accepted RC09 and RC12 on 2026-10-28
([coordinator §9.2](../plans/phase-0_2026-10-28.md#92-rule-changes-of-the-domain-model-alignment-review),
decision 19).

Expected changes: a method version adds an optional field to its payload; a pack adds a statement
kind or predicate; a predicate is renamed or split; a canonical form is fixed; a business qualifier
becomes something a query filters on; a source profile changes. Nothing is stored yet, so registries
and revision ids cost nothing to introduce now and much to retrofit after data exists.

Owners amended: DESIGN §B5; D2 §2 and §8; D3 §3 and §7. Consumers: the schema-version and model
revision registries (schema and rules), every payload reader and writer, Alembic, evaluation's frames
and items, the source-profile loader (ingest), the change records operators review.

## Options

1. **Keep D2 §8's two classes** (the simplest viable alternative): additive or breaking pack
   changes, a YAML mapping for breaking ones, payloads read under current defaults. Least machinery,
   but DA-009 stays: a stored payload has no schema identity, the key scheme and core contracts have
   no version, and the no-migration idea has no governed registry, so it could not safely be used.
   Rejected.
2. **The no-migration route as the general mechanism:** every evolution through a registry of
   payload schemas over JSONB, no DDL. Unsound wherever PostgreSQL enforces or reads the changed path
   (a CHECK, FK, index, generated column, view, query or partial predicate). Rejected as general; kept
   for its sound class.
3. **Migrations for everything, payloads included,** rewriting stored payloads in place. Observations
   are immutable and reused across runs by content, and input digests include upstream payload
   hashes, so an in-place rewrite silently changes what reused tasks depended on (DP-09, DP-19).
   Rejected.
4. **Payloads as files outside PostgreSQL** (Arrow IPC or Parquet referenced by rows). Breaks
   §B4's one transaction and can orphan files. Rejected for authoritative data; accepted for exports.
5. **Change modelled in the model** (chosen): revisions, a payload-schema registry, change records
   whose compatibility class decides the route, Alembic revisions linked to model revisions, and
   versioned derived artifacts.

Option 5 adds registries and a classifier over option 1. It retains what option 1 cannot: every
stored value names the schema it was written under, every change is routed by a declared class, and
the no-migration route is available exactly where it is sound.

## Decision

**Revisions.**

- A **model revision** covers `core` and `system` together: the LinkML `version`, the SHA-256 of
  the canonical JSON of the parsed `core` and `system` files (D2 §2's hashing rule), the compiler
  versions and the key-scheme version. The checked-in log `model/revisions.yaml` is the authority,
  one entry per revision with its change record; `meta.model_revision` is its projection. Every run
  records the revision it ran under, and a run whose recorded revision differs from the installed
  one is refused.
- A **schema version** covers a pack: D2 §2's hash, which now covers the model revision id instead
  of the mirror `core.yaml`, so the authority is inside the hash. The core `rules.yaml` stays a pack
  file of its own and is hashed into every schema version.
- A **payload schema** is one version of a nested payload class: a `meta.payload_schema` row with
  its JSON Schema `$id`, Arrow schema bytes, `sql_visible` paths, upcaster, compatibility class,
  reason and authorizing circumstance.
- The **key scheme** is versioned beside keys (ADR-0023).

**Schema identity on stored values.** Rows that outlive a model revision carry a
`payload_schema_id`: `kb.observation`, `eval.golden_pass`, `meta.compiled_artifact`,
`kb.rendition_build` and `ops.intervention`. Per-run materialized rows inherit the run's recorded
model revision, schema version and key scheme. Readers dispatch by the recorded schema and refuse an
unknown id with a typed error; a stored value is never reinterpreted under current defaults (DP-24).

**Change records.** One per revision step, held in the revision log (and `meta.model_revision`) for
`core` and `system` and in `meta.schema_version.migration` for packs. Each holds the from and to
revisions; the element changes, computed by an own `SchemaView` diff (LinkML has none); per change,
its compatibility class, reason and authorizing circumstance (the model rule under which this kind
of change is allowed, such as `method_version:<method>/<n>`); the migration mapping (an Alembic
revision, an upcaster or a name map); the key consequences (scheme change, carry-over map, affected
prefixes); the judgment carry-over; and the compiled artifacts and source profiles affected.

**Compatibility classes decide the route:**

| Class | Examples | Route | Keys |
|---|---|---|---|
| `descriptive` | descriptions, examples, titles | new revision or schema version; no DDL; dependent compiled artifacts change, so dependent work re-runs | unchanged |
| `nested-additive` | an optional field on a payload class; a nested closed-set member no CHECK lists | registry row with upcast "absent"; no DDL, no data rewrite | unchanged for existing data |
| `relational-additive` | a column, table, static enum member, index, edge kind; a newly `sql_visible` path | generated Alembic revision; no data rewrite | unchanged |
| `version-scoped-additive` | a pack adds a class, predicate, statement kind or enum member | new schema version; per-version vocabulary rows | unchanged |
| `mapped` | a rename, split or merge of a class, predicate, qualifier or member | name map applied when items are derived or payloads read; authored artifacts never rewritten; an Alembic data step only for relational data | affected keys move with a carry-over map |
| `key-bearing` | an identity-qualifier, canonical-form or key-part change | key-scheme version (core) or schema version (pack identity) with carry-over and new conformance vectors | keys move by the map |
| `breaking` | removal or narrowing without a mapping | refused unless an explicit decision is recorded | — |

The classifier checks each declared class against the diff; a `nested-additive` change that touches
an `sql_visible` path or a key-bearing path is refused.

**The no-migration route** is the `nested-additive` class, and applies only when all of these hold:
the class is a registered nested payload class; the change is backward-readable; no PostgreSQL CHECK,
FK, index, generated column, view, D3 §9 query path or partial predicate reads the changed path
(checked mechanically against the declared `sql_visible` paths and the overlay); no key, digest or
identity reads the path in a way the change alters; and an upcast from every still-referenced older
version is declared. It covers observation payloads, compiled-artifact bodies, golden batches and
frames, `parse_detail` and measurement `detail`, and their Parquet and DuckDB projections. Anything
PostgreSQL enforces or reads takes the migration route; the decision-relevant structure of knowledge
rows is rebuilt per run under the run's revision, so its "migration" is re-consolidation.

**Alembic is linked to the model.** Each revision carries the model revision it realizes through
`context.configure(template_args=…)`; `process_revision_directives` refuses a revision whose model
revision is not registered; `on_version_apply` records applications; `checkconstraint_byname` makes
named CHECK changes visible, and CHECK names carry a digest of their member list so a changed list
is a drop and an add.

**Derived artifacts are keyed on their derivation.** A `claim_proposal` payload records the cascade
version and schema version that derived its stored batch; a golden item is keyed by pass, rendition,
cascade version and schema version; a re-location adds a citation-frame version with a parent link
and never rewrites a frame; authored artifacts are never rewritten, and a rename map is applied when
items are derived from them. Compiled artifacts stay keyed by compiler version (D2 §7).

**Source profiles are model-governed data** (RC12, its model part). A profile is validated at load
against the profile class in `system`, whose domain-bearing slots range over core vocabulary
(statement kinds, segment kinds, core predicates); a run checks it against its schema version,
pack-scoped members included; change records list the profiles a change affects. The hints stay in
the profile, because they are facts about one source and the core vocabulary.

## Consequences

- **Easier:** a method can add an optional payload field with no DDL and no rewrite; every stored
  value names its schema, so old data stays readable or is refused, never misread; a key-bearing
  change is announced with a carry-over map instead of silently re-keying; results stay tied to the
  frames and items they scored.
- **Harder:** the registry and change records are written and reviewed with every revision; readers
  carry upcasters for every still-referenced version; the `SchemaView` diff and classifier are own
  code; an unregistered Alembic revision cannot be generated.
- **Evidence:** the Alembic hooks (`template_args`, `process_revision_directives`, `on_version_apply`,
  `ext/checkconstraint_byname`) are Interface-checked in installed Alembic 1.20.0 source
  (2026-10-28); DuckDB 2.0.0's VARIANT and `KV_METADATA` round trips are Interface-checked by a review
  contributor on scratch data (2026-10-28); the schema-version hash's stability is Tested (S4,
  record `s4.schema-hash`). The change model itself is Proposed.
- **Not yet built:** the revision log and `meta.model_revision` (P0-M-1, P0-S-1b), the registry,
  classifier, reader dispatch and Alembic hooks (P0-M-4), frame versions (evaluation and goldens),
  the source-profile model's validation (ingest; D4 M01 and D6 §7.2 text by P0-D-2). Disposition of
  DA-009, DA-010 and DA-011 is in the
  [phase 0 coordinator's §11](../plans/phase-0_2026-10-28.md#11-findings-disposition); acceptance
  of this record closes none of them.
- **Revisit** (front matter).

## Amendments

- 2026-10-29: a payload schema's first registered version carries the compatibility class `initial`; `meta.payload_schema` needs a class on every row and none of the seven fits a row with no parent (P0-M-4). No decision changes.
