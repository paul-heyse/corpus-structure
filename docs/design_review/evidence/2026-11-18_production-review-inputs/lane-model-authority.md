# Lane: model authority, re-read at `d78c98765`

**Interface-checked by source inspection, 2026-11-18**, frozen snapshot `snap5/` of `d78c98765`.
Nothing was run. Paths are relative to `snap5/python/corpus-structure/src/corpus_structure/`
unless they start with `domains/` (read with `git show d78c98765:domains/...`, because the snapshot
omits `domains/`) or `model/`, which is also under the package. History comes from read-only
`git log fbd3f2a98..d78c98765`.

**Read fully:** the six findings and the cited audit sections; `data_operation_compiler_native.py:440–552, 900–935`;
`data_validity_native.py:1–340`; `contextual_admission_native.py:1–60, 205–235`;
`data_completion_settlement_native.py:525–600, 700–800`; `change_impact.py:150–200, 332–441`;
`support_trust_native.py:80–125`; `data_operation_storage.py:50–140, 1830–1965`;
`target_installation.py:195–375`; `alembic_privileges.py:1–80`; `schema/model_change.py:45–70, 520–560`;
`schema/generate.py:540–580`; `schema/physical.py:140–197`; the `SchemaView` composition sites.
**Sampled:** `schema/relational.py` (annotation readers), the model YAML (feature counts by
search, headers, `data-operation-physical.yaml:60–100`), `data_operation_model.py` (dataclass
fields), Arrow schema sites, `sql/admission.sql` (role literals). **Not read:** generator bodies
for equivalence with the SQL they replaced, `ontology.py` beyond the dynamic-enum block,
`conditional_rules.py`, `schema/stage_b.py`, `rulelang.py`, the DuckDB modules beyond their schemas.

## 1. Re-examination of the findings

**The earlier observation holds at `d78c98765`.** The conversion "changed how statements are
written, not where their facts come from" for every fact in this lane's findings. The hand
lists were moved into Python, often word for word, as SQLAlchemy `in_()` tuples, `case()`
mappings or `for name in (...)` loops. None of them is read from a declaration. In several places,
including the family guards and validators, they remain raw PL/pgSQL text inside Python strings.
**Contrary evidence:** physical immutability, archive roles, physical value sets (`ph:values_from`)
and public-function grants (protocol `purposes`) do derive from declarations, as listed in §5. One
membership, shared-stream triggers, has a declaration available that the code does not read
(§4, N2).

### DA-070: validity families, assigned from operation-id lists, fail open. Status: **stands, changed footprint**

- **Classification.** `_classify_programs(model)` holds the seven families and their 27 ids as a
  Python tuple (`semantic/data_operation_compiler_native.py:470–519`) and renders
  `ops.ddo_classify_validity` as `CASE operation IN (...)` with no `else`, so the result is NULL
  (`:520–529`). The `model` parameter is unused for this purpose. Release lowering stores the
  result: `validity_family := ops.ddo_classify_validity(lowered.operation_id)` (`:920–926`). The
  archived effective operation (`operation`) is in scope at that point, and `dependencies` is
  lowered from it in the same block (`:905–911`).
  Moved by `937d98415` (compiler) and `555e28d59`. `semantic/sql/data_operations.sql` was deleted in `2910d9817`.
- **Dispatch.** `semantic/data_validity_native.py:272–288`: a *second* tuple maps family names to
  validator owners, and `case(..., value=definitions.c.validity_family, else_=True)` handles everything else.
  Fail-open dispatch is unchanged. There are now **two** family-name lists. A family returned by
  the classifier but missing from the dispatch tuple also takes `else_=True`. Moved by `d422c48e7`.
- **Column.** `validity_family: {range: string, required: false}`
  (`model/semantic/data-operation-physical.yaml:88`) has no enum and no check, so any string or NULL
  is accepted.
- **Self-selecting guards and validators.** Unchanged in substance. Completion calls every
  family guard unconditionally from a Python tuple
  (`semantic/data_completion_settlement_native.py:538–553`, loop `:566–590`), with an
  operation-event id list inlined at `:570–576`. Each guard selects itself with
  `IF r.operation_id NOT IN (...) THEN RETURN`, still as hand-written SQL text:
  `contextual_admission_native.py:16–21` (full list of 12), `:214–219` (validator, `RETURN true`);
  `definition_admission_native.py:83, 106, 124`; `rich_admission_native.py:183`. The record-grade
  validator, now typed, self-selects with `If(operation.is_distinct_from(GRADE_OPERATION), Return(True))`
  (`record_grade_native.py:691`). `ddo_require_completion_live` remains a chain of `If` on literal
  operation ids (`data_completion_settlement_native.py:714–800+`).
