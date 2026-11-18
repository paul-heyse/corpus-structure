# Current domain model map

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
This is a diagnostic map of the model found in source; the architectural owners keep
authority. The fact-ownership and library-role tables were rebuilt at `5139eaba3` and mark
each row as new, changed or unchanged since the previous map at `d78c98765`. The sections on
declaration owners, LinkML features and composition were written at `d78c98765`; the model
files they describe changed in two places only in `d78c98765..5139eaba3` (a `public_disclosure`
flag on the read boundary and three protocol definitions), and their figures were not
recounted. Some strengths, marked below, carry forward 2026-11-17 observations that were not
re-read.

Paths omit `python/corpus-structure/src/corpus_structure/`; `model/` is under that package;
`domains/` is at the repository root (read with `git show <commit>:domains/…`, because the
frozen snapshot omits it). Counts marked "search" are counts of a key or pattern. Nothing was
run.

Terms used on this page. *LinkML* is the schema language the model is mostly written in. A
*`SchemaView`* is LinkML's in-memory view of a schema and its imports. The *physical model* is
the part of the LinkML model that declares PostgreSQL tables. *`MetaData`* is SQLAlchemy's
in-memory description of tables, which the physical model is compiled into. The *protocol* is
`model/semantic/data-operation-native.yaml`, the JSON Schema document that declares the native
(in-database) operations and their wire shapes. A *pack* is a domain's own model under
`domains/<name>/`. A *native program* is a generated PostgreSQL routine.

<a id="current-model"></a>

## Declaration owners

### LinkML, released model

`model/semantic/` holds 50 YAML files. 43 are LinkML schemas (counted by schema header) and
seven are other formalisms, listed in the next subsection. With the two earlier-model schemas
`model/core.yaml` and `model/system.yaml` there are 45 LinkML schemas under `model/`. By role:

| Role | Files | Notes |
|---|---|---|
| Semantic core | `core.yaml` (schema name `semantic_core`) | Statement and record vocabulary; imported by packs |
| Shared semantic schemas | `observations.yaml`; `characterization.yaml` (imports `observations`); `reference.yaml`; `rule-view.yaml` (Entity, Value, Statement, Claim, `RuleReadingOutcome`); `scientific.yaml`; `agent.yaml`; `analytics.yaml`; `analysis-policies.yaml`; `native-adapters.yaml`; `selected-source.yaml` | — |
| Product kinds per operation family | `data-operation-*.yaml`: sentences, hanlp, learned, contextual, constructions, characterization, interpretation, record-policy, references, assessment, rich-proposals, pdf-capture, pdf-region, visual, external-extraction, source, source-discovery, source-profile, candidate-inspection, definition-location, reading-resolution | They form a directed acyclic graph through `imports` (for example, learned imports source, source-discovery, candidate-inspection and constructions) |
| PDF | `pdf-products.yaml`, `pdf-records.yaml`, `pdf-staging.yaml`, `pdf-payloads.yaml` | `pdf-payloads.yaml` carries `pdp:` annotations that describe an Arrow payload family |
| Physical | `physical.yaml` (root; imports `linkml:types`, `pdf-records`, `pdf-staging`, `data-operation-physical`, `data-operation-task-physical`); `characterization-physical.yaml` | Tables are classes placed in a subset that names the PostgreSQL schema; keys are `unique_keys` (144, search); everything else physical is a `ph:` annotation |
| Projections | `read-projections.yaml` (imports `physical`; `rv:` annotations); `companion-projections.yaml` (imports the PDF schemas; `cp:` annotations that carry a JSON query tree in `cp:sources` and `cp:helpers`); `operation-reports.yaml` (imports `pdf_products`, `observations`) | — |

Physical annotation keys and their counts (search): `ph:foreign_keys` 117, `ph:immutability`
116, `ph:read_roles` 84 (every one is the empty list `'[]'`), `ph:checks` 68 (JSON predicate
trees with hashed names), `ph:indexes` 32, `ph:archive_role` 15, `ph:sql_type` 10,
`ph:python_type` 8, `ph:values_from` 3, `ph:search_configuration` 1, and `ph:generated_*`,
`ph:server_default_*` and `ph:identity`. Other annotation prefixes: `cp:` 177, `ci:` 57, `cs:`
42 (`cs:data_universe`), `rv:` 37, and `pds:`, `pdp:`, `pdr:`.

### Declarations in the model directory that are not LinkML

| File | Formalism | What it declares | What derives from it |
|---|---|---|---|
| `data-operation-native.yaml` (3,033 lines, the largest model file) | JSON Schema draft-7 with `x-ddo-lifecycle` extensions and an `operations:` block from `:2809` | The protocol: wire definitions, state lifecycles and transitions, the public native operations and the `purposes` of each | Wire types, fates, physical value sets, protocol function grants, the task guard |
| `data-operation-wire-types.yaml` | Map from JSON pointer to nominal type | Nominal wire types | Generated wire module |
| `pdf-actions.yaml` (1,987 lines) | Custom catalog | PDF actions and calls | PDF call bindings |
| `analysis-policy.yaml`, `metrics.yaml`, `scientific-policies.yaml`, `characterization-questions.yaml` | Custom YAML | Policy decision table, metrics, questions | Policy and evaluation code |
| `analytical-profile.json`, `operation-report-schemas.json`, `pdf-observation-meaning.json`, `nce-section-packets.json`, `section-text-recipe.json`, `docling-validation.schema.json` | JSON, JSON Schema | Profiles, report shapes, recipes | Their own consumers; not traced |

