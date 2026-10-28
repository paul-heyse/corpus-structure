# S4 · LinkML compilation — report

**Run:** 2026-10-28, by Claude Opus 5.5 (executor W-S2, coordinated). **Brief:**
[S4-linkml-compilation](S4-linkml-compilation.md); plan
[S4](../../../plans/design-spikes-s0-s1/S4-linkml-compilation.md). **Status:** passed.

## Answer

Yes. The statistics pack, rewritten in D2 §3's native form (`results/s4/schema/`), loads with its core
import and lints with 0 errors; its 129 scalar `ci:` annotations round-trip unchanged (OPEN-D2-6
closed). Every phase 0 compiler runs end to end on it: schema-table rows in D3's columns, a hash
reproduced by 3 of 3 subprocess runs, both batch forms from
per-predicate Pydantic models, which validate all 135 listed
batches once 45 recorded batch defects are moved
to one entity-reference shape (`{"ref": …}`, V1) and one statement home (`statements[]`, V2), with
jsonschema agreeing on every verdict; 16 typed rule-engine rules
(the 11 guideline checks among them) with 0 warnings on the v1 batches and 16 of 16
seeds caught (OPEN-D2-3); a generated annotator reference that carries S0-R2's information but one
per-card sentence; GLiNER2 dicts that gliner2 2.1.0 accepts and round-trips (OPEN-D2-1); and a decoding
form that vLLM 0.31's xgrammar compiles with no downgrade once `oneOf` branches are inlined, accepting
15 of 15 canonical batches. The reference is far above 1,500
tokens and filtering by statement kind cannot bring it there (V4 not adopted).

## What was run

All from the evidence folder; `$REPO` is the repository root.

| Step | Command | Outcome | Records |
|---|---|---|---|
| S4-A pack files, lint, round trip | `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s4_lint.py` | passed | [s4.pack-lint](records/s4.pack-lint.json) · `results/s4/schema/`, `results/s4/lint/`, `results/s4/roundtrip.md` |
| S4-B tables, hash, schemas, contract test, validation | `… uv run --locked python code/s4_compile.py` | passed | [s4.batch-validation](records/s4.batch-validation.json), [s4.schema-hash](records/s4.schema-hash.json) · `results/s4/compiled/`, `results/s4/validation.tsv` |
| S4-C rules and guideline warnings | `… uv run --locked python code/s4_rules.py` | passed | [s4.rules](records/s4.rules.json) · `results/s4/rules.tsv`, `rules_compile.json`, `rules_seeds.json` |
| S4-D GLiNER2 dicts (CPU) | `HF_HUB_OFFLINE=1 … uv run --locked python code/s4_gliner.py` | passed | [s4.gliner-roundtrip](records/s4.gliner-roundtrip.json) · `results/s4/compiled/gliner2/`, `results/s4/gliner2.json` |
| S4-D reference, diff, sizes | `… uv run --locked python code/s4_reference.py` | passed | [s4.reference-diff](records/s4.reference-diff.json), [s4.sizes](records/s4.sizes.json) · `results/s4/compiled/reference.md`, `reference_diff.md`, `sizes.tsv` |
| S4-D decoding form in xgrammar | `cd results/s4/xgrammar-env && UV_PROJECT_ENVIRONMENT=$REPO/build/spike-xgrammar-venv uv sync --locked`, then `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-xgrammar-venv uv run --project results/s4/xgrammar-env --locked python code/s4_decoding.py` | passed | [s4.decoding-form](records/s4.decoding-form.json) · `results/s4/decoding.json` |
| S4-E records | `python3 code/s4_records.py`; `just evidence finalize 2026-10-28_design-spikes s4.…` | passed | the eight above |