- **Per-operation contract restatement.** The contextual guard still restates each operation's
  prepared-factory entry point, profile, forms and CPU-receipt count as SQL `CASE` over ids
  (`contextual_admission_native.py:23–44`). These are facts the compiled model holds per operation
  (`EffectiveOperation.profile`, `capabilities.forms`, `capabilities.prepared_factory.entrypoint`;
  `semantic/data_operation_model.py:288–296, 495–526`).
- **Commits.** `contextual_admission_native.py` has no commit in `fbd3f2a98..d78c98765`.
- **Consequence now.** The same as before. An operation omitted from either list skips its
  family's dependency premises, and from a guard list its completion checks. Changing premises are
  lost for record grade, record fit, operation events and contextual scores.
- **Uncertainty.** Whether a dispatch tuple entry naming a non-existent
  `ddo_<owner>_dependencies_valid` would fail at install or only at first call (PL/pgSQL defers
  name resolution) was not established.
- **What closes it.** The audit's own condition: the compiler takes family membership from the
  model and refuses an undeclared operation. That condition is unmet. The plan step "DDO kernels
  through Core and a finite compiler" delivered a Python transcription, which the audit said
  keeps the cause.

### DA-071: support-graph meaning encoded three times. Status: **stands. Three encodings, all now Python; the disagreement is unchanged**

- Validity edges: `ops.ddo_validity_edges` is a typed program
  (`semantic/data_validity_native.py:88–240`). For a `use`, alternative 1 follows producer,
  populations and episode. Alternative 2 is gated by `value_substitution`, follows the selected
  support and maps references to nodes inline (`:171–190`). Scope key: `ops.ddo_scope`
  (`semantic/support_trust_native.py:100–118`) returns `project:` when the source is NULL,
  otherwise `source:`.
- Locks, read scopes and universes: `_support_walk`
  (`semantic/data_operation_projections.py:132–242`), with its own `_reference_node`
  (`:117`). It has four consumers (`:363, 468, 1071, 1586`).
- Change impact: `_revocation_causes` (`semantic/change_impact.py:332–441`), with a third
  `reference_node` (`:345–350`). It follows the episode with no expansion (`:364–366`),
  follows selected support always, and has an unconditional `"source:"` scope (`:427`).
  `changed_operations` rebuilds the dependency graph by hand (`:157–193`) beside the compiled
  `potential-producers` / `selected-dependencies` projections (`data_operation_model.py:713–725`).
- `change_impact.py` has **no commit** in the range. The two disagreements recorded at `fbd3f2a98`
  are therefore unchanged: missing episode expansion and the scope prefix.
- Dependency lists are still checked only for resolution (`data_operation_compilation.py:1830–1838`).
- **Consequence.** As recorded: weaker or wrong change-impact explanations, not wrong admission.
  A new edge kind needs three edits, and now also three reference-to-node mappings.
- **Count.** The audit predicted the conversion would leave "two at best". It left three, because the
  validity copy became Python Core rather than being derived.

### DA-072: earlier core and system model still live. Status: **stands, cited lines moved**

- `model/core.yaml` (1096 lines), `model/system.yaml` (2023) and `model/revisions.yaml` (1118)
  are still generated into `core/vocab.py` and `core/_model/*` by `schema/generate.py:540–578`, which
  is the only self-checking generator registry and covers *only* this earlier model. They are read
  by `schema/model.py:57–59, 235` (two `SchemaView`s). The earlier pack loader is `schema/pack.py:232`
  (`importmap={"core": ...}`).
- `StatementKind`, `ClaimModality`, `StatementRole`, `EvidenceRole`, `Establishment` and
  `ScopeExtent` are each declared in both `model/core.yaml` and `model/semantic/core.yaml` (search, 2026-11-18). The pairs
  `PdfObservationOutcome`/`DdoPdfObservationOutcome` and `ParseOutcome`/`RuleReadingOutcome`
  remain.
