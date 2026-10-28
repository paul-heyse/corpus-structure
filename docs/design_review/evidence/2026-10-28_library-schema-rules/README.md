# Library research: schema and rules (LinkML, Pydantic, JSON Schema, rule-engine)

**Date:** 2026-10-28. **Role:** library-research worker (`.agents/roles/library-research.md`).
**Status:** evidence, not authority. The design authority decides adoption; nothing here changes D2,
D5, D6 or D9 by itself.

## Question

The phase 0 build plan and the design's "Library realization" text need the best use of the
schema-and-rules libraries from the outset: LinkML as the single schema source compiled to every
consumer, Pydantic for the core types, JSON Schema validation, and rule-engine for validation rules
and routing policies. Six decisions were posed:

1. One source for value shapes (LinkML `gen-pydantic`, hand-written Pydantic checked against
   `gen-json-schema`, or Pydantic as source with LinkML checked).
2. `SchemaView` use by the compilers (induced slots, `ci:` annotations and OPEN-D2-6, imports,
   hashing, `linkml-lint`, native replacements for `ci:` annotations).
3. JSON Schema for LLM batches (D2 §7.3), both forms, per-predicate branches, `cN` citations,
   backend constraints.
4. JSONB validation on write (D9 §3, D3 §6).
5. rule-engine 5.1 for M19 and the D6 policies, including the two M19 call sites.
6. The S0-R2 guideline checks (`code/s0r2_rules.py`) as rule-engine `guideline:` warnings.

**Baseline examined.** Repository HEAD `71bb064` plus the uncommitted working-tree edits to
`docs/design/` present on 2026-10-28 (D2 now says prompts carry the annotator reference and the
GLiNER2 compiler arrives in phase 1). Design inputs read: D2 §2, §3, §6, §7, §9, §11, §12.1; D1
§5–§7; D3 §6, §11; D5 §8; D6 §7; D9 §1–§3; rationale §3 (P1) and §4.3; the S4 brief; spike code
`schema/core.yaml`, `schema/statistics.yaml` (both byte-equal to D2 §6 and §9),
`instruments/batch.py`, `instruments/schema_lookup.py`, `s0r2_inputs.py`, `s0r2_rules.py`; the v1
model-facing reference batches `results/s0r2/reference_model_v1/{T1..T4,U5..U12}.json` and worked
examples `results/s0r2/examples/E1–E3.json` (15 batches, 86 claims).

## Sources and versions

| Source | What it supplied | Strength |
|---|---|---|
| Overviews, read end to end: `docs/libraries/linkml.md`, `pydantic.md`, `rule-engine.md`; `gliner2.md` §6 | Orientation, version notes (LinkML 1.12 closed classes, Pydantic 2.14 `MISSING`, rule-engine 5.1 `Chain`) | Secondary |
| Context7 `/websites/linkml_io_linkml` | `jsonschemagen.handle_class_slot` (type designator → `enum: [value]`), `get_type_designator_value` (string range → class name), SchemaView `get_type_designator_slot` | Documentation and quoted source |
| Context7 `/zerosteiner/rule-engine` | `OBJECT.reference`/`OBJECT.self`, type resolvers raising `SymbolResolutionError`, `Chain.find`/`evaluate` source | Documentation and quoted source |
| Context7 `/python-jsonschema/jsonschema/v4.26.0` | `Draft202012Validator`, `check_schema`, `referencing.Registry` (`with_resources`, `retrieve=`, no automatic remote retrieval), `best_match` and `relevance` (anyOf/oneOf are weak; v4.8.0 no descent when equally applicable), `ValidationError` attributes, format checking off by default | Documentation, versioned |
| Context7 `/websites/vllm_ai_en_stable` | `has_xgrammar_unsupported_json_features`, `auto` backend fallback xgrammar → guidance → outlines, `check_json_nesting`, `MAX_STRUCTURED_OUTPUT_JSON_NESTING = 64` | Documentation of the **stable** docs, not pinned to vLLM 0.31: re-check in S3 |
| Installed sources, `build/spike-venv` (Python 3.14.10): linkml 1.12.1, linkml-runtime 1.12.1, pydantic 2.14.1 (pydantic-core 2.50.1), jsonschema 4.26.0, referencing 0.37.0, jsonschema-specifications 2025.9.1 | Generators run (`gen-json-schema`, `gen-pydantic`, `linkml-lint`), `linkml/linter/config/default.yaml`, metamodel `meta.py` | Primary, executed |
| rule-engine 5.1.0 wheel installed with `uv pip install --target <scratch>` (not into the spike venv); sources `rule_engine/engine/context.py`, `builtins.py`, `ast/expression/access.py`, `engine/chain.py` | Context signature (no builtins parameter; builtins built in `__init__` from `Builtins.from_defaults`), default builtins (`now`, `today`, `random`), OBJECT accessor error handling | Primary, executed |
| xgrammar `cpp/json_schema_converter.cc` at `main` 7e269d5 (2026-10-14; latest release v0.2.8, 2026-09-24), fetched with `gh api` | `not`, `if`, `then`, `else`, `dependentRequired`, `dependentSchemas` warned and ignored; `oneOf` must be provably pairwise disjoint, else downgraded to `anyOf` with a warning; `$ref`, `const`, `enum`, `anyOf`, `allOf` supported | Primary, but main branch, not the xgrammar bundled with vLLM 0.31: re-check in S3 |
| jsonschema (no overview) | Context7 then installed 4.26.0 | Re-check against an overview if one is written |