### Operations

Operations are not in LinkML. Each is a `__data_operation__` declaration in one of about 62
Python modules (85 modules mention the name; search), extracted statically without importing the module (for example
`methods/contextual_scoring.py:110–135`). `dependencies`, `capabilities`, `numerical_policy`,
enforcement claims and coverage are declared there. The grammar of these literals is a
hand-written validator (`semantic/data_operation_compilation.py:143–188`, with `_PROFILES` at
`:85` and `_KIND_UNIVERSES` at `:341`), not a schema. Native operations come from the protocol.
Having these two authoring routes, compiled into one effective model, is the accepted
decision of [ADR-0092](../../adr/0092-ddo-operation-authority.md) (`:19–25`).

### Earlier model

`model/core.yaml` (1,096 lines), `model/system.yaml` (2,023 lines; `ci:payload` classes) and
`model/revisions.yaml` (1,118 lines; a revision log, not LinkML). Still live
([DA-072](semantic-model-and-authority.md#da-072)).

### Packs (`domains/`)

| File | Content |
|---|---|
| `statistics/semantic.yaml` | `statistics_semantic`; imports `semantic_core` and `statistics_terminology` |
| `statistics/terminology.yaml` | LinkML enums with STATO `meaning` terms |
| `statistics/terminology/sources/*-valuesets-0.4.2.yaml` | Vendored copies of `valuesets` schemas; the Python package is not imported (search) |
| `statistics/schema/statistics.yaml` | The earlier-model pack; imports `linkml:types` and the earlier `core` |
| `*/schema/rules.yaml` | A custom rule language (`schema/rulelang.py`), not LinkML `rules` |
| `operations.yaml`, `methods.yaml`, `slices.yaml`, `construction.yaml`, `profiles/*` | Release flags and method configuration ([DA-073](semantic-model-and-authority.md#da-073)) |
| Toy pack | The same shape |

<a id="linkml-features"></a>

## LinkML features used and not used

An unused feature is a fact for the design review, not a finding.

**Used** (counts by search over `model/`): `is_a` 446; `attributes` 730 (classes are mostly
attribute-local, with few shared slots); `slot_usage` 40; `mixins` 32 (with no `mixin: true`
declarations); `abstract` 36; `any_of` 12; `unique_keys` 144; `identifier` 26; `pattern` 238;
`minimum_value` 284; `enums` 25 with 203 `permissible_values`; `meaning` 15 (more in the pack);
`in_subset` 233 (used as the PostgreSQL schema); `slot_uri` 637; `inlined` 558; `rules` 6;
`preconditions` and `postconditions` 13; `unit` 17; `range: json_payload` 69.

**Generators and plugins used:** `JsonSchemaGenerator` (`semantic/conditional_rules.py`);
`OwlSchemaGenerator` and `ShaclGenerator` (`semantic/ontology.py`); `DynamicEnumPlugin` and
`BindingValidationPlugin` from linkml-term-validator (`semantic/ontology.py:388, 644`). The
ontology code supports `reachable_from` (`:380–395`), but no `reachable_from` declaration was
found in `model/` or the statistics pack.

**Not used:** `exactly_one_of`, `equals_expression`, `designates_type` (type designators),
`structured_pattern`, `enum_range`, `string_serialization`, `boolean_slot`, `reachable_from`
in declarations; LinkML's SQL, SQLAlchemy and Pydantic generators (`sqltablegen`,
`sqlalchemygen`, `pydanticgen`); `linkml-validate`; `schema-automator`; and any LinkML
representation of operations or of the protocol.

**Encoded outside LinkML's reach.** Foreign keys, checks and indexes are JSON strings inside
annotations, decoded by custom code (`schema/relational.py:297, 548–563`). Foreign keys are
not expressed as slot ranges.

<a id="composition"></a>

## Composition: no single compiled effective schema

Each consumer builds its own import closure and its own `SchemaView`
([DA-085](semantic-model-and-authority.md#da-085)):

| Consumer | Site | How it composes |
|---|---|---|
| Physical | `schema/physical.py:166–197` | Trusted closure of named bytes; resolves `ph:values_from`; pins the `linkml:types` bytes; compiles `MetaData` |
| Physical, at import | `semantic/metadata.py:32–50` | Reads the closure and compiles two `MetaData` projections (physical tables and `read-projections.yaml`) in every importing process |
| Semantic release | `semantic/prepare.py:350–373` | Seeds an import map, merges imports, wraps the merged schema in a new `SchemaView` |
| Operation call sources | `semantic/native_call_sources.py:95–117` | The same routine again, with a hand map between file names and schema names (`:57–64`) |
| Projection analysis | `semantic/projection_analysis_products.py:85–107` | The same routine a third time |
| Companion projection | `semantic/companion_projection.py:552` | `SchemaView` read from a disk path |
| Rule views; conditional rules; ontology; source values | `semantic/rule_views.py:402`; `semantic/conditional_rules.py:178`; `semantic/ontology.py:159, 260, 626`; `semantic/source_value_native.py:56` | One view each |
| Earlier model | `schema/model.py:235`; `schema/pack.py:232` | Two views from disk paths; an import map for the earlier core |

A captured import closure exists per consumer. The physical part is identified by
`physical_sources_id` (`schema/physical.py:142–151`) and the semantic part by the release id.
Value-set populations are resolved for physical enums from the protocol (`ph:values_from`,
`schema/physical.py:62, 138`) and for packs by the ontology and terminology code.

<a id="compiler-path"></a>

## Compiler paths to what generators consume

| Path | From, to | Code |
|---|---|---|
| Physical | LinkML closure, to `SchemaView`, to SQLAlchemy `MetaData` whose `info` carries immutability, archive role, read roles, sources and types | `schema/physical.py:166–197`; `schema/relational.py:385, 492–506` |
| Semantic release | LinkML pack and semantic schemas, to a merged `SchemaView`, to `PreparedRelease` | `semantic/prepare.py:350–373` |
| Operations | Python literals, LinkML kinds and the protocol, to `EffectiveDataOperationModel` (frozen dataclasses), archived as JSON and decoded with cattrs | `semantic/data_operation_compilation.py:806–1864`; `semantic/data_operation_model.py:878, 1225–1264` |
| Protocol | Draft-7 YAML, to a `Draft7Validator`, a `TypedDict` facade and fates | `semantic/data_operation_wire.py:1–22`; `semantic/typed_generation.py:100–105` |
| Native programs | Captured `MetaData` and call bindings, to SQLAlchemy Core statements and parsed PostgreSQL nodes framed by the program compiler, to SQL text, to server-normalized catalog objects frozen in a migration revision | `semantic/native_program.py`; `semantic/data_operation_storage.py:48–575, 761–822`; `semantic/native_objects.py`; `semantic/target_installation.py` |
| Earlier | `core.yaml` and `system.yaml`, to `Model`, to vocabulary, `_model`, stage-B pydantic shapes and JSON Schemas | `schema/generate.py:560–578` |

The native program path is the addition of the model-owned SQL conversion
([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md)). Its finite forms, and the rule
that Core and parsed nodes own statements while the compiler owns only procedural framing, are
stated in `semantic/native_program.py`. What happens after rendering is part of
[DA-081](semantic-model-and-authority.md#da-081).

**What the generators receive.** Every admission generator regenerated in
`d78c98765..5139eaba3` takes the captured `MetaData` as its only model input and resolves
relation and column names against it, so a missing name fails at generation (signatures and
the search are listed on the
[model-authority page](semantic-model-and-authority.md)). None receives the effective
operation model or the protocol. Relations and columns are therefore model-owned in generated
SQL, while everything that identifies an operation (family, producer, entry point, profile,
role, universe) is a string in the generator. Eight generators inside the native capture now
take the captured physical metadata instead of metadata compiled at import
(`semantic/data_operation_storage.py:251–356`).

<a id="generated"></a>

## What is generated from each source

| Source | Generated from it |
|---|---|
| `MetaData` | Tables and DDL through Alembic autogenerate; typed column facades (`_typed_columns.py`, via `schema/relational.py:768`); `identifiers.py` (`semantic/typed_generation.py:21`); PDF native ids and calls; source-admission calls; Arrow schemas for PDF records (`semantic/pdf_record_model.py:103–122`) and exports (`serve/native_source.py:944–971`, via `semantic/arrow_types.py:13`); immutability and archive triggers; and the table objects every typed native program references |
| Protocol | `_data_operation_wire.py`, `_data_operation_fates.py`, physical enum checks, function grants by purpose, the task guard's states |
| Effective operation model | Lowered definitions (at release admission, in PL/pgSQL), identities, graph projections, the source-interface export |
| Seven generated Python facades, rendered together at preview | `_source_admission_calls.py`, `_typed_columns.py`, `identifiers.py`, `_data_operation_fates.py`, `_pdf_native_calls.py`, `_pdf_native_ids.py`, `_data_operation_wire.py` (`schema/model_change.py:53–61, 525–552`; [DA-081](semantic-model-and-authority.md#da-081)) |
| **No declaration** | The native kernels for validity, completion and family guards: typed programs that reference generated tables and take their membership lists from Python ([DA-070](semantic-model-and-authority.md#da-070)); role, grant and guard membership ([DA-074](native-integrity.md#da-074)); DuckDB relation schemas (`semantic/analytical_kernels.py:21–60`; `semantic/rich_relations.py:24–34`; [DA-086](semantic-model-and-authority.md#da-086)); data steps (`schema/data_steps.py`, closed first-party builders); the scientific policy recipe ([DA-077](served-claims.md#da-077)) |

<a id="fact-ownership"></a>

## Fact ownership

**Rebuilt 2026-11-18 at `5139eaba3`.** "Derivable from today" names an existing typed source
in the codebase that the code literal could be computed from, or says that none exists and a
declaration would be needed. It is a statement of what exists, not a selected change. The
last column marks each row against the previous map at `d78c98765`: **new** row, **changed**,
or **unchanged**. In this table and the next, a Python file named without a directory is under
`semantic/`, and a YAML file named without a directory is under `model/semantic/`. The table
has 40 rows.

| Fact | Declared in the model | Held as code | Restated at | Derivable from today | Mark |
|---|---|---|---|---|---|
| Record and product shape | LinkML classes | — | Earlier-model copies ([DA-072](semantic-model-and-authority.md#da-072)); DuckDB Arrow schemas (`analytical_kernels.py:21–60`; `rich_relations.py:24–34`) | Rich and view relations: none. PDF: already from `MetaData` | unchanged |
| Relation and column used by native programs | Physical LinkML, compiled to `MetaData` | — | — | Already derived: generators resolve against captured `MetaData` | changed (now all nine admission modules) |
| Field type and constraint | LinkML range; `ph:checks` JSON | — | The `data_kind_contract` universe check (`data-operation-physical.yaml:71`) beside `_KIND_UNIVERSES` (`data_operation_compilation.py:341`) | The `NativeKindProjection["universe"]` typed literal (`native_definition_projection.py:23`) | unchanged |
| Kind-universe values in kernels | Physical check (`data-operation-physical.yaml:71`) | — | 43 lines in `semantic/*.py` (survey), including the new public-disclosure rule (`data_operation_projections.py:97`) | The typed literal, as `support_trust_native.py:91` already reads it | changed |
| Field kind to database and Python type | LinkML `uri`; `ph:sql_type` | — | `native_call_contracts.py:16–25`; `native_call_sources.py:28–37`; `pdf_search_native.py:98–104`; `native_program.py:657` | The physical compiler's resolution (`schema/relational.py:79–89, 437–440`) | unchanged |
| Enum and value set | LinkML enums; protocol enums | — | Six enums in both cores; the PDF outcome pair | One side from the other (none chosen) | unchanged |
| Operation | — (the two-route design of ADR-0092) | `__data_operation__` declarations in about 62 modules | — | None; Python is an admitted declaration medium | unchanged |
| Operation inputs, outputs and dependencies | — | Literal `roles`, `dependencies` | `change_impact.py:157–193`; producer per input role (`contextual_admission_native.py:301–310`); `STRUCTURAL_REPORT_PRODUCERS` (`declared_structural_admission.py:276`) | Compiled `selected-dependencies` and `potential-producers` (`data_operation_model.py:713–725`); role kinds | changed (kernel restatements located) |
| Role collection semantics | The operation role's `collection` | — | — | Read directly (`characterization_ports.py:746–749`) | new (sound) |
| Validity family | **Column only, no values** (`data-operation-physical.yaml:88`) | `data_operation_compiler_native.py:470–519` | Dispatch (`data_validity_native.py:272–288`); guard tuple (`data_completion_settlement_native.py:548–563`); authorization subset (`:576–587`); live chain (`:744–803`); contextual (`contextual_admission_native.py:188–201`); definition (`definition_admission_native.py:33–38`); artifact (`artifact_admission_native.py:112, 147, 217`); rich (`rich_admission_native.py:606–622, 816–823, 903–910`); operation event (`operation_event_native.py:55–60`); record grade (`record_grade_native.py:55`); record fit (`record_policy_completion_native.py:1140, 1170, 1471`) | None; needs a declaration. Hosts exist: lowering beside the effective operation (`data_operation_compiler_native.py:905–926`), and selection by a declared effect, which rich admission already does (`rich_admission_native.py:1136–1145`) | changed |
| Prepared-factory entry point | Per operation in the effective model (`capabilities.prepared_factory.entrypoint`) | — | 53 lines in 15 files (search), for example `contextual_admission_native.py:189–200`, `definition_admission_native.py:39–44`, `rich_admission_native.py:607–619`, `record_policy_completion_native.py:60–61`, `evaluate/declared_operation_events.py:42–44`, `declared_structural_admission.py:276` | `EffectiveOperation.capabilities`, an `ImplementationCapabilities` (`data_operation_model.py:288–296`). Caution: the guards compare the literal with the admitted row, so it acts as an independent pin | changed (was contextual only) |
| Profile, forms and receipt count per operation | Effective model | — | `contextual_admission_native.py:234–259`; `definition_admission_native.py:358–372`; `artifact_admission_native.py` | `EffectiveOperation.profile`, `.capabilities.forms` (same caution) | changed |
| Operation constants in owner modules | — | `AUTHORIZATION_OPERATION` (`evaluate/declared_operation_events.py:31`, the authorize id only); `GRADE_OPERATION` (`record_policy_authority.py:39`); `ADMISSION_OPERATION` (`declared_structural_admission.py:11`) | Inline ids: `"operation_event.frame"` and the fit id, which have no owner constant (`operation_event_native.py:295, 315, 1206`), and `"record_policy.fit"` | The owner constants, where one exists | new |
| Native effect per family operation | — | Declared in the operation's `effects` for four families (`methods/record_policy.py:70`; `methods/operation_events.py:328`; `methods/rich_knowledge.py:405`; `methods/structural_admission.py:132`); contextual, definition and artifact operations declare none | — | Lowered in `support_contract` and already read by two guards (`rich_admission_native.py:1136–1145`; `record_policy_completion_native.py:425–441`); not used for the family lists ([DA-070](semantic-model-and-authority.md#da-070)) | new (found by the independent challenge) |
| Encoder failure codes | — | `contextual_encoder_batch.py:19–26`; a `Literal` of two codes (`methods/contextual_embeddings.py:333`) | `contextual_admission_native.py:653–660` | The Python set | new |
| Product member families, fields and required sets | Protocol definitions `coordinate`, `role_member`, `endpoint`, `coverage`, `choice`, `product_member` (`data-operation-native.yaml`) | `_FAMILIES` (`data_product_admission_native.py:56–90`) | — | The protocol definitions' `properties` and `required` | new |
| Support-edge meaning; reference-to-node map | — | `data_validity_native.py:88–240` | `_support_walk` (`data_operation_projections.py:156, 171`); `_revocation_causes` (`change_impact.py:332–441`); a narrow lineage walk (`source_admission_native.py:1129–1135`) | None; needs a declaration ([DA-071](semantic-model-and-authority.md#da-071)) | changed (fourth walk located) |
| Trust-scope key | — | `support_trust_native.py:100–118` | `change_impact.py:427` (disagrees) | The program, or one shared function | unchanged |
| Public disclosure of a read | `public_disclosure` (`data-operation-physical.yaml:629`); protocol `read_demand_selection` | — | — | Already read (`data_read_boundary_native.py:31–34, 103`; `data_operation_projections.py:84–89`) | new (sound) |
| Frontier-guard membership | — | Twelve names (`data_operation_storage.py:1952–1965`) | The admission descriptor, built from the same list | None; needs a declaration ([DA-074](native-integrity.md#da-074)) | changed (trigger now typed) |
| Shared-stream trigger membership | `ph:immutability: pending-content` (`physical.yaml:1757, 1776`, two relations) | Name set (`target_installation.py:371`) | — | `relation.info["immutability"]` | unchanged |
| Immutability and archive triggers | `ph:immutability`, `ph:archive_role` | — | — | Already derived (sound) | unchanged |
| Task states and transitions | Protocol lifecycle (`data-operation-native.yaml:5–14`) | Kernel literals (21 quoted `pending` or `running` in eight `*native*.py` files) | — | Already read by the task guard, before and after the range (`data_operation_protocol.py:117–128`) | changed in form only: the guard is now a typed program; the literals are unchanged |
| Role names | — | `alembic_privileges.py:25–33` | 199 occurrences in 47 `.py` files; new tuples at `native_admission_tables.py:27–32` and `native_admission_principals.py:8–9` | Constants exist; none in the model | changed: the literals moved from the deleted SQL files into Python, and the total fell from 246 to 199 |
| Purpose-to-role map | Purposes per protocol function | `data_operation_storage.py:1899–1907` | `closure_native.py:174–181` | Purposes: yes. Roles: needs a declaration | changed (second copy) |
| Execute grants for non-protocol functions | — | `data_operation_storage.py:1908–1928` | `target_installation.py:227–249, 291`; `native_admission_release.py:397–407`; `native_authoring.py:165, 183` | None | changed |
| Table read grants | `ph:read_roles` (84 annotations, all `'[]'`) | Default (`alembic_privileges.py:74–75`) | JSON literal (`native_admission_tables.py:176–184`) | `DEFAULT_READ_ROLES`, identical in content and order, as `native_admission_functions.py:149` already uses it | changed |
| Principal restrictions; application schemas; private kernels | — | `native_admission_principals.py:8–16` | — | Schemas: the `MetaData` table schemas (plus `eval`). Kernels: the program objects, if a registry existed ([DA-081](semantic-model-and-authority.md#da-081)) | new |
| Release composition | Flags (`domains/statistics/operations.yaml`) | `primary_operations.py:118–392` | Family source functions; a new hand source (`characterization_ports.py:1141–1155`) | Partly (`python_operation_sources.py`); [DA-073](semantic-model-and-authority.md#da-073) | changed |
| Physical index and check | `ph:indexes`, `ph:checks` | — | — | Derived; admission compares them (sound) | unchanged |
| Wire shape | Protocol draft-7 | — | Wire-type map | Derived | unchanged |
| Value-codec vocabulary | SourceValue variants in LinkML | `data_operation_value_native.py:44–50` | — | Two codecs, two authorities | unchanged |
| Codec tags in kernels | The same codec | — | Tag literals in every regenerated module (survey) | The constants of `data_operation_value_native.py` | new |
| Search configuration | `ph:search_configuration` | — | — | Derived | unchanged |
| Identity determinants | Operation literals | `_compile_identities` | — | Compiled (sound) | unchanged |
| Scientific policy parameters | `scientific-policies.yaml` | — | Archived recipe text ([DA-077](served-claims.md#da-077)) | Not examined | unchanged |
| Which code determines an artifact | Implementation slices, for Python operations only | The capture list (`native_products.py:134–164`, 28 names); `LOWERING_FILES`; the kernel capture; query-custody lists | Each other, in part ([DA-068](execution-fit.md#da-068), [DA-082](execution-fit.md#da-082), [DA-076](served-claims.md#da-076)) | None for generators. The capture list is also digested into the deployed execution-contract descriptor as 48 `authoring/*` entries ([DA-068](execution-fit.md#da-068)) | changed (ten names added) |
| Generated-facade and program-set ownership | — | `_NATIVE_OUTPUTS` (7); capture sources 91; required set 94; `native_sql` 39; install table 11; providers 7 | Owner writers; `LOWERING_FILES` | The owners' path constants; no registry for the released model | changed |
| Catalog-check boundaries in the admission guard | — | Marker comments (`native_admission_release.py:35–38, 371, 382`) | Text recovery (`native_admission.py:42–82`) | The program objects, for guards generated in the current process | new |
| Graph-projection catalog | — | `compiled_graph_projections` | — | Derived (sound) | unchanged |

<a id="library-roles"></a>

## Data-model libraries and their roles

**Rebuilt 2026-11-18 at `5139eaba3`.** Pinned versions are in
`python/corpus-structure/pyproject.toml` (LinkML 1.12.1, DuckDB 2.0.0, SQLAlchemy 2.1.6,
pglast 8.7, SQLGlot 30.27.0, pydantic 2.14.1, pyarrow 26.0.0); `pyproject.toml` and `uv.lock`
have no diff in `d78c98765..5139eaba3`. The last column marks each row against the previous
map.

| Library | Source of truth for | Holds as derived (from what, where) | Same fact held independently elsewhere | Mark |
|---|---|---|---|---|
| LinkML, linkml-runtime | Classes, enums, physical tables (through `ph:`), projections, packs | — | Enums in both cores ([DA-072](semantic-model-and-authority.md#da-072)); operation shapes are Python literals | unchanged |
| SQLAlchemy `MetaData` | Nothing primary | Tables, columns, checks, indexes and `info` (`schema/relational.py:385–563`); the only model input of every regenerated generator | Role, guard and family membership beside it ([DA-070](semantic-model-and-authority.md#da-070), [DA-074](native-integrity.md#da-074)) | changed |
| SQLAlchemy Core | Statement construction | All admission kernels; the task guard (`data_operation_protocol.py:117–128`); triggers (`native_before_trigger_sql`, `native_objects.py:154`); catalog checks over lightweight `pg_catalog` tables (`native_catalog.py` and the three `native_admission_*` modules) | — | changed (wider) |
| Alembic | The migration graph; privilege operations | Autogenerate from `MetaData`; privilege policy from `info["read_roles"]` plus `DEFAULT_READ_ROLES`; typed privilege admission over `PURPOSE_ROLES` | Default roles again as JSON text (`native_admission_tables.py:176–184`) | changed |
| pglast | — | Parses every native statement; retargets scratch tables on the parse tree (`native_authoring.py:303–328`); re-parses the assembled kernel for grants (`data_operation_storage.py:1887–1897`); 62 `semantic/` modules use it (59 before); validates submitted read-only SQL | — | changed |
| SQLGlot | — | Projection lineage and type analysis | — | unchanged |
| jsonschema | Validation of the protocol (draft-7) | Wire validation; nullable inference; kind schemas now pass `checked_json_schema` (`data_operation_storage.py:1146–1150`) | Protocol member families restated in `_FAMILIES` (`data_product_admission_native.py:56–90`) | changed |
| pydantic | Earlier-model shapes; `BaseModel` classes; the `TypedDict` read boundary (`native_definition_projection.py`) | A `TypeAdapter` for native selection custody (`data_operation_preparation.py:304`) and for PDF records | The lowered `support_contract` typed as `dict[str, Any]` beside the typed `EffectiveOperation.capabilities` | changed |
| pydantic-settings | Deployment settings | — | Analytics fields declared and unread ([DA-020](boundaries-and-composition.md#da-020)) | unchanged |
| Plain frozen dataclasses with cattrs | The effective operation model | cattrs decodes the archive | Facts it holds per operation (entry points, profile, forms) restated in kernels | changed |
| pyarrow | DuckDB analytical relation schemas (hand-written) | PDF record and export schemas from `MetaData` | — | unchanged |
| DuckDB | Nothing; it computes over relations built elsewhere | — | Its input shapes are hand-written in three modules ([joint page](model-and-execution.md#analytical)) | unchanged |
| valuesets; linkml-term-validator, oaklib, pronto; attrs, msgspec | As on the previous map: vendored YAML copies only; ontology bindings and dynamic enum expansion; not used | As on the previous map | — | unchanged |

## One compiled operation model, and what sits around it

Inside the declared-data-operations target there is one compiled operation model per release.
Four declaration media feed it (Python literals, LinkML kinds, the protocol, schema-derived
kinds), their origins are tracked, and conflicting owners and unresolved references are refused
(`semantic/data_operation_compilation.py:823–830, 955–960, 1836–1838`). Semantic identity
(recipe, kind and slice fingerprints) is kept apart from build provenance (the release id), and
the native request key uses the semantic identity
(`semantic/binding_admission_native.py:213`; `semantic/request_attachment_native.py:1254–1317`).
That separation is what lets a result survive a new release.

Around that model sit further inventories that it does not govern:

- the separate LinkML view that each consumer composes
  ([DA-085](semantic-model-and-authority.md#da-085));
- the earlier core and system model, with its own generated code, revision log and pack
  schemas ([DA-072](semantic-model-and-authority.md#da-072));
- the hand-written release composition ([DA-073](semantic-model-and-authority.md#da-073));
- the hand lists inside the native kernel and its installation
  ([DA-070](semantic-model-and-authority.md#da-070), [DA-074](native-integrity.md#da-074)), and
  literals in generators for facts that are declared
  ([DA-086](semantic-model-and-authority.md#da-086));
- the three encodings of the support graph ([DA-071](semantic-model-and-authority.md#da-071));
- the hand-kept lists that stand for "the code that determines this artifact"
  ([DA-068](execution-fit.md#da-068), [DA-082](execution-fit.md#da-082),
  [DA-076](served-claims.md#da-076)) and the hand-written description of the scientific kernel
  ([DA-077](served-claims.md#da-077));
- the small residue of hand-written PostgreSQL left by the conversion
  ([DA-084](boundaries-and-composition.md#da-084)).

The model therefore covers operations, kinds, roles, states and identities well. What it does
not yet hold are several facts about how those operations are *governed at run time*: which
validity rules apply, what a support edge means, what must be guarded, who may execute what,
and which code an answer depends on.

<a id="openness"></a>

## Where the model is open and where the kernel closes it

Established 2026-11-18 at `5139eaba3` by the model lane. "Open" here means a state that is
optional, provisional or allowed to vary; "closed" means a fixed set outside which the code
refuses.

**Openness declared in the model, kept or added in `d78c98765..5139eaba3`:**

| Site | State | Character |
|---|---|---|
| `model/semantic/data-operation-native.yaml:469–493` | A read selection is one of an intent selection or a public selection (`read_demand_selection`); `authority_selection` carries `protected_dependencies: undisclosed`, an explicit undisclosed authority state | Added, declared |
| `model/semantic/data-operation-physical.yaml:629` | `public_disclosure`, a required boolean on the read boundary with default false, read by the projections | Added, declared |
| `semantic/characterization_ports.py:746–749`; `methods/characterization.py` (`b0ae4d21a`) | Composition inputs declared `collection: set` and ordered canonically, without asserting a reading order | Added, declared |
| `semantic/data_operation_bindings.py` (`1d3640990`) | Independent optional binding roles admit the anchor's empty row | Kept, declared by the `optional` operator |

**Openness that is implicit in the kernel:**

| Site | State | Character |
|---|---|---|
| A null `validity_family`; the dispatch default; the guards' early returns | "No validator applies" cannot be told apart from "omitted" | Kept, implicit: the fail-open shape of [DA-070](semantic-model-and-authority.md#da-070) |
| `semantic/definition_admission_native.py:345–350` | An unlisted id falls to the last factory by default | Implicit; masked because the guard returns for unlisted ids first |

**Closed sets, with their origin:**

| Site | Closed set | New or transcribed from the SQL it replaced |
|---|---|---|
| `semantic/data_operation_projections.py:91–103` | Public reads disclose only kinds whose universe is `ordinary` or `source` | New (`6d699ab46`, `ed410b80f`) |
| `semantic/data_operation_preparation.py:305–330` | A native selection must have exactly the keys `profile`, `fingerprint`, `assets`, `asset_custody`, and its file population must equal the declared one | New (`188ec73c2`) |
| `semantic/contextual_admission_native.py:301–310, 369` | An input role may come only from listed operation ids | Transcribed |
| `semantic/contextual_admission_native.py:234–259` | Profile, forms and receipt count fixed per id | Transcribed |
| `semantic/contextual_admission_native.py:653–660` | Four encoder failure codes | Transcribed |
| `semantic/rich_admission_native.py:623–634` | Rich preparation requires one of three named owners, otherwise it raises | Transcribed |
| `semantic/closure_native.py:174–186` | An unknown runtime purpose raises | Transcribed |
| `semantic/data_product_admission_native.py:443–452` | Endpoint scope is `local` or `external`, otherwise it raises | Transcribed |
| `semantic/operation_event_native.py:488` | Partition is `development` or `feature_fit` | Transcribed (not traced) |

The pattern: the openness added recently is declared in the model (protocol variants, a
boolean, a role's collection), while the kernel's openness is implicit and its closures are
lists of operation ids. The transcribed closures are where the model expresses variability
that the kernel narrows; the query-encoder example is under
[DA-070](semantic-model-and-authority.md#da-070).

## How a change becomes recomputation

Traced through source on 2026-11-17 at `fbd3f2a98`; the kernel and release rows were re-read on
2026-11-18, the others were not.

- **Source bytes.** Product ids are content-addressed, so new source gives new inputs and new
  request keys.
- **A changed recipe, kind or result-affecting binding.** The recipe identity changes, the
  request key changes, and that operation recomputes. Binding nodes that only affect
  eligibility are dropped from the recipe (`semantic/data_operation_compilation.py:2114–2135`).
- **A changed implementation.** It enters through the implementation-slice fingerprint in the
  recipe. Where the operation declares an opaque boundary, the fingerprint is much coarser
  ([DA-069](execution-fit.md#da-069)).
- **Dependents.** They recompute only if their content-addressed inputs change, unless a role
  declares an episode identity requirement.
- **Runtime and execution profile.** Excluded from the request key. Distrust is applied by
  explicit revocation, evaluated when results are read.
- **Native kernel source (re-read 2026-11-18 at `5139eaba3`).** Any change to one of 99
  captured modules or to one of six library versions invalidates admission, reads, carried
  assurance and waiting-obligation watermarks at once, changes every native operation's
  declared behavior, and changes the release id ([DA-068](execution-fit.md#da-068)). One native
  revision in the range existed only for such a change.
- **A model YAML edit (inferred from what each identity covers, not traced end to end).** A
  physical model edit changes the physical id, the compiled `MetaData`, every generated
  program that references the changed table, the kernel digest and the release id. A renamed
  relation or column now fails generation in every converted module. The edit does not reach
  literals for declared facts ([DA-086](semantic-model-and-authority.md#da-086)), and a new
  member of an operation family reaches no guard
  ([DA-070](semantic-model-and-authority.md#da-070)).

The unit of recomputation is the request generation. The unit of scheduling is the whole
demand, swept once per round.

<a id="strengths"></a>

## Strengths to preserve

Established or re-read on 2026-11-18 at `5139eaba3`:

- Every regenerated admission module resolves relations and columns against captured
  `MetaData`, so a missing relation or column fails at generation; raw SQL text inside a
  program is refused, as is an unresolved bind parameter (`semantic/native_program.py:128–131`).
- The task guard, which already read the protocol lifecycle, is now a typed program over the
  captured `ops.task` columns (`semantic/data_operation_protocol.py:117–128`).
- Selection by a declared effect read from the lowered definition at run time
  (`semantic/rich_admission_native.py:1136–1145`), and operation constants taken from the
  operation's owner module (`GRADE_OPERATION`, `AUTHORIZATION_OPERATION`,
  `ADMISSION_OPERATION`).
- One Python table consumed by both the Python validator and the native generator
  (`STRUCTURAL_REPORT_PRODUCERS`, `semantic/declared_structural_admission.py:276`), which
  removes a copy where two existed; and a closed-set check at generation of the structural
  disclosure fields (`semantic/structural_admission_native.py:1680–1694`).
- Declared variability: the protocol's read-selection variants, the explicit undisclosed
  authority state, the `public_disclosure` column and `collection: set` read from the role
  ([above](#openness)).
- Immutability triggers derive from `ph:immutability` through `MetaData.info`
  (`semantic/target_installation.py:351–356`); privilege admission compares the complete ACL
  over `PURPOSE_ROLES`; `semantic/native_admission_functions.py:6, 149` imports
  `DEFAULT_READ_ROLES` instead of restating it.
- Scratch relations for authoring are retargeted on the parse tree
  (`semantic/native_authoring.py:303–328`).
- Universe validity reads the typed literal with `get_args(get_type_hints(...))`
  (`semantic/support_trust_native.py:91`), and the SourceValue codec is generated from the
  LinkML layout and refuses on drift (`semantic/source_value_native.py:55–66`).

Re-read at `d78c98765` on 2026-11-18; their files have no commit in the range unless noted:

- Physical enums derive from the protocol (`ph:values_from`, `schema/physical.py:62, 138`).
- Protocol function grants derive from declared `purposes`
  (`semantic/data_operation_storage.py:1897–1907` at `5139eaba3`).
- `ops.ddo_classify_command` classifies by eligibility predicates, not by ids
  (`semantic/data_operation_compiler_native.py:530–550`).
- Arrow schemas for PDF records and exports derive from `MetaData`, with the physical model id
  in the schema metadata (`semantic/pdf_record_model.py:103–122`; `semantic/arrow_types.py:13`).
- Unresolved operation and kind references refuse at compile
  (`semantic/data_operation_compilation.py:1836–1838`), and graph projections are derived from
  owned edges instead of being a second authored catalog
  (`semantic/data_operation_model.py:705–725`).
- The physical closure refuses extra or missing sources and pins the LinkML types bytes
  (`schema/physical.py:156–197`).

Carried forward from 2026-11-17, not re-read:

- Operation facts are extracted statically without importing the target, acquisition is closed
  and workspace-relative, and a file that changes during acquisition is refused
  (`semantic/python_operation_sources.py:585–645`; `semantic/data_operation_preparation.py:145–155`).
- Enforcement claims separate documentation from checked enforcement and keep documentation
  out of the recipe.
- Revocation is by selector with scoped epochs, and validity is relative to the read boundary
  (2026-11-17). A directly revoked producer cannot be rehabilitated (re-located 2026-11-18):
  settlement refuses when the producing runtime or recipe has a revocation in scope
  (`semantic/data_derivation_native.py:200–216`, refusal at `:354`), and revocation rows are
  declared `ph:immutability: intrinsic`
  (`model/semantic/data-operation-physical.yaml:513–531`), so the immutability trigger forbids
  removing one.
- Unknown is kept distinct from absent in served reports
  (`serve/contribution_facets.py:150–187, 331–341`).

## Limits

Read on 2026-11-18 at `5139eaba3` by the model lane: the model-authority findings and their
cited code; the contextual and definition admission generators in large part; the three
`native_admission_*` modules; the full diffs of the model YAML and of six owner modules.
Sampled: the rich, operation-event, structural, record-policy, record-grade and product
admission generators. Not read: generator bodies for equivalence with the SQL they replaced;
`archive_native.py`, `pdf_spool_native.py` and `visual_read_native.py` beyond searches; tests;
`semantic/ontology.py` beyond its dynamic-enum block; `semantic/conditional_rules.py`;
`schema/stage_b.py`; `schema/rulelang.py`. Counts are search counts with the stated patterns.
Whether the per-consumer closures differ in result was not tested. The library inquiry
recorded on 2026-11-05 was not repeated; it is in Git at `fbd3f2a98`.