- 39 modules still import `core.vocab`, `core._model` or `core.keys`, including
  `semantic/native_call_generation.py:106`, which emits `from corpus_structure.core.vocab import
  TaskUnitType` into a generated *released-model* facade. So the earlier model feeds the released
  model's generated code.
- Every model-change preview still loads and logs the earlier model
  (`schema/model_change.py:590, 633–670`). `semantic/regeneration.py:86`, `pdf_lowering.py:102, 119`
  and `pdf_domain.py:92, 156` read `model/semantic/core.yaml`, the released core.
- `domains/statistics/schema/statistics.yaml` still `imports: [linkml:types, core]`, which is the
  earlier core, beside `domains/statistics/semantic.yaml` (`imports: [semantic_core,
  statistics_terminology]`).
- No commit in the range touched these owners.

### DA-073: release membership composed by flag logic. Status: **stands unchanged**

`domains/statistics/operations.yaml` still names flags, not operations (`source_bindings`,
`pdf_contracts`, `protected_*`, `primary_profile.visual/downstream/...`). None of
`primary_operations.py`, `data_operation_preparation.py`, `canonical_sentences.py`,
`characterization_ports.py`, `hanlp_products.py` or `domains/` has a commit in
`fbd3f2a98..d78c98765`. The audit's line references stand.

### DA-074: authorization and guard membership as code lists. Status: **stands. Membership unchanged; one sub-item now has an unread declaration**

- Frontier guard: a 12-name tuple (`semantic/data_operation_storage.py:1934–1960`). The trigger is
  still a concatenated `CREATE TRIGGER` string passed to `definition_from_sql`. All 16 candidate
  DDO relations have `ph:immutability: intrinsic` (search), so no declared attribute separates the
  guarded relations from the unguarded ones (`data_product`, `data_publication_receipt`,
  `data_intent_adoption`, `data_attempt_failure`, `data_revocation`).
- Shared-stream triggers: chosen by name,
  `relation.fullname in {"ops.pdf_shared_stream", "ops.pdf_shared_stream_part"}`
  (`semantic/target_installation.py:350`). The model **already declares** exactly these two, and only
  these two, as `ph:immutability: pending-content` (`model/semantic/physical.yaml:1757, 1776`), and
  nothing reads that value (search: no Python consumer of `pending-content`). See N2.
- Function grants: protocol functions derive their roles from declared `purposes`
  (`data_operation_storage.py:1882–1891`). This is sound, but the purpose→role map is a literal dict
  there. Non-protocol functions are an `elif name == ...` chain (`:1892–1914`). Target installation
  holds `(file, schema, name, roles)` tuples (`target_installation.py:209–244`) and a
  runtime-binding grant (`:266–277`).
- Default table read roles are `DEFAULT_READ_ROLES` (`semantic/alembic_privileges.py:25–33`),
  applied when `ph:read_roles` is absent (`:74–75`). Every `ph:read_roles` in the model is `'[]'`
  (84 relations, search), so the annotation only ever *denies*, and the grants come from code.
  The same four-role default is restated **twice more as JSON text** inside
  `semantic/sql/admission.sql:148`. Role sets, prohibited memberships and earlier private kernel
  signatures remain literals at `admission.sql:130, 162–186`. `admission.sql` is still a
  hand-written file, read through `native_authoring.py:805`.
- Commits touching membership: none. Rendering changed in `30bf7ec6c`, `455405a8d` and `4f38ddead`.

### DA-081: generated facades registered twice by hand. Status: **stands, lines moved**

`_NATIVE_OUTPUTS` (`schema/model_change.py:53–61`) and a positional tuple of generator calls
(`:538–548`) are paired by `zip(strict=True)` (`:551`). Owners name their own paths and writers
(`semantic/typed_generation.py:87, 105, 116–117`; `pdf_call_generation.py:27, 35`;
`original_document_contracts.py:229, 243`), and `_pdf_native_ids.py` and `_pdf_native_calls.py`
appear a third time in `pdf_lowering.py:33–72` (`LOWERING_FILES`). The self-checking registry
(`schema/generate.py:540–578`) belongs to the earlier model only, so **the released model has no
generator registry at all**. Last touched in `708c119a6`, before the earlier delta.

## 2. Model map, refreshed

### Declaration owners

**LinkML, released model (`model/semantic/`, 45 schema files).** By role:

