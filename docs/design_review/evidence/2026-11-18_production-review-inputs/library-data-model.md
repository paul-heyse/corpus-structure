# LinkML and the data-model libraries as owners of one domain model

Library research for the design review, 2026-11-18. Baseline is snapshot `d78c98765` (`snap5/`).
Installed contracts were checked in the repository venv
(`/home/paul/corpus-structure/.venv`: linkml 1.12.1, linkml-runtime 1.12.1,
linkml-term-validator 0.4.5, pydantic 2.14.1, jsonschema 4.26.0). The venv was used read-only.
A throwaway probe lives in the session scratchpad (`linkml_probe/`), not in the repository.

**Evidence labels.** **[Doc]** means upstream documentation says it (from the overviews or
Context7). **[Obs]** means I saw it in the installed source or in the probe, run 2026-11-18
against 1.12.1. **[Src]** means a fact about project source, with a path relative to
`snap5/python/corpus-structure/src/corpus_structure/`. **[Inf]** means my inference.
**[Unconf]** means I could not confirm it.

**What I read.** In full: the overviews `linkml.md` (§3–§11 and addendum §1–§2, §4–§5,
§8–§12), `linkml_extension_libraries.md` and `linkml-map.md` §1–§16. In part: `valuesets.md`
(§1, §4, §6, §10–§12 and addendum §2). Skimmed for headings only: `linkml-datalog.md`,
`pyshacl.md`, `rdflib.md`, `PyOxigraph.md`, `schema-automator.md`. Not read: `jsonschema.md`,
`pydantic.md` and `msgspec_attrs_and_cattrs.md`.

In project source I read `schema/model.py:1–260`, the heads of `schema/stage_b.py`,
`schema/relational.py` and `semantic/conditional_rules.py`, `semantic/ontology.py` (its
imports), `schema/generate.py:545–580` and one operation literal
(`semantic/operation_policy.py:230–330`). I sampled the model YAML and the audit pages
DA-070 to DA-074 and DA-081. I did not read the operation compiler body or the physical
annotation reader in full.

---

## 0. Facts about the installed versions that drive the answers

| # | Fact | Label |
|---|---|---|
| F1 | `Annotation.value` is `AnyValue`, and annotations can nest. A structured value (a list of dicts) loads as a Python list through `SchemaView`. The project's JSON-string annotations, such as `ph:foreign_keys: '[{...}]'` in `model/semantic/physical.yaml:87`, are therefore unnecessary. | [Obs] |
| F2 | **Class annotations are not inherited.** `induced_class("Child")` returns no annotations even when its `is_a` parent and its mixin both carry annotations. `annotation_dict` is also empty. | [Obs] |
| F3 | **Slot annotations are inherited, but `slot_usage` replaces them.** An inherited attribute keeps its annotations. A `slot_usage` that sets any annotation yields only the `slot_usage` dict: the base `ex:sql_type` disappears. | [Obs] |
| F4 | Induced slot annotations come back as a `jsonasobj2.JsonObj`, not a dict. The project's `ci_annotations` (`schema/model.py:238–246`) already copes with this. | [Obs] |
| F5 | Annotations are untyped by default. The docs say an element that `instantiates` a metaclass "validates all annotations" (LinkML ≥1.6), but they also say enforcement is "under active development". In 1.12.1 the only enforcement is `InstantiatesValidationPlugin`, which checks two hard-coded tags (`must_not_have_id_slot`, `must_be_inlined`). Nothing validates annotation values against the metaclass's slots. | [Doc] + [Obs] `linkml/validator/plugins/instantiates_validation_plugin.py` |
| F6 | `SchemaView.induced_enum` does not expand `inherits`, `include` or `minus`. In the probe, `KindEnum` (inherits `BaseEnum`) induced only its own `Z`, and `MinusEnum` induced nothing. The project's own `expand_enum` exists for exactly this reason (`schema/model.py:25–31`). | [Obs] |
| F7 | The JSON Schema and Pydantic generators share that gap: `KindEnum` became `enum: ['Z']`, so the inherited value `X` was rejected. `MinusEnum` got no `enum` at all. | [Obs] |
| F8 | `rules` (pre- and postconditions) **are** enforced by the JSON Schema plugin, which emits `if`/`then` and reported `'a' is a required property`. The Pydantic plugin did **not** enforce the same rule. | [Obs] |
| F9 | `unique_keys` were enforced by neither the JSON Schema nor the Pydantic validator: a duplicate `(a,b)` passed. `gen-sqltables` emits `UNIQUE (a, b)` plus an index. | [Obs] |
| F10 | `gen-sqltables` and `RelationalModelTransformer` read only these annotations: `index` (class), `primary_key` and `foreign_key`. They have no notion of PostgreSQL schemas, range, vector or tsvector types, checks, triggers or grants. | [Obs] `generators/sqltablegen.py:250,305`; `transformers/relmodel_transformer.py:22–32` |
| F11 | The `Generator` base (`linkml/utils/generator.py:83`) is a single-schema visitor: `visit_class`, `visit_slot`, `visit_enum`, then `serialize() -> str`, with an optional `directory_output`. It has no multi-output registry and no ownership check. `gen-project` only sequences generators. | [Obs] |
| F12 | `linkml.validator.plugins` exports the JSON Schema, Pydantic, RecommendedSlots and Instantiates plugins. A `shacl_validation_plugin.py` module exists but is not exported from `__init__`. The CLI has no schema-diff command. | [Obs] |
| F13 | linkml-map, schema-automator and linkml-datalog are **not installed**. pyoxigraph and sssom are present only as dependencies. | [Obs] |

