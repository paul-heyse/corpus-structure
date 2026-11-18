# Current domain model map

**Interface-checked by source inspection, 2026-11-18**, source `d78c98765`
([refresh](README.md#refresh-2026-11-18); [baseline and limits](README.md#baseline)). This is a
diagnostic map of the model found in source; the architectural owners keep authority. It
replaces the map of 2026-11-17 at `fbd3f2a98`, which was written before most of the
model-owned SQL conversion ([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md))
landed and cited the since-deleted `semantic/sql/data_operations.sql` as the realization of
most facts. That conversion is still open: the ADR and the DDO plan record residual SQL
authoring as remaining work ([DA-084](boundaries-and-composition.md#da-084)). Two
sections, marked below, carry forward 2026-11-17 observations that were not re-read.

Paths omit `python/corpus-structure/src/corpus_structure/`; `model/` is under that package;
`domains/` is at the repository root (read with `git show d78c98765:domains/…`, because the
frozen snapshot omits it). Counts marked "search" are counts of a key or pattern over the
model directory on 2026-11-18. Nothing was run.

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
| `data-operation-native.yaml` (3,007 lines, the largest model file) | JSON Schema draft-7 with `x-ddo-lifecycle` extensions and an `operations:` block from `:2783` | The protocol: wire definitions, state lifecycles and transitions, the public native operations and the `purposes` of each | Wire types, fates, physical value sets, protocol function grants |
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
| Native programs | Compiled tables and call bindings, to SQLAlchemy Core statements and parsed PostgreSQL nodes framed by the program compiler, to SQL text, to server-normalized catalog objects frozen in a migration revision | `semantic/native_program.py`; `semantic/data_operation_storage.py:48–567, 753–862`; `semantic/native_objects.py:381–440, 950–1121`; `semantic/target_installation.py:189–405, 767–855` (the last two as read by the generator lane) |
| Earlier | `core.yaml` and `system.yaml`, to `Model`, to vocabulary, `_model`, stage-B pydantic shapes and JSON Schemas | `schema/generate.py:560–578` |

The native program path is the conversion's addition. Its finite forms, and the rule that Core
and parsed nodes own statements while the compiler owns only procedural framing, are stated in
`semantic/native_program.py:1–5, 176–320`. What happens after rendering is part of
[DA-081](semantic-model-and-authority.md#da-081).

<a id="generated"></a>

## What is generated from each source

| Source | Generated from it |
|---|---|
| `MetaData` | Tables and DDL through Alembic autogenerate; typed column facades (`_typed_columns.py`, via `schema/relational.py:768`); `identifiers.py` (`semantic/typed_generation.py:21`); PDF native ids and calls; source-admission calls; Arrow schemas for PDF records (`semantic/pdf_record_model.py:103–122`) and exports (`serve/native_source.py:944–971`, via `semantic/arrow_types.py:13`); immutability and archive triggers; and the table objects every typed native program references |
| Protocol | `_data_operation_wire.py`, `_data_operation_fates.py`, physical enum checks, function grants by purpose, the task guard's states |
| Effective operation model | Lowered definitions (at release admission, in PL/pgSQL), identities, graph projections, the source-interface export |
| Seven generated Python facades, rendered together at preview | `_source_admission_calls.py`, `_typed_columns.py`, `identifiers.py`, `_data_operation_fates.py`, `_pdf_native_calls.py`, `_pdf_native_ids.py`, `_data_operation_wire.py` (`schema/model_change.py:53–61, 525–552`; [DA-081](semantic-model-and-authority.md#da-081)) |
| **No declaration** | The native kernels for validity, completion and family guards (typed programs or hand-written SQL strings that reference generated tables but take their membership lists from Python: [DA-070](semantic-model-and-authority.md#da-070), [DA-084](boundaries-and-composition.md#da-084)); DuckDB relation schemas (`semantic/analytical_kernels.py:21–60`; `semantic/rich_relations.py:24–34`; [DA-086](semantic-model-and-authority.md#da-086)); data steps (`schema/data_steps.py`, closed first-party builders); the scientific policy recipe ([DA-077](served-claims.md#da-077)) |

<a id="fact-ownership"></a>

## Fact ownership

"Derivable from today" names an existing typed source in the codebase that the code literal
could be computed from, or says that none exists and a declaration would be needed. It is a
statement of what exists, not a selected change.

| Fact | Declared in the model | Held as code | Restated at | Derivable from today |
|---|---|---|---|---|
| Record and product shape | LinkML classes (`model/semantic/*.yaml`, packs) | — | Earlier-model copies ([DA-072](semantic-model-and-authority.md#da-072)); DuckDB Arrow schemas (`semantic/analytical_kernels.py:21–60`; `semantic/rich_relations.py:24–34`) | Rich and view relations: none, needs a declaration. PDF: already from `MetaData` |
| Field type and constraint | LinkML range, pattern, minimum; `ph:checks` JSON | — | The `data_kind_contract` universe check (`model/semantic/data-operation-physical.yaml:71`) beside `_KIND_UNIVERSES` (`semantic/data_operation_compilation.py:341`) | The `NativeKindProjection["universe"]` typed literal, already read at `semantic/support_trust_native.py:91` |
| Field kind to database and Python type | LinkML type `uri` and the `ph:sql_type` annotation (for example `model/semantic/physical.yaml:33–36`) | — | Four maps (`semantic/native_call_contracts.py:16–25`; `semantic/native_call_sources.py:28–37`; `semantic/pdf_search_native.py:98–104`; `semantic/native_program.py:621–622`; [DA-086](semantic-model-and-authority.md#da-086)) | The physical compiler's type resolution (`schema/relational.py:79–89, 437–440`) |
| Enum and value set | LinkML enums; protocol enums | — | Six or more enums in both cores; the PDF outcome pair | One side from the other (none chosen) |
| Operation | — (by the two-route design of ADR-0092) | `__data_operation__` declarations in about 62 modules | — | None; Python is an admitted declaration medium |
| Operation inputs, outputs and dependencies | — | Literal `roles`, `dependencies` | The `changed_operations` graph (`semantic/change_impact.py:157–193`) | Compiled `selected-dependencies` and `potential-producers` (`semantic/data_operation_model.py:713–725`) |
| Validity family | **Column only, no values** (`model/semantic/data-operation-physical.yaml:88`) | Tuple at `semantic/data_operation_compiler_native.py:468–519` | Dispatch tuple (`semantic/data_validity_native.py:272–282`); guard lists (contextual `:16–21, 214–219`; definition `:83, 106, 124`; rich `:183`; record grade `:691`); completion chain (`semantic/data_completion_settlement_native.py:712–800`); guard tuple (`:537–553`) | None; needs a declaration. A host exists: the effective operation is lowered right beside it (`data_operation_compiler_native.py:905–926`) |
| Per-operation family contract (entry point, profile, forms) | Per operation in the effective model | SQL `CASE` (`semantic/contextual_admission_native.py:23–44`) | — | `EffectiveOperation.capabilities.prepared_factory`, `.profile`, `.capabilities.forms` (`semantic/data_operation_model.py:288–296, 497`). Caution: the `CASE` is compared with the admitted definition and so acts as an independent pin; taking it from the effective model keeps a meaningful check only if the kernel's captured model and the admitted release stay distinct inputs |
| Support-edge meaning; reference-to-node map | — | Validity edges (`semantic/data_validity_native.py:88–240`) | `_support_walk` (`semantic/data_operation_projections.py:117, 132–242`); `_revocation_causes` (`semantic/change_impact.py:332–441`) | None; needs a declaration |
| Trust-scope key | — | `ops.ddo_scope` (`semantic/support_trust_native.py:100–118`) | `semantic/change_impact.py:427` (disagrees) | The `ddo_scope` program itself, or one shared Python function |
| Frontier-guard membership | — | Twelve-name tuple (`semantic/data_operation_storage.py:1936–1949`) | The admission descriptor, built from the same list | None; immutability does not separate the relations; needs a declaration |
| Shared-stream trigger membership | **`ph:immutability: pending-content`** (`model/semantic/physical.yaml:1757, 1776`) | Name set (`semantic/target_installation.py:350`) | — | `relation.info["immutability"]`, already populated (`schema/relational.py:492`) |
| Immutability and archive triggers | `ph:immutability`, `ph:archive_role` | — | — | Already derived (sound) |
| Task states and transitions | Protocol lifecycle (`model/semantic/data-operation-native.yaml:5–14`) | String literals in kernels (`semantic/data_claim_native.py:77`; about 37 sites in twelve generators, survey) | — | The protocol lifecycle, already read by the task guard (`semantic/data_operation_protocol.py:116–160`) |
| Role names; purpose-to-role map | Purposes per protocol function (`data-operation-native.yaml:2783` onward) | Dictionary (`semantic/data_operation_storage.py:1887–1893`); `PUBLISHER`, `DEFAULT_READ_ROLES`, `PURPOSE_ROLES` (`semantic/alembic_privileges.py:25–35`) | `sql/admission.sql:130, 148, 162–186`; `semantic/target_installation.py:209–231, 266–277`; the name chain at `data_operation_storage.py:1896–1914`; 176 occurrences of role names in 39 modules (literals, constants, comments and SQL strings) | Purposes: yes. Role names and defaults: none; needs a declaration |
| Table read grants | `ph:read_roles` (deny only; all `'[]'`) | Default from code (`semantic/alembic_privileges.py:74–75`) | `sql/admission.sql:148` | `relation.info["read_roles"]`, once defaults are declared |
| Release composition | Flags (`domains/statistics/operations.yaml`) | `semantic/primary_operations.py:118–392` | Family source functions ([DA-073](semantic-model-and-authority.md#da-073)) | Partly: static operation extraction exists before compilation (`semantic/python_operation_sources.py`). The map from family to source: none |
| Physical index and check | `ph:indexes`, `ph:checks`, `unique_keys` | — | — | Already derived; admission compares them (sound) |
| Wire shape | Protocol draft-7 | — | Wire-type map (`data-operation-wire-types.yaml`) | Already derived |
| Value-codec vocabulary | SourceValue variants in the LinkML observations schema | Python `Literal` types and a hand tuple for the data-operation codec (`semantic/data_operation_value_native.py:44–50`) | — | The SourceValue codec already reads LinkML (`semantic/source_value_native.py:55–66`); the two codecs have separate authorities |
| Search configuration | `ph:search_configuration` (`model/semantic/physical.yaml:1733`) and a check | — | — | Already derived |
| Identity determinants | Operation literals (recipe, eligibility) | `_compile_identities` (`semantic/data_operation_compilation.py:2138–2233`) | — | Compiled (sound) |
| Scientific policy parameters | `scientific-policies.yaml` (not LinkML); a `numerical_policy` asset per operation | — | Archived recipe text ([DA-077](served-claims.md#da-077)) | Not examined |
| Which code determines an artifact (kernel, PDF lowering, served read) | Implementation slices for Python operations only (`semantic/data_operation_identity.py:378–414`) | Capture enumerated in code; `LOWERING_FILES`; query-custody lists | Each other, in part ([DA-068](execution-fit.md#da-068), [DA-082](execution-fit.md#da-082), [DA-076](served-claims.md#da-076)) | None for native generators, PDF lowering or served reads |
| Generated-facade and program-set ownership | — | `_NATIVE_OUTPUTS` (`schema/model_change.py:53–61`); the six program lists of [DA-081](semantic-model-and-authority.md#da-081), two of which disagree | Owner writers; `LOWERING_FILES` (`semantic/pdf_lowering.py:33–104`) | The owners' path constants. A registry of the `schema/generate.py:540–578` kind exists only for the earlier model |
| Graph-projection catalog | — | `compiled_graph_projections` | — | Derived from owned edges (sound; `semantic/data_operation_model.py:705–725`) |

<a id="library-roles"></a>

## Data-model libraries and their roles

Pinned versions are in `python/corpus-structure/pyproject.toml` (LinkML 1.12.1, DuckDB 2.0.0,
SQLAlchemy 2.1.6, pglast 8.7, SQLGlot 30.27.0, pydantic 2.14.1, pyarrow 26.0.0).

| Library | Source of truth for | Holds as derived (from what, where) | Same fact held independently elsewhere |
|---|---|---|---|
| LinkML, linkml-runtime | Classes, enums, physical tables (through `ph:`), projections, packs | — | Enums in both cores ([DA-072](semantic-model-and-authority.md#da-072)); operation shapes are Python literals, not LinkML |
| SQLAlchemy `MetaData` and Core | Nothing primary | Tables, columns, checks, indexes and `info` (`schema/relational.py:385–563`); native programs as Core statements | Role and guard membership beside it ([DA-074](native-integrity.md#da-074)); DuckDB Arrow schemas |
| Alembic | The migration graph; privilege operations | Autogenerate from `MetaData`; privilege policy from `info["read_roles"]` plus `DEFAULT_READ_ROLES` (`semantic/alembic_privileges.py:74–75`) | Default roles again in `sql/admission.sql:148` |
| pglast | — | Parses and normalizes every native statement; supplies PostgreSQL-only nodes to programs; re-parses the assembled kernel text (`semantic/data_operation_storage.py:1873–1875`); validates submitted read-only SQL (`semantic/authored_sql.py`) | — |
| SQLGlot | — | Projection lineage and type analysis (`semantic/projection_analysis.py:15–21`); a change-explanation diff | — |
| jsonschema | Validation of the protocol (draft-7) | Wire validation from the protocol (`semantic/data_operation_wire.py:22`); nullable inference (`semantic/data_operation_compilation.py:2544–2611`) | Protocol enums also appear in physical checks, derived through `ph:values_from` (sound) |
| pydantic | Earlier-model shapes (stage B); 144 `BaseModel` classes in `semantic/` and `schema/` (preview requests, data-step parameters, native effects) | A `TypeAdapter` boundary for PDF records from `MetaData` (`semantic/pdf_record_model.py:125`) | The hand-written `BaseModel` classes were not compared field by field with `MetaData` (not examined) |
| pydantic-settings | Deployment settings (`settings.py:219`) | — | Analytics fields declared and unread ([DA-080](boundaries-and-composition.md#da-080)) |
| Plain frozen dataclasses with cattrs | The effective operation model (`semantic/data_operation_model.py:53–890`) | cattrs decodes the archive (`:1225–1264`) | The `profile` literal (`:497`) restated in `_PROFILES` (`semantic/data_operation_compilation.py:85`) |
| pyarrow | DuckDB analytical relation schemas (hand-written) | PDF record and export schemas from `MetaData` (`semantic/pdf_record_model.py:103–122`; `semantic/arrow_types.py:13`); PDF payloads from JSON Schema (`semantic/pdf_payloads.py:87–149`); companion export schema from the LinkML projection (`semantic/companion_projection.py:88–140`) | — |
| DuckDB | Nothing; it computes over relations built elsewhere | — | Its input shapes are hand-written in three of five modules ([joint page](model-and-execution.md#analytical)) |
| valuesets | Vendored YAML copies only; the package is not imported | — | — |
| linkml-term-validator, oaklib, pronto | Ontology bindings; dynamic enum expansion | Members expanded at preparation (`semantic/ontology.py:380–395, 644`) | — |
| attrs, msgspec | Not used | — | — |

## One compiled operation model, and what sits around it

Inside the declared-data-operations target there is one compiled operation model per release.
Four declaration media feed it (Python literals, LinkML kinds, the protocol, schema-derived
kinds), their origins are tracked, and conflicting owners and unresolved references are refused
(`semantic/data_operation_compilation.py:823–830, 955–960, 1836–1838`). Semantic identity
(recipe, kind and slice fingerprints) is kept apart from build provenance (the release id), and
the native request key uses the semantic identity
(`semantic/binding_admission_native.py:213`; `semantic/request_attachment_native.py:1024–1539`).
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
- hand-written PostgreSQL whose conversion is scheduled and still open
  ([DA-084](boundaries-and-composition.md#da-084)).

The model therefore covers operations, kinds, roles, states and identities well. What it does
not yet hold are several facts about how those operations are *governed at run time*: which
validity rules apply, what a support edge means, what must be guarded, who may execute what,
and which code an answer depends on.

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
- **Native kernel source (re-read 2026-11-18).** Any change to a captured module or to one of
  six library versions invalidates admission, reads, carried assurance and waiting-obligation
  watermarks at once, changes every native operation's declared behavior, and changes the
  release id ([DA-068](execution-fit.md#da-068)).
- **A model YAML edit (2026-11-18; inferred from what each identity covers, not traced
  end to end).** A physical model edit changes the physical id, the compiled `MetaData`, every
  generated program that references the changed table, the kernel digest and the release id.
  It does not reach hand-written bodies
  ([DA-084](boundaries-and-composition.md#da-084)) or literals for declared facts
  ([DA-086](semantic-model-and-authority.md#da-086)).

The unit of recomputation is the request generation. The unit of scheduling is the whole
demand, swept once per round.

<a id="strengths"></a>

## Strengths to preserve

Established or re-read on 2026-11-18 at `d78c98765`:

- Immutability and archive triggers derive from `ph:immutability` and `ph:archive_role`
  through `MetaData.info` (`semantic/data_operation_storage.py:1925–1935`;
  `semantic/target_installation.py:334–347`).
- Physical enums derive from the protocol (`ph:values_from`, `schema/physical.py:62, 138`;
  `model/semantic/data-operation-physical.yaml:11–14`).
- Protocol function grants derive from declared `purposes`
  (`semantic/data_operation_storage.py:1885–1895`).
- Universe validity reads the typed literal with `get_args(get_type_hints(...))`
  (`semantic/support_trust_native.py:91`), and the SourceValue codec checks its closed set
  against LinkML and refuses on drift (`semantic/source_value_native.py:55–66`).
- `ops.ddo_classify_command` classifies by eligibility predicates, not by ids
  (`semantic/data_operation_compiler_native.py:530–550`).
- Arrow schemas for PDF records and exports derive from `MetaData`, with the physical model id
  in the schema metadata (`semantic/pdf_record_model.py:103–122`; `semantic/arrow_types.py:13`;
  `serve/native_source.py:944–971`).
- Unresolved operation and kind references refuse at compile
  (`semantic/data_operation_compilation.py:1836–1838`), and graph projections are derived from
  owned edges instead of being a second authored catalog
  (`semantic/data_operation_model.py:705–725`).
- The physical closure refuses extra or missing sources and pins the LinkML types bytes
  (`schema/physical.py:156–197`).
- Native programs resolve relations and columns against compiled tables, so a missing relation
  or column fails at generation; raw SQL text inside a program is refused; a security-definer
  routine without a search path is refused (`semantic/native_program.py:126–131, 536–538`).

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

Read on 2026-11-18 by the model lane: the six model-authority findings and their cited code,
the composition sites, the model YAML by header and by search counts, and the dataclass fields
of the effective model. Not read: generator bodies for equivalence with the SQL they replaced;
`semantic/ontology.py` beyond its dynamic-enum block; `semantic/conditional_rules.py`;
`schema/stage_b.py`; `schema/rulelang.py`; the DuckDB modules beyond their schemas. Whether the
per-consumer closures differ in result was not tested. The library inquiry recorded on
2026-11-05 (LinkML, Pydantic, RDFLib, pySHACL and others) was not repeated; it is in Git at
`fbd3f2a98`.