- **Semantic core and packs.** `core.yaml` (`semantic_core`: statement and record vocabulary,
  imported by packs); `observations.yaml`; `characterization.yaml` (imports `observations`);
  `reference.yaml`; `rule-view.yaml` (Entity, Value, Statement, Claim, `RuleReadingOutcome`);
  `scientific.yaml`; `agent.yaml`; `analytics.yaml`; `analysis-policies.yaml`;
  `native-adapters.yaml`; `selected-source.yaml`.
- **Product kinds per operation family.** `data-operation-*.yaml` (sentences, hanlp, learned,
  contextual, constructions, characterization, interpretation, record-policy, references,
  assessment, rich-proposals, pdf-capture, pdf-region, visual, external-extraction, source*,
  candidate-inspection, definition-location, reading-resolution). These form a DAG through `imports`
  (for example, learned imports source, source-discovery, candidate-inspection and constructions).
- **PDF.** `pdf-products.yaml`, `pdf-records.yaml`, `pdf-staging.yaml`, `pdf-payloads.yaml`.
- **Physical.** `physical.yaml` is the root and imports `linkml:types`, `pdf-records`,
  `pdf-staging`, `data-operation-physical` and `data-operation-task-physical`. It declares tables as classes in
  `in_subset` schemas, with `unique_keys` (144) and the `ph:` annotations.
- **Projections.** `read-projections.yaml` (imports `physical`, `rv:` annotations);
  `companion-projections.yaml` (imports pdf-*; `cp:` annotations carrying a JSON query AST in
  `cp:sources`/`cp:helpers`); `operation-reports.yaml` (imports pdf_products, observations).
- **Physical annotation keys** (counts, search): `ph:foreign_keys` 117, `ph:immutability` 116,
  `ph:read_roles` 84 (all `'[]'`), `ph:checks` 68 (JSON predicate ASTs with hashed names),
  `ph:indexes` 32, `ph:archive_role` 15, `ph:sql_type` 10, `ph:python_type` 8,
  `ph:generated_*`, `ph:values_from` 3, `ph:server_default_*`, `ph:identity`,
  `ph:search_configuration` 1. Other prefixes: `cp:` 177, `ci:` 57, `cs:` 42 (`cs:data_universe`),
  `rv:` 37, `pds:`/`pdp:`/`pdr:`.

**Non-LinkML declarations in the model directory** (the model is plural in formalism):

- `data-operation-native.yaml` (3007 lines, the largest model file) is a **JSON Schema draft-7**
  document. It has `definitions`, `x-ddo-lifecycle` extensions for states and transitions, and an
  `operations:` block from `:2783` with per-function `purposes`. It is the protocol, and wire types,
  fates and physical value sets derive from it.
- `data-operation-wire-types.yaml`: a map from JSON-pointer to nominal type.
- `pdf-actions.yaml` (1987 lines): a PDF action and call catalog.
- `analysis-policy.yaml`, `metrics.yaml`, `scientific-policies.yaml` (policy decision table) and
  `characterization-questions.yaml`.
- JSON: `analytical-profile.json`, `operation-report-schemas.json`, `pdf-observation-meaning.json`,
  `nce-section-packets.json`, `section-text-recipe.json`, `docling-validation.schema.json`.

**Earlier model:** `model/core.yaml`, `model/system.yaml` (`ci:payload` classes) and
`model/revisions.yaml` (revision log, not LinkML).

**Operations** are not in LinkML. They are `__data_operation__` dict literals in **85 Python
modules** (search), extracted statically, for example `methods/contextual_scoring.py:110–135`.
`dependencies`, `capabilities`, `numerical_policy`, enforcement claims and coverage live there. The
declaration grammar is a hand-written validator (`data_operation_compilation.py:143–188` helpers,
`_PROFILES :85`, `_KIND_UNIVERSES :341`), not a schema.

**Packs (`domains/`).**

- `statistics/semantic.yaml`: `statistics_semantic`, importing `semantic_core` and
  `statistics_terminology`.
- `statistics/terminology.yaml`: LinkML enums with STATO `meaning:`s.
- `statistics/terminology/sources/*-valuesets-0.4.2.yaml`: vendored copies of `valuesets`
  schemas. The Python package is not imported (search).
