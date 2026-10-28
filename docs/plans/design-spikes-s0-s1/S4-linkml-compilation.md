# S4 · LinkML compilation: plan

**Status: Proposed (2026-10-28).** Part of the [spike plan series](../design-spikes-s0-s1_2026-10-28.md),
which owns shared decisions (§3.5), the execution queue (row 27) and spike-execution findings. The
question is the [S4 brief](../../design_review/evidence/2026-10-28_design-spikes/S4-linkml-compilation.md)'s;
this document says what remains of it after the schema-and-rules library research, how each brief
step now runs, and which phase 0 package each result feeds.

## 1. What S4 must establish now

The [schema-rules note](../../design_review/evidence/2026-10-28_library-schema-rules/README.md)
(2026-10-28) answered the library questions by probe on the 15 v1 model-facing batches, and D2
was amended from it: Pydantic in `core` owns the shared D1 shapes and `core.yaml` mirrors them
(D2 §6); native LinkML slots and scalar annotations (D2 §3, OPEN-D2-6 answered); batch models
built per predicate with `create_model` and exported by `TypeAdapter` (D2 §7.3); typed rule-engine
contexts, `at:`, `tables:` and cached view attributes (D2 §7.4, D5 §8.2, OPEN-D2-3 answered).

S4 now does what the probes did not: it writes the **pack as files** in that form and runs **every
phase 0 compiler end to end** on it, so the schema-and-rules packages of the
[phase 0 series](../phase-0_2026-10-28.md) port a working specification. It settles the points the
note left open:

- the **stored-form** batch models (only the model-facing form was built);
- **one canonical entity-reference shape and one formula shape** (T1 uses `{"t":"entity","ref":…}`
  where the reference uses `{"ref":…}`);
- whether a **`Statement` belongs in `entities[]`** (U6 does this) or only in `statements[]`;
- the **contract test** between the `core` Pydantic shapes and the `core.yaml` mirror;
- the **view builder** for rules, properly rather than minimally;
- the **generated annotator reference** against S0-R2's hand-assembled one;
- the **decoding form** under vLLM's bundled xgrammar, if the vLLM environment exists (else S3).

Its evidence also decides whether ADR-0017 (LinkML packs) and ADR-0018 (policy routing, through
the rule syntax) are accepted.

## 2. Brief steps as they now run

| Step | Now | Mechanism (owner) |
|---|---|---|
| 1 Schema files | Write `core.yaml`, `statistics.yaml` and `rules.yaml` in the native form: `examples`, `unique_keys`, `subsets`/`in_subset`, `symmetric`, `transitive`, `title`; derived `ci:kind`/`ci:object`; scalar space-separated `ci:qualifiers`, `ci:identity_qualifiers`, `ci:target`; the `core.yaml` value classes restructured as the mirror (`Value` base, `t` by `equals_string`, `Condition` ranges) | D2 §3, §6 |
| 2 Load and lint | `linkml-lint` per file (not the directory, which lints `rules.yaml` as a schema) with a `.linkmllint.yaml` extending `recommended`; decide the `ci`/`core`/`stat` prefix collision with registered prefixes (it matters for JSON-LD exports) | note L-09 |
| 3 Schema tables | Rows with applicability by `domain ∈ class_ancestors(cls)` then `induced_slot`; prefixed names by `get_uri(…, expand=False)`; the schema hash as canonical JSON of the parsed files, computed in two processes with different hash seeds | D2 §2, §7.1 |
| 4 GLiNER2 | Phase 1 (D2 §7.2): compiled here only as S2's input, in the GPU environment, with the `Schema.from_dict(d).to_dict() == d` round-trip as the compile check (OPEN-D2-1) | note L-12 |
| 5 Batch schema | Replaced: build both forms from per-predicate Pydantic models; validate the v1 reference (both forms), the three worked examples and the S0 batches with the adapters; check the exported JSON Schema with jsonschema `Draft202012Validator.check_schema` and validate the same batches with jsonschema as an independent oracle; derive the decoding form by the D2 §7.3 rules and, if `build/spike-vllm-venv` exists, compile it in the bundled xgrammar offline | D2 §7.3 |
| 6 Rules | Confirm on the pack's own `rules.yaml`: typed OBJECT contexts, `$all`/`&.`/`??`, `at:` per rule, rejected nondeterministic builtins; both call sites through one view (`claim.id`, nullable `claim.key`) | D2 §7.4, D5 §8.2 |
| 7 Guideline warnings | Write the 11 checks as the `guideline:` group with the `tables:` section; build the view builder (flattened condition nodes, premises, the "given elsewhere" map); 0 warnings on the v1 reference and examples, every seeded violation caught | D2 §7.4 |
| 8 Annotator reference | Generate from `SchemaView` plus the batch models' shapes; diff by information against `results/s0r2/inputs/packet_v1/reference.md`; size with the served Qwen tokenizer (`encode_batch_fast`, no special tokens; revision recorded) | D2 §7.5, D4 §4.1 |