---

## A. Declaring operational facts

### A.1 Mechanisms: what each one is, and its contract at 1.12.1

- **`annotations`** (the `extensions` slot is equivalent). Use these for facts *about a schema
  element*: a class, slot, type, enum or permissible value. Values are untyped and
  unvalidated (F5). Class annotations are not inherited (F2), and `slot_usage` replaces
  inherited slot annotations rather than merging (F3). Structured values work (F1). No stock
  tool acts on them except the three SQL tags in F10. Any custom tag needs its own reader and
  its own checker.
- **`subsets` and `in_subset`.** Named, declared groups. `linkml-lint` refuses undeclared
  subsets (`NoUndeclaredSubsetsRule`) [Obs], and `SchemaView.all_subsets()` and an element's
  `in_subset` enumerate members. The project already uses `in_subset` on permissible values as
  "member properties" that require a declared consumer (`schema/model.py:14–23`). Limits:
  - membership is positive only, so leaving an element out is indistinguishable from
    deciding to exclude it;
  - I did not establish whether `in_subset` inherits through `is_a` [Unconf].
- **`instantiates` and a profile metaclass.** This is the documented way to type annotations,
  but only declarative in 1.12.1 (F5). The supported pieces still compose into a working
  check (see A.3).
- **`implements`.** Declares that a class or slot conforms to a role without inheriting from
  it, for example a slot that implements `rdfs:label`. The only reader I know of is
  term-validator's label discovery [Doc]. It is weak as a carrier of operational facts.
- **`class_uri`, `slot_uri` and mappings.** These give semantic identity. They are not
  executable and do not carry operational facts.
- **Enums.** Each permissible value can carry `meaning`, `annotations`, `in_subset` and
  `description`, which suits closed vocabularies that have per-member properties. Dynamic
  enums (`reachable_from`, `concepts`, `include`, `minus`, `inherits`, `matches`) are
  resolved only by tooling: term-validator's `DynamicEnumPlugin` (no `matches`), or the
  project's own `expand_enum` for the static composition operators (F6) [Doc]/[Obs].
- **`rules`, `classification_rules`, `equals_expression` and the boolean expressions
  (`any_of`, `all_of`, `exactly_one_of`, `none_of`).** These are per-instance constraints.
  - Enforcement depends on the generator: JSON Schema handles rules (F8); Pydantic does not;
    `classification_rules` and `equals_expression` need runtime inference, which is off by
    default [Doc].
  - The docs label this area experimental [Doc].
  - They constrain one record. They cannot say "every operation in family F has property P",
    and they cannot state cross-record facts.
