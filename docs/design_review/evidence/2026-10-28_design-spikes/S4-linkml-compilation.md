# S4 · LinkML compilation

**Brief, 2026-10-28.** CPU. Can run any time; its outputs help S2 and S3, which can otherwise
hand-write their schemas.

## Question

Does the statistics schema v0 of [D2 §9](../../../design/D2-schema-and-guidelines.md#9-statistics-schema-v0),
written in LinkML 1.12.1 with the `ci:` annotations, load cleanly and compile into what each
consumer needs, as D2 §7 specifies: schema tables, GLiNER2 schema dicts, the ClaimProposalBatch
JSON Schema (model-facing and stored forms), rule-engine rules, and the prompt inventory?

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D2-1 | Exact `Schema.from_dict` keys for structures, attributes and thresholds in gliner2 2.1.0 |
| OPEN-D2-3 | rule-engine syntax for `rules.yaml` checks; custom functions or resolver-backed symbols |
| OPEN-D2-6 | Whether list-valued annotations round-trip through `SchemaView` |
| D2 §7.3 | Whether the per-predicate `oneOf` batch schema validates S0 batches and is accepted by vLLM's structured-output backend |
| D2 §2 | Whether the schema version hash is stable across loads and machines |

## Inputs

- D2 §3–§6 and §9 (vocabulary, core schema, statistics schema v0, initial rules).
- S0 reference batches, when available, for validation; otherwise the trace's target claims
  written as batches by hand.
- Library overviews: [linkml](../../../libraries/linkml.md), [gliner2](../../../libraries/gliner2.md),
  [rule-engine](../../../libraries/rule-engine.md).

## Procedure

1. **Write the schema files** as spike copies under `code/schema/` (`core.yaml`,
   `statistics.yaml`, `rules.yaml`), following D2 exactly. Record every place where D2 is
   ambiguous or where LinkML rejects a construct, and how you resolved it.
2. **Load and lint.** `linkml-lint`; `SchemaView` with imports; induced slots for every class;
   read back every `ci:` annotation, including lists (`OPEN-D2-6`).
3. **Compile to schema tables** (D2 §7.1): rows for `meta.schema_class`, `schema_slot`,
   `schema_enum`, `schema_rule` as JSON. Compute the content hash twice in separate processes.
4. **Compile to GLiNER2** (D2 §7.2): the `Schema.from_dict` dict and the `JointIE` schema. Load
   both with gliner2 2.1.0 and run one trivial extraction on a trace sentence to prove they are
   accepted. Record the accepted keys (`OPEN-D2-1`).
5. **Compile to JSON Schema** (D2 §7.3): the stored form and the model-facing form (quotes).
   Validate every S0 batch with `jsonschema` (draft 2020-12), and the entity-type side-table check
   in a few lines of Python. If the vLLM environment is available, check that the model-facing
   schema compiles in its structured-output backend (offline, without a model, if the backend
   allows; otherwise note it for S3).
6. **Compile rules** (D2 §7.4): each rule's `when` and `check` with `rule_engine.Rule` under a
   typed `Context`; register `family_params` both as a custom function and as a resolver-backed
   attribute; evaluate on S0 claims, including one deliberately wrong claim per rule. Report
   which form type-checks cleanly (`OPEN-D2-3`).
7. **Prompt inventory** (D2 §7.3, §7.5): generate it; measure its size in tokens with the
   Qwen3.5 tokenizer.

## Data to collect

| File | Content |
|---|---|
| `results/s4/schema/` | The schema files as compiled |
| `results/s4/compiled/` | Tables JSON, GLiNER2 dict and joint schema, both JSON Schemas, rules report, inventory |
| `results/s4/roundtrip.md` | Annotation round-trip findings, lint output, LinkML workarounds |
| `results/s4/validation.tsv` | batch × form: valid, errors |
| `results/s4/rules.tsv` | rule × claim: expected, result, type-check outcome per function form |
| `results/s4/sizes.tsv` | artifact: bytes, tokens; hash stability |

## How to interpret

| Finding | Reading |
|---|---|
| All compile, S0 batches validate, rules type-check | D2 §7 confirmed; the compilers become the P0.4 specification |
| LinkML loses list annotations | Store lists as YAML strings in annotations, or move them to a sidecar file; `OPEN-D2-6` closed either way |
| The per-predicate `oneOf` is too heavy for the structured-output backend | Emit a flatter model-facing schema (predicate as an enum, qualifiers as a permissive object) and validate predicate-specific rules after generation |
| Custom functions do not type-check in rule-engine | Use resolver-backed attributes (`claim.family_params`); `OPEN-D2-3` closed |
| The inventory exceeds about 1,500 tokens | Filter it by statement kind as D4 §4.2 allows |

## Report

`S4-report.md` from the [template](report-template.md), answering `OPEN-D2-1`, `OPEN-D2-3` and
`OPEN-D2-6`, listing every D2 ambiguity found, and proposing the corrected schema text.
