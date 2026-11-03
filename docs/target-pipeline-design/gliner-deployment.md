# GLiNER2.5 deployment

## Implemented private adapter constraints

**Implemented; bounded Tested, 2026-11-03.** The
[private runtime evidence](../design_review/evidence/2026-11-03_m1-gliner-runtime/README.md)
establishes one exact local combined CPU profile and retained-context literal mapping. It does
not establish released packs, family quality, aggregate fit or an assembled M1 release.

- Load the verified immutable local snapshot directory. Installed AutoExtractor does not forward
  Hub revision options to every loader; the first repo-name attempt is retained with narrowed custody.
- Bind the exact loader file closure. Additional tokenizer files can alter loading; the initial
  profile admits only the five qualified artifacts and encoder configuration directory.
- Reject duplicate structure field names before native compilation, and require report/pack
  fingerprint equality before field interpretation. Native schema admission alone permits a
  duplicate-name classification/literal mismatch.
- Keep cache paths and native `_name_or_path` out of computation identity while retaining them in
  provenance. Canonicalize named artifact hashes; preserve schema order that conditions extraction.
- Delegate preprocessing to the native transformer and retain its actual synthetic suffix and
  distinct word/schema-conditioned-token limits. Source mapping refuses synthetic material.
- Bound metadata and complete finite request/reply frames, not just text/raw output. The current
  serial owner admits one live batch and zero queued batches, with fail-fast saturation. Aggregate
  spaCy/Torch/DuckDB admission remains a separate integration obligation.
- High-level pool/count/null/suppression diagnostics remain unavailable. Classified values do not
  become literal quotes merely because native output contains offsets.

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
| `extract_json` and `structure(...).field(...)` | Natural, latent or anchorless grouped record candidates | Required evidence, normalization, semantics of missing fields and complete-record validation |
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

