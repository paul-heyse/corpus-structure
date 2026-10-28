# S6 joint dry run (S6-D, plan §3)

S4-B's `results/s4/compiled/tables.json` (schema version 0.2.0, content hash `0af28efdb3ddc863…`) loaded into `meta.schema_*` of `cs_spike_s6` (PostgreSQL 18.6, project-local cluster, as the non-superuser `cs_s6_app`); the twelve core units of the v1 reference inserted against it as run 27. Input not yet recorded by S4 (its records come at S4-E).

## Registration

- Content hash recomputed here from the 10 listed sources (canonical JSON of the parsed files): **matches**.
- `json_schema` `batch.model_facing`: body hash recomputed matches
- `json_schema` `batch.stored`: body hash recomputed matches
- `json_schema` `batch.decoding`: body hash recomputed matches
- `schema_tables` `tables`: body hash recomputed matches

| table | rows | inserted |
|---|---|---|
| meta.schema_class | 25 | 25 |
| meta.schema_slot | 97 | 97 |
| meta.schema_enum | 10 | 10 |
| meta.schema_rule | 16 | 16 |

Every compiled row inserts; no constraint rejects one.

## Trace rows against the version

67 entities and 70 claims inserted; renditions selected through reused ingest tasks: 4; not loaded (as in S6-B): U6/e_last_result, U6/c_follows.

## Mismatches between the trace rows and the compiled tables

**predicate not a predicate slot:** 0


**entity type not equal to a schema_class name:** 6

- `["Concept", 1]`
- `["DistributionFamily", 6]`
- `["FamilyConstruction", 1]`
- `["FamilyParameter", 11]`
- `["RandomVariable", 27]`
- `["Statement", 21]`

**entity type matching a class only once prefixed:** 6

- `["Concept", 1, ["stat:Concept"]]`
- `["DistributionFamily", 6, ["stat:DistributionFamily"]]`
- `["FamilyConstruction", 1, ["stat:FamilyConstruction"]]`
- `["FamilyParameter", 11, ["stat:FamilyParameter"]]`
- `["RandomVariable", 27, ["stat:RandomVariable"]]`
- `["Statement", 21, ["core:Statement"]]`

**entity type with no class at all:** 0


**subject type outside domain_class (with parents and mixins):** 0


**object entity type outside range:** 0


**object kind differs from object_kind:** 0


**qualifier key matching the slot's qualifiers only once prefixed:** 5

- `["stat:construction_formula", "base_variable", 1]`
- `["stat:construction_formula", "param_symbols", 1]`
- `["stat:has_distribution", "param_values", 17]`
- `["stat:transformation_of", "param_mapping", 2]`
- `["stat:transformation_of", "transform", 3]`

**qualifier key not allowed for the predicate:** 0


**row values outside the compiled enum:** 0


**DDL CHECK lists against the compiled enums**

| column | DDL | compiled enum | equal |
|---|---|---|---|
| kb.claim.statement_role | conclusion, definiens, example_value, premise, restriction | conclusion, definiens, example_value, premise, restriction | True |
| kb.claim_evidence.role | condition, definition, primary, supporting | condition, definition, primary, supporting | True |
| kb.segment.parse_status | failed, ok, partial | ambiguous, failed, ok, partial | False |

**slot domain_class or range naming a class or enum only by its bare name (within the compiled rows):** 43

- `["domain_class", "BoolValue"]`
- `["domain_class", "Concept"]`
- `["domain_class", "DateValue"]`
- `["domain_class", "Distributed"]`
- `["domain_class", "DistributionFamily"]`
- `["domain_class", "Entity"]`
- `["domain_class", "EntityRef"]`
- `["domain_class", "EnumValue"]`
- `["domain_class", "FamilyConstruction"]`
- `["domain_class", "FamilyParameter"]`
- `["domain_class", "Formula"]`
- `["domain_class", "IntervalValue"]`
- `["domain_class", "MapEntry"]`
- `["domain_class", "NumberValue"]`
- `["domain_class", "Parameterized"]`
- `["domain_class", "PhraseValue"]`
- `["domain_class", "RandomVariable"]`
- `["domain_class", "Statement"]`
- `["domain_class", "SymbolBinding"]`
- `["domain_class", "TextValue"]`
- `["range", "BindKind"]`
- `["range", "ClaimModality"]`
- `["range", "Condition"]`
- `["range", "DistributionFamily"]`
- `["range", "Entity"]`

**value-class attribute rows (named <prefix>:<Class>.<attr>):** 29

## Reading (2026-10-28)

- **The path works.** Pack → compiled rows → migration-0001 tables → trace rows: every compiled row inserts, the hashes recompute, every claim predicate is a predicate slot, subject and object types agree with `domain_class` and `range` (through `parent` and the pack's mixins), value kinds agree with `object_kind`, and every enum value the rows use is in its compiled enum.
- **Names do not join as stored.** `schema_class.name` and `schema_slot.qualifiers` are prefixed (`stat:RandomVariable`, `stat:param_values`), while `kb.entity.type` (D3 §9, §10: `s.type = 'DistributionFamily'`) and the `kb.claim.qualifiers` keys (D3 §6.1) are bare: 6 entity types and 5 (predicate, qualifier) pairs match only after prefixing; within the compiled rows `domain_class`/`range` name classes bare (43 values) while `name` is prefixed. One convention is needed before SQL joins from claims to their schema definitions (D3 §3) work: prefixed everywhere, or bare classes with prefixed slots, with the compiler and the repository agreeing (P0-F-4, D2 §7.1).
- **Value-class attributes** are slot rows named `<prefix>:<Class>.<attr>` (29): D3's `meta.schema_slot` key `(schema_version_id, name)` cannot hold an attribute such as `v` of two value classes under its bare name, so the class is folded into the name; a `domain_class` column in the key would say it directly (DDL / D2 §7.1 finding).
- **`ParseStatus` has `ambiguous`**, which D3's `parse_status` CHECKs (`kb.segment`, `kb.rendition`) do not allow; one of the two moves.
- U6's `Statement`-typed entity stays a misfit against either version (OPEN-D1-5).