Machine for every timing: AMD Ryzen 9 9950X3D, Linux 7.0.0-38, Python 3.14.10, single process,
small samples. Timings are indicative ratios, not capacity figures.

## Findings by decision

Claim labels follow the design principles: **Tested** (a named probe below exercised it),
**Measured** (a probe timing), **Documented** (a cited source states it), **Proposed** (a
recommendation). All verified on 2026-10-28.

### 1. One source for value shapes

**Recommendation (Proposed).** Split ownership by what varies, and make each part single-sourced:

- **D1 representation shapes** (value variants tagged `t`, condition nodes tagged `op`, symbol
  bindings, evidence, batch items in both forms) are **hand-written Pydantic in `core/`**. These are
  domain-independent (D1 §6–§7), so P1 ("the domain model is data") is not breached; rationale §4.3
  rejects Pydantic as *the domain schema*, not as the type system of the representation.
- **Domain vocabulary** (entity classes, predicates, qualifiers, enums, condition predicates) stays
  in LinkML and is compiled at load time into Pydantic per-predicate models (decision 3). The core
  Pydantic types keep schema-owned names as plain strings, as the spike's `batch.py` did, so an
  unknown name is a schema-check error, not a malformed-JSON error.
- **`core.yaml` keeps the value classes as a checked mirror.** Predicate ranges name them, and the
  schema tables and annotator reference list them. Restructure them: an abstract `Value` base; `t`
  declared on it, with `slot_usage: {t: {equals_string: formula}}` per class (gen-json-schema emits
  `const: "formula"`, Tested P3); `IntervalValue.start/end` ranged on `Value` instead of `string`;
  `conditions`/`param_constraints` ranged on a placeholder `Condition` class instead of `string`.
  A contract test compares each `Value` descendant's `SchemaView.class_induced_slots` (names,
  required, multivalued) and its `equals_string` tag with the Pydantic variant's `model_fields` and
  `Literal` tag. The two declarations are authored independently, so the test is non-circular.
- Do not use `gen-pydantic` output as runtime types, and do not take value `$defs` from
  `gen-json-schema` (decision 3).

**Why not `gen-pydantic` (Tested P2, P3, linkml 1.12.1):**

- On `core.yaml` it emits `symbols: Optional[dict[str, SymbolBinding]]` while `SymbolBinding.symbol`
  stays required. It therefore rejects `{"latex": "a + b Z", "symbols": {"a": {"bind": "free"}}}`
  (`missing` at `symbols.a.symbol`), which is the shape every v1 batch uses. `gen-json-schema` emits
  a `SymbolBinding__identifier_optional` variant for the same slot and also accepts
  `{"a": "free"}`. The two LinkML generators disagree on one schema.
- There is no `t` in the declared classes. With `designates_type` on a string slot the tag value is
  the class name (`"Formula"`, `"SetExpr"`), generated as `Literal["Formula"] = "Formula"`, so a
  missing tag is silently defaulted. A slot ranged on the abstract base becomes a plain
  `Union[Formula, TextValue, SetExpr]` (smart mode), not `Field(discriminator=…)`. With
  `equals_string`, the tag is correct (`Literal["formula"]`, required), but a slot ranged on that
  base stays typed as the base and its descendants are not unioned. Neither LinkML tagging route
  yields D1's tagged union in Pydantic.
- Generated config: `validate_assignment`, `validate_default`, `arbitrary_types_allowed`,
  `use_enum_values`, `strict=False`, not frozen. Docstrings containing `\R` raise `SyntaxWarning`
  on import under 3.14.
- Recursion works (`args: Optional[list[Union[And, ClaimNode]]]`).

**How to write the Pydantic side (Tested P5 unless marked):**

- Use `ConfigDict(extra="forbid", frozen=True)` and `tuple[...]` for sequences. A frozen model with
  a `list` field is unhashable (`TypeError`), and `frozen` does not deep-freeze lists. A `tuple`
  validates from and serializes to a JSON array (`{"type": "array", "items": …}`).
- Name recursive unions with `TypeAliasType("Condition", Annotated[Union[...],
  Field(discriminator="op")])`. This gives one `$defs/Condition` referenced from `and`, `or`, `not`
  and `forall`. The spike's anonymous `Annotated` union is re-inlined at every `args` site: its
  condition schema is 8.8 KB, against 0.9 KB for a 3-node aliased probe.
- Discriminated-union errors are precise: `union_tag_invalid` at `('and', 'args', 0)`; `missing`
  at `('and', 'args', 0, 'claim', 'ref')`, with the tag in the location path.
- Defaults: `Field(default="asserted", exclude_if=lambda v: v == "asserted")` fills the default for
  rule views (D5 §8.2, "qualifiers with defaults filled in") and omits it from `model_dump`, so equal
  meaning gives equal JSON (D3 §6.1). Use `MISSING` (stable in 2.14, Documented) where absent and
  null differ.
- Strictness: validate LLM and agent batches with `strict=True` on the JSON path, so that `"1"`
  never coerces to `1`. Strict JSON validation still accepts what JSON itself encodes (Documented,
  pydantic overview §3.3).
- Method configurations (`methods.yaml` `configs:`, D2 §12.1) fit the same pattern: one model per
  method with `extra="forbid"` and `frozen`. The config hash is taken over the canonical JSON of
  `model_dump(mode="json")`, so a changed code default changes the hash (Proposed).