Use natural record mode with an explicit anchor as the initial profile; source occurrence identity
is independent of native instance slots. Anchor definitions on the defined term, measurements on the quantity, qualified assertions on the predicate or statement, symbols on their declaration or occurrence, and procedure steps on an action or list item. Keep the required acceptance fields from the [record contracts](first-production-milestone.md#products-and-scope). The grouped candidate may remain incomplete. Cardinality controls decoder output and cannot establish that a field is stated. Preserve original strings and offsets before numeric/unit normalization. Keep classified enums such as rated distinguishable from literal extracted text.

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
local inference remains unqualified. The supplemental-source reconciliation below establishes
record cardinality, occurrence-policy and exclusivity interfaces at source level. Their checkpoint
quality and the low-level explicit-span bridge still require execution qualification.

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


## Supplemental capability integration

**Proposed revision · 2026-11-03.** Reconciles the user-supplied
[supplemental reference](../libraries/parsing/gliner2.md#gliner25--supplemental-capability-reference),
§§1–8, with [review O02/O05/O11](../functional_reviews/m1-target-design_2026-11-03.md#O02).
Source availability, enabled checkpoint modules, learned quality and released runtime behavior
remain separate claims. No new model, parameter setting or training run is activated by this page.

### Record formation and native assignment

Use `.structure(..., mode="natural", anchor=...)` explicitly, never a silent first-field anchor.
Field order is model input and stays in the schema digest. Native fields use `cardinality` values
`optional_one`, `required_one`, `zero_or_more`, `one_or_more`, with `exclusive=True` only where a
single source candidate really belongs to one instance of that field. Scalar `ABSENT` is a model
assignment option, not proof of source absence. Prefer `optional_one` for extracted scalar roles, even when
the domain requires them for final acceptance, so decoding can retain a missing role. In the reviewed decoder `required_one` can force a
low-scoring candidate past the ordinary field threshold, while `one_or_more` is not an enforced
nonempty guarantee. Outer completeness/quality checks must not rely on those names. Outer field states still distinguish missing
candidate, unstated, inapplicable and unresolved, and required fields still need located evidence.

Delegate supported within-invocation assignment to the record head before considering custom
reconciliation. Exclusive scalar fields use a linear assignment route; exclusive lists allocate
a candidate to its strongest instance. Neither establishes arbitrary joint semantic optimality.
For two measurements in one passage, exclusivity can prevent reusing the same value occurrence;
a shared unit/header/condition can legitimately support both records and must not be exclusive
merely because it is textually present once. Scope is the same field within one record group's selected instances, not other fields/groups,
every occurrence of an equal string or all windows. Outer cross-window grouping remains necessary. Pin threshold wiring as well as advertised knobs:
the reviewed high-level engine passes one record threshold into anchor/field/object decode
arguments, followed by field formatting filters. Do not promise independently tunable high-level
thresholds merely because lower-level configuration fields exist.

Support registry declarations for `mode="latent"` and `mode="anchorless"` as conditional grouping
challengers. Try latent grouping on a documented missed-anchor cohort when another field can seed
the record; try anchorless only when no reliable field consistently identifies instances. Compare
with natural grouping and deterministic assembly on complete records and matched precision or
coverage. Promotion is pack-specific, with checkpoint/learned-capability and CPU evidence. These
modes do not relax required evidence. Latent seeds still require detected candidates; anchorless
queries still draw field values from candidates and have trained instance capacity. Do not resize
`record_instance_queries` as an inference-only recall knob. Persist source-based occurrence
identity and candidate membership, never learned query-slot indices as durable record identities.

`occurrence_policy` concerns ambiguous training targets, not inference-time coreference. Prefer
explicit half-open offsets for repeated strings. Where text-only supervision is unavoidable,
choose a declared policy (`error_on_ambiguous` for curated scalar targets; intentional latent
matching only for explicitly weak labels). `all` and `latent_all` retain multiple scalar matches
in the reviewed preprocessing; they are not evidence of two distinct runtime resolution methods.

Primary interfaces: tagged [schema](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py),
[record specifications](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/records.py),
[record head](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/records.py),
[boundary preprocessing](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/boundary_preprocessing.py).

### Checkpoint-aware candidate recovery

Capture effective checkpoint head configuration, not `BoundaryHeadSettings` defaults. The supplied
base/multi configurations use shared pools (`pool_size=192`, `pool_boundary_top_k=32`, `min_pool_per_query=8`,
`candidate_budget=192`, start/end top-k 24), with candidate/query attention layers zero. Treat
these as reviewed configuration observations requiring an immutable checkpoint revision at
activation, not settings automatically applied to small or a later revision. Shared pool coverage
can couple pack labels: broad versus routed schemas can change which candidates survive even
when the text is identical. Retain effective schema and pool controls with diagnostics. Research resolved base revision
[54785d51…](https://huggingface.co/fastino/gliner2.5-base-v1/blob/54785d51df8d86a0d8f2eb212fec15871aad2c4d/config.json) and multi revision
[cf5593a5…](https://huggingface.co/fastino/gliner2.5-multi-v1/blob/cf5593a5d45e3bbf204b9df621b13b1c0cf25ee3/config.json); these inspected configurations are source evidence,
not automatically selected deployment weights.

The base/multi configuration enables learned abstention/count heads while leaving
`adaptive_threshold=False`. Keep that default initially. Where the selected public/qualified
surface exposes abstention and Poisson log-rate counts, retain their score meaning and common
model lineage; neither proves absence, gives record counts, nor supplies independent evidence.
In the reviewed engine, null suppression applies to entity tasks and count-guided decoding
follows the grouped candidate path; the native record head has its own formation/selection route.
Evaluate `adaptive_threshold=True` only as a dense-span retention challenger on supported tasks: it unions threshold
hits with count-guided selections within the existing candidate pool. It cannot invent boundaries
or recover truncated context. Promotion requires new correct whole records without unacceptable
false positives and with recorded candidate/CPU effects.

For a deterministic parser's located spans missed by proposal generation, retain a conditional
`score_explicit_spans()` bridge. Convert mapped character spans into exact half-open model-word
spans using the same splitter/encoding/query contract. A mismatch remains unresolved; do not round
boundaries silently. In shared-pool mode, injected spans consume pool capacity and can raise when
they do not fit. Fail explicitly or retry a separately identified smaller context or qualified partition of explicit-span requests; reducing batch size alone does not fix per-document pool overflow. Never
silently discard requests or label a failed rescore negative evidence. Shared-state reuse requires
identical effective encoding and lifecycle. No generic hidden-state cache is introduced.

Shape-changing attention, representation, pool organization and record-query modules must match
saved weights. Only source-qualified runtime controls are tunable without a new checkpoint;
capacity and compatibility still require checks. `export_mode` selects an internal streaming/
vectorized boundary execution strategy, not ONNX or another deployment runtime. Preserve the
checkpoint path initially; compare alternate strategies only on a demonstrated working-set gap.

### Schema conditioning and coordinate-safe lifecycle

For routing, version label descriptions, `prompt`, development-only `examples`, `class_act`,
`cls_threshold` and `top_k`. Mixed roles use sigmoid/multi-label semantics; a mutually exclusive
schema must justify softmax. Try concise descriptions/examples before adding a specialist model.
Examples never come from calibration/final references, and prompt/example changes invalidate
schema-conditioned encodings as well as outputs. Route registry inputs through strict `SchemaInput`/`Schema.from_dict()` validation; permissive
builder kwargs are not equivalent admission. Round-trip the supported declarative subset with
`to_dict()`. Callable `RegexValidator` objects are not fully serialized there: retain separately
versioned validators under this same registry owner and qualify their binding. Keep domain
validation separate and reject unsupported keys instead of repairing them silently.

Enum field choices are classified values, not necessarily literal source substrings. The reviewed
record formatter can attach record-anchor offsets (or `(0,0)` without an anchor) to enum outputs.
Never interpret these as literal field-value evidence or validate them by pretending the selected
label occurs there. Preserve classified status, record association and independently located cues;
unavailable cue evidence remains unavailable. Literal spans must still reconstruct exactly.

Pin the GLiNER word splitter independently of spaCy tokenization and transformer tokenization.
A custom splitter returns `(token, start, end)` against original text. Persist its identity/recipe,
restore it explicitly after `save_pretrained`/reload, and prohibit mutation on a worker serving an
incompatible in-flight profile. Unicode lowercasing, combining marks and zero-width joiners need
coordinate tests; equal normalized strings do not identify equal source occurrences.

`SchemaTransformer.transform_record()` is a public inspection/preparation seam when separating
preprocessing is useful. It does not perform inference and may append terminal punctuation.
Account for that synthetic material in the existing context map and refuse unmappable field
anchors. Use native preprocessing once rather than recreating it independently. A saved checkpoint
contains weights/config/tokenizer, not a complete deployment manifest or assurance that runtime
splitter state was restored.

Use the qualified local inference dependency profile and lazy method-boundary import. The tagged
`local` extra includes PEFT; lazy adapter imports do not mean that extra omits the dependency. Do not
assume base-package import is Torch-free from optional-dependency metadata; verify the exact
resolved environment. `quantize("bf16")` and `quantize("fp16")` are dtype conversions, not integer
compression, and remain challengers to FP32 CPU qualification. Hosted builders do not expose all
local record/schema semantics; partial results/retry APIs provide no local parity or automatic
fallback. Native Transformers metadata similarly does not establish Classifier/JointIE parity.

### Specialization and additional checkpoints

If a persistent gap justifies training, use native dataset validation/statistics and explicit-span
supervision. Audit task/label balance with `stats()`, preserve explicit negative-label meaning and
check alignment before specialization. `find_unalignable_entities()` is a helper for literal entity
values, not a universal structured-offset validator. Pin `dedupe_contained_entity_spans`: its
same-query contained-span reduction can erase intended nested supervision despite correct offsets;
partial crossing overlaps and cross-label nesting are distinct cases. `TrainingDataset.validate(raise_on_error=False)` is the reviewed signature, not the
stale `strict=True` example. Case-insensitive surface matching alone cannot establish exact
occurrence alignment. Use native injection-free proposal-recall diagnostics (`dry_run_recall_steps`,
no gold injection) to distinguish discovery from scoring, and assess downstream records separately.
The diagnostic path returns without ordinary weight updates. Its built-in recall gates do not
replace family release criteria or certify pretrained accuracy.

Default specialization to explicit capacity failure (`on_capacity_exceeded="raise"`) and strict
numerical/data error handling; any skip/truncation policy needs retained sample denominators and
reasons. Gold injection schedules, proposal losses and capacity budgets are training settings,
not inference-time recall guarantees. LoRA/DoRA through PEFT, objective schedules and distributed
training are conditional tools for that selected specialization, not M1 dependencies. NCCL/DDP
support does not imply a CPU distributed route or fit the current inference-only CPU scope.

Distinguish 340M English Decide, span-architecture Decide-1B and multilingual boundary Decide by
exact checkpoint. A larger classifier is not a replacement for boundary record/relation heads.
Safety/PII and combined guardrail checkpoints can support a future sensitive-source export or
agent-input workflow if explicitly requested and evaluated; they do not improve the current
statistics record target by default. Detection, redaction and deterministic security guarantees
are separate. Keep these as scoped follow-ons without a new safety pipeline or hosted service.


### Composed execution without duplicate model residency

The original reference's combined extraction, attributes and score/decode APIs compose with the
supplemental assignment and schema facilities. Prefer `extract` with one compatible compact schema
for co-produced entity/attribute/record candidates. Join role attributes to grouped fields by source
occurrence, never array position; scores from shared heads remain dependent. Existing outer
interpretation reconciles units, qualifiers and cross-context identity. A JointIE graph is a
separate local candidate mechanism, not a globally consistent extension of every combined head.

`Classifier(model)` and `JointIE(model)` can wrap one already resident compatible boundary model,
avoiding an automatic second checkpoint load. Qualify operation/head support and scheduling for
the exact profile. Shared weights do not establish compatible encoder inputs. Batch/hidden-state
paths validate tensor shape without proving schema/token provenance, so the adapter owns exact
input, query, mask/order, weight/adapter, precision and splitter compatibility. Retain only scoped
states with a useful consumer; no persistent generic tensor cache follows from API availability.

For fixed-evidence classification comparisons, re-decode only when the score fingerprint matches
the compiled schema. Supported search/configuration and `active` selection changes can reuse those scores; changes to
schema constraints also change that fingerprint and require public re-scoring. JointIE score
lattices have their own qualified decode contract, not an assumed interchangeable Classifier score
format. Schema-conditioned score reuse and source-only inference reuse are different promises.

If later adapters share base weights, exclusive admission protects load/unload/switch and every
in-flight operation or cached state using the old adapter. Pin base, adapter target modules and
PEFT format with splitter/schema/precision. Saving and reloading does not establish concurrency
isolation. A checkpoint-only change or new adapter invalidates affected encoding/scoring results.


For “Group A: mean 12, SD 3; Group B: mean 10, SD 2,” the compact schema can propose entities,
role attributes and grouped records together. Associate attributes with matching source mentions,
not automatically every record field. Native exclusive value assignment avoids duplicate same-field
use; shared population/condition notes remain reusable. If capture is adequate but attachments
are wrong, compare a typed local JointIE formulation against native records before custom graph
repair. If anchors fail, compare latent formation; if boundaries fail, diagnose proposals and use
the qualified deterministic-span bridge. These are different failure/action routes and not a
mandatory stack of decoders. Whole-record acceptance still includes scope and qualifications.

Sources for composed reuse: tagged [classifier](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/classification/engine.py),
[fingerprint](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/classification/compiler.py),
[joint constructor](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/joint_ie/engine.py),
[hidden-state admission](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/base.py).
Tensor shape validation is useful but does not supply the missing input-identity checks.