- **`unique_keys`.** A native compound key. SQL DDL honours it (F9); no instance validator
  does.
- **`slot_usage`.** Contextual refinement of a slot within a class. Beware F3.
- **`structured_pattern` and `settings`.** Reusable regular-expression fragments, resolved by
  `resolve_pattern()` [Doc]. Fine for identifier formats; not a carrier of operational facts.

### A.2 Where each fact belongs: three candidate routes per fact

The rule that falls out of F1–F5 [Inf]:

- **An annotation** is sound only when the fact is about a *schema element* and is read by a
  project compiler that also *checks* it.
- **Instance data that conforms to a LinkML class** is the right home when the fact is about a
  *domain or operational entity*: an operation, a family, a role, a release or a policy. Such
  data gets typed validation, closed-world checks, defaults, docs and generated Python types
  for free. Annotation values get none of these (F5).
- **Connecting code to a declaration that already exists** comes first whenever an existing
  typed declaration determines the fact. It needs no new specification.

Today operations are **already instance data**: `__data_operation__` dict literals in 85
modules [Src], compiled into hand-written frozen dataclasses (`semantic/data_operation_model.py`,
40+ classes) through a strict cattrs converter (`:1215–1260`) [Src]. They are just not
instances of a *LinkML* class.

| Fact | Sound home | Lighter route through an existing declaration | When a new declaration is truly needed |
|---|---|---|---|
| Validity-family membership of an operation (DA-070) | A field on the operation declaration, with its range a LinkML enum `ValidityFamily`. Include an explicit `none` member, make the field required, and refuse an absent value. The family contract (premises, completion guard) goes on the enum member as structured annotations, or on a `ValidityFamily` instance. | DA-070 notes the model already declares `support_contract.capabilities`, `profile` and `implementation_root` per operation, and that `ddo_classify_command` classifies by predicate rather than by list. If family is a pure function of those compiled fields, derive it in the compiler and generate the SQL `CASE` or table from the compiled model. No new specification is needed. | When family is a deliberate choice that existing fields do not determine. Then it must be a required field, never an inferred default; a missing value must refuse. Annotations would be wrong here because operations are not schema elements. |
| Dependency or support edge between products (DA-071) | Edges are already instance data: role `kind` plus `support` (`provenance`, `source`, `identity_requirements`). What is missing is the *meaning* of each edge kind, which needs a closed vocabulary `SupportEdgeKind` (use, episode, population, original). Each member should declare its traversal (follows producer, populations, episode or selected support, under which provenance) and its scope-key rule as structured data. | The compiler already builds the dependency graph (`potential-producers` and `selected-dependencies`). Have the change-impact and projection walkers consume that compiled graph plus the declared traversal table, instead of re-deriving it (`change_impact.py:177–193`). | The traversal semantics themselves. They exist today only as three pieces of code, so they need one declaration from which the SQL validity walk and the Python walks are generated or parameterized. |
| Which relations a guard covers (DA-074) | An annotation on the relation class, because a relation is a schema element. It should be a **required total classification**, for example `ph:frontier_guard: guarded \| exempt`, on every class in the guarded schema, enforced by the profile check (A.3). `in_subset: [frontier_guarded]` alone does not fix fail-open, since an absent element is not a decision. | — | Yes. Today the fact exists only as a code list. |
| Which roles receive which grants | Relations: the physical model already declares read roles per relation (DA-074), so extend that with structured annotations. Generated functions: the grant belongs to the *program declaration*, a typed Python object in the program compiler. | Derive EXECUTE grants from the program registry the compiler already builds, so membership is the program's own field and not a separate list. | Role definitions (role names, prohibited memberships) are operational entities. They suit a small instance document validated against a LinkML `Role` class, or a typed Python registry. |
| Which operations a release contains (DA-073) | A manifest instance validated against a LinkML `ReleaseManifest` class that names families or operations. | The compiled dependency closure already determines what executes. Add one field, `acquired_by: <source family>`, to the operation declaration; composition then becomes "closure of the requested operations, mapped to source families". That removes the flag logic. | Only that `acquired_by` field. |
| Physical checks and indexes | Annotations on classes and slots, as today. Use structured values (F1) instead of JSON strings, typed by a profile (A.3). Use native `unique_keys` for uniqueness (F9). | — | Already declared, partly. Type it. |
| Identity determinants | Use a named `unique_key` (for example `identity`) when the determinant set is also a database uniqueness. That one declaration then feeds both the DDL `UNIQUE` and the digest recipe. Otherwise use a required slot annotation such as `ph:identity: determinant \| excluded` on identity-bearing classes, with a totality check. | The per-operation recipe identities are compiled already (`data_operation_compilation.py:2138–2233`); no new declaration is needed there. | Only for record identities not yet declared. Caveat [Inf]: digest semantics (nullable or multivalued members, canonical form) differ from SQL `UNIQUE`, so one declaration fits both only when they truly coincide. |
| Search configuration and scientific policy parameters | Instance documents validated against LinkML classes. `model/semantic/scientific-policies.yaml`, `analysis-policy.yaml` and `metrics.yaml` are already instance lists without a LinkML header [Src]. | If a policy's shape is already a typed Python class, validate the YAML through it; but make LinkML the source of that class, or the class becomes a second metamodel. | The shape, if none exists. |
| Registry of generated outputs (DA-081) | A typed Python registry is the right authority, because the outputs are code artifacts and not domain data. Bring the seven facades into `schema/generate.py`'s self-checking ownership registry (`:556–578`). | Exactly that. The registry exists; the facades bypass it. | No LinkML is needed. |