Environment: Python 3.14.10; `build/spike-venv` (record `e4.env-cpu`): linkml 1.12.1, linkml-runtime
1.12.1, pydantic 2.14.1, jsonschema 4.26.0, rule-engine 5.1.0, gliner2 2.1.0 on torch 2.14.1+cpu,
tokenizers 0.23.3. Side environment `build/spike-xgrammar-venv` from the uv project
`results/s4/xgrammar-env/` (its own `uv.lock`): xgrammar 0.2.7 (vLLM 0.31's), torch 2.14.1+cpu,
transformers 5.21.0, apache-tvm-ffi 0.1.15.post1, triton overridden away; no vLLM, no GPU. Checkpoints:
`Qwen/Qwen3.5-9B` tokenizer at revision c202236…, `fastino/gliner2.5-base-v1` at 54785d5…. CPU only
(AMD Ryzen 9 9950X3D); timings are indicative. The finalize-site grammar reader is the I-R2
instruments' `math_parse` (its source hash is in `rules_compile.json`).

## Results

### S4-A · Pack files (record s4.pack-lint)

The pack is written in the D2 §2 layout: `domains/core/schema/{core,rules}.yaml`,
`domains/statistics/schema/{statistics,rules}.yaml`, `domains/statistics/reference/E1…E3/`. Lint, per
file with `.linkmllint.yaml`: 0 errors and
2 warnings, both `standard_naming` on D1's field names `t` and
`v`, kept. Both rules files pass their strict model (2 of 2).
Annotation round trip: 129 of 129 equal. Directory mode reports
6 errors, all from linting `rules.yaml` as a schema
(note L-09 confirmed). The 21 places where D2's drafts were ambiguous or LinkML rejected a construct,
and their resolutions, are in `results/s4/roundtrip.md` (A1–A21); the consequential ones are in the
design implications below.

### S4-B · Compiled schemas, validation, contract, hash and tables (records s4.batch-validation, s4.schema-hash)

25 predicate branches; the model-facing schema is
42559 bytes compact; both exported schemas and
the decoding form pass `Draft202012Validator.check_schema` (3 of 3),
and the schema text is byte-identical across two processes with different hash seeds
(True).

| Batch set | Form | Batches | Valid as written | Migrated (V1/V2) | Valid after | Validators agree |
|---|---|---|---|---|---|---|
| `examples` | model | 3 | 3 | 0 | 0 | 3 of 3 |
| `s0.reference` | stored | 12 | 8 | 4 | 4 | 16 of 16 |
| `s0.stored.adjudication_d7` | stored | 12 | 7 | 5 | 5 | 17 of 17 |
| `s0.stored.adjudication_d7_s` | stored | 12 | 7 | 5 | 5 | 17 of 17 |
| `s0.stored.pass_a` | stored | 12 | 7 | 5 | 5 | 17 of 17 |
| `s0.stored.pass_b` | stored | 12 | 8 | 4 | 4 | 16 of 16 |
| `s0.stored.pass_h` | stored | 12 | 9 | 3 | 3 | 15 of 15 |
| `s0.stored.pass_p` | stored | 12 | 8 | 4 | 4 | 16 of 16 |
| `s0.stored.pass_sg` | stored | 12 | 8 | 4 | 4 | 16 of 16 |
| `s0.stored.pass_sp` | stored | 12 | 9 | 3 | 3 | 15 of 15 |
| `v1.model` | model | 12 | 8 | 4 | 4 | 16 of 16 |
| `v1.stored` | stored | 12 | 8 | 4 | 4 | 16 of 16 |

Every as-written failure is one of the two shapes S4 chose away, and every migrated batch validates
(45 of 45;
126 rewrites, listed per batch in `validation_errors.jsonl`):
`{"t": "entity", "ref": r}` in `pred` arguments and `base_variable` (the v1 reference: T1, U5, U11; all
S0 passes but pass P), a dict-valued identity slot (pass P only), and a `Statement` row in `entities[]`
(U6's "the last result" in every reference; U7's five cited results in passes A and both adjudications).
After migration the side-table check is clean on every valid batch
(135 of 135), and the validators agree on
180 of 180. Seeded errors:
13 of 13 caught (`compiled/seeded_errors.json`); Pydantic
names the exact location (`claims.0.has_distribution.qualifiers.modality literal_error`), jsonschema's
`best_match` stops at the whole claim under `oneOf`, and the five reference errors (wrong subject class,
unresolved object, a variable binding to a global entity, a missing map entry, a global entity with an
extent) are caught by the side table only. Median cost per valid batch: Pydantic
0.073 ms, jsonschema 12.022 ms
(indicative; jsonschema reaches about 0.5 s on a failing batch, whose `oneOf` errors multiply).

The **mirror contract test** (`compiled/contract.json`) compares, per batch form, each value tag's
fields, required-ness, multivalued-ness and range between the core Pydantic shapes and core.yaml's
value classes through SchemaView, plus bind kinds, binding fields, `EntityRef` and evidence roles:
passed (dropping `NumberValue.basis` on the Pydantic side
fails it, adding `TextValue.lang` on the LinkML side fails it).

**Schema version hash** `0af28efdb3ddc863280f41fbe09c3e2122584e79dc4303300e2a602f54d1c85c`, reproduced by
3 of 3 subprocess runs of the in-process value (`PYTHONHASHSEED`
1 and 777; 4242 on a copy elsewhere). **Schema tables** (`compiled/tables.json`, for S6-D):
25 class, 97
slot, 10 enum and 16
rule rows, with the `schema_version` and `compiled_artifact` rows.

### S4-C · Rules (record s4.rules)

| Rule | Group | Evaluations (unseeded) | Unexpected fires | Seed caught |
|---|---|---|---|---|
| `core.value_kind_matches_slot` | rules | 24 | 0 | 1 of 1 |
| `guideline.binding_priority` | guideline | 157 | 0 | 1 of 1 |
| `guideline.formula_excludes_defined_variable` | guideline | 22 | 0 | 1 of 1 |
| `guideline.modality_by_role` | guideline | 128 | 0 | 1 of 1 |
| `guideline.no_claim_nodes_on_form` | guideline | 71 | 0 | 1 of 1 |
| `guideline.parameter_role_differs` | guideline | 2 | 0 | 1 of 1 |
| `guideline.premise_conditions_index_only` | guideline | 31 | 0 | 1 of 1 |
| `guideline.references_a_premise` | guideline | 28 | 0 | 1 of 1 |
| `guideline.role_by_kind` | guideline | 130 | 0 | 1 of 1 |
| `guideline.structural_no_conditions` | guideline | 27 | 0 | 1 of 1 |
| `guideline.structural_role_modality` | guideline | 27 | 0 | 1 of 1 |
| `guideline.symbol_keys_no_backslash` | guideline | 157 | 0 | 1 of 1 |
| `stat.domain_is_set` | rules | 7 | 0 | 1 of 1 |
| `stat.no_family_on_variable` | rules | 16 | 0 | 1 of 1 |
| `stat.one_distribution_per_statement` | rules | 18 | 0 | 1 of 1 |
| `stat.param_keys_known` | rules | 21 | 0 | 1 of 1 |

866 evaluations over the 15 batches at the batch site and the 12-unit
pool at the finalize site: 0 unexpected fires; seeds
16 of 16, and S0-R2's Python checker also warns on
11 of 11 guideline seeds; parity on the
unseeded batches: True. One seed fires a second rule
(`role_by_kind` also fires `modality_by_role`), the expected coupling. Negative compiles rejected:
7 of 7 (a misspelled attribute, attribute access on a
nullable, a wrong argument type, an unknown symbol, `$now`, D2 §7.4's earlier `all(...)`, a keyword
argument). OPEN-D2-3: the resolver-backed view attribute and the `$family_params(id)` function form
both type-check and agree on 21 of 21; the attribute is computed
once per view by the generic builder from the `views:` declaration, with no domain code.

Findings while compiling the pack's own rules: rule-engine does not narrow a type after a null test
(`claim.value != null and claim.value.slot_kind` fails to compile), so every nullable access is `&.`;
strings from SchemaView are `extended_str` and two of them compared unequal in rule-engine until the
loader cast them to `str`; the guideline's "given as a parameter value" relation holds only for givers
that are premises or example values (without that restriction `binding_priority` fired falsely on
U10 and E1).

### S4-D · Annotator reference, sizes, GLiNER2, decoding form

**Reference** (record s4.reference-diff; `reference_diff.md`): 25
cards; empty meanings 6 in S0-R2's, 0
generated; names in S0-R2's predicate cards and not in the generated ones: 9,
all from S0-R2's per-card role/modality lines (`premise`, `definiens`, `asserted`, …), which the
generated reference states once in its tables section and rule descriptions. The
single information loss is the per-card role/modality sentence for the six family-structure-only
predicates (the same facts are in the generated tables section). Additions: descriptions, exact
shapes of every item, the tables, `unschematized`, symmetric/transitive flags; and S0-R2's number
example `"unit": null` is now invalid (absent, never null).

**Sizes** (record s4.sizes; Qwen3.5-9B tokens): generated reference 12851
(without examples 6339; predicate cards
2762, shapes 1231);
S0-R2's 11486 (4956 without examples);
smallest per-kind variant 6347; decoding schema
12716; GLiNER2 extraction dict 676.

**GLiNER2** (record s4.gliner-roundtrip; OPEN-D2-1): accepted keys for v0 are `entities` (label →
description), `entity_attributes` (`labels`, `applies_to`, `qualify_labels`), `classifications`
(`task`, `labels` as label → description) and `relations` (name → `{description}`); an unknown key is
rejected (ValidationError). `to_dict` compacts a
description-only entity config to a plain string, so the compiled dict equals `to_dict` only in that
canonical form (fixpoint: True); the
JointIE schema round-trips (True). Both ran on
T3 s1 on CPU (passed, passed).
Structures and per-type thresholds are not exercised: v0 declares none.

**Decoding form** (record s4.decoding-form; V3): xgrammar 0.2.7
keeps 8 of 8 `oneOf`s with 0
warnings, compiles in 0.03 s, accepts
15 of 15 canonical batches (compact and indented, and T3 token
by token through the matcher) and rejects 7 of 7 seeds. Before
the branches were inlined, every `oneOf` whose branches were `$ref`s fell back to `anyOf` with a
warning (probe: two const-tagged `$ref` branches downgrade, the same branches inline are kept). The
grammar fixes the schema's property order: a batch in the authors' key order is accepted only with
`any_order=True` (False by default).

## Assumptions

- **V1, entity reference: `{"ref": …}`** everywhere a position may take an entity (claim objects,
  entity qualifiers, `pred` arguments); fields that only ever hold a reference (subject, statement,
  identity slots, binding targets) stay local-ref strings. Why: the S0-R2 reference and its three
  passes write `{ref}`; storage already separates entity objects from values (D3 `object_entity_id` and
  `object_value`), so an entity reference is a position type, not a D1 value; the only union with values
  (`pred` arguments) decodes as `anyOf` without loss. Confirmed by validation: 135 of 135 batches valid
  in this shape after migration.
- **V2, statements only in `statements[]`**; a statement outside the unit (U6 "the last result", U7's
  "[14]") is a `statements[]` item with `anchor: "outside"`, resolved by consolidation through the
  link targets of the citing claim's evidence or left unresolved. An entity row for a statement would
  give statements a second identity path (D1 §10.1 keys statements by anchor). Migrated items take kind
  `theorem` (each names a result).
- **V3: the per-predicate `oneOf`** (V3a) is kept; the flat form was not built because V3a compiled
  without downgrade.
- **V4: not adopted.** The reference exceeds 1,500 tokens at every per-kind filter.
- **Optional fields are absent, never null**: no batch contains a null; the models reject one.
- **Prefixes kept** (`ci`, `core`, `stat`), `canonical_prefixes` disabled deliberately (roundtrip.md).
- **`t`/`v` kept**, `standard_naming` at warning.
- **Finalize site** is a 12-unit pool with spike keys (global entities by class and casefolded label,
  parameters by family key and canonical name, the rest by unit and local ref), standing in for
  consolidation's keys; symbol facts are scoped to the unit. Its parse data comes from the I-R2
  instruments' grammar reader with the pack's fallback macros only.
- **Worked examples** in `reference/E*/` hold the packet text and the batch; no citation frame (the spike
  sample has no D1 §3.4 sentence locators).
- `lemma` was added to `roles_by_kind` (S0-R2's checker had no row for it); no batch has a lemma.

## Design implications

| Design item | Proposed change or answer | Evidence |
|---|---|---|
| OPEN-D2-6 | **Closed.** Native `examples`, `unique_keys`, subsets, `symmetric`, `transitive`, `title`, `ifabsent`; scalar `ci:` annotations only (space-separated lists for `ci:qualifiers`, `ci:identity_qualifiers`, `ci:target`); 129 of 129 round-trip | s4.pack-lint |
| OPEN-D2-3 | **Closed as proposed**: typed OBJECT contexts, cached view attributes from `views:`, `at:` per rule; functions only for parameterized lookups (`$is_a`); both forms type-check and agree | s4.rules |
| OPEN-D2-1 | **Answered for v0**: the accepted keys above; the compile check is `Schema.from_dict(d).to_dict() == d` on the compiled canonical form (description-only entity configs as strings), and `JointSchema.from_dict(d).to_dict() == d` | s4.gliner-roundtrip |
| OPEN-D2-10 | Shapes of `param_mapping`, `param_symbols`, `param_constraints` are stated: `{<name>: <string>}`, `{<name>: <formula>}`, a condition tree (descriptions in statistics.yaml; rendered by the reference) | s4.reference-diff |
| D2 §2 | Confirmed: schema version = SHA-256 of canonical JSON of the parsed `<pack>.yaml`, both `rules.yaml`, `core.yaml` and `reference/E*` (packet text, batch); stable across seeds and locations. The examples need a citation frame file once D1 §3.4 sentence locators exist | s4.schema-hash |
| D2 §3 | Replace the annotation tables with the native form: drop `ci:kind`, `ci:object`, `ci:role: identity/field`, `ci:group`, `ci:gliner_label`, `ci:examples`, `ci:identity_keys`, `ci:symmetric` (derived or native); keep `ci:role` only for predicates and qualifiers; add `ci:form` (`model`/`stored`/`consolidated`) and `ci:required_in` for form-specific value fields; add `ci:symmetric` on `ConditionPredicate` permissible values (D1 §7 sorts arguments of symmetric condition predicates, and nothing declared them); the derivation rule for kinds: entity = `Entity` ancestor and not abstract or mixin, value = `Value` ancestor, map = `MapEntry` subclass, condition = `Condition` | s4.pack-lint; roundtrip.md A1–A16 |
| D2 §3.2 | Subsets `structural` and `unsupported` (core), `formula_definition`, `family_structure`, `distribution` (statistics) replace `ci:group`; the guideline's formula-or-family set is `formula_definition ∪ family_structure` | s4.rules |
| D2 §5 | `ConditionPredicate` values carry `ci:symmetric`; the side table checks `ci:arity` and `ci:args` | s4.batch-validation |
| D2 §6 | Replace the core.yaml draft with `results/s4/schema/domains/core/schema/core.yaml`: abstract `Value` with `t` by `equals_string`; `EnumValue` added; `EntityRef` (a position type, not a value); `Condition` placeholder; `MapEntry`; `EvidenceRole` enum; `ParseStatus.ambiguous`; `ifabsent` defaults on `modality`/`polarity`; descriptions everywhere. The contract test (field by field through SchemaView, per batch form) is the P0-F-2b/P0-S-1 contract | s4.batch-validation |
| D2 §7.1 | Applicability by `domain ∈ class_ancestors`, prefixed names by `get_uri(…, expand=False)`; slot rows for class-local attributes need a name scheme because D3's `(schema_version_id, name)` key cannot hold `v` of two classes: `<prefix>:<Class>.<attribute>` (or no field rows: the core Pydantic shapes own them) | s4.schema-hash |
| D2 §7.3 | (a) Entity reference `{"ref": …}` (V1) and the statement anchor `"unit" | [ids] | "outside"` (V2) are the outline's shapes; `entities[].type` excludes `Statement`. (b) Optional fields absent, never null. (c) The decoding form inlines `oneOf` branches (xgrammar 0.2.7 downgrades `$ref` branches to `anyOf`), strips `discriminator`/`description`/`default`/`title`, and fixes property order (authors' order needs `any_order`). (d) The entity-type side table also checks binding targets, map entries, scope by class and condition-predicate arity, and is the only catcher of reference errors | s4.batch-validation, s4.decoding-form |
| D2 §7.4 | `guideline:` entries take an optional `when`; `applies_to` lists may mix predicates and `subset:<name>`; tables may use `none` for "no role"; every nullable access must use `&.`/`??` (no narrowing after a null test); SchemaView strings must be cast to `str` before reaching rule-engine; one context per expression with `$now`/`$today`/`$random` rejected | s4.rules |
| D2 §7.5, §10.10 | The reference compiler is specified by `code/s4/reference.py`'s sources: cards grouped by subsets with the guideline rules that apply by `applies_to`, the tables section, shapes from the core models. To restore the one lost sentence, the `family_structure` subset description should state the role/modality rule (proposed text below). The 1,500-token budget is not reachable by statement-kind filtering; the reference is about 6,300 tokens without examples | s4.reference-diff, s4.sizes |
| D2 §9 | Replace the statistics.yaml draft with `results/s4/schema/domains/statistics/schema/statistics.yaml`: `Parameterized` mixin as `has_parameter`'s domain and `family`'s range (subsumes `stat.no_family_on_variable`); `parameter_role` not multivalued; `symbol` a plain slot, not identity; `special_case_of` transitive; descriptions for `support`, `cdf`, `mgf`, `mean_value`, `variance_value`, `definition_formula` and every qualifier. Rules table: `stat.variance_nonnegative` leaves rules.yaml (a verifier, M20/M21) | s4.pack-lint, s4.rules |
| D5 §8.2 | Final view names: `claim.bindings` is a list of `{symbol, bind, entity, claim, param}` (not a mapping); `claim.subject.index_symbols`; `claim.value.{t, latex, v, enum, slot_kind, parse, math_kind}` (parse fields null at batch); `claim.given_by_others`/`gives_symbols` count only givers whose role is premise or example value; new `claim.same_slot` and `claim.alternative_of` (for `stat.one_distribution_per_statement`); `claim.predicate` is prefixed | s4.rules |
| D1 §6 | The `entity` row of the value table becomes "an entity reference `{ref}`, a position type, not a value" (V1) | s4.batch-validation |
| D1 §10.3 | The generic item models and the side table are domain-free as stated; the pack types only objects and qualifiers. Per-class entity branches (scope and identity by `type`) would let the decoder refuse a global `RandomVariable`; not built (follow-up) | s4.batch-validation |
| D3 §3 | `meta.schema_slot` names for class-local attributes (above) | s4.schema-hash |
| ADR-0017 (LinkML packs) | Evidence for acceptance: the pack compiles end to end in the native form | s4.pack-lint, s4.batch-validation |
| ADR-0018 (policy routing through the rule syntax) | Evidence for acceptance: the shared rule-language helper compiles every pack rule with compile-time errors for typos, nullable misuse, wrong arguments, unknown symbols and nondeterministic builtins | s4.rules |

### Proposed schema text

The complete proposed text for D2 §6 and §9 is the pack files themselves
(`results/s4/schema/domains/core/schema/core.yaml`, `…/statistics/schema/statistics.yaml`) and for the
`rules.yaml` of §7.4 and §9, `…/statistics/schema/rules.yaml` and `…/core/schema/rules.yaml`. The parts
that change D2's prose:

**D2 §3 (annotation vocabulary), replacing the three tables' derived rows:**

```yaml
# derived, never written: kind (entity | value | abstract), object (from the range), role identity/field
# native: examples, unique_keys, subsets/in_subset, symmetric, transitive, title, ifabsent
# remaining ci: annotations (scalars only)
ci:role: predicate | qualifier                    # slots
ci:scope: global | local                          # entity classes
ci:extract: mention | none | relation | llm | attribute | classification
ci:reify: true
ci:parameter_class: <identity slot>               # e.g. family
ci:qualifiers: "transform param_mapping"          # space-separated
ci:identity_qualifiers: "transform"
ci:param_map: <map qualifier>                     # e.g. param_values
ci:functional: true
ci:target: "unit paragraph"                       # space-separated segment kinds
ci:applies_to: <class>
ci:claim_bearing: true | false                    # StatementKind values
ci:arity: "2+" ; ci:args: <class> ; ci:symmetric: true ; ci:z3: <name>   # ConditionPredicate values
ci:form: model | stored | consolidated            # value-class attributes present in one form only
ci:required_in: stored                            # required in that form only
```

**D2 §6, the value-class mirror (excerpt):**

```yaml
  Value:
    abstract: true
    slots: [t]
  Formula:
    is_a: Value
    slot_usage: {t: {equals_string: formula}}
    attributes:
      latex: {required: true}
      sympy: {annotations: {ci:form: consolidated}}
      parse: {range: ParseStatus, annotations: {ci:form: consolidated}}
      symbols: {range: SymbolBinding, multivalued: true, inlined: true}
  EnumValue:
    is_a: Value
    slot_usage: {t: {equals_string: enum}}
    attributes: {enum: {required: true}, v: {required: true}}
  EntityRef:                       # a position type, not a value (V1)
    attributes: {ref: {required: true}}
  Condition: {abstract: true}      # node shapes owned by the core Pydantic Condition union
  MapEntry:
    abstract: true
    attributes: {key: {identifier: true}, value: {}}
slots:
  modality: {range: ClaimModality, ifabsent: string(asserted), annotations: {ci:role: qualifier}}
  conditions: {range: Condition, annotations: {ci:role: qualifier}}
```

**D2 §7.3, the outline's changed lines:**

```text
  entities[]   { local_ref, type ∈ enum(entity classes except Statement), label, scope, extent?, symbol?, aliases?, identity? }
  statements[] { local_ref, kind, anchor: "unit" | [sentence ids] | "outside" }     stored: anchor = [segment keys] | "outside"
  claims[]     oneOf per predicate: { …, object: <entity ref {ref}> | <value of p>, … }
  (optional fields are absent, never null)
```

and in "How the schema is built": "The decoding form inlines the branches of every `oneOf`; with `$ref`
branches xgrammar 0.2.7 cannot prove them disjoint and falls back to `anyOf` (S4)."

**D2 §7.4, guideline entry form (example):**

```yaml
guideline:
  - id: guideline.references_a_premise
    applies_to: any
    description: Every other claim references at least one premise of its statement or of a context-premise assumption (§10.7 rule 3).
    when: >-
      not ('structural' in claim.groups or 'formula_definition' in claim.groups or 'family_structure' in claim.groups)
      and not (claim.statement_role in ['premise', 'example_value'])
    check: "claim.statement_premises.is_empty or $any([p in claim.claim_refs for p in claim.statement_premises])"
tables:
  roles_by_kind: {definition: [definiens, premise], remark: [premise, conclusion, definiens, none], convention: [none], …}
```

**D2 §9, the changed declarations (excerpt), and the restored sentence for the reference:**

```yaml
subsets:
  family_structure:
    description: >-
      Claims about a family's parameters as such … stated only in a definition of the family (§10.4).
      In a definition their role is definiens and their modality defined.      # proposed addition
classes:
  Parameterized: {mixin: true, description: Things that have parameters, a family or a construction.}
  DistributionFamily: {is_a: Entity, mixins: [Distributed, Parameterized], title: distribution family, …}
slots:
  family: {range: Parameterized}
  has_parameter: {domain: Parameterized, range: FamilyParameter, in_subset: [family_structure], …}
  parameter_role: {domain: FamilyParameter, range: ParameterRole, in_subset: [family_structure], …}   # not multivalued
  special_case_of: {domain: DistributionFamily, range: Entity, transitive: true, …}
```

## Follow-ups

- **Reference size for the local tier (S3, P0-A-1).** About 6,300 tokens without examples: decide the
  local tier's budget against D4's packet caps, and whether per-kind card filtering is worth a schema
  fact (the statement kinds a predicate occurs in), or the shapes section can be dropped for decoders
  that are constrained anyway.
- **vLLM itself (S3).** The decoding form was checked in xgrammar 0.2.7 offline; S3 confirms vLLM 0.31
  passes the schema through unchanged (and its property-order behaviour) and measures generation.
- **Per-class entity branches** in the decoding form (scope and identity typed by `type`), if S3 shows
  models emitting class/scope mismatches.
- **Citation frames** for `reference/E*` once D1 §3.4 sentence locators exist (D2 §2 hash input).
- **Finalize keys.** The pool used spike keys; P0-F-2b's real keys and consolidation's entity
  resolution replace them, and `stat.param_keys_known` should be re-run on that pool.
- **Derivations** (`derive:`) were not compiled (outside S4).

<!-- generated by `just evidence render S4-report.md.j2` on 2026-10-28; records: 2026-10-28_design-spikes/s4.batch-validation, 2026-10-28_design-spikes/s4.decoding-form, 2026-10-28_design-spikes/s4.gliner-roundtrip, 2026-10-28_design-spikes/s4.pack-lint, 2026-10-28_design-spikes/s4.reference-diff, 2026-10-28_design-spikes/s4.rules, 2026-10-28_design-spikes/s4.schema-hash, 2026-10-28_design-spikes/s4.sizes -->
