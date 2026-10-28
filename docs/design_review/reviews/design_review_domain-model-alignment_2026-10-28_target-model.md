# Target model: the integrated corpus-structure data model

**Role.** This is a supporting document of the
[domain-model alignment review](design_review_domain-model-alignment_2026-10-28.md). It specifies,
at the precision subsequent planning needs, the target that recommendations R01–R12 describe:

- modules and lifecycles;
- concepts and contexts;
- the declaration vocabulary;
- each projection and its generator;
- the relational projection of knowledge;
- translations;
- the identity model;
- the schema-change model;
- where each data operation runs.

It makes no judgment of its own. The principal review owns the argument, findings, gates,
judgments, decision and rule impacts (review#RC01–RC19).

**Baseline and status.** Read against `6f31f75`, 2026-10-28. Everything here is **Proposed**
unless a line names stronger evidence. Table and column names are illustrative and settled in
planning.

## 1. What "integrated" means here

One model knows each representation and how each may change. Concretely:

1. **Each consequential fact has one authored declaration.** The facts in question:
   - closed-set members and member properties;
   - defaults;
   - qualifier specifications, including key roles;
   - cross-field invariants of the templated kinds;
   - relationships;
   - the class of each stored value.
2. **Every representation is generated from the model,** or it is a hand-written *physical
   overlay* bound by name to generated objects and checked at import. No representation is a
   second writable definition of a fact. The representations:
   - the Python `core` imports;
   - per-version Pydantic models;
   - SQLAlchemy `MetaData` and Alembic revisions;
   - CHECKs and FKs;
   - per-version vocabulary rows;
   - Arrow schemas;
   - JSON Schemas;
   - DuckDB types;
   - the rule-engine context;
   - the annotator reference.
3. **Every representation records the revision it was generated from:** a model revision, a
   schema version, a payload-schema version or a key scheme.
4. **Every allowed change is classified by the model** (§9). The class decides the route: no
   migration, a generated Alembic revision, a versioned upcast, or a key carry-over.
5. **Behaviour stays in ordinary domain functions** over the generated types: canonical forms,
   keys, locators, frames, the quote cascade, consolidation steps and queries. The model holds
   *what* things are and *which* rules apply. It holds no algorithms.

## 2. Modules, lifecycles and revision identity

| Module | Holds | Authored in | Changes with | Identity |
|---|---|---|---|---|
| `core` | The knowledge core: values, condition nodes, bindings, entity/statement/claim/alternative/unsupported items per form, evidence, segments and segment kinds, qualifier specs, closed sets with member properties, the key-scheme declaration, `ExternalReference` | LinkML (today's `domains/core/schema/core.yaml`, promoted from mirror to authority) | code releases | **model revision** |
| `system` | The classes of `meta`, `ops`, `kb`, `eval`: runs, tasks, observations and their payload classes, materialized entities and claims, edges, evaluation rows, registries; their closed sets, invariants and relationships | LinkML (a new module beside `core`; location is a planning choice) | code releases | **model revision** (with `core`) |
| Domain packs | Classes, predicates, schema qualifiers, enums, predicate subsets, `rules.yaml` (rules, guideline, views, tables, derive), worked examples | LinkML plus `rules.yaml` (as D2 §2) | data (operator and agent proposals) | **schema version**: D2 §2's hash, now also covering the model revision id |
| Source profiles | Per-source HTML conventions, with core-vocabulary hints | YAML validated by a profile model in `system` | data | content hash (already in `ingest.html`'s configuration hash); validated against the run's schema version |
| Physical overlay | Indexes, partial predicates, BM25/HNSW, views, extension assertion | Python (SQLAlchemy) bound by name to generated tables | code releases | part of the model revision's compiled output |
| Evidence records (tooling) | `Record` | Pydantic, `tools/evidence` (a separate bounded context) | tool releases | `Record.schema_version` |

**The model revision** is:

- the LinkML `version`;
- the SHA-256 of the canonical JSON of the parsed `core` and `system` files (D2 §2's hashing rule
  applied to them);
- the compiler versions;
- the key-scheme version.

It is recorded as a `meta.model_revision` row, and every run records the revision it ran under.
The schema-version hash of D2 §2 includes the model revision id instead of hashing `core.yaml` as a
mirror. The authority is then inside the hash, which closes DA-009's first gap.

## 3. Concepts and contexts

| Context | What it is | Names | Model classes it uses | Owned translation in |
|---|---|---|---|---|
| Authored batch | What an author writes, citing `sN`/`cN` | local | `core` item classes, authored form | T1 |
| Stored batch | The authored batch located on one rendition by the cascade | prefixed | `core` item classes, stored form, *with its rendition reference* | T1 → T2 |
| Keyed candidate set | The complete core claim set both rule call sites and consolidation read | prefixed | candidate classes: complete, typed references, `MISSING` | T2, T3 → T4 |
| Rule view | The derived read-only object rule-engine evaluates | prefixed classes; generated qualifier identifiers | generated typed context | T4 |
| Pool | The run's effective observations and candidates as relations | prefixed | Arrow relations generated from `system` and `core` | T3, T5 |
| Consolidated knowledge | Rows per run in `kb` | prefixed | `system` `kb` classes | T5 |
| Operations | Runs, tasks, fates, policies, measurements | — | `system` `ops` classes | T5 |
| Evaluation | Goldens (authored, derived), alignments, results | — | `system` `eval` classes | T1 (items), T5 |
| Decoding form | The JSON Schema given to constrained decoding | local | derived from the authored-form JSON Schema | T6 |
| Interchange and analytics | Arrow streams, Parquet exports, DuckDB relations | prefixed; registry ids in metadata | generated Arrow schemas | T5, T7 |
| Served answer | Typed query rows with keys, locators and coverage | prefixed | query result models | — (queries over T5 rows) |
| Evidence records | Spike and probe results | record ids | `Record` (tooling) | its own DuckDB projection |

The authored and stored forms of every item remain one declaration with `ci:form` attributes, as
in S4's `core.yaml`.

## 4. The declaration vocabulary

Native LinkML carries every meaning it can express (D2 §3). The project annotations below are
added only where a named consumer needs them, the bar AGENTS.md sets.

| Declaration | On | Meaning | Consumers |
|---|---|---|---|
| `ci:lifecycle: static \| schema_version` | enum | Static sets change with code and become CHECKs. Version-scoped sets can be extended by packs and become per-version rows with FKs | MetaData compiler; per-version models; Python generator |
| permissible-value `in_subset: [<property>]` (native) | enum member | Member properties, for example modality `premise_forming`, segment kind `search_block`, statement kind `claim_bearing` | keys, locators, consolidation, queries, generated SQL constants, rule view, reference. Replaces scalar `ci:claim_bearing` where native subsets suffice; probe Q-2 confirms lint and read-back |
| `ci:key_role: identity \| meaning \| inert` | qualifier slot | Whether the qualifier enters the claim key, carries meaning outside it (disagreement makes alternatives), or neither | `KeySchema`; C1 slots, alternatives and conflicts; rule view |
| `ci:key_role_when: <property>` | qualifier slot | The role applies only when the claim's modality has that property, for example attribution under `attribution_identifying` | `KeySchema` |
| `ci:case: fold \| preserve` | string-ranged slot; a class's label | Case policy for canonical forms and label normalization; `preserve` for math-bearing text | `KeySchema`, label normalization |
| `ci:form`, `ci:required_in` (existing) | value-class attribute | Form-specific fields | Python generator; the contract of T1 |
| `ci:stored_range: <class>` | slot | The stored form's range where it differs from the authored range (today only `scope`: `ScopeExtent` authored, `StoredScope` stored) | Python generator |
| `ci:invariant: <template>(…)` | class | One of a closed set of templates: `ordered(a, b)` (a < b), `ordered_eq(a, b)`, `iff_present(x, y = v)`, `together(a, b)`, `exactly_one(a, b)` | generated Pydantic validator **and** generated CHECK |
| `ci:store: table \| nested \| edge` | class or slot | Relational placement. Defaults are derived: system classes are tables; scalar slots are columns; single-valued class-ranged references are FKs; multivalued or nested references are edges; inlined value classes are nested | MetaData compiler; Arrow schema compiler |
| `ci:payload: <kind>` | nested class | The class is a registered payload schema for that kind (observation kind, compiled-artifact kind, …) | registry writer; readers' upcast dispatch |
| `ci:sql_visible: [paths]` | nested class | The paths PostgreSQL reads: CHECK, index, generated column, view, D3 §9 query | change classifier (§9); overlay check |
| `ci:null: never \| json` | nested slot | Whether Arrow null may stand for "absent" (`never`: null forbidden) or the value travels as `arrow.json` text | Arrow schema compiler |
| `ci:key_scheme: N` | schema (`core`) | The key-scheme version | runs, judgment targets, conformance vectors |
| LinkML `types:` (native) | schema | `Key`, `Locator`, `CanonicalDecimal`, `SentenceId`, `Timestamp`, each with its base type, pattern and projection type | all compilers |

Not added: no annotation for indexes, BM25 settings, operator classes or partial predicates. Those
are physical choices and belong in the overlay (FP-04: declarations judge representations; they
do not prescribe physical layout).

## 5. Projections

| Projection | Projects | Generator | Enforces | Rebuilt by | Changes by |
|---|---|---|---|---|---|
| `core/_model/` Python (checked in) | Stage A: enums, member-property sets, qualifier specs, defaults, name tables, SQL constants, templated validators. Stage B: shape classes | `schema` codegen (a `PydanticGenerator` subclass or own emitter over `SchemaView`) | Boundary validation (with the hand-written validators that remain) | regeneration; drift test | model revision |
| Per-version Pydantic models | Per-predicate claim branches, typed statement kinds and entity types, schema qualifiers | `create_model` from `SchemaView` (S4) | Submission and method-output validation | per schema version (`meta.compiled_artifact`) | schema version |
| SQLAlchemy `MetaData` + overlay | Tables, columns, types, CHECKs (enums by digest name; invariants), FKs, edge tables, per-version vocabulary FKs; overlay indexes and views | own compiler over `SchemaView` (optionally `RelationalModelTransformer`) | Store constraints | regeneration | model revision → generated Alembic revision |
| Alembic revisions | Differences between `MetaData` and the database | `alembic revision --autogenerate`, reviewed; `template_args` carry the model revision; `process_revision_directives` refuses an unregistered revision | Ordered DDL | — (append-only) | model revision |
| Per-version vocabulary rows (`meta.schema_*`, member tables) | Classes, slots, enums, rules of a schema version | schema-table compiler (existing) | FK targets for version-scoped values | per schema version | schema version; replacement becomes an upsert |
| Payload-schema registry (`meta.payload_schema`) | Each version of each nested payload class: JSON Schema `$id`, Arrow schema bytes, `sql_visible` paths, upcaster | registry writer | FK from payload-bearing rows | per model revision | nested-additive or mapped change (§9) |
| Arrow schemas | Every table and payload class; field metadata `cs.model_revision`, `cs.class`, `cs.payload_schema_id` | own compiler | none (Arrow enforces types, not meaning) | at import or as compiled artifact | model revision |
| JSON Schemas | Core shapes and per-version batch forms; `$id` carries the revision | `CoreJsonSchema` over the generated Pydantic | external validation (`referencing.Registry`); derivation check (not an oracle) | regeneration | revision |
| Decoding form | Per-version authored batch schema, transformed | existing pure transform (D2 §7.3) | constrained decoding | per schema version | schema version |
| Rule-engine context | Typed symbols from the model plus pack `views:` | existing (S4), with generated qualifier identifiers and collision check | compile-time rule typing; literal checks against vocabularies (R07) | per schema version | schema version |
| DuckDB types and exports | Arrow schemas; VARIANT `SHREDDING` from payload classes; `KV_METADATA` with registry ids | own small compiler | none (analytics) | per export | revision |
| Annotator reference | Classes, predicates, subsets, tables, shapes, examples | existing (S4) | — | per schema version | schema version |
| Design text | D2 and D3 cite model files and generated renderings by revision | — | — | — | — |

## 6. The relational projection of knowledge (sketch)

These changes apply to D3 §5. Columns not mentioned are unchanged. The SQL sketches shape, not
final DDL.

```sql
-- kb.claim: scalars that queries, slots and conflicts read become columns; integrity by FK
modality              text   NOT NULL DEFAULT 'asserted' CHECK (modality IN (/* generated */)),
polarity              text   NOT NULL DEFAULT 'positive' CHECK (polarity IN (/* generated */)),
attribution_entity_id bigint REFERENCES kb.entity,            -- same-run: composite FK, below
schema_version_id     bigint NOT NULL REFERENCES meta.schema_version,
FOREIGN KEY (schema_version_id, predicate) REFERENCES meta.schema_slot (schema_version_id, name),  -- INV-03
UNIQUE (run_id, id)                                            -- target of same-run composite FKs
-- qualifiers jsonb keeps hedge, conditions, scope, valid_time and the schema qualifiers;
-- modality, polarity and attribution leave it (equal meaning, equal JSON is preserved)

-- kb.entity
UNIQUE (run_id, id),
resolved_to_id bigint,                       -- ExternalReference only: the statement it resolved to
CHECK ((type = 'core:ExternalReference') OR resolved_to_id IS NULL)
-- statement kind against the run's schema version: a per-version member table
-- FOREIGN KEY (schema_version_id, kind) REFERENCES meta.statement_kind (schema_version_id, value)

-- claim → claim relationships derived from typed values (INV-08 by construction)
CREATE TABLE kb.claim_ref (
  run_id          bigint NOT NULL,
  claim_id        bigint NOT NULL,
  kind            text   NOT NULL CHECK (kind IN ('condition_premise', 'binding_param')),
  path            text   NOT NULL,           -- JSON pointer to the node: parallel references stay distinct (CI-03)
  target_claim_id bigint NOT NULL,
  PRIMARY KEY (claim_id, kind, path),
  FOREIGN KEY (run_id, claim_id)        REFERENCES kb.claim (run_id, id) ON DELETE CASCADE,
  FOREIGN KEY (run_id, target_claim_id) REFERENCES kb.claim (run_id, id) ON DELETE CASCADE
);
CREATE INDEX claim_ref_target ON kb.claim_ref (target_claim_id);

-- claim → entity relationships: entity-ranged qualifiers, pred arguments, binding entity targets
CREATE TABLE kb.claim_entity_ref (
  run_id    bigint NOT NULL,
  claim_id  bigint NOT NULL,
  role      text   NOT NULL,                 -- 'qualifier', 'pred_arg', 'binding_variable', 'binding_family_param'
  slot      text,                            -- the prefixed qualifier name for role 'qualifier'
  path      text   NOT NULL,
  entity_id bigint NOT NULL,
  PRIMARY KEY (claim_id, role, path),
  FOREIGN KEY (run_id, claim_id)  REFERENCES kb.claim  (run_id, id) ON DELETE CASCADE,
  FOREIGN KEY (run_id, entity_id) REFERENCES kb.entity (run_id, id) ON DELETE CASCADE
);
CREATE INDEX claim_entity_ref_entity ON kb.claim_entity_ref (entity_id, role);

-- identity attributes as rows (replacing kb.entity.attrs for identity)
CREATE TABLE kb.entity_identity (
  entity_id       bigint NOT NULL REFERENCES kb.entity ON DELETE CASCADE,
  slot            text   NOT NULL,           -- prefixed identity slot
  value_entity_id bigint REFERENCES kb.entity,
  value_text      text,
  PRIMARY KEY (entity_id, slot),
  CHECK ((value_entity_id IS NULL) <> (value_text IS NULL))
);
CREATE INDEX entity_identity_value ON kb.entity_identity (slot, value_entity_id);
```

Notes on these tables:

- **Writers.** The consolidation bulk writer writes edge and identity rows from typed instances in
  the same transaction as their claims and entities. They are derived and never edited.
- **When.** Because they serve queries, which refuse unfinished runs, they can be written only at
  the run's final pass.
- **Deletion.** D3 §8's delete order still holds: edges cascade from claims, and identity rows
  from entities.
- **Enforcement fallback.** Whether same-run integrity is enforced by FKs or by the bulk writer is
  settled by probe Q-4. The tables stay either way.
- **`ExternalReference`** is an entity class in `core`:
  - local scope, anchored at the citing statement's anchor segment;
  - identity: the citing statement key plus the descriptor's text form, and the author link
    target when present;
  - `kind` stays NULL, so D3's statement CHECK holds;
  - `resolved_to_id` records a resolution.

**What stays nested:**

| Value | Why nested | Governed by |
|---|---|---|
| condition-tree structure | recursive; read whole by z3, rules and rendering; its `claim` references are projected to `kb.claim_ref` | `core` `Condition` classes |
| schema qualifier maps (`param_values`, …) | read by path at small selectivity behind `claim_pred` (S6 Tested); a pack may declare a path `sql_visible`, which is then a relational change | pack classes |
| values, including bindings | typed unions; keyed in Python | `core` value classes |
| `valid_time` | ISO strings, possibly partial; a range type would be lossy; overlap is tested in the pool | `core` `IntervalValue` |
| observation payloads, golden batches and frames, compiled-artifact bodies, `parse_detail`, `cost`, `trigger_metrics`, measurement `detail` | immutable or per-attempt; versioned | registry (§9) |

## 7. Translations

Each translation is an ordinary function with a declared source and target. A test derived from
the model enumerates the source's slots, each either mapped or declared omitted (DP-08).

| ID | Translation | Owner | Preserves | Declared omissions and failures |
|---|---|---|---|---|
| T1 | authored → stored (local → prefixed names; frame resolution; quote cascade) | `validate` (names, checks); `methods.llm.parse` (cascade) | every item; names by the generated map; the rendition reference; `coarse` where a quote is unlocated | sentence ids replaced by offsets; refusal by typed frame reasons |
| T2 | stored → keyed candidate set | `validate` | entities, statements, `ExternalReference` items, claims with `establishment`/`derived_from`/`rule`, alternatives, unsupported items, rendition reference; typed references; `MISSING` | none silent |
| T3 | pool → keyed candidate set | `consolidate` | as T2, with supports (observation ids) | — |
| T4 | candidate → rule view | `validate` (view builder) | the generic facts of D5 §8.2 and pack `views:`; qualifier identifiers by the generated rule | read-only; no field written back |
| T5 | typed instance ↔ row / Arrow | generated codec | lossless round trip for every stored class: defaults as columns, `MISSING` as absent | none (a round-trip test per class) |
| T6 | authored JSON Schema → decoding form | `schema` | D2 §7.3's rules | descriptions, `discriminator`, `default` stripped (declared) |
| T7 | payload version upcast (vN → current) | the class's owner, declared in the change record | as declared | a missing upcast is a refusal |
| T8 | key carry-over (scheme N → M) | `core` keys | old key → new key over stored authored inputs | keys whose input is unavailable are reported, never guessed |

## 8. Identity model

**Qualifier specifications (core):**

| Qualifier | Range | Default | Key role | Condition | Canonical form | Store |
|---|---|---|---|---|---|---|
| `modality` | `ClaimModality` (static) | `asserted` | identity | — | the member value | `kb.claim.modality` |
| `polarity` | `Polarity` (static) | `positive` | identity | — | the member value | `kb.claim.polarity` |
| `hedge` | `PhraseValue` | — | meaning | — | text form (fold) | JSON |
| `attribution` | entity reference | — (the author) | meaning | identity when modality ∈ `attribution_identifying` (`{cited}`) | resolved entity key | `kb.claim.attribution_entity_id` |
| `conditions` | `Condition` | — | identity | — | D1 §7 canonical tree, leaves by range | JSON tree plus `kb.claim_ref` |
| `scope` | `ScopeExtent` (authored); `StoredScope` (stored) | — | meaning | — | extent plus segment locator (member keys only) | JSON |
| `valid_time` | `IntervalValue` | — | identity | — | canonical interval | JSON |

`statement` stays a key part of its own, beside the qualifiers, as in D1 §10.1. Schema qualifiers
take their key role from the pack: `ci:identity_qualifiers` becomes `ci:key_role` on the slot, or
the existing list is compiled into the same spec.

**Canonical form by range** (replacing the JSON-shape test):

| Range | Canonical form |
|---|---|
| `Formula`, `SetExpr` | token form over the rendition's effective macro table (ADR-0012) |
| `TextValue`, `PhraseValue` | text form: NFC, whitespace collapsed, case per policy (fold by default) |
| string identifier (`string` range, `ci:case` declared) | NFC, whitespace collapsed, declared case |
| enum | `{enum: <prefixed enum name>, v: <member>}` verbatim (enum names are normalized by prefixing, not by case) |
| entity class or `Entity` | the resolved key, after a kind check (T2) |
| `IntervalValue` | recursive over bounds and inclusivity |
| `MapEntry` subclass | object from key (NFC) to the canonical form of the entry's value range |
| `NumberValue` | canonical decimal; `unit` and `basis` collapsed (D1 §6.2) |
| `DateValue`, `BoolValue` | verbatim |

**Case policy.**

- `fold` applies to prose labels and prose literals.
- `preserve` applies to:
  - labels of classes declared math-bearing (`RandomVariable`, whose label is the defining
    expression when it has no symbol);
  - literal identity slots whose fallback is a symbol (`FamilyParameter.canonical_name`, under
    OPEN-D1-3's rule).
- Symbols already keep case (`symbol_form`). The two paths become consistent.

**Key scheme.**

- `ci:key_scheme: N` in `core`.
- Each run records the scheme of its keys, and each judgment target records the scheme of the key
  it names.
- A conformance vector per scheme holds hand-authored inputs (values, condition trees, entities
  with identity, statements on a small rendition) and their expected keys, pinned. A change to any
  output fails until the scheme moves.
- A scheme change ships a carry-over map (T8). Cross-run comparisons, carried judgments and
  reference-run key reuse go through the map when the schemes differ.

**Stability limits** (D1 §10.3, to be stated):

- locator regeneration (existing);
- the first-sentence ordinal shift within an anchor when an earlier sentence in that anchor is
  inserted or re-segmented (DA-014);
- key-derivation changes, which are handled only through scheme versions and carry-over.

## 9. The schema-change model

**Registries:**

```sql
CREATE TABLE meta.model_revision (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  label         text NOT NULL,          -- LinkML version of core/system
  content_hash  text NOT NULL UNIQUE,   -- canonical JSON of the parsed core and system files
  compilers     jsonb NOT NULL,         -- compiler name → version
  key_scheme    integer NOT NULL,
  parent_id     bigint REFERENCES meta.model_revision,
  change_record jsonb,                  -- below; null for the first revision
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE meta.payload_schema (
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  model_revision_id   bigint NOT NULL REFERENCES meta.model_revision,
  class               text NOT NULL,    -- prefixed class name, e.g. 'core:MentionPayload'
  kind                text NOT NULL,    -- what it is the payload of: an observation kind, a compiled-artifact kind, …
  version             integer NOT NULL,
  parent_id           bigint REFERENCES meta.payload_schema,
  compatibility_class text NOT NULL,    -- below
  json_schema_id      text NOT NULL,    -- $id of the generated JSON Schema
  arrow_schema        bytea NOT NULL,   -- Schema.serialize()
  sql_visible_paths   text[] NOT NULL DEFAULT '{}',
  upcaster            text,             -- name of the upcast from the parent version; null for an initial version
  reason              text NOT NULL,
  authorized_by       text NOT NULL,    -- the model rule permitting this change, e.g. 'method_version:mention.gliner/3'
  UNIQUE (class, version)
);
```

**Rows that carry a `payload_schema_id`** (rows that outlive a model revision):

- `kb.observation`;
- `eval.golden_pass` (batch and frame);
- `meta.compiled_artifact`;
- `kb.rendition_build` (`parse_detail`);
- `ops.intervention` (`refs`).

Per-run rows inherit the run's recorded `model_revision_id`, `schema_version_id` and key scheme.

**The change record** is held in `meta.model_revision.change_record` for core and system, and in
`meta.schema_version.migration` for packs (both extended). It holds:

- the from and to revisions;
- the element changes, from a `SchemaView` diff (own code; LinkML has no schema diff): added,
  removed, renamed (declared), range changed, member added or removed, property changed, key role
  changed, placement changed, invariant changed;
- per change: its compatibility class, reason and authorizing circumstance;
- the migration mapping: an Alembic revision id, an upcaster, or an old → new name map;
- the key consequences: a scheme change, the carry-over map reference, and the affected key
  prefixes;
- the judgment carry-over: by carry-over map, or orphaned with report;
- the compiled artifacts affected, which invalidates reuse through their hashes (D6 §4);
- the source profiles affected.

**Compatibility classes and routes:**

| Class | Examples | Route | Keys |
|---|---|---|---|
| `descriptive` | descriptions, examples, titles | new revision or schema version; no DDL; compiled artifacts change, so dependent work re-runs | unchanged |
| `nested-additive` | an optional field on a payload class; a new member of a nested closed set that no CHECK lists | registry row with upcast "absent"; **no DDL, no data rewrite**, under the conditions of the principal review §4.6 | unchanged for existing data |
| `relational-additive` | a column, table, static enum member, index, edge kind; a newly `sql_visible` path | generated Alembic revision; no data rewrite | unchanged |
| `version-scoped-additive` | a pack adds a class, predicate, statement kind or enum member | new schema version; per-version vocabulary rows | unchanged |
| `mapped` | a rename, split or merge of a class, predicate, qualifier or member | new revision or schema version with a name map, applied when items are derived or payloads read; authored artifacts are never rewritten; an Alembic data step only for relational data | prefixed names enter keys, so affected keys move with a carry-over map |
| `key-bearing` | an identity-qualifier change, a canonical-form change, a key-part change | key-scheme version (core) or schema version (pack identity) with carry-over and new conformance vectors | keys move by the map |
| `breaking` | removal or narrowing without a mapping | refused unless an explicit decision is recorded (DP-24) | — |

## 10. Where each data operation runs

| Operation | Shape | Engine | Determinism rule |
|---|---|---|---|
| `canonical_json`, digests, keys, `text_form`, `normalize_label`, `symbol_form`, token form | per-item recursive normalization | Python | exact (one implementation; Unicode tables of Python 3.14) |
| Locators (generate, resolve), annotation units | sorted prefix index, prepared once per rendition | Python | exact |
| Quote cascade (regex, rapidfuzz) | per-item | Python | step and edit counts recorded |
| Math grammar, SymPy, z3, pgmpy, `linear_sum_assignment`, bootstrap | non-relational | Python | as their own contracts (S0 checked the bootstrap to one ulp) |
| Symbol-binding rules (D5 §4) | per-unit, first appearance | Python over hydrated objects | exact |
| Keying in topological order of condition references | recursive over per-item keys | Python | exact |
| Mention clustering (IoU within a segment) | interval join | DuckDB | set result; ties by key |
| Alias-equality linking (phase 0 stand-in for M14) | equality join | DuckDB (pool) or PostgreSQL | set result |
| M14 candidate ranking (phase 2, bulk) | top-k similarity | DuckDB `NEAREST` over exported vectors, or PostgreSQL HNSW for serving | ranked by score, then key |
| Merges: union-find with cannot-links (phase 2) | components | Python with a declared order (score, then key); or DuckDB `USING KEY` if refusal is made order-independent (F03) | partition by membership |
| Fusion by key; slots; alternative groups | group-by | DuckDB | set result |
| Refinement ("strictly extends"), deterministic tie-breaks | pairwise test | Python over grouped rows | smallest key wins (D5 §5.3) |
| Conflict (same subject, functional predicate, overlapping validity) | self-join | DuckDB; satisfiability in z3 | set result |
| Rule-view cached facts; pack `views:` | joins and group-bys | DuckDB (compiled from `views:`) | set result |
| Rule evaluation | per row | Python (rule-engine) | deterministic contexts (D2 §7.4) |
| Noisy-OR confidence (phase 1) | product aggregate | DuckDB ordered aggregate | `ORDER BY` key |
| Materialization, deletion, fates, `kb.run_observation`, coverage | transactional sets | PostgreSQL | as of the run's cut (R08) |
| Typed queries (D8) | indexed joins | PostgreSQL | pinned run |
| Run diffs, experiments | full outer join on key | DuckDB over finished runs (Parquet, or a `READ_ONLY` attach with NUMERIC handled) | key order |
| Evaluation candidate pairs; score aggregates | join; group-by | DuckDB; assignment in SciPy | ordered sums |
| Exports; payload analytics | projection; VARIANT shredding | DuckDB `COPY … KV_METADATA` | `ORDER_BY` declared |
| Streaming re-encodes | read → project → write | PyArrow 26 Acero (optional; experimental) | set result |

## 11. Vocabularies to model

**Static (CHECK)**, the current `vocab.py` sets plus:

- `ClaimModality`, `Polarity`, `ScopeExtent`, `EntityExtent`, `BindKind`;
- `ParseOutcome`, the formula outcome, renamed from `ParseStatus`;
- `DelimitingStatus`, the segment and rendition parse status: one definition, replacing
  `evidence.ParseStatus` and `vocab.SegmentParseStatus`;
- `SegmentKind`;
- `Stage` (new; `ops.task.stage`);
- `SkipReason` (new; `ops.task.reason`, free text in D3 today although coverage groups by it);
- `MarkupKind`;
- `InterventionTargetKind`, `JudgmentTargetKind`;
- `JudgmentDecision`, `JudgmentConfidence`;
- `VerificationVerdict`;
- `DropReason` and `FrameFailureReason` (new; R07);
- `ConfidenceSource` and its per-source states (new; D5 §6.2);
- `PolicyChain`, including `gaps`: the prior review found it absent from the CHECK.

**Schema-version-scoped (per-version rows and FKs):**

- `StatementKind`: core members plus pack members;
- entity classes;
- predicates and schema qualifiers;
- pack enums;
- `ConditionPredicate`;
- predicate subsets.

**Member properties** (each with its consumers):

- **`ClaimModality`:**
  - `premise_forming` `{supposed}`: D8 defaults, INV-06;
  - `attribution_identifying` `{cited}`: keys;
  - `conflict_bearing` `{asserted, defined}`: D5 §5.5;
  - `reserved` `{posed}`: the guideline.
- **`SegmentKind`:**
  - `annotation_unit` `{unit}` and `top_level_annotation_unit` `{paragraph}`: locators, keys;
  - `statement_anchor` `{unit, details}`: keys;
  - `search_block` `{paragraph, heading, list_item, caption}`: the BM25 index and query predicate;
  - `section_like` `{document, section}` and `label` `{heading}`: the current `_NOT_UNCOVERED`;
  - `container`;
  - the email kinds' roles, decided with the email adapter. The model gives them a place;
    `email_message` would carry `annotation_unit` and `container`.
- **`StatementKind`:** `claim_bearing`, read by policies and by D6 §7.2's override order.

## 12. Transition (preservation constraints, not a schedule)

- No production data, keys or migration 0001 exist yet. Every change above is a design change, not
  a data migration.
- **Interim guard.** Until Stage A generates a fact, the mirror contract test is extended to cover
  it. This is the audit's lead, and it makes the interim state G1-safe.
- **Carrying the evidence over.** The S6-tested DDL and S4's compiled rows are the reference for
  the first generated `MetaData` and schema-table rows, through the pglast-normalized comparison of
  probe Q-3. S6's evidence then carries over to the generated form instead of being re-earned.
- **Key freeze.** Key functions freeze, as `tex.py` will on `s5.keys-property`, only after R02's
  specifications and R03's typed dispatch are in. The first conformance vector is written at that
  freeze.