- `statistics/schema/statistics.yaml`: the earlier-model pack.
- `*/schema/rules.yaml`: a custom rule language (`schema/rulelang.py`), not LinkML `rules`.
- `operations.yaml`, `methods.yaml`, `slices.yaml`, `construction.yaml` and `profiles/*`.
- Toy pack: the same shape.

### LinkML features

**Used** (counts by search over `model/`): `is_a` 446; `attributes` 730 (classes are mostly
attribute-local, with few shared slots); `slot_usage` 40; `mixins` 32 (but no `mixin: true`
declarations); `abstract` 36; `any_of` 12; `unique_keys` 144; `identifier` 26; `pattern` 238;
`minimum_value` 284; `enums` 25 / `permissible_values` 203; `meaning` 15 (more in the pack);
`in_subset` 233 (as the PostgreSQL schema); `slot_uri` 637; `inlined` 558; `rules` 6;
`preconditions`/`postconditions` 13; `unit` 17; `range: json_payload` 69.

**Generators and plugins used:** `JsonSchemaGenerator` (`conditional_rules.py`), `OwlSchemaGenerator` and `ShaclGenerator`
(`ontology.py`), `DynamicEnumPlugin` and `BindingValidationPlugin` from linkml-term-validator
(`ontology.py:388, 644`, with code support for `reachable_from` at `:380–395`, but no `reachable_from`
declaration was found in `model/` or the statistics pack).

**Not used:** `exactly_one_of`, `equals_expression`, `designates_type`/type designators,
`structured_pattern`, `enum_range`, `string_serialization`, `boolean_slot`, `reachable_from` in
declarations, LinkML's SQL/SQLAlchemy/Pydantic generators (`sqltablegen`, `sqlalchemygen`,
`pydanticgen`), `linkml-validate`, `schema-automator`, and any LinkML representation of operations
or of the protocol.

The physical layer encodes foreign keys, checks and indexes as **JSON strings inside annotations**,
decoded by custom code (`schema/relational.py:297, 548–563`). They are invisible to LinkML tooling.
Foreign keys are not expressed as slot ranges.

### Composition: no single compiled effective schema

Each consumer builds its own import closure and `SchemaView`:

- physical: `schema/physical.py:166–197` (closure, `ph:values_from` resolution, pinned `linkml:types`
  bytes, `compile_metadata`);
- semantic release: `semantic/prepare.py:350–373` (seeded importmap, then `merge_imports`, then a
  new `SchemaView`);
- operation sources: `semantic/native_call_sources.py:95–117`, the same routine again;
- projection analysis: `semantic/projection_analysis_products.py:85–107`, the same routine a third time;
- companion projection: `semantic/companion_projection.py:552` (`SchemaView(str(MODEL))`, read from disk);
- rule views: `semantic/rule_views.py:402`; `conditional_rules.py:178`; `ontology.py:159, 260, 626`;
  `source_value_native.py:56`;
- earlier model: `schema/model.py:235` and `schema/pack.py:232`.

The "captured import closure" exists per consumer, keyed by `physical_sources_id`
(`schema/physical.py:142–151`) for the physical part and by `release_id` for the semantic part.
Value-set populations are resolved for physical enums from the protocol (`ph:values_from`,
`schema/physical.py:62, 138`) and for packs by the ontology and terminology code.

### Compiler path to what generators consume

| Path | From → to | Code |
|---|---|---|
| Physical | LinkML closure → `SchemaView` → **SQLAlchemy `MetaData`** (`info` carries immutability, archive role, read roles, sources and types) | `schema/physical.py:166–197`; `schema/relational.py:385, 492–506` |
| Semantic release | LinkML pack + semantic → merged `SchemaView` → `PreparedRelease` | `semantic/prepare.py:350–373` |
| Operations | Python literals + LinkML kinds + protocol → `EffectiveDataOperationModel` (frozen dataclasses), archived as JSON and decoded with cattrs | `data_operation_compilation.py:806–1864`; `data_operation_model.py:878, 1225–1264` |
| Protocol | draft-7 YAML → `Draft7Validator`, TypedDict facade and fates | `data_operation_wire.py:1–22`; `typed_generation.py:100–105` |
| Earlier | `core.yaml`/`system.yaml` → `Model` → vocab, `_model`, stage-B pydantic shapes, JSON Schemas | `schema/generate.py:560–578` |