### A.3 A profile that types annotations, built only from supported pieces [Inf; parts Obs]

The project already hand-rolls a profile for the older model: `VOCABULARY` in
`schema/model.py:116–178` lists, for each tag, where it may appear, its admitted values and
its consumer. A LinkML-native equivalent:

1. Author `PhysicalRelation`, `PhysicalColumn` and similar metaclasses as ordinary LinkML
   classes in a profile schema. Give them typed slots, for example `immutability`, an enum,
   and `foreign_keys`, a multivalued inlined `ForeignKey`.
2. Mark the elements with `instantiates: [ph:PhysicalRelation]`.
3. In a small custom `ValidationPlugin`, or a plain loop at build time, read each element's
   annotations (F1, F4), strip the prefix, and validate the resulting dict as an instance of
   the metaclass. Use the standard `Validator(profile, [JsonschemaValidationPlugin(closed=True)])`.

This gives closed, typed, documented annotation contracts declared in LinkML, at the cost of
about 50 lines of glue. It replaces string-encoded JSON and hand checks. Because of F2, the
reader must resolve class-level inheritance itself, for example by walking `class_ancestors`.

### A.4 Annotations compared with instance data, concretely

| | Annotation on a schema element | Instance of a LinkML class |
|---|---|---|
| Typing and validation | None by default (F5); needs A.3's glue | Native: JSON Schema or Pydantic plugins, closed-world (F8) |
| Inheritance | Class: none (F2). Slot: replaced by `slot_usage` (F3) | Not applicable; references are explicit |
| Cross-record constraints | Custom code | Custom code too (F9); but the records are uniform, so one compiled pass checks them |
| Generated Python types | None | Pydantic or dataclasses, or the project's own emitter |
| Locality | Sits beside the shape it qualifies | Separate document, or a Python literal next to the callable (today's operation pattern) |
| Precedent | ADR-era `ci:` and `ph:` tags | linkml-map's own `TransformationSpecification` is a LinkML schema with generated classes [Doc] |

**Verdict [Inf].**
- Physical facts belong in annotations, under a typed profile.
- Operational entities (operations, families, edge kinds, roles, manifests, policies) belong
  in instance data, with their vocabularies as LinkML enums. A **Python literal colocated with
  the callable is a valid storage form** for that data, provided its *schema* is
  model-authored.
- The heavy part is the operation metamodel: 40+ hand dataclasses plus cattrs. Two sound end
  states exist:
  1. a LinkML-authored declaration schema, with generated typed classes replacing the hand
     dataclasses for the *authored* document; the compiled `EffectiveDataOperationModel` stays
     derived Python;
  2. a pydantic-authored metamodel, with JSON Schema derived from it.

  Option 1 is the one that unifies. Option 2 is lighter if no consumer besides Python ever
  reads the declaration vocabulary. Today SQL reads it, through families and edge kinds, so
  at least the **vocabularies** should be LinkML enums either way.

---

## B. Composition and one authority

- **Imports and `SchemaView`.** `imports_closure()` resolves transitively. Later imports
  override earlier ones with the same name [Doc]. So importing the older and released cores
  together would silently resolve a duplicated name such as `StatementKind`. A name-collision
  refusal over the closure is cheap; the project already refuses class/enum/type name
  clashes across core and system. `merge_imports()` and `materialize_derived_schema()`
  produce one explicit schema [Obs, methods present]. `get_mappings` and `element_by_schema_map`
  give the URI mappings and each element's origin module [Obs].
- **`version` and `id`.** These are plain metadata. The project's revision is a digest of the
  canonical parse plus compiler versions (`schema/model.py:33–36`), which is stronger than
  LinkML's `version`. Keep the digest.
- **Retiring the older model (DA-072).** No LinkML tool is needed. The sound route [Inf]:
  1. make the released model authoritative for every shared value set;
  2. either regenerate `core/vocab.py`, `core/_model/*` and `core/keys.py` from the released
     model with the existing emitters, or move their live consumers (`ParseOutcome`,
     `TaskUnitType`, `CaseRule`, `core.keys`, `core.values`) to released-model types;
  3. delete `model/core.yaml`, `model/system.yaml` and `model/revisions.yaml` together with
     `schema/change.py` and `schema/pack.py`, once nothing reads them.

  The pack double declaration (`domains/statistics/schema/` against `semantic.yaml`) retires
  the same way.
- **linkml-map (0.5.4 stable; 0.6.0-rc1 is a prerelease) [Doc].** It owns *instance
  transformation between different models*:
  - the `ObjectTransformer` is the complete executor;
  - `SchemaMapper` derives target schemas, though the result may be invalid without a
    separate check;
  - `TransformationSpecificationInverter` inverts the simple cases;
  - `validate-spec` checks a specification.

  The SQL and DuckDB compiler drops `expr`, `value`, `case()`, units and value mappings
  silently [Doc]. **Do not adopt for retiring the older model.** That problem is duplicated
  schema, not data to move, and design-phase data is regenerable. Revisit only if a durable
  store must be migrated across model versions.
- **schema-automator.** Irrelevant here. It infers or imports schemas; the JSON Schema
  importer could seed LinkML from `data-operation-native.yaml`, but lossily (see G).
- **Schema diff.** There is no stock LinkML diff command (F12). Keep the project's
  classifier, rebased onto the released model; SQLGlot `diff` already serves SQL text
  (`schema/model_explanation.py:362–367`) [Src].

## C. Generators and derived artifacts

| Generator | What it gives | Fidelity limits relevant here |
|---|---|---|
| `gen-json-schema` | Closed classes (`additionalProperties: false`), `if`/`then` from `rules` (F8), patterns, bounds | No expansion of `inherits`, `include` or `minus` (F7); no `unique_keys` (F9); dynamic enums unresolved. The project already uses it narrowly for rule fragments (`semantic/conditional_rules.py`). |
| `gen-pydantic` / `PydanticValidationPlugin` | Pydantic models with `extra=forbid` | No rules (F8); same enum gap (F7). The project chose a direct emitter over `SchemaView` after probe Q-1, which overrode most of the generator (`schema/stage_b.py:17–23`). That stands. |
| `gen-sqltables`, `gen-sqla`, `RelationalModelTransformer` | Normalised relational model, FKs, link tables, `UNIQUE` from `unique_keys` | Only three annotations honoured (F10); no PostgreSQL schemas, types, checks, triggers or grants. It also emitted a table for a mixin in the probe [Obs]. The project's `schema/relational.py` (LinkML physical to SQLAlchemy `MetaData`) is the right owner. The transformer could at most supply normalisation of multivalued slots, which the project has its own rules for. |
| `gen-shacl`, `gen-owl` | RDF shapes and ontology | Already used for ontology checking with pyshacl (`semantic/ontology.py:20–21, 247–254`) [Src]. SHACL generation is beta [Doc]. |
| `gen-doc`, `gen-erdiagram` | Documentation and Mermaid ER diagrams | Cheap, read-only wins for model documentation. |
| `gen-linkml --materialize-attributes` | A materialised derived schema | Useful as one canonical input for generators that should not re-implement induction. |

**Custom generators.** The `Generator` base contract (F11) is a CLI-compatible visitor that
emits one string. It offers nothing for multi-output ownership, freshness or registration.
Modern stock generators read `SchemaView` directly with `uses_schemaloader=False`. Recommend:
keep generators as plain functions over `SchemaView`, keep the project's typed output registry
with its ownership check (`schema/generate.py:556–578`) as the single generator registry, and
fold the stray facades into it (DA-081). **Do not subclass `Generator`** unless a stock CLI
entry point is wanted.

## D. Validation routes

- **`linkml.validator.Validator(schema, validation_plugins=[...])`** compiles the schema once,
  to JSON Schema or a generated Pydantic module, when the validator is built. After that each
  instance is cheap. On a toy schema the first validation took 0.08 s with the JSON Schema
  plugin and 0.03 s with Pydantic. That is not a performance claim [Obs].
  - **Build time** (declaration documents, profile checks): use one validator per schema,
    with the JSON Schema plugin closed. It is the only stock plugin that enforces `rules`.
  - **Runtime hot paths**: use the generated Pydantic types or a cached compiled jsonschema
    validator directly, not a `Validator` per call [Inf].
- **Closed world.** `closed=True` refuses undeclared fields [Obs]. Cross-record facts
  (uniqueness, totality, references existing) need either the compiler's own pass over
  compiled data or the database. No stock LinkML plugin does them (F9).
- **linkml-term-validator 0.4.5.** Already used: `DynamicEnumPlugin`,
  `PermissibleValueMeaningPlugin` and `BindingValidationPlugin` (`semantic/ontology.py:34–38,
  388, 517, 644`) [Src]. Its scope is ontology membership and labels. `matches` is
  unsupported [Doc].
- **Custom `ValidationPlugin`.** The supported extension point for A.3's profile check and
  for totality rules such as "every operation declares a family".

## E. Value sets

- **Static enums and composition.** Runtime and generators do not expand `inherits`,
  `include` or `minus` (F6, F7). The project's `expand_enum` is therefore necessary; it must
  be the one expander every consumer uses, including any generated JSON Schema. Otherwise
  JSON Schema rejects inherited members (F7).
- **Dynamic enums.** Validated at instance time by term-validator with OAK, using
  progressive or greedy caches and an offline mode [Doc]. valuesets 0.4.2's generator skips
  `reachable_from`. Its separate `DynamicEnumExpander` materialises expansions in batch
  [Doc].
- **valuesets in this project** is consumed as captured YAML, not imported:
  `terminology/valuesets/*-valuesets-0.4.2.yaml` (`semantic/terminology.py:139–140,
  182–187`) [Src]. Most of its sets are `DRAFT` [Doc].
- **Identity of a resolved population.** LinkML gives none. Give it the digest of the
  canonical expanded member list (text, meaning, properties) plus the ontology artifact
  digest and the expander version, matching the project's model-revision pattern [Inf]. Pin
  by package version plus vendored file; for dynamic sets, also record the ontology artifact.

## F. Graph and rule routes for derived facts (support closure, change impact)

- **linkml-datalog: do not adopt.**
  - 0.2.0 dates from 2022, is self-described alpha, and is not installed [Doc]/[Obs].
  - It needs an external Soufflé binary and round-trips data through RDF.
  - Its docs describe LinkML 1.2-era plans.
- **SHACL with pyshacl: do not adopt for operational closure.**
  - It would require projecting the compiled operation model into RDF and writing SHACL-SPARQL
    constraints.
  - It works under open-world graph semantics, which do not match closed compiled
    declarations.
  - The project's pyshacl use is rightly limited to ontology artifacts.
- **An RDF store (rdflib, Oxigraph): do not adopt for this.** Integration burden with no
  consumer that needs RDF.
- **Recommended route [Inf].** The support closure and "which operations a change affects"
  are small graph computations over the compiled model at build time.
  1. Compute them once in the compiler. networkx is pinned and used (`semantic/graph_runtime.py`
     and others) [Src]; plain dicts also suffice.
  2. Publish one compiled edge relation, with edge kinds from the declared vocabulary of A.2.
  3. Have native SQL validity, the projection walks and change impact all consume that one
     declaration and relation.
  4. If an analytical surface is wanted, DuckDB recursive CTEs over the compiled edge
     relation are a better fit than any RDF route.

  LinkML's `transitive_form_of` and `transitive` are executed only by OWL reasoners [Doc], so
  declaring them buys nothing operational.

## G. Every data-model library as a candidate authority

Pinned in `pyproject.toml` (snapshot) [Src]. "Files" counts source files that import the
library (a grep over `src/`).

| Library (files) | Role today | Could own | Holds a fact another library also holds | Supported bridge to or from it |
|---|---|---|---|---|
| LinkML / linkml-runtime (18 / 2) | **Source of truth** for domain classes, enums, the physical model (`ph:` annotations) and read projections. Also the older model (DA-072). | The authored model: domain shapes, closed vocabularies, physical annotations under a typed profile (A.3), and schemas of operational declaration documents. | Older and released enums (DA-072). Operation metamodel against hand dataclasses (A.4). | Generates JSON Schema, Pydantic, SQL DDL, SQLAlchemy, SHACL and OWL [Doc]. The project uses its own emitters over `SchemaView`. |
| JSON Schema / jsonschema (16) | **A second authored schema language.** `data-operation-native.yaml` is draft-7 with `x-ddo-lifecycle` and holds the wire contracts and operation list ("Python, SQL and effective kinds derive from these schemas"). It is also a validator for kind bodies and reports. | Wire encodings that LinkML cannot express. The tagged positional tuples (`items: [const, type]` with `additionalItems: false`) have no LinkML equivalent; `ArrayExpression` is numeric [Inf; not probed]. | Wire kinds against LinkML product classes (domain map row "Products and kinds"). | LinkML to JSON Schema (generator). Pydantic to JSON Schema (`TypeAdapter.json_schema`) [Doc]. JSON Schema to LinkML only through schema-automator, lossily. |
| pydantic (229) | Generated Stage B shapes from the **older** model, plus many hand-written models (not classified). It is the boundary type system. | The **runtime typed form** of anything LinkML authors: generated, never hand-authored for model-owned shapes. | Hand pydantic models that restate LinkML classes [Unconf: count not established]. | LinkML to Pydantic (project emitter or `gen-pydantic`). Pydantic to JSON Schema (supported). |
| pydantic-settings (1) | Configuration | Configuration only, outside the domain model | — | — |
| cattrs (6) | Strict structuring of the hand dataclass metamodel and archives (`data_operation_model.py:1225`) | An implementation detail of whichever typed form the metamodel uses | Restates the dataclass shapes' structuring policy | Disappears if the metamodel becomes generated Pydantic [Inf] |
| msgspec / attrs | Not used | — | — | — |
| SQLAlchemy Core `MetaData` (173); Alembic (12) | **Derived artifact**: `schema/relational.py:402` builds `MetaData` from LinkML physical declarations. `semantic.metadata.metadata` is the one instance, and generated typed columns come from it (`semantic/typed_generation.py`). Alembic applies and checks it. | The single relational authority *derived* from LinkML: tables, constraints, indexes, grants, guard membership if annotated (A.2). | The guard and grant lists in code (DA-074) are relational facts that `MetaData.info` could carry from annotations | LinkML to `MetaData` (project). `MetaData` to Arrow: no SQLAlchemy bridge; the project's `semantic/arrow_types.sql_arrow_type`. Database catalog to Arrow: ADBC `adbc_get_table_schema` [Obs `adbc_driver_manager/dbapi.py:655`]. Alembic autogenerate compares `MetaData` with the database. |
| pyarrow (24) | **Mixed.** Derived from `MetaData` (`semantic/pdf_record_model.py:103–108`). Derived from JSON Schema (`semantic/pdf_payloads.py:87–105`). **Hand literals** in `rich_relations.py:24–27`, `analytical_kernels.py:18–60`, `ingest/pdf_stream_reconciliation.py:36, 235`, `serve/demand_export.py:76` and `serve/native_source.py:944` (sampled; not checked whether these mirror model relations). | The transport schema, always derived | Hand Arrow literals against model relations or JSON Schema payloads | `MetaData` to Arrow (project). Arrow to DuckDB: native scan with type mapping [Doc]. Arrow to PostgreSQL COPY: pgpq (`semantic/arrow_transfer.py`) [Src]. |
| DuckDB (6) | Executes analytical relations | Not a schema authority; consumes Arrow | — | Arrow to DuckDB relation types (supported) |
| pglast (64), SQLGlot (2) | Typed SQL syntax: programs, not data declarations. SQLGlot is used for SQL diffs. | Representation of generated SQL programs | Hand SQL literals listing operations or tables (DA-070, DA-074) | `MetaData` to SQL through SQLAlchemy compile; pglast for parse and verify |
| valuesets (0 imports) | Vendored YAML source data (E) | Vocabulary source, consumed as captured files | — | LinkML enum import |
| linkml-term-validator (1), oaklib, pronto, rdflib, pyshacl | Ontology and vocabulary validation | Ontology-backed membership checks | — | Stock plugins (D) |

**The smallest set of authorities [Inf; Proposed].** Two of them are authored:

1. **LinkML** for every domain shape, closed vocabulary, physical annotation (with a typed
   profile) and operational-declaration schema.
2. **JSON Schema** only for wire encodings LinkML cannot express, until those encodings are
   redesigned; it is a peer, not a source of domain meaning.

Instance data (operation literals, policies, manifests, metrics) is authored against (1).

Everything else is derived through supported or existing project bridges:

```
LinkML → Pydantic (runtime types) → JSON Schema (validation and wire where expressible)
LinkML → SQLAlchemy MetaData → { DDL and grants (SQLAlchemy and pglast),
                                 Arrow schema (sql_arrow_type) → DuckDB }
compiled declarations → typed Python registries (generator outputs, program grants)
```

What leaves:

- the older LinkML model;
- the hand dataclass metamodel and cattrs, or else they become generated;
- hand Arrow literals for model relations;
- hand SQL membership lists.

Typed Python objects stay the right *single* authority for code-shaped facts (generator
registry, program declarations), with no LinkML. LinkML stays their source wherever the fact
is domain meaning that SQL or documentation also reads.

## Things to avoid

- JSON-encoded strings inside annotations; use structured values (F1).
- Relying on class-annotation inheritance (F2) or on `slot_usage` merging annotations (F3).
- Reading positive-only subset membership as a decision. Use required total
  classifications.
- Trusting a generated JSON Schema for inherited or composed enums (F7), or for
  `unique_keys` (F9).
- linkml-map's SQL backend, linkml-datalog, and an RDF store for operational graphs.
- Subclassing `Generator` for output governance.
- A second hand-written metamodel beside LinkML for anything SQL also reads.

## Open uncertainties

- Whether `in_subset` is inherited through `is_a`. Not probed.
- Whether the released model already has a typed check for `ph:` annotations like the older
  model's `VOCABULARY`. The physical reader was not read.
- Whether validity family is fully derivable from existing operation fields. DA-070 suggests
  so; not verified.
- How many hand Pydantic models and hand Arrow schemas restate model relations. Sampled
  only.
- The claim that LinkML cannot express the wire contract's positional tuples comes from
  metamodel knowledge, not a probe.