## 3. Variants

| Variant | Alternatives | What it would change |
|---|---|---|
| V1 entity reference | `{"ref": …}` · `{"t":"entity","ref":…}` | The one shape D2 §7.3 and the reference state; the decoding form's disjointness |
| V2 statements | `Statement` also in `entities[]` · only in `statements[]` | Whether `defines`/`refers_to` subjects need an entity row for a statement |
| V3 decoding form | discriminated `oneOf` on `predicate` · flat (predicate enum, permissive qualifiers, predicate checks after generation) | Only if V3a is rejected by xgrammar or too slow to compile; then D2 §7.3 states the flat form for the local tier |
| V4 reference filtering | whole · filtered by statement kind | Only if the generated reference exceeds about 1,500 tokens (brief) |

## 4. Consumers

| Output | Feeds |
|---|---|
| Pack files, lint configuration | phase 0 schema-and-rules (the pack files phase 0 loads); D2 §6 and §9 drafts replaced |
| Batch models in both forms, the mirror contract test | phase 0 foundations (`core` shapes) and schema-and-rules (compilers); agent interface (`read_instructions` serves the schema) |
| Schema-table rows | S6-D (loaded before the trace rows); phase 0 foundations' migration tests |
| Rules, view builder, guideline group | phase 0 schema-and-rules (M19 runner) and orchestration (`Chain` contexts, ADR-0018) |
| Generated reference, sizes | phase 0 agent interface (prompts, packet caps) |
| GLiNER2 dicts | S2 |
| Decoding form, compile result | S3; D2 §7.3's local-tier form |

## 5. Packages

| Package | Scope | Outputs | Done when |
|---|---|---|---|
| S4-A | Steps 1–2 in the CPU spike environment | `results/s4/schema/`, `.linkmllint.yaml`, `roundtrip.md` | All three files lint clean, or each remaining finding is listed with its reason |
| S4-B | Steps 3 and 5, variants V1 and V2 | `results/s4/compiled/` (tables JSON, both JSON Schemas, the mirror contract test), `validation.tsv` | Every listed batch validates in both forms or each failure is a recorded schema or batch defect; the hash is stable |
| S4-C | Steps 6–7 | `rules.tsv`, the view builder | The 11 guideline checks and the pack rules compile, give 0 warnings on the v1 reference and examples, and catch every seeded violation |
| S4-D | Step 8; step 4 and the decoding check where their environments exist (E4) | `reference_diff.md`, `sizes.tsv`, GLiNER2 dicts, the decoding-form result | Every information difference is listed; the GLiNER2 and xgrammar parts pass or are `not_run` with the missing environment named |
| S4-E | Report | `S4-report.md`, records `s4.*` | The template is satisfied; corrected schema text proposed for D2 §3, §6, §7 and §9 |

Records (`consumed_by` names the phase 0 package and the OPEN item): `s4.pack-lint`,
`s4.batch-validation`, `s4.schema-hash`, `s4.rules`, `s4.reference-diff`, `s4.sizes`, and where run,
`s4.gliner-roundtrip`, `s4.decoding-form`.

## 6. Choices left to execution

- The exact `.linkmllint.yaml` rule levels beyond the note's list, and the prefix decision's form.
- How the contract test compares the Pydantic shapes with the `core.yaml` mirror (exported JSON
  Schema, or field by field through `SchemaView`), as long as either side's change fails it.