### What is generated from each source

- From `MetaData`: tables and DDL through Alembic/autogenerate; typed column facades
  (`_typed_columns.py` via `relational.render_typed_columns :768`); `identifiers.py`
  (`typed_generation.py:21`); PDF native ids and calls; source-admission calls; Arrow schemas for
  PDF records (`pdf_record_model.py:103–122`) and exports (`serve/native_source.py:944–971` via
  `arrow_types.sql_arrow_type :13`); immutability and archive triggers; and the tables every typed
  native program references (`model.tables[...]`).
- From the protocol: `_data_operation_wire.py`, `_data_operation_fates.py`, physical enum checks,
  and function grants by purpose.
- From the effective operation model: lowered definitions (at release admission, in PL/pgSQL),
  identities, graph projections and the source-interface export.
- **Not generated from any declaration:** native kernels for validity, completion and family
  guards (typed Python programs or hand SQL strings that reference generated tables), DuckDB
  relation schemas (`analytical_kernels.py:21–60`, `rich_relations.py:24–34`, hand Arrow schemas
  with no model counterpart), DATA steps (`schema/data_steps.py`, closed first-party builders), and
  the scientific policy recipe.

### Data-model libraries and their roles

| Library | Source of truth for | Holds as derived (from what, where) | Same fact held independently elsewhere |
|---|---|---|---|
| LinkML / linkml-runtime | Classes, enums, physical tables (via `ph:`), projections, packs | — | Enums in both cores (DA-072); operation shapes held in Python literals, not LinkML |
| SQLAlchemy `MetaData`/Core | Nothing primary | Tables, columns, checks, indexes, `info` (`relational.py:385–563`); native programs as Core | Role and guard membership beside it (DA-074); DuckDB Arrow schemas |
| Alembic | Migration graph; privilege operations | Autogenerate from `MetaData`; privilege policy from `info.read_roles` plus `DEFAULT_READ_ROLES` (`alembic_privileges.py:74–75`) | Default roles again in `admission.sql:148` |
| pglast | — | Parse and normalize every native statement; `native_program` AST; re-parses the assembled kernel text (`data_operation_storage.py:1873–1875`) | — |
| SQLGlot | — | Projection lineage and type analysis (`projection_analysis.py:15–21`) | — |
| jsonschema | Protocol (draft-7) validation | Wire validation from the protocol (`data_operation_wire.py:22`); nullable inference (`data_operation_compilation.py:2544–2611`) | Protocol enums also in physical checks, derived via `values_from` (sound) |
| pydantic | Earlier-model shapes (stage B); 144 `BaseModel` classes in `semantic/` and `schema/` (preview requests, DATA-step parameters, native effects) | `TypeAdapter` boundary for PDF records from `MetaData` (`pdf_record_model.py:125`) | Hand `BaseModel`s were not compared field by field with `MetaData` (not examined) |
| pydantic-settings | Deployment settings (`settings.py:219`) | — | — |
| Plain frozen dataclasses (+ cattrs) | Effective operation model (`data_operation_model.py:53–890`) | cattrs decodes the archive (`:1225–1264`) | `profile` Literal (`:497`) restated in `_PROFILES` (`data_operation_compilation.py:85`) |
| pyarrow | DuckDB analytical relation schemas (hand) | PDF record and export schemas from `MetaData` (`pdf_record_model.py:103–122`; `arrow_types.py:13`); PDF payloads from JSON Schema (`pdf_payloads.py:87–149`) | — |
| valuesets | Vendored YAML copies only (package not imported) | — | — |
| linkml-term-validator / oaklib / pronto | Ontology bindings, dynamic enum expansion | Members expanded at preparation (`ontology.py:380–395, 644`) | — |
| attrs / msgspec | Not used | — | — |

## 3. Fact-ownership table

"Derivable from" answers the operator's addition: an existing typed source in the codebase the
code literal could be computed from, or "none; needs a declaration".

