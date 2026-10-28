# Phase 0 model and projections: the one model, its revision and every generated representation

**Status:** Proposed (2026-10-28). Part of the [phase 0 series](../phase-0_2026-10-28.md), which owns
shared decisions, contracts, the dependency graph and the findings table (§11), including every row of
the domain-model alignment review.

**Basis.** This document builds the alignment review's R01, R05 (its compiler), R06, and the generator
half of R10:
- [design review](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md),
  decision Revise;
- the [target model](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md),
  cited here as "TM";
- the [audit](../../design_review/audit/README.md), published in `f9695d3`.

It follows coordinator decisions 1, 18, 19 and 25 and the rule changes of coordinator §9.2: RC01, RC03,
RC04, RC05, RC06, RC09 and RC12.

**Baseline (2026-10-28):**
- P0-F-1, F-2a, I-0 and F-2b are built in `python/corpus-structure/src/corpus_structure/core/`.
- No product `core.yaml` exists; the only copy is S4's
  (`docs/design_review/evidence/2026-10-28_design-spikes/results/s4/schema/domains/core/schema/core.yaml`).
- `vocab.py` is hand-written: 39 enums mirroring D3's CHECK lists, `SegmentParseStatus` among them.
- D3's DDL text was planned as the specification for migration 0001.

Every design claim here is **Proposed** unless it carries another label.

## 1. What this document builds

The **corpus-structure model** is the single authority for the structure and meaning of the knowledge
the system stores, and of the system's own records. Every other representation is generated from it by a
pure function of `SchemaView`, checked in where `core` imports it, and covered by a drift test.

The model has three modules (TM §2):

| Module | Holds | Lives in | Changes with | Identity |
|---|---|---|---|---|
| `core` | Values, condition nodes, bindings, items per form, evidence, segment kinds, qualifier specifications, closed sets with member properties, the key-scheme declaration, `ExternalReference` | `python/corpus-structure/src/corpus_structure/model/core.yaml`, promoted from S4's mirror to authority | code releases | the **model revision** |
| `system` | The classes of `meta`, `ops`, `kb` and `eval`: runs, tasks, observations and their payload classes, materialized entities and claims, edges, evaluation rows, the registries; their closed sets, invariants and relationships; the source-profile class; the `EmbeddingSpec`; the unit-feature vocabulary used by `agent_reuse: by_unit` | `…/model/system.yaml` (new) | code releases | the model revision, together with `core` |
| Domain packs | Classes, predicates, schema qualifiers, enums, predicate subsets, `rules.yaml`, worked examples | `domains/<pack>/` (schema and rules) | data | the **schema version**: D2 §2's hash, which now covers the model revision id |

The parts this document builds:

- **the model loader and declaration check** (`schema/model.py`). It verifies that every project
  annotation has a named consumer (TM §4) and computes the model revision.
- **Stage A generation** into the checked-in `core/_model/`, plus the generated `core/vocab.py`.
- **Stage B generation** of the shape structure, or its fallback (§3.4).
- **The relational projection.** A generated SQLAlchemy `MetaData` (`core/db/_tables.py`) and a
  hand-written physical overlay (`core/db/overlay.py`).
- **The interchange projections.** Arrow schemas, JSON Schemas with a versioned `$id`, and DuckDB
  types and `SHREDDING` specs.
- **The schema-change model.** The revision log, the payload-schema registry content, change records
  with compatibility classes, reader dispatch, and the Alembic linkage.

What this document does not build:
- the per-version pack compilers, which are schema and rules' (S1);
- migration 0001 and the repository, which are foundations' (F4);
- the pool and exports, which are pool and interchange's (P).

## 2. Contracts

### 2.1 Consumed

| Contract | Owner |
|---|---|
| D1 shapes as built (`values.py`, `batch.py`, `candidates.py`, `payloads.py`), migrated rather than rewritten | foundations (F2b, reworked by F2c–F2e) |
| The rule routes of RC01, RC03–RC06 and RC09: ADR-0020 and ADR-0022; D2 §2, §3, §6, §8; D3 header, §1, §3, §5, §6 | coordinator P0-D-1 |
| S4's pack files and compiled rows, and S6's tested DDL, as the reference the first generated forms are compared against (TM §12) | evidence `s4.*`, `s6.*` |
| Probe results Q-1, Q-2, Q-3 (this document) and Q-4 (foundations) | `p0q.*` records |

