# S4-A · Pack files: load, lint and annotation round trip

Run 2026-10-28 (Claude Opus 5.5, executor W-S2), linkml 1.12.1 / linkml-runtime 1.12.1, Python 3.14.10,
`build/spike-venv` (record `e4.env-cpu`). Command:
`UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s4_lint.py` (from the
evidence folder). Machine-readable outputs: `lint/core.json`, `lint/statistics.json`,
`lint/directory_mode.json`, `lint/lint.json`, `lint/readback.json`.

## Files

The pack in the D2 §2 layout, under `schema/domains/`:

| File | What |
|---|---|
| `core/schema/core.yaml` | Core classes, predicates, qualifiers, the value-class mirror, enums (D2 §6), native form |
| `core/schema/rules.yaml` | The domain-free rule `core.value_kind_matches_slot` |
| `statistics/schema/statistics.yaml` | Statistics schema v0 (D2 §9), native form; imports `../../core/schema/core` |
| `statistics/schema/rules.yaml` | `views:` (`family_params`), `rules:` (4), `guideline:` (11), `tables:` (2), `derive: []` |
| `statistics/reference/E1…E3/` | The worked examples: `packet.md` (S0-R2's example packet) and `batch.json` (already canonical; no rewrite was needed) |
| `.linkmllint.yaml` | Lint configuration |

`SchemaView(statistics.yaml)` resolves the import relative to the importing file with no `importmap`:
closure `['linkml:types', '../../core/schema/core', 'statistics']` (25 classes, 68 slots, 10 enums,
25 predicates, 15 qualifiers).

## Lint

Each file is linted alone with `linkml-lint --config .linkmllint.yaml <file>`:

| File | Errors | Warnings | Findings kept, with reason |
|---|---|---|---|
| `core.yaml` | 0 | 2 | `standard_naming`: slots `t` and `v`. D1 fixes these JSON field names (the value tag and a scalar value); the rule's snake-case pattern wants two characters. Kept; the rule is at warning for this reason |
| `statistics.yaml` (with its core import) | 0 | 2 | The same two, from the import |
| `rules.yaml` (both) | 0 | — | Not LinkML schemas: checked by the rules-file model (`code/s4/pack.py` `RulesFile`, `extra="forbid"`): both pass. Their expressions are compiled in S4-C |

Directory mode (`linkml-lint … schema/domains`) lints the two `rules.yaml` files as schemas and reports
`valid-schema` errors (`'rules' was unexpected`, `'id'`/`'name'` required), confirming note L-09: lint
files, never the directory.

Configuration (`.linkmllint.yaml`): extends `recommended`; `recommended` at **error** (descriptions are
model input, D2 §1.3: every class, slot, enum and permissible value has one); `no_undeclared_subsets`,
`no_undeclared_ranges`, `no_invalid_slot_usage` at error; `standard_naming` at warning (above);
`no_empty_title` off (titles are GLiNER2 labels on mention classes only); `canonical_prefixes` **off,
deliberately**: `ci`, `core` and `stat` are registered elsewhere (content-inventory, VIVO core, POSIX
stat), but every IRI is explicit under `https://corpus-structure.dev/` and every export carries its
own prefix map (JSON-LD `@context`, D8 §6). Renaming would move every stored predicate name
(`stat:has_distribution`) for a tooling convenience; the decision is recorded here and in the report.

## Annotation round trip (OPEN-D2-6)

`lint/readback.json` compares, for each of the **129** `ci:` annotations in the two schema files, the
value `yaml.safe_load` reads from the file with the value `SchemaView` returns (through
`element.annotations[tag].value`; induced slots carry a `JsonObj` that must be unwrapped). All 129 are
equal and of the same type: 97 strings, 20 booleans, 12 tuples split from the three space-separated
list annotations (`ci:qualifiers`, `ci:identity_qualifiers`, `ci:target`). No list or object value
remains, so metamodel validation passes. Strings come back as LinkML's `extended_str`; they must be cast
to `str` before reaching rule-engine, whose equality between two such values failed in S4-C until the
pack loader cast them.

Native features read back (`readback.json` `native`): `examples` on the five mention classes,
`unique_keys.identity = [family, canonical_name]` on `FamilyParameter`, `title` (the GLiNER2 label),
subsets with `in_subset`, `symmetric` (`identical_parameter`), `transitive` (`special_case_of`),
`equals_string` tags of the nine value classes, `ifabsent` defaults (`modality: asserted`,
`polarity: positive`), and prefixed names from `get_uri(…, expand=False)` (`stat:has_distribution`,
`core:defines`). Induced slots for every class and the predicate applicability per entity class
(`domain ∈ class_ancestors(cls)`, mixins included) are listed in `readback.json`.

## Where D2 was ambiguous or LinkML rejected a construct, and the resolution

| # | D2 text (§6, §9 drafts) | Resolution in the pack files |
|---|---|---|
| A1 | List-valued annotations (`ci:examples`, `ci:qualifiers`, `ci:identity_keys`, `ci:target`) fail metamodel validation | Native `examples`, `unique_keys`; scalar space-separated `ci:qualifiers`, `ci:identity_qualifiers`, `ci:target` (D2 §3 as amended) |
| A2 | `ci:kind`, `ci:object` on every element | Derived: entity class = `Entity` ancestor, not abstract or mixin; value class = `Value` ancestor; object kind from the range (value-class tag, entity class or mixin, enum, `MapEntry` subclass → `map`, `Condition` → `condition`). No `ci:kind`/`ci:object` remains |
| A3 | `ci:role: field` and `ci:role: identity` on every attribute | Dropped: identity = in a class's `unique_keys`; field = everything that is neither predicate nor qualifier. `ci:role` stays only for `predicate` and `qualifier` (40 uses) |
| A4 | `ci:group` (`structure`, `distribution`, `unsupported`) and the guideline's hard-coded STRUCTURAL / FORM / FAMILY sets | Subsets: core `structural`, `unsupported`; statistics `formula_definition`, `family_structure`, `distribution`. The guideline's FORM set is `formula_definition ∪ family_structure`; `family_structure` holds D2 §3.2's eight predicates. Subset descriptions carry the guideline rule they stand for (rendered by the reference compiler) |
| A5 | `ci:gliner_label`, `ci:symmetric` | Native `title`, `symmetric`; `transitive: true` added on `special_case_of` |
| A6 | Value classes without `t`; `IntervalValue.start/end` and `conditions`/`param_constraints` ranged on `string` | Abstract `Value` base with slot `t`, each class `slot_usage: {t: {equals_string: …}}`; bounds ranged on `Value`; a placeholder abstract class `Condition` names the condition range |
| A7 | No `EnumValue` class (D1 §6 has `enum`); no `EvidenceRole` enum (every batch uses evidence roles) | Both added to core.yaml |
| A8 | Entity references: D1 §6 lists `entity` as a value `{t: entity, ref}`; D2 §7.3 and the reference use `{ref}` | V1 = `{"ref": …}`, a position type (`EntityRef` class, not a `Value`); see the report |
| A9 | One `PhraseValue` with fields of both batch forms; `Formula.sympy`/`parse` absent from both batch forms | `ci:form: model | stored | consolidated` on form-specific attributes, `ci:required_in: stored` on the stored offsets, so the contract test compares each form with its own fields |
| A10 | The stored `scope` qualifier is `{extent, segment}`, the model-facing one a `ScopeExtent` string | No LinkML expression for a form-dependent shape; the range stays `ScopeExtent` and the stored shape is the core Pydantic `ScopeSt`; the slot description says so |
| A11 | Map qualifiers recognised by `ci:object: map` on ad-hoc classes with `key`/`value` | Abstract core `MapEntry` (`key` identifier, `value`); `ParamValue` and `ParamMapping` are its subclasses with `slot_usage` on `value` |
| A12 | `parameter_role` declared `multivalued: true` | Removed: `multivalued` is per instance record, meaningless on a predicate (note's `ci:functional` remark) |
| A13 | `has_parameter` domain `Entity`, with rule `stat.no_family_on_variable` to exclude random variables | New mixin `Parameterized` on `DistributionFamily` and `FamilyConstruction`; `has_parameter` and the `family` identity slot range on it. Every `has_parameter` subject and every parameter's family in the 135 batches is one of the two (checked before the change); the rule is now subsumed by the side-table check and kept only as the `$is_a` builtin's test |
| A14 | `symbol` declared `ci:role: identity` on `RandomVariable` | Not an identity key: batches carry `symbol` at the top of the entity item, `identity` holds only `unique_keys` slots. A plain slot |
| A15 | D1 §7's canonical form sorts `pred` arguments "only when the schema declares the condition predicate symmetric", but D2 §5 has no such declaration | `ci:symmetric: true` on the permissible values `independent`, `identically_distributed`, `iid` |
| A16 | Defaults "filled in for rules, omitted in storage" (D5 §8.2, D3 §6.1) not stated in the schema | Native `ifabsent` on `modality` and `polarity`; the batch models use `exclude_if` defaults |
| A17 | Six predicates and eleven qualifiers without description; enum values without descriptions | Descriptions written (lint `recommended` at error requires them) |
| A18 | Prefix collisions (`canonical_prefixes`) | Kept, rule disabled deliberately (above) |
| A19 | `rules.yaml`: D2 §7.4's `guideline:` entries have no `when`; `applies_to` lists mixing subsets and predicates; a table value meaning "no role" | `when` optional (default `true`); lists may mix `subset:<name>` and predicates; the token `none` in `roles_by_kind` |
| A20 | D2 §9's `stat.variance_nonnegative` is "checked by M20 with z3, not by rule-engine" | Not a rules.yaml entry (it has no expression); belongs to the verifiers (D2 §7.6, D4 M21) |
| A21 | D2 §2 puts the worked examples in the hash with "packet text, authored batch and citation frame" | `reference/E*/packet.md` and `batch.json`; the citation frame is not written: sentence locators (D1 §3.4) are not in the spike sample |