| Fact | Declared in model | Held as code | Restated at | Derivable from today |
|---|---|---|---|---|
| Record and product shape | LinkML classes (`model/semantic/*.yaml`, packs) | — | Earlier-model copies (DA-072); DuckDB Arrow (`analytical_kernels.py:21–60`, `rich_relations.py:24–34`) | Rich and view relations: none (needs a declaration); PDF: already from `MetaData` |
| Field type and constraint | LinkML range, pattern, min; `ph:checks` JSON | — | `data_kind_contract` universe check (`data-operation-physical.yaml:71`) vs `_KIND_UNIVERSES` (`data_operation_compilation.py:341`) | `NativeKindProjection["universe"]` Literal, already used at `support_trust_native.py:91` |
| Enum / value set | LinkML enums; protocol enums | — | 6+ enums in both cores; PDF outcome pair | One side from the other (none chosen) |
| Operation | — | `__data_operation__` literals, 85 modules | — | — (Python is the declaration medium) |
| Operation I/O and dependencies | — | Literal `roles`, `dependencies` | `changed_operations` graph (`change_impact.py:157–193`) | Compiled `selected-dependencies`/`potential-producers` (`data_operation_model.py:713–725`) |
| Validity family | **Column only, no values** (`data-operation-physical.yaml:88`) | Tuple `data_operation_compiler_native.py:470–519` | Dispatch tuple `data_validity_native.py:272–282`; guard lists (contextual `:16–21, 214–219`, definition `:83, 106, 124`, rich `:183`, record grade `:691`); completion `If` chain (`data_completion_settlement_native.py:714–800`); guard tuple (`:538–553`) | None; needs a declaration. Host: `EffectiveOperation` is lowered right beside it (`compiler_native.py:905–926`) |
| Per-operation family contract (entry point, profile, forms) | Per operation in the effective model | SQL `CASE` (`contextual_admission_native.py:23–44`) | — | `EffectiveOperation.capabilities.prepared_factory`, `.profile`, `.capabilities.forms` (`data_operation_model.py:288–296, 497, 510`) |
| Support-edge meaning, reference→node map | — | Validity edges (`data_validity_native.py:88–240`) | `_support_walk` (`data_operation_projections.py:117, 132–242`); `_revocation_causes` (`change_impact.py:332–441`) | None; needs a declaration |
| Trust-scope key | — | `ddo_scope` (`support_trust_native.py:100–118`) | `change_impact.py:427` (disagrees) | The `ddo_scope` program itself, or a shared Python function |
| Frontier-guard membership | — | 12-name tuple (`data_operation_storage.py:1934–1960`) | Admission descriptor (built from the same list) | None; immutability does not separate; needs a declaration |
| Shared-stream trigger membership | **`ph:immutability: pending-content`** (`physical.yaml:1757, 1776`) | Name set (`target_installation.py:350`) | — | `relation.info["immutability"] == "pending-content"`, already populated (`relational.py:492`) |
| Immutability / archive triggers | `ph:immutability`, `ph:archive_role` | — | — | Already derived (sound) |
| Role names and purpose→role map | Purposes per protocol function (`data-operation-native.yaml:2783+`) | Dict (`data_operation_storage.py:1884–1891`); `PURPOSE_ROLES`/`DEFAULT_READ_ROLES` (`alembic_privileges.py:25–33`) | `admission.sql:130, 148, 162–186`; `target_installation.py:209–244, 266–277`; `elif` chain (`data_operation_storage.py:1892–1914`) | Purposes: yes. Role names and defaults: none; needs a declaration |
| Table read grants | `ph:read_roles` (deny only, all `'[]'`) | Default from code | `admission.sql:148` (×2) | `relation.info.read_roles` once defaults are declared |
| Release composition | Flags (`domains/statistics/operations.yaml`) | `primary_operations.py:118–392` | Family source functions (DA-073) | Partly: static operation extraction exists before compilation (`python_operation_sources.py`); family→source map: none |
| Physical index and check | `ph:indexes`, `ph:checks`, `unique_keys` | — | — | Already derived; admission compares them (sound) |
| Wire shape | Protocol draft-7 | — | Wire-type map (`data-operation-wire-types.yaml`) | Already derived |
| Search configuration | `ph:search_configuration` (`physical.yaml:1733`) and a check | — | — | Already derived |
| Identity determinants | Operation literals (recipe, eligibility) | `_compile_identities` (`data_operation_compilation.py:2138–2233`) | — | Compiled (sound) |
| Scientific policy parameters | `scientific-policies.yaml` (not LinkML); `numerical_policy` asset per operation | — | Archived recipe text (DA-077, not re-read) | Not examined in this lane |
| Generated-facade ownership | — | `_NATIVE_OUTPUTS` (`model_change.py:53–61`) | Owner writers; `LOWERING_FILES` (`pdf_lowering.py:33–72`) | The owners' path constants. A registry of the `generate.py:540–578` kind exists only for the earlier model |
| Graph-projection catalog | — | `compiled_graph_projections` | — | Derived from owned edges (sound, `data_operation_model.py:705–725`) |