### 2.2 Produced

| Contract | Consumers |
|---|---|
| The model files and the model revision (log file and `meta.model_revision`) | every document; runs record the revision (orchestration O1) |
| `core/_model/`: `QualifierSpec`s, defaults, local ↔ prefixed name tables, SQL-literal constants, templated validators | foundations (keys, shapes), schema and rules, ingest and math (locators, M01), orchestration, consolidation |
| The generated `core/vocab.py`: `StrEnum`s with member-property frozensets | orchestration (O0), every writer |
| The generated `MetaData` and the overlay | foundations (0001, repository), every SQL reader |
| Arrow schemas for every table and payload class | pool and interchange |
| JSON Schemas with `$id` per revision; a `referencing.Registry` builder | schema and rules, agent interface (`read_instructions`), pool and interchange (external consumers) |
| The payload-schema registry content, upcasters and reader dispatch | foundations (repository writes `payload_schema_id`), schema and rules (S1b registers), every payload reader |
| The change classifier and change records | schema and rules (schema versions), operators reviewing a revision |

## 3. Design of the parts

### 3.1 The model and its revision (M1)

**Promotion and authoring.**
- `core.yaml` is promoted from S4's file. Before Stage B, the file still mirrors the hand shapes for
  the facts Stage A does not generate.
- `system.yaml` declares the classes of D3's `meta`, `ops`, `kb` and `eval`, with:
  - their closed sets (TM §11 lists every vocabulary to model, with its lifecycle);
  - their invariants, through the `ci:invariant` templates;
  - their relationships, with ranges that the FK and edge placement read;
  - their payload classes (`ci:payload`, `ci:sql_visible`, `ci:null`).

  It also declares:
  - the source-profile class (RC12), typed against core vocabulary;
  - the `EmbeddingSpec`: model, dimension, metric, family id;
  - the unit-feature vocabulary that `by_unit`'s section → unit mapping ranges over (coordinator
    decision 15). The per-section mapping itself is declared beside the guideline's sections, under the
    guideline's own version (D7 §2), and is validated against this vocabulary; P0-D-2 writes the text.