**Version caveats.** Pydantic's version policy allows JSON Schema reference formatting to change in
minor releases (Documented). A Pydantic bump then changes compiled-artifact hashes, which is the
correct invalidation. LinkML 1.12 changed closed-class JSON Schema and enum generation
(Documented); none of this route depends on those changes.

### 2. SchemaView for the compilers

**Loading and imports (Tested P1).** `SchemaView("domains/statistics/schema/statistics.yaml")`
resolves `../../core/schema/core` relative to the importing file in the D2 §2 layout. The import
closure is `['linkml:types', '../../core/schema/core', 'statistics']`. The spike's `importmap` was
needed only for its flat copy.

**Annotations and OPEN-D2-6 (Tested P1, P4).** Read them with `element.annotations[tag].value`.
Strings come back as `extended_str`, booleans as `bool`, and lists as Python lists, unchanged. Lists
therefore round-trip through `SchemaView`, **but they are not valid LinkML**:

- `linkml-lint` 1.12.1 always runs metamodel validation (`--validate` is deprecated: "Metamodel
  validation now always runs"). It reports every list-valued annotation as a `valid-schema` error:
  10 on `statistics.yaml` and 1 on `core.yaml` (`ci:target: [unit, paragraph]`). The metamodel
  allows null, boolean, object, number or string values, not arrays.
- Object values are not an escape. A mapping value is parsed as an `Annotation` record, and loading
  fails (`Annotation.__init__() got an unexpected keyword argument 'unit'`).

**Native features that replace `ci:` annotations.** A lint-clean probe schema exercised these
(Tested P4):

| `ci:` annotation | Native LinkML | Notes |
|---|---|---|
| `ci:examples` (list) | `examples: [{value: …}]` | gen-json-schema copies them into JSON Schema `examples` |
| `ci:identity_keys` (list) | `unique_keys: {identity: {unique_key_slots: [family, canonical_name]}}` | Read as `sv.get_class(c).unique_keys` |
| Guideline predicate groups (STRUCTURAL, FORM, FAMILY, now hard-coded in `s0r2_inputs.py` and `s0r2_rules.py`) | `subsets:` plus `in_subset:` on slots | Multi-membership (FAMILY ⊂ FORM); the `no_undeclared_subsets` lint rule catches typos |
| `ci:symmetric` | `symmetric: true` | `inverse` is already native (D2 §7.2 b) |
| (none yet) | `transitive: true` on `special_case_of` | Can drive the transitivity derive rule (D2 §7.4) |
| `ci:gliner_label` | `title` | Display name of the class |
| `ci:kind` | Derivable: `abstract`/`mixin`, and ancestry (`Entity` versus a `Value` base) | Drop it, or keep it only as a checked redundancy |
| `ci:object` | Derivable from `range` once conditions have a class range and maps are recognized structurally (multivalued, inlined, range with `key`/`value`) | Same choice as `ci:kind` |

The remaining list-valued annotations (`ci:qualifiers`, `ci:identity_qualifiers`, `ci:target`)
become scalar space-separated strings, parsed by the loader and checked against declared slots
(Proposed). The alternative is Biolink-style association classes (`represents_relationship: true`,
qualifiers as class slots), which would give native induced slots per predicate. It is a larger
re-model and not recommended for v0. These annotations have no native equivalent and stay:
`ci:scope`, `ci:extract`, `ci:reify`, `ci:threshold`, `ci:functional`, `ci:group`,
`ci:claim_bearing`, `ci:arity`, `ci:args`, `ci:z3`, `ci:applies_to`. `ci:functional` has no
equivalent because `multivalued` is per instance record, not per statement.

**Induced slots (Tested P1).** `class_induced_slots(cls)` covers slots attached to the class
(`slots:`, attributes, mixins), but **not predicates**, which are free slots with a `domain`. For
`RandomVariable` it returns `[symbol, label]`. Predicate applicability is
`{p | sv.get_slot(p).domain in sv.class_ancestors(cls)}` (mixins included). `RandomVariable` then
gets `cdf, defined_as, has_distribution, has_parameter, mean_value, mgf, pdf, support,
takes_values_in, unschematized, variance_value`. `sv.induced_slot(p, cls)` returns the resolved
domain and range with annotations merged. D2 §7.1's phrase "induced slots … through
`class_induced_slots`" needs this addition.

**Prefixed names (Tested P1).** `sv.get_uri(slot, expand=False)` returns `stat:has_distribution`,
`core:defines`, `core:modality` and `core:Statement` natively. It replaces the spike's
`_slot_prefix` heuristic in `schema_lookup.py`.

**Hashing (Tested P9).** Compute the schema version as the SHA-256 of canonical JSON (sorted keys,
compact separators) of `yaml.safe_load` of the pack schema, `rules.yaml` and `core.yaml`. It was
identical across `PYTHONHASHSEED` 1, 2, 999 and 7 and across relative and absolute load paths. It
does not depend on the library version and ignores comments and formatting. A SchemaView
merged-import dump is unsuitable: it carries `source_file` (the path as given) and depends on
linkml-runtime (metamodel defaults and the `linkml:types` content). Compiled artifacts keep their
own byte hashes (D2 §1.2), which capture generator and library changes.

**`linkml-lint` (Tested P1, P4).**

- Lint each schema file, not the `schema/` directory. Directory mode lints `rules.yaml` as a LinkML
  schema and reports `valid-schema` errors.
- The default configuration disables the convention rules. Add a `.linkmllint.yaml` with
  `extends: recommended`, and raise `recommended` (missing descriptions) to `error` for classes and
  predicates, because descriptions are model input (D2 §1.3). Run on `statistics.yaml` with
  imported core attributes, it gives 34 warnings, including six predicates without a description:
  `support`, `cdf`, `mgf`, `mean_value`, `variance_value` and `definition_formula`. Enable
  `no_undeclared_ranges`, `no_undeclared_subsets` and `no_invalid_slot_usage`.
- `canonical_prefixes` warns that `ci`, `core` and `stat` are registered prefixes for other
  namespaces (content-inventory, VIVO core, POSIX stat). This is harmless while IRIs are explicit,
  but D8 §6 JSON-LD exports and bioregistry-based tools may misread the CURIEs. Rename the prefixes
  (for example `csci:`) or disable the rule deliberately.

**Caching.** `SchemaView` memoizes lookups. Treat one instance as immutable per schema version and
build a new one per version.

### 3. JSON Schema for LLM batches

**Recommendation (Proposed).** Build both batch forms from Pydantic:

- The per-predicate claim models are created with `pydantic.create_model` from SchemaView and
  discriminated on `predicate` (`Literal[p]`), with per-predicate qualifier models, object types
  from `ci:object` or range, and enum `Literal`s injected from the schema.
- Entity, statement, alternative and unsupported item models exist for each form (model-facing:
  `sentence`/`quote`, anchors as `"unit"` or ids; stored: `start`/`end`/`coarse`, segment keys,
  `scope_segment`).
- One `TypeAdapter` per form (a) validates, with precise errors, and (b) exports the JSON Schema
  through `json_schema(mode="validation", schema_generator=<custom>)`.

Evidence:

- **Tested P7.** 25 predicate branches were built in 37 ms, including the SchemaView load. All 15 v1
  batches validated. Seeded errors were reported at `2.defined_as.qualifiers.modality`
  (`literal_error`), `…conditions.and.args.0.member.set.SetValue.t` and
  `8 union_tag_invalid` ("Input tag 'has_distrib' … does not match any of the expected tags").
- **Mode (Tested P5).** Use `mode="validation"` for both forms, because both are inputs: LLM output,
  Opus submissions, and stored payloads read back. Serialization mode differs only for computed
  fields, custom serializers and `json_schema_serialization_defaults_required`. Fields with
  `exclude_if` are not required in either mode.
- **Custom generator (Tested P5, P7).** Subclass `GenerateJsonSchema`, override
  `field_title_should_be_set → False` to drop field titles, and add
  `"$schema": "https://json-schema.org/draft/2020-12/schema"`. The output was byte-identical across
  processes (`PYTHONHASHSEED` 3 and 11). `Draft202012Validator.check_schema` passes.

**Why not `gen-json-schema` for the value classes (Tested P2, P3).** This answers D2 §7.3's last
paragraph:

- It emits `"$schema": "https://json-schema.org/draft/2019-09/schema"`, and `validator_for` picks
  `Draft201909Validator`, not 2020-12 as D2 §7.3 states.
- There is no `t`, so `{"t": "formula", …}` fails on `additionalProperties: false`.
- Compact SimpleDict forms (`"a": "free"`) are accepted.
- Optional slots accept `null` unless `--no-include-null` is passed.
- Free-standing predicate and qualifier slots are absent from the output, which only emits classes.
- `--include-range-class-descendants` gives `anyOf` without a discriminator.

**Constraints of structured-output backends.** These notes are for S3:

- Keep `oneOf` or `anyOf` over branches made disjoint by `predicate: const`. xgrammar keeps a
  `oneOf` it can prove pairwise disjoint and otherwise downgrades it to `anyOf` with a warning
  (Documented, xgrammar main).
- Never use `if`/`then`/`else` or `not`. xgrammar warns and ignores them (Documented), so a
  dispatch written that way would decode unconstrained.
- Strip the OpenAPI `discriminator` keyword that Pydantic emits. It is not JSON Schema; jsonschema
  ignores it, and xgrammar does not list it. Its xgrammar behaviour is unverified.
- Avoid `multipleOf`, `uniqueItems`, `contains`/`minContains`/`maxContains`, unsupported string
  `format`s, `pattern` or `format` combined with length bounds, and `propertyNames` combinations.
  vLLM's `auto` mode moves such schemas from xgrammar to guidance (Documented, vLLM stable docs).
- Sentence-id patterns `^[sc][0-9]+$` without length bounds are acceptable.
- vLLM rejects a schema nested more than 64 levels (`check_json_nesting`, Documented). The probe
  schemas nest 9–11 levels.
- Sizes: the Pydantic-built claims schema is 72.6 KB compact; a hand-assembled `oneOf` batch schema
  is 48.8 KB (Measured). Core qualifiers are flattened into every branch. S3 should measure grammar
  compile time and memory for 25 branches plus the recursive `Condition`, and keep the schema text
  byte-stable so compiled grammars can be reused. vLLM's grammar caching behaviour is unverified.
- Descriptions: constrained decoders do not show schema text to the model. D2 §7.3's "descriptions
  are carried into the schema so the model sees them" holds only if the schema is placed in the
  prompt (interpretation; S3 to confirm). The working-tree D2 says prompts carry the annotator
  reference, so descriptions in the decoding schema are optional bulk.

**The hand-assembled alternative (Tested P6, Measured).** A JSON Schema dict was assembled around
Pydantic value `$defs` with one `oneOf` branch per predicate. It validates the same 15 batches once
two shape questions below were relaxed.

| Validator | ms per batch |
|---|---|
| jsonschema, `oneOf` dispatch | 14.4 |
| jsonschema, `allOf` of `if`/`then` dispatch | 2.4 |
| Pydantic per-predicate models (P7, claims) | 0.021 |

Error quality differs as much as speed:

- Under `oneOf`, `best_match` stops at the whole claim, with 106 context errors. jsonschema ranks
  `oneOf` and `anyOf` as weak and does not descend when the branches are equally applicable
  (Documented, jsonschema 4.8.0 changelog).
- Under `if`/`then`, errors carry precise paths (`$.claims[2].qualifiers.modality`), but xgrammar
  ignores `if`/`then`.

So a decoding schema and a diagnostic validator cannot both be jsonschema `oneOf`. Pydantic gives
precise diagnostics while the exported schema stays decodable.

**Shape questions the compiled schema will force (Tested P6; inputs for S4).**

- The spike accepted three entity-argument forms (`{"ref": r}`, `{"t": "entity", "ref": r}`, a
  bare string) and bare LaTeX strings in formula positions. T1 `c_constr` uses
  `{"t": "entity", "ref": "Z"}` for `base_variable`, while reference §5 gives `{"ref": …}`.
  Choose one canonical shape per position.
- U6 lists an entity of type `Statement` in `entities[]`, contrary to the reference ("A `Statement`
  is listed in `statements[]`").
- The `entity_types` side-table check (subject and object classes per branch) stays in Python,
  because JSON Schema cannot follow local references (D2 §7.3).

### 4. JSONB validation on write

**Recommendation (Proposed).** Validate once, at the Pydantic boundary.

- Repository-layer writers accept core Pydantic models, or run `TypeAdapter.validate_python` on raw
  payloads such as observation payloads (D3 §6.2), and write `model_dump(mode="json")` with
  `exclude_if` defaults to JSONB.
- `kb.claim.qualifiers` validity depends on the predicate and the run's schema version (D3 §6.1).
  It is checked by the compiled per-predicate models of decision 3, not by a static file.
- Generate `core/schemas/*.json` (D9 §1) from the same adapters, for documentation and external
  consumers.
- In tests, run `Draft202012Validator.check_schema` on every generated artifact, and validate
  fixture payloads with jsonschema as an **independent implementation**. This is the
  non-circular contract check AGENTS.md asks validators' tests to keep.

**jsonschema mechanics (Documented, Tested P10).**

- Build one validator per schema and reuse it:
  `Draft202012Validator(schema, registry=Registry().with_resources([(uri, DRAFT202012.create_resource(s)), …]))`.
  Construction took about 20 µs, because references resolve lazily on first validation.
- `DRAFT202012.create_resource` fixes the dialect for schemas without `$schema`. A URN-keyed
  in-memory registry resolved `{"$ref": "urn:ci:value"}` (Tested). `referencing` never retrieves
  remote references, unlike the old `RefResolver`. Use URNs, or `Registry(retrieve=…)` reading
  `core/schemas/`.
- Error reporting:
  - `iter_errors` for all errors and `best_match` for one;
  - `error.json_path`, `error.context` for branch errors, and `ErrorTree`;
  - `format` is not asserted unless `format_checker=Draft202012Validator.FORMAT_CHECKER` is passed.

**Cost (Measured P10).**

| Payload | jsonschema | Pydantic |
|---|---|---|
| Formula value | 118 µs | 1.5 µs |
| Small condition tree | 338 µs | 2.0 µs |

At D3 §11 volume (about 10⁵ observations and 10⁴–10⁵ claims per run), jsonschema on every write
costs seconds to minutes per run; Pydantic costs well under a second. The larger cost is semantic:
two production validators for one meaning drift, and a JSON Schema pass after Pydantic adds no
assurance except as a test oracle. `jsonschema-rs`, `fastjsonschema` (drafts up to 7 only) and
PostgreSQL-side `pg_jsonschema` were not evaluated.

### 5. rule-engine 5.1 for M19 and policies

**Typed context (Tested P8).**

- Construct `Context(type_resolver=type_resolver_from_dict(TYPES), resolver=…,
  mapping_attribute_lookup=False, default_timezone="utc")`.
- Type every structured symbol as `DataType.OBJECT` with `accessor=getattr` over view objects, not
  as `MAPPING`. Mapping dot-access is deprecated and removed in 6.0 (Documented), and only `OBJECT`
  gives compile-time attribute errors.
- Generate the type resolver per schema version (D5 §8.2): for example a `Qualifiers` OBJECT with
  every qualifier slot as `NULLABLE`, so a misspelled qualifier fails compilation.
- These failed at construction, as D2 §7.4 requires:
  - a misspelled attribute: `ObjectAttributeError`, with a suggestion;
  - attribute access on a nullable value: "attribute access target is nullable; discharge with
    '??' or use '&.'";
  - a wrong function argument type: `FunctionCallError`;
  - an unknown root symbol: `SymbolResolutionError`.
- Equality and `in` accept nullable operands.

**D2 and D6 syntax corrections (Tested P8).**

- D2 §7.4's example fails three ways. `all(...)` is not a symbol (the builtin is `$all`);
  `claim.object.key` dereferences a nullable value; `.param_values.keys` is nullable. Valid forms:
  - `$all([k in claim.family_params for k in (claim.qualifiers.param_values ?? {}).keys])`
  - `$all([k in family_params(claim.object&.id ?? '') for k in (claim.qualifiers.param_values ?? {}).keys])`
- D6 §7.3's `eval.recall_trend(predicate, runs=2)` is a `RuleSyntaxError`: calls take positional
  arguments only. An OBJECT attribute typed `FUNCTION` is callable, and
  `eval.recall(predicate) < 0.6 and eval.recall_trend(predicate, 2) <= 0.02` compiled and evaluated.

**OPEN-D2-3: functions or resolver-backed attributes (Tested P8).** Both type-check.

- **Prefer resolver-backed attributes for per-claim pool lookups** such as `claim.family_params`.
  The attribute is computed once per view (`functools.cached_property`), and the Context stays
  independent of the call site. A `FUNCTION` is called once per comprehension element (twice for
  two keys) and must be bound to a pool, through a closure resolver or by passing it in the thing.
- Use FUNCTIONs for parameterized lookups such as `claims_of(key, predicate)`, `is_a(type, class)`
  and `value_type(v)`. They can be exposed as `$` builtins with
  `context.builtins = Builtins.from_defaults(values=…, value_types=…)`; Context has no `builtins`
  parameter (Tested with a typed table).
- Views must be plain objects. Through an `obj[name]` accessor, a `dict` subclass's `__missing__`
  was not consulted. That suggests the value is converted on resolution (interpretation). A plain
  object with a `getattr` accessor and `cached_property` works.

**Nested condition trees and lists (Tested P8, P11).** The language has no recursion, and
comprehensions bind one loop variable. The view therefore flattens the tree into
`condition_nodes: ARRAY(OBJECT Node{op, ref, x_latex})`, `claim_refs`, `bindings` and so on, and
rules iterate those (decision 6).

**Two call sites with one compiled rule (Tested in principle, P8 and P11; Proposed contract).**
One rule serves both sites if the Context is site-agnostic and two view builders implement the same
OBJECT attributes:

- `id`: the local ref at submission, the claim key at finalize;
- `key`: `NULLABLE(STRING)`, null before keys exist;
- `subject`/`object`: `id`, `type`, `label`; `statement`: `id`, `kind`;
- `family_params`: at submission, from the batch's own `has_parameter` claims plus the canonical
  labels the packet lists (D4 §4.1); at finalize, from the run pool, any status except `rejected`.

The *meaning* differs between sites: at submission `family_params` is incomplete, so
`stat.param_keys_known` would warn falsely. Each `rules.yaml` entry therefore declares
`at: [batch]`, `[finalize]` or both. D5 §8.2's `claim.key` and `subject.key` become `id`, with `key`
nullable. The probes used a single view class; a second class with the same attributes works
because the accessor is `getattr` (interpretation).

**`Chain` for D6 policy chains (Tested P8).**

- Construct `Chain([(when, {"key", "method", "limit", "then"}), …], context=uc, default_value=None)`.
  `find` returns `ChainEntry(rule, value)`, which has no id field, so the rule key lives in the
  value.
- `then: continue` is `chain[i+1:]`, a new Chain sharing the context, followed by `find` again. A
  phase 1 unit fired `propose.local_llm.claim_bearing` (continue), then `escalate.unresolved`
  (stop).
- Type errors raise at Chain construction, so policy loading fails as D6 §7.1 requires.
- Without a default, an unmatched chain raises `ChainExhaustedError`. Evaluation is sequential
  first match; mutation is copy-on-write (Documented).

**Determinism and security (Tested P8, Documented).**

- The default builtins include `$now` and `$today` (timezone-dependent; the Context default
  timezone is `local`) and `$random`. They break P8 determinism. Compile each rule in its own
  Context and reject it if `context.symbols & {"now", "today", "random"}` is non-empty: symbol sets
  record builtin names, and `$now` produced `['now', 'x']`. A shared Context accumulates symbols
  across rules.
- The grammar has no `eval`, but there are no resource limits on regular expressions or
  comprehensions. `rules.yaml` and `policies.yaml` are repo-authored by the operator or the agent,
  and the exposed FUNCTIONs are our own pure functions.
- Do not pickle rules. A lambda accessor is unpicklable, and the Context does not pickle its
  builtins table: it restores the defaults (source). Compiling from YAML at load is cheap.

**Cost (Measured P8, P11).** Evaluation is a Python AST interpreter. Eleven guideline rules ran at
0.23 ms per claim, including view building and the Python reference checker. One rule over nested
mappings took 118 µs per evaluation. At finalize volume (10⁴–10⁵ claims), index rules by
`applies_to` before evaluating `when`.

### 6. Guideline checks as rule-engine `guideline:` warnings

**Result (Tested P11).** Every check in `code/s0r2_rules.py` compiled as a rule-engine warning rule,
11 of 11 (`when`/`check` pairs). On the 12 v1 reference batches and 3 worked examples they gave
**0 warnings**, as `s0r2_rules.rule_warnings` does. One seeded violation per rule was caught, and
`s0r2_rules` also warned on each seed. The `role_by_kind` seed also fired `modality_by_role`, which
is expected coupling.

| Rule (guideline §) | Expressed as | Needs from the view |
|---|---|---|
| structural claims: no role, `asserted` (§10.3, §10.6) | `'structural' in claim.groups` → `claim.statement_role == null and claim.modality == 'asserted'` | `groups` from LinkML subsets |
| role by statement kind (§10.3) | `claim.statement_role in ($roles_by_kind&[claim.statement_kind ?? ''] ?? [])` | `statement_kind`; the table as a typed builtin (the probe inlined a mapping literal) |
| modality by role (§10.6) | `claim.modality == ($modality_by_role&[claim.statement_role ?? ''] ?? '')` | the table |
| structural: no conditions (§10.7 rule 4) | `claim.condition_nodes.is_empty` | flattened condition nodes |
| premises and example values: only an index range (rule 1) | `$all([n.op == 'and' or (n.op == 'member' and (n.x_latex ?? '') in claim.subject_index_symbols) for n in claim.condition_nodes])` | flattened nodes; the subject's index symbols (regex on its symbol) |
| formula and family-structure claims: no `claim` nodes (rule 2) | `claim.claim_refs.is_empty` | `claim_refs` |
| other claims reference a premise (rule 3) | `claim.statement_premises.is_empty or $any([p in claim.claim_refs for p in claim.statement_premises])` | premises of the same statement or of an `assumption` statement (cross-claim join) |
| `parameter_role` only when it differs (§10.4) | `claim.object_enum_value != claim.subject_canonical_name` | the subject's identity |
| a formula excludes the variable it defines (§10.7) | `not (claim.object_latex ?? '') =~ r'^\s*[A-Za-z]\w*(_\{?\w+\}?)?\s*='` | none |
| symbol keys without backslash (§10.7) | `$all([not b.symbol.starts_with('\\') for b in claim.bindings])` | flattened bindings |
| binding priority (§10.7) | `$all([not ((claim.given_by_others&[b.symbol] ?? []).length > 0 and b.bind in ['free','family_param'] and not (b.symbol in claim.gives_symbols) and not ('family' in claim.groups and b.bind == 'family_param')) for b in claim.bindings])` | a batch-level "given as a parameter value by another premise" map (cross-claim join) |

**What rule-engine cannot do alone.** It cannot walk the recursive condition tree, join across
claims (statement premises, the binding "given" map) or extract symbols from LaTeX. These belong in
a single generic, schema-driven view builder in `validate/`, not in per-rule Python. The guideline
decision tables (roles by kind, modality by role) should be data, such as a `tables:` section in
`rules.yaml` compiled into typed `$` builtins, rather than mapping literals repeated in rule text
(Proposed). Two checks remain the author's, as D2 §7.4 says: which premises a claim depends on, and
restrictions repeated in each dependent claim.

## Library proposals (D2 §7 contracts and neighbours)

| Id | Where | Proposal |
|---|---|---|
| L-01 | D2 §6, §7.3; D9 §1 | D1 value, condition and batch-item shapes are owned by hand-written Pydantic in `core/`: discriminated on `t`/`op`, `TypeAliasType`-named recursive `Condition`, frozen, `extra="forbid"`, tuples. `core.yaml` value classes become a contract-tested mirror with an abstract `Value` base and `t` via `equals_string`; `IntervalValue.start/end` ranged on `Value`; `conditions` and `param_constraints` ranged on a `Condition` placeholder, not `string` |
| L-02 | D2 §7.3, last paragraph | Replace "LinkML's own gen-json-schema is used for the value classes" with: per-predicate claim models built with `create_model` from SchemaView, discriminated on `predicate`; one `TypeAdapter` per form validates and exports a draft 2020-12 JSON Schema (custom `GenerateJsonSchema`: no titles, `$schema` set, deterministic) |
| L-03 | D2 §7.3 | Decoding-form rules: const-disjoint `oneOf`/`anyOf`; never `if`/`then`/`not`; strip `discriminator`; none of the xgrammar-unsupported keywords; nesting ≤ 64; one canonical shape per position (entity reference, formula); descriptions optional in the decoding schema, because the reference in the prompt is what the model reads |
| L-04 | D2 §7.4, D6 §7.1, §7.3 | Fix the rule syntax (`$all`, `&.`, `??`, positional arguments). Each rule declares `at: [batch, finalize]`. Add a `tables:` section compiled to typed builtins. Contexts use `mapping_attribute_lookup=False`, `default_timezone="utc"` and OBJECT types generated from the schema version. Reject `$now`, `$today` and `$random` at compile time, compiling each rule in its own Context |
| L-05 | D5 §8.2, OPEN-D2-3 | Close OPEN-D2-3: resolver-backed, cached view attributes for per-claim pool facts (`family_params`); FUNCTIONs only for parameterized lookups. Symbols: `claim.id` (local ref or key) plus `claim.key` as `NULLABLE`. Views are plain objects; recursive and cross-claim facts are precomputed by one generic view builder |
| L-06 | D2 §3, OPEN-D2-6 | Close OPEN-D2-6. List annotations load in SchemaView but fail metamodel validation (`linkml-lint` `valid-schema` errors), and object values do not load. Use native `examples`, `unique_keys`, `subsets`/`in_subset`, `symmetric`, `transitive` and `title`; derive `ci:kind` and `ci:object`; make `ci:qualifiers`, `ci:identity_qualifiers` and `ci:target` scalar space-separated strings |
| L-07 | D2 §2 | Schema version = SHA-256 of canonical JSON of the parsed pack schema, `rules.yaml` and `core.yaml`, not raw bytes or SchemaView dumps |
| L-08 | D2 §7.1 | Predicate applicability per class comes from `domain ∈ class_ancestors(cls)`, then `induced_slot(p, cls)`, because `class_induced_slots` omits domain-declared predicates; prefixed names come from `get_uri(…, expand=False)` |
| L-09 | D9 §4 (tests), D2 §1 | A `.linkmllint.yaml` (extends `recommended`; `recommended` at error for classes and predicates; undeclared ranges and subsets; a decision on `canonical_prefixes`); lint files, not the `schema/` directory |
| L-10 | D9 §3, D3 §6 | "JSONB columns are validated against `core/schemas` on write" becomes: validated once at the Pydantic boundary with the compiled per-version models; `core/schemas/*.json` are generated from them; jsonschema runs as an independent oracle in tests and as `check_schema` on artifacts |
| L-11 | D3 §6.1 | Implement "defaults omitted" with `Field(default=…, exclude_if=…)`: defaults filled for rules, omitted in storage; `MISSING` where absent and null differ |
| L-12 | D2 §7.2 (phase 1) | When the GLiNER2 compiler lands: gliner2 2.1.0 `Schema.from_dict` rejects unknown keys and `to_dict()` round-trips (Documented, overview §6.1), so assert `Schema.from_dict(d).to_dict() == d` as the compile check. Not probed: gliner2 is not installed |

## Uncertainties and items for other spikes

- **S3 (vLLM 0.31).** Check the bundled xgrammar version and its handling of `oneOf`,
  `discriminator` and `title`; grammar compile time and memory for the 49–73 KB per-predicate
  schema; whether vLLM caches compiled grammars per schema text; and that the schema text is not
  injected into prompts. The sources cited are vLLM *stable* docs and xgrammar *main*.
- **S4.** Choose one canonical entity-reference and formula shape. Settle U6's `Statement` in
  `entities[]`. The stored-form models were not built in these probes; only model-facing ones were.
  Build the contract test of L-01 and the view builder of decision 6 properly; the probes were
  minimal.
- **Not evaluated.** `jsonschema-rs`, `pg_jsonschema`, LinkML association-class modeling
  (`represents_relationship`), and `gen-pydantic` custom templates (`--template-dir`), which could
  emit discriminated unions at the price of maintaining templates.
- **Search coverage for negative claims.** "`gen-pydantic` emits no discriminated unions" rests on
  running it on `core.yaml` and a probe schema with `designates_type`, `equals_string` and
  recursion. Other metaslots (`any_of`, `exactly_one_of`, `--meta`, templates) were not tried.
  "rule-engine has no recursion" rests on its grammar as documented (comprehensions, no
  user-defined functions; overview §6.1) and on the probes.

## Probes run (scratch, not retained)

The brief allowed only this README in the folder, so the probe scripts stayed in the session
scratchpad (`/tmp/claude-1000/…/scratchpad/`) and are not preserved. Each ran with
`build/spike-venv/bin/python -I`; rule-engine probes added a scratch `--target` directory holding
rule-engine 5.1.0 to `sys.path`. They can be recreated from these descriptions or added here on
request.

| Id | What | Inputs |
|---|---|---|
| P1 | `linkml-lint` on core and statistics; SchemaView imports, annotation types, induced slots, `get_uri`, predicate applicability | `code/schema/*.yaml` copied into a D2 §2 pack layout |
| P2 | `gen-json-schema --no-metadata` and `gen-pydantic --extra-fields forbid --meta None`; batch-shaped values validated against both outputs | The same |
| P3 | Probe schema: `designates_type`, `equals_string`, recursive `Condition`, `--include-range-class-descendants` | A scratch `values.yaml` |
| P4 | Native-feature schema (`examples`, `unique_keys`, `subsets`, `symmetric`, `transitive`, `title`, scalar annotations); lint; SchemaView readback; an object-valued annotation (fails to load) | A scratch `native.yaml` |
| P5 | Pydantic JSON Schema of the spike `batch.py` types; `TypeAliasType`; `GenerateJsonSchema` override; frozen with tuples; `exclude_if`; validation versus serialization mode | `code/instruments/batch.py` |
| P6 | Hand-assembled per-predicate batch schema (`oneOf` and `if`/`then`); 15 v1 batches; `best_match` quality; timing | `results/s0r2/reference_model_v1/`, `results/s0r2/examples/` |
| P7 | `create_model` per-predicate claim models; validation, seeded errors, schema size and determinism; timing | The same |
| P8 | rule-engine typed Context, compile-time errors, D2 and D6 rule texts, function versus attribute, nullability, Chain with `continue`, builtins, symbols, pickling | Synthetic claim and unit views |
| P9 | Schema-version hashing: canonical JSON versus a merged SchemaView dump, across seeds and paths | Pack layout |
| P10 | jsonschema versus Pydantic micro-timings; `referencing` URN registry | Spike types |
| P11 | The 11 guideline rules over generic views; parity with `s0r2_rules.rule_warnings`; 11 seeds | v1 batches, `code/s0r2_rules.py` |

## Consumers

The design authority's phase 0 build plan and the "Library realization" text for D2 §7, D5 §8, D6
§7.1 and D9 §2–§3. The S4 spike (`../2026-10-28_design-spikes/S4-linkml-compilation.md`) can take
P6, P7 and P11 as its starting point. OPEN-D2-3 and OPEN-D2-6 can close on L-05 and L-06 when the
design authority accepts them.