## 4. New structural causes (candidate findings for the coordinator)

**N1: Model composition is reimplemented per consumer; there is no single compiled effective
schema.** FP-04/A2; DP-01, DP-02. There are three near-identical "seed importmap → `merge_imports` →
re-wrap" routines (`prepare.py:350–373`, `native_call_sources.py:95–117`,
`projection_analysis_products.py:85–107`), a separate physical closure (`schema/physical.py:166–197`)
and disk-path views (`companion_projection.py:552`, `schema/model.py:235`). *Consequence:* each
generator sees its own model, and facts that cross views have no shared object to derive from,
for example roles, the operation-to-kind relation and the shared-stream class. That is why
membership facts fall back to Python lists. Every new consumer adds another closure, and
custody digests multiply. *Contrary evidence:* each routine refuses unresolved imports with no
filesystem fallback, and the physical closure is content-identified. *Uncertainty:* whether the
closures differ in result was not tested.

**N2: Declared facts that membership code ignores.** FP-04; DP-01. Shared-stream trigger
membership by name (`target_installation.py:350`) beside the declared `pending-content` class
(`physical.yaml:1757, 1776`). Also `_KIND_UNIVERSES`/`_PROFILES` beside the typed Literals that
`support_trust_native.py:91` already reads with `get_args`. *Consequence:* small today. It is
evidence that the condition for closing DA-074 can partly be met by connecting existing
declarations, not only by adding new ones. This could be filed under DA-074 rather than as a new
identity.

**N3 (for reconciliation with DA-080 and the SQL-text lanes): the family layer is still
hand-written SQL text.** At least 17 `semantic/*_native.py` modules hold `CREATE OR REPLACE
FUNCTION` text (search). Among them, the contextual, definition, rich and artifact guards and validators are exactly where
the DA-070 lists live. The kernel is assembled as one text and re-parsed by pglast
(`data_operation_storage.py:1873–1875`). *Consequence for this lane:* converting these to typed
programs, as was done for record grade, will again transcribe the lists unless family membership
is declared first. This is an ordering hazard for the next conversion step.

**N4: The released model lacks the guard the earlier model has.** No released-model generator
registry exists (DA-081). The only self-checking registry covers `core/vocab` and friends
(`schema/generate.py:540–578`), so the stronger custody sits on the model being retired.

## 5. Sound designs to preserve

- Immutability and archive triggers derive from `ph:immutability` and `ph:archive_role` through
  `MetaData.info` (`data_operation_storage.py:1923–1933`; `target_installation.py:334–347, 369`).
- Physical enums derive from the protocol (`ph:values_from`, `schema/physical.py:62, 138`;
  `data-operation-physical.yaml:11–14`).
- Protocol function grants derive from declared `purposes` (`data_operation_storage.py:1882–1891`).
- Universe validity reads the typed Literal with `get_args(get_type_hints(...))`
  (`support_trust_native.py:91`). This is the pattern to copy for `_PROFILES` and `_KIND_UNIVERSES`.
- `ddo_classify_command` classifies by eligibility predicates, not ids
  (`data_operation_compiler_native.py:530–550`).
- Arrow schemas for PDF records and exports derive from `MetaData`
  (`pdf_record_model.py:103–122`; `arrow_types.py:13`; `serve/native_source.py:944–971`), with
  the physical model id in the schema metadata.
- Unresolved operation and kind references refuse at compile (`data_operation_compilation.py:1836–1838`).
  Graph projections are derived from owned edges, "not a second authored graph catalogue"
  (`data_operation_model.py:705–725`).
- The physical closure refuses extra or missing sources and pins the LinkML types bytes
  (`schema/physical.py:156–197`).
- Lowering already carries the archived effective operation beside `validity_family`
  (`compiler_native.py:905–926`). A declared per-operation family could be lowered the same way
  `dependencies` is, with an install-time check that the dispatch covers every declared family. This
  is a solution lead, not a selected remedy.