**The model revision** (TM §2) is the LinkML `version`, the SHA-256 of the canonical JSON of the parsed
`core` and `system` files (D2 §2's hashing rule), the compiler versions and the key-scheme version.
- **The checked-in log**, `model/revisions.yaml`, is the authority: a list of entries
  `{label, content_hash, key_scheme, compilers, parent, change_record}`. Each entry holds a revision and its
  change record (§3.7).
- **`meta.model_revision`** is its projection, written by S1b's `ensure`. It stores the content hash and
  the change record, not the model source, which stays in Git at the revision; a run whose recorded
  revision differs from the installed one is refused by S1b's `compiled_for`.

**The declaration check** refuses three things:
- an annotation outside TM §4's vocabulary;
- an annotation without a consumer;
- a member property absent from the consuming code's generated set.

The annotation bar is AGENTS.md's: each declaration has a named consumer.

**Pack extension of core enums.** A schema-version-scoped closed set such as `ClaimModality` is
extended by a pack enum that declares `inherits: ClaimModality` (or composes with `include` / `minus`)
and adds its members, each with its member properties. This is native LinkML (operator, 2026-10-28;
linkml overview §3.4). linkml-runtime 1.12.1's `SchemaView.induced_enum` does not materialize enum
expressions, so the compilers expand `inherits`, `include` and `minus` themselves: M1 for core enums, S1
for pack enums into the per-version member rows. `code_set` / `code_set_version` and `meaning` remain
available for versioned vocabularies and ontology ties.

**Member properties.** These use native permissible-value `in_subset` if probe Q-2 confirms that
`linkml-lint` accepts it and `SchemaView` reads it back (`permissible_value_ancestors`,
`annotation_dict`). Otherwise they use one scalar `ci:properties` annotation per member, holding
space-separated property names. Examples:
- modality: `premise_forming` `{supposed}`, `attribution_identifying` `{cited}`, `conflict_bearing`
  `{asserted, defined}`;
- segment kind: `annotation_unit`, `statement_anchor`, `search_block` and `container` (the email
  kinds included);
- statement kind: `claim_bearing`.

### 3.2 Stage A generation (M1)

**`just model generate`** writes the following:

| Output | Contents |
|---|---|
| `core/_model/qualifiers.py` | `QualifierSpec`s for the core qualifiers (TM §8): range, default, key role, conditional role, canonical form by range, store placement |

**The `QualifierSpec` contract** (fixed 2026-10-28 so that F2d can be built against it):

| Field | Values |
|---|---|
| `name` | prefixed name |
| `local_name` | local name |
| `range` | class, enum or type name |
| `default` | `MISSING` or a value |
| `key_role` | `identity` \| `meaning` \| `inert` |
| `key_role_when` | member-property name, or `None` |
| `canonical` | `token_form` \| `text_form` \| `identifier` \| `enum` \| `entity_key` \| `interval` \| `map` \| `number` \| `verbatim` (TM §8) |
| `case` | `fold` \| `preserve` |
| `store` | `column` \| `json` \| `edge` |

Core specs are generated here. Pack specs are compiled by S1 into the same type.
| `core/_model/names.py` | Local ↔ prefixed name tables for core elements (the core half of X2-01; the pack map is S1's) |
| `core/_model/sql.py` | SQL-literal constants for the overlay and queries, such as the `search_block` kind list for the BM25 predicate |
| `core/_model/validators.py` | Validator functions generated from `ci:invariant` templates (`ordered`, `ordered_eq`, `iff_present`, `together`, `exactly_one`), called by the shapes and mirrored as CHECKs by M2 (F01) |
| `core/vocab.py` | Regenerated at its existing import path: one `StrEnum` per closed set, each member's properties as frozensets, and `lifecycle` metadata. The hand enums `DropReason` and `FrameFailureReason` (added by F2c) and `ConfidenceSource` (added by O0) are taken over with the same names and members; P0-D-2 may change members, and M1 regenerates |

`core/vocab.py`'s regeneration also makes these changes:
- `SegmentParseStatus` and `evidence.ParseStatus` merge into `DelimitingStatus`;
- `ParseStatus` (the formula outcome) is renamed `ParseOutcome`;
- the new sets `Stage`, `SkipReason`, `MarkupKind`, `InterventionTargetKind`, `JudgmentTargetKind`,
  `JudgmentDecision`, `JudgmentConfidence`, `VerificationVerdict`, `DropReason`,
  `FrameFailureReason` (introduced by F2c as hand enums and taken over by M1 with the same members) and
  `ConfidenceSource` are added, together with `GpuMode` (imported by `settings.py` and the `RunOptions`
  class) and `AgentMode` (`RunOptions` only; no setting supplies it; coordinator decision 26). Members
  follow the consumers: `SkipReason` (`scope`, `limit`, `budget`, `prerequisite_failed`,
  `run_cancelled`; orchestration §3.5) and `DropReason` (including `orphaned_premise`, `identity_cycle`,
  `malformed_evidence`; consolidation §3.7); the `system` method class carries a `ConfidenceSource`
  attribute. `ClaimModality` is schema-version-scoped, so packs may add members with properties;
- `PolicyChain` gains `gaps`.

**Consumer migration in the same package:**
- `batch.py`'s `Literal`s, `DEFAULT_MODALITY`, `CORE_QUALIFIERS` and `STORED_CORE_QUALIFIERS` read
  `_model`;
- `keys.statement_anchor` and `locators.annotation_units` read member-property sets instead of literal
  kind subsets (DA-003);
- the four span-ordering copies call the generated validator (F01).

The IR regression tests stay unchanged and must pass.

**The interim mirror guard** (TM §12) extends the contract test to every shape fact Stage A does not
generate: tags, bind kinds and binding fields, the item fields per form, `ci:form` / `ci:required_in`.
It also keeps the hand source-profile model in `ingest/profile.py` equal to the `system` source-profile
class until that model is generated (M5 covers it). It fails on a seeded difference on either side, and
it lasts until M5.

**Drift tests.** Regenerating into a temporary directory must reproduce every committed file byte for
byte. A hand edit fails.

### 3.3 Stage B, or its fallback (M5)

Probe **Q-1** decided the variant (`p0q.stage-b`, Tested 2026-10-28): **Stage B through a `PydanticGenerator`
subclass.** It reproduced every named feature, the four union aliases exactly, 35 of 45 classes structurally,
and agreed with the hand models on all 300 validations of S4's 135 batches. M5 carries the residue:
model additions (condition nodes, batch items, evidence, a qualifiers class, the envelope, an `Expression`
base, typed interval bounds, a declaration order matching the hand unions); three Stage B annotations
`ci:py_type`, `ci:validator`, `ci:py_name`; the hand private bases flattened into functions; `CitationFrame`
and `FrameEntry` and the canonical-decimal validator staying hand-written; JSON Schema descriptions moved
into the model. The fallback below is kept only as the route if the residue proves larger.

- **Stage B.** A `PydanticGenerator` subclass (overriding `generate_slot` and `get_class_slot_range`,
  with a `template_dir` for frozen config), or an own Jinja emitter over `SchemaView`, generates the
  shape structure:
  - discriminated `t` and `op` unions, with a named recursive `Condition`;
  - `ci:form` variants for the authored and stored forms;
  - `MISSING` defaults, frozen models with tuples, and prefixed aliases.

  It replaces the hand structure in `values.py`, `batch.py`, `candidates.py` and `payloads.py`, with
  behaviour kept in hand-written functions over the generated types. LinkML 1.12.1's `gen-pydantic`
  as-is emits no discriminators and no `MISSING`, and models its tag as a class-name default
  (Interface-checked, lib note A, 2026-10-28). That is why a subclass or own emitter is needed.
- **Fallback.** If Q-1 fails, an own emitter writes `core.yaml`'s shape classes from the Pydantic
  `model_fields`, through `SchemaBuilder`. The Pydantic shapes stay hand-written, and the model's shape
  classes become generated from them. Either way no hand-kept mirror remains, and the interim guard is
  retired.

Stage B blocks nothing (coordinator §7).

### 3.4 The relational projection and the overlay (M2)

**The compiler, `schema/relational.py`, builds `MetaData` from `SchemaView`** under R05's rules and
TM §6:
- **Classes:** a `system` class is a table, and a scalar slot is a column.
- **Closed sets:**
  - static closed sets are `text` columns with digest-named `CheckConstraint(col.in_(…))`;
  - version-scoped sets are per-version member tables, referenced by composite FKs
    `(schema_version_id, value)`.
- **References:**
  - single-valued class-ranged references are FKs;
  - multivalued or nested references are edge tables: `kb.claim_ref` and `kb.claim_entity_ref`, each
    keyed by `(claim_id, kind/role, path)` so parallel references stay distinct (CI-03);
  - identity attributes are `kb.entity_identity` rows.
- **Invariants:** `ci:invariant` templates become CHECKs.
- **Scalars moved out of JSONB:** `kb.claim` gains `modality`, `polarity`, `attribution_entity_id` and
  `schema_version_id`. The compiler also ties a row's `schema_version_id` to its run's recorded schema version (a
  composite FK `(run_id, schema_version_id)` to `ops.run`, or the bulk writer per Q-4); D3 leaves this open
  after P0-D-1.
- **Run and versioning tables and columns:**
  - `UNIQUE (run_id, id)` as the target of same-run composite FKs;
  - `kb.entity.resolved_to_id` for `ExternalReference`;
  - `ops.run.cut_at`, `ops.run.cut_m19_task_id` (the sealed final M19 task, DA-015) and the run's revision,
    schema and scheme columns;
  - `meta.model_revision` and `meta.payload_schema` (TM §9);
  - citation-frame versions: a frame-version relation for golden passes (and any authored frame), each
    version with a parent link, written by the consumer of a re-location (E1), never rewritten
    (coordinator decision 2; RC09); `eval.golden_item`'s unique key gains the cascade version and the
    schema version;
  - `payload_schema_id` on `kb.observation`, `eval.golden_pass`, `meta.compiled_artifact`,
    `kb.rendition_build` and `ops.intervention`.

**Naming.** `MetaData(naming_convention=…)` makes constraint names stable. `Identity(always=True)`
generates ids.

**INV-03 and INV-08** (same-run FKs) are enforced by FKs: probe Q-4 (`p0q.fk-cost`, Measured 2026-10-28)
found the cost acceptable at run scale. The compiler gives every composite FK whose columns no existing
index starts with a supporting index, for example `kb.claim (run_id, attribution_entity_id)`.

**Generator choice.** `RelationalModelTransformer` may be used as an intermediate model, but not
`gen-sqltables`. That generator emits native PostgreSQL enums, no CHECKs and no JSONB, and Alembic's
PostgreSQL implementation does not compare enum values (Interface-checked, lib note A).

**The overlay, `core/db/overlay.py`,** owns every physical access-path choice:
- the indexes: partial queue indexes, `task_unit`, `claim_ref_target`, `claim_entity_ref_entity`,
  `entity_identity_value`;
- the BM25 partial index, with `'english'::regconfig` and the kind predicate read from
  `_model.sql.SEARCH_BLOCK`;
- views, through SQLAlchemy 2.1's `CreateView`, or `DDL` where needed, carrying the run-cut predicate;
  the run's own finalize-stage outputs, which finish after the cut, are read by `cut_m19_task_id`;
- the extension assertion, by version: it reads F5's record of expected extension versions (DA-018),
  never mere presence.

It binds to generated tables by name and fails at import on a missing table or column. The model
declares no index or physical setting (TM §4: declarations judge representations, they do not prescribe
layout).

**Port check.** Probe Q-3 (`p0q.port-check`, Tested 2026-10-28) found the split sound: over 84 columns, 38
constraints and 12 indexes the only residue is the intended BM25 kind list, once four declarations are
added to the vocabulary (`ci:on_delete`, `ci:generated: insert_time`, `ci:sql_type`, the `iff_absent`
invariant template; D2 §3.4). The migration environment filters views with `include_object` on SQLAlchemy
2.1's `Table.is_view` (Alembic 1.20 has no view support, and `CreateView` leaves `Table.info` empty), and
avoids `compare_server_default` on the `regconfig` column (it crashes with `22P02`). The probe compared a
LinkML sketch of five D3 tables plus the overlay against S6's
tested DDL, through a normalized pglast 8.7 projection:
- columns, with type, nullability and default;
- the set of constraints;
- each index's `USING`, `WITH` and `WHERE`.

It compares those because raw AST equality fails on harmless differences. M2 then runs the full
comparison. The residue is listed and either removed or recorded with a reason, so S6's evidence carries
over to the generated form instead of being re-earned. `pglast.visitors.referenced_relations` also
checks that every D3 §9 query names only tables in `MetaData`.

### 3.5 Interchange projections (M3)

- **Arrow.** One schema per table and per payload class.
  - Field metadata `cs.model_revision`, `cs.class` and `cs.payload_schema_id`.
  - The `ci:null` policy: `never` forbids null; `json` carries the value as `arrow.json` text. Arrow
    has only null, so absent and null would otherwise collapse.
  - Recursive values (condition trees, nested values) travel as `arrow.json`.
  - No Arrow extension types: they have no kernels and DuckDB does not read them.
  - Byte form `Schema.serialize()`, with `pa.ipc.read_schema` round-trip tests.
- **JSON Schemas.** The existing `CoreJsonSchema` generator adds `$id = …/<model revision>/<name>`.
  - `Draft202012Validator.check_schema` runs on every artifact.
  - Agreement with Pydantic is derivation conformance (coordinator decision 24), not an independent
    oracle.
- **DuckDB.**
  - Column types from the Arrow schemas.
  - VARIANT `SHREDDING` specs generated from payload classes, for pool and interchange's exports.

### 3.6 The schema-change model (M4)

The **change record** (TM §9) holds:
- the from and to revisions;
- the element changes, from a `SchemaView` diff (own code; LinkML 1.12.1 has no schema diff);
- per change, its compatibility class, reason and authorizing circumstance;
- the migration mapping: an Alembic revision id, an upcaster, or a name map;
- the key consequences: scheme change, carry-over map, affected prefixes;
- the judgment carry-over;
- the compiled artifacts and source profiles it affects.

For `core` and `system` it lives in the revision log; for packs, in `meta.schema_version.migration`.

**Compatibility classes decide the route:**

| Class | Route |
|---|---|
| `descriptive` | new revision; no DDL |
| `nested-additive` | registry row with upcast "absent"; no DDL, no rewrite |
| `relational-additive` | generated Alembic revision |
| `version-scoped-additive` | new schema version |
| `mapped` | name map applied when items are derived or payloads read; authored artifacts never rewritten |
| `key-bearing` | new key scheme with carry-over and new conformance vectors |
| `breaking` | refused unless an explicit decision is recorded (DP-24) |

**The classifier** checks each declared class against the diff. A `nested-additive` change that touches
a `sql_visible` path or a key-bearing path is refused.

**The operator's no-migration route** is the `nested-additive` class, under the review's §4.6
conditions:
- the data is an immutable, versioned payload that no constraint, key, index or query reads, or a
  Parquet or DuckDB projection of one;
- the change is recorded with its reason and authorizing circumstance, for example
  `method_version:<method>/<n>`;
- readers dispatch by `payload_schema_id`.

Anything PostgreSQL enforces or reads takes the relational route. Authoritative payloads stored as files
outside PostgreSQL are rejected: they would sit outside the transaction.

**The payload-schema registry content** (`meta.payload_schema`, TM §9) holds, per payload class and
version:
- the JSON Schema `$id`;
- the Arrow schema bytes;
- the `sql_visible` paths;
- the upcaster name.

Readers dispatch by recorded schema and refuse an unknown id with a typed error.

**Alembic linkage** (Alembic 1.20, Interface-checked in installed source):
- `context.configure(template_args=…)` puts the model revision into `script.py.mako`;
- `process_revision_directives` refuses a revision not registered in the log;
- `on_version_apply` callbacks record applied revisions;
- `alembic.ext.checkconstraint_byname` makes named CHECK changes visible, by name only, so a changed
  expression under the same name needs a new digest name. Digest naming exists for this.

## 4. Probes

| Probe | Question | Decides | Evidence |
|---|---|---|---|
| **P0-M-Q1** (Q-1) | Can a `PydanticGenerator` subclass or an own emitter over S4's `core.yaml` produce the discriminated `t`/`op` unions with a named recursive `Condition`, `MISSING`, frozen tuples, both `ci:form` variants and prefixed aliases? Diff against `values.py` and `batch.py`; validate S4's 135 batches; compare the committed JSON Schemas byte for byte | M5's variant | `p0q.stage-b` |
| **P0-M-Q2** (Q-2) | Do permissible-value `in_subset` member properties pass `linkml-lint` and read back through `SchemaView`? | M1's declaration form | `p0q.member-properties` |
| **P0-M-Q3** (Q-3) | Generated `MetaData` from a LinkML sketch of five D3 tables plus the overlay, against S6's DDL through the pglast-normalized projection; Alembic autogenerate with a `CreateView` table, with and without `include_object` | What the overlay or compiler carries; M2's acceptance | `p0q.port-check` |

Evidence goes in `docs/design_review/evidence/2026-10-28_phase0-model-probes/`, owned by this series
(coordinator decision 10). Probes run in a scratch environment; none changes product code.

## 5. Packages

| Package | Scope | Prerequisites | Done when (closure evidence) | Closes (§11) |
|---|---|---|---|---|
| P0-M-Q1 | Probe Q-1 (§4) | none | Record finalized; M5's variant chosen | Q-1 |
| P0-M-Q2 | Probe Q-2 (§4) | none | Record finalized; declaration form chosen | Q-2 |
| P0-M-Q3 | Probe Q-3 (§4) | none | Record finalized; residue listed | Q-3 |
| P0-M-1 | Model modules, loader, declaration check, revision log; Stage A generation; generated `vocab.py` with the merges, renames and new sets; consumer migration; interim mirror guard; drift tests; `just model generate` and `just model check`; pins linkml-runtime 1.12.1 (`schema`) and linkml 1.12.1 (dev) | P0-D-1, P0-M-Q2, P0-F-2c | Every TM §11 set generated; no consumer tests a literal subset; the email kinds carry roles; drift test fails on a hand edit; interim guard fails on a seeded difference on either side; IR tests pass | DA-002, DA-003 (properties), DA-012 (vocabulary), F01 (validators), X2-01 (core half) |
| P0-M-2 | `MetaData` compiler and the checked-in `core/db/_tables.py`; overlay; the TM §6 and §9 tables and columns; INV-03 and INV-08 placement per Q-4; the pglast port check and the `referenced_relations` query check; pin pglast 8.7 (dev) | P0-M-1, P0-M-Q3, P0-F-Q4, P0-D-1 | Port-check residue empty or recorded; every CHECK digest-named; overlay import fails on a missing column; D3's queries name only `MetaData` tables | DA-011 (DDL), DA-003 (SQL literals), DA-012 (CHECKs), F01 (CHECK side), F04 (shape), DA-006 (store) |
| P0-M-3 | Arrow schemas with `cs.*` metadata and the null policy; JSON Schema `$id`; DuckDB types and `SHREDDING` specs; pin pyarrow 26 | P0-M-1, P0-M-2 | Schema byte round trip; every committed schema carries `$id`; derivation-conformance test | DA-009 (`$id`) |
| P0-M-4 | `SchemaView` diff and change classifier; change-record model; registry content; reader dispatch with typed refusal; Alembic hooks | P0-M-2, P0-M-3 | Each compatibility class classified and routed on a seeded change; an unregistered revision refused; an unknown `payload_schema_id` refused; a `nested-additive` change touching an `sql_visible` path refused | DA-009 (revisions, registry), DA-010 (profiles in change records), DA-011 (versions of copies) |
| P0-M-5 | Stage B or the fallback emitter per Q-1; interim guard retired | P0-M-Q1, P0-F-2e, P0-M-1 | No hand-kept mirror remains; every core test passes unchanged | DA-002, F01 (completion) |

## 6. Tests

- **Drift tests.** One per generated file; regeneration must be byte-identical.
- **Declaration check.** Seeded unknown annotations and consumer-less annotations are refused.
- **Interim mirror guard.** A seeded difference on each side fails (until M5).
- **Port check and query check** (M2).
- **Overlay import.** A missing column fails at import.
- **Arrow round trips.** Also a null-policy refusal: a `never` slot given null fails.
- **Change classifier.** One seeded change per compatibility class.
- **Registry.** Unknown-id refusal.
- **Alembic.** An unregistered revision is refused.
- **Independent controls** (coordinator decision 24): the negative store tests per invariant, written
  from D1 §11, are foundations' (F4). The probes' external comparisons against S4's batches and S6's
  DDL are the independent evidence here.

## 7. Indicative size

About 1,500 product lines: loader and check 250; Stage A and B generators 500; relational compiler 350;
overlay 150; interchange 100; change model 150. Generated files are excluded.

## 8. Choices left to implementation

- Whether `RelationalModelTransformer` serves as the intermediate model or the compiler reads
  `SchemaView` directly.
- The layout of `core/_model/` beyond the contracts above.
- The revision log's file format.
- How `just model` reports a drift.
- Whether a `nested-additive` upcaster is a function, or a declared default for "absent".
