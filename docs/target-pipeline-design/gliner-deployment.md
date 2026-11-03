# GLiNER2.5 deployment

**Proposed for M1 · 2026-11-03.** Use one governed adapter and versioned schema registry for GLiNER2.5 boundary extraction, classification, mention attributes, relations, grouped records and local constrained decoding. The [repository capability reference](../libraries/parsing/gliner2.md) covers package `gliner2` 2.1.0 and the 2.5 model family. Treat that version as the reviewed reference. Pin the actual package, checkpoint revision, tokenizer, operation signatures and dependencies in the deployment manifest. [Notion deployment design](https://app.notion.com/p/40d141b58369811aa70ddcc1d75473ac)

## Checkpoint and execution policy

| Candidate | Role and gate |
| --- | --- |
| `fastino/gliner2.5-base-v1` (194M) | English FP32 CPU reference, subject to record-level qualification |
| `fastino/gliner2.5-small-v1` (74M) | Cost challenger under the same family gates, with schema-specific routing only after evaluation |
| `fastino/gliner2.5-multi-v1` (287M) | Language-triggered extension with an admitted target population and language-specific evaluation |
| GLiNER2.5-Decide | Optional classification challenger when measured routing failures warrant it. Its architecture and task differ from the general-purpose boundary models. |

Load boundary checkpoints through `AutoExtractor.from_pretrained`. Python 3.14 compatibility is operator-confirmed in the milestone. Qualify the pinned product environment and each selected CPU operation. Reuse a resident model instance per checkpoint/adapter profile. A persistent process boundary can manage memory, scheduling and lifecycle. Bound queue size, aggregate threads, memory and time. Batch by compatible schema and similar input length. Compare cold and warm execution, inference, decoding, mapping and persistence. Compatible combined operations can share contextual encoding. Separate decoders and schemas may require separate passes.

The documented `quantize=True` route is FP16 conversion. Qualify any optimization, quantization or alternative backend against the FP32 CPU record baseline on actual source data. GPU attention benchmarks do not establish CPU resource fit. [Library reference](../libraries/parsing/gliner2.md) · [CPU capacity policy](rollout-and-evaluation.md#capacity-and-operating-evidence)

## Operations and authority

| Native operation | Candidate product | Pipeline responsibility |
| --- | --- | --- |
| `extract_entities` | Source spans for concepts, entities, quantities, properties, conditions and symbols | Offset mapping, identity, sense, scope and candidate recall |
| `classify_text` and combined classification | Multi-label content role and route cues | Applicability, mixed roles, unknowns and skipped-route audit |
| `AttributeGroup` | Role or status attached to a selected mention | Mention discovery, evidence and cue-to-proposition scope |
| `extract_relations` | Directed local relation candidates | Endpoint reconciliation, canonical identity and qualification |
| `extract_json` and `structure(...).field(...)` | Anchored grouped records | Required evidence, normalization, semantics of missing fields and complete-record validation |
| Combined `extract` | Co-produced outputs under compatible schemas | Dependence accounting and consistency across separately decoded heads |
| `Classifier` | Constrained label assignments | Sound exclusivity/implication/cardinality premises and feasible result policy |
| `JointIE` | Bounded typed entity/relation graphs | Cross-window identity, units, scope, multiple evidence sources and acceptance |
| Native long and batch APIs | Overlapping windows and offset-remapped candidates | Structure-aware segmentation, cross-window joins and retained alternatives |
| Explicit-span and hidden-state surfaces | Optional scoring of supplied spans or reuse of compatible states | Qualify operation, token/query contracts and lifecycle before use |

## Seven schema packs

Each registry entry versions descriptions, intended span boundaries, applicability, cardinalities, packing/overlap policy, limits and test examples. Descriptions condition predictions. The registry and model-input version must change when they change. Keep a compact coverage schema and route specialized packs. A single large schema increases candidate competition and costs.

| Pack | Proposed candidate fields or labels | Use |
| --- | --- | --- |
| A · Content role and routing | Definition, assumption, theorem/result, proof, example, measurement, comparison, procedure, limitation, citation context, other/unknown | High-recall coverage with mixed roles allowed |
| B · Concepts and definitions | Defined term, definition text, alias/abbreviation, broader concept, instance, definition scope | Definitions and explicit terminology links with reviewable ontology proposals |
| C · Quantities and comparisons | Entity, property, value/range, unit, comparator, reference value, uncertainty, condition and measured/rated/predicted/required/threshold roles | Numeric and unit parser plus attachment template |
| D · Formula context | Formula reference, symbol occurrence, declaration, quantity meaning, domain, assumption and where/let cues | Link existing formula objects to local declarations |
| E · Qualified assertions | Predicate/statement, participants, argument roles, conditions, exceptions, negation, modality and attribution | Local source assertions with qualifications preserved |
| F · Procedures and rules | Action, actor, inputs, outputs, parameters, prerequisites, exceptions and list position | Shadow evaluation of explicit ordered lists |
| G · Table semantics | Header/property roles, row entity, unit declarations, cell type, captions, note markers and conditions | Assist native row/header/cell assembly |

### Grouped fields and mention attributes

Use record mode and a stable occurrence anchor. Anchor definitions on the defined term, measurements on the quantity, qualified assertions on the predicate or statement, symbols on their declaration or occurrence, and procedure steps on an action or list item. Keep the required acceptance fields from the [record contracts](first-production-milestone.md#products-and-scope). The grouped candidate may remain incomplete. Cardinality controls decoder output and cannot establish that a field is stated. Preserve original strings and offsets before numeric/unit normalization. Keep classified enums such as rated distinguishable from literal extracted text.

Mention attributes follow mention selection. Separate boundary or suppression misses from attribute errors. A negation class on a cue requires scope and attachment before it can qualify a proposition. Verify attribute-specific training support before committing to specialization. [Library reference](../libraries/parsing/gliner2.md)

### Constrained decoding

Use multi-label classification for heterogeneous passages. Use constrained assignments for scoped tasks with justified exclusivity, implication or cardinality and a defined unresolved option. The documented `Classifier` default `on_infeasible="relax"` can produce a best-effort assignment. Configure explicit failure or retain feasibility/violations and exclude infeasible results from acceptance. Re-decoding cached scores shares the original evidence.

For `JointIE`, record entity IDs, source spans, relation endpoints, available lattices and the search diagnostics. Apply functional and acyclic constraints only when the scoped relation entails them. Distinguish `feasible=False` from a feasible empty result. Greedy or beam search has candidate and search limits. The graph and its input scores share evidence, as do local and outer applications of a constraint. Whole-record acceptance remains with the [outer interpreter](first-production-milestone.md#bounded-interpretation). [Library reference](../libraries/parsing/gliner2.md)

### Windows and candidate retention

Begin with coherent source-aware windows covering definitions, sentence groups, formula neighborhoods and table contexts. Use long APIs when useful under the library's actual splitting semantics. Track word, subword and character limits separately. Long boundary spans remain limited by window fit and sparse candidate budgets. Retain start/end proposal budgets and overlap policy, especially for nested terms. Local relations require their endpoints to coexist in a window. Keep per-window observations or sufficient diagnostics before duplicate merging so higher-score retention cannot hide a discarded alternative. A deterministic source candidate can trigger a targeted schema/window or an evaluated explicit-span bridge.

## Cache, specialization and qualification

Key observations by source and effective context, schema, operation, weights/adapter, tokenizer, normalization and configuration. Preserve dependency identities for repeated text. Hidden state reuse requires compatible encodings, masks and query construction. Version schema edits and replay affected work. Repair descriptions, anchors, overlap policy, budgets and context before adding another model. Compare supervised or LoRA adaptation against the base only after a systematic gap has suitable references. Use explicit span supervision for repeated strings, negative labels and nesting. Isolate concurrent requests with incompatible mutable adapter state.

Run real retained source examples across all selected operations. Verify exact mappings, grouping with several anchors, nested/long spans, and explicit empty, failed, infeasible, truncated and over-budget outcomes. Audit absent output and missed routing in independent source samples. Compare base/small, combined/separate, broad/routed, native/outer assembly and independent/JointIE where applicable using full records, evidence alignment, CPU and peak memory. A decoder score is an input to calibration and acceptance. Each released family requires its own evaluated subset. [Deployment acceptance](https://app.notion.com/p/40d141b58369811aa70ddcc1d75473ac) · [Release gates](rollout-and-evaluation.md#release-gates)


## Reviewed M1 operation profile

**Proposed · 2026-11-03; [review O02/O05](../functional_reviews/m1-target-design_2026-11-03.md#O02).**
Use the base FP32 CPU checkpoint as the reference and small as the resource challenger. Verify
actual package/checkpoint/tokenizer/relation-head support before activation. Tagged v2.1.0
[tutorials](https://github.com/fastino-ai/GLiNER2/tree/v2.1.0/tutorial) support the operation choices;
local inference remains unqualified. Rich record cardinality/ambiguity signatures and the
explicit-span bridge require exact-source confirmation; unavailable documentation is not proof
of capability absence.

Schema registry entries bind native serialized schema, domain release, applicability, descriptions,
span conventions, occurrence anchor, limits, required evidence and examples. Derive shape from
owned domain definitions, with authored model descriptions as versioned extraction policy.
Round-trip the selected supported schema representation before reuse; do not create a second
independently mutable family schema. The extraction adapter returns native diagnostics plus
source-bound observations through existing result binding, never directly accepted facts.

Run compatible combined heads over one context where useful, but compare with separate packs
when context or recall differs. Retain per-window outputs before merging. Use explicit
`Classifier` infeasibility handling and preserve `JointIE` candidate/feasibility diagnostics;
shared scores or repeated decoding remain one evidence lineage. Native long APIs cannot create
cross-window edges. A required field without located evidence remains incomplete regardless of
cardinality constraints. Mention attributes cannot recover a suppressed mention or establish
negation scope on their own.

Keep model initialization resident and batch through one run-owned CPU admission route initially.
The source runner does not yet implement the proposed coordinated scheduler. Reuse task fencing,
cancellation and scoped ownership; implement CPU admission and worker supervision as delivery work. No hidden hosted fallback, model swap or adaptive candidate reduction
may silently preserve the same computation identity. Pin any output-affecting batch/precision
behavior and keep retry attempts distinct from logical observation identity.
