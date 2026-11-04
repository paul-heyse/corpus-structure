# M1 GLiNER operations and CPU runtime

**Target: Proposed; mixed implementation maturity · reconciled 2026-11-03.** This companion
owns the detailed design and completion conditions for M1-06/07. The
[coordinator](../first-production-milestone_2026-11-03.md) owns current package state,
dependencies, findings and assembled acceptance. Implemented foundations below are source
inspection claims at `71a78774`; historical receipts retain their own source/context. Remaining
qualification is Planned. This revision changes plans, not production code or deployments.

**Execution baseline, 2026-11-04:** AC selected acceptance is complete on71a78774/native105;
current controlled candidate/native/reference/consumer tests retain that bounded evidence. M1
accepted lowering, actual CPU fidelity/resources, independent references and release gates remain
open. This companion retains the remaining target; the coordinator owns current package state.

## Basis, foundation assessment and responsibility

Consume the [M1 proposal](../../target-pipeline-design/first-production-milestone.md),
[review O02/O05/O06](../../functional_reviews/m1-target-design_2026-11-03.md#O02) including its
combined/supplemental dispositions, and [GLiNER deployment](../../target-pipeline-design/gliner-deployment.md)
in full. Current source `71a78774` includes `GlinerProfile`, strict `GlinerPack`, mapped reports,
`GlinerWorker` and the retained-only `orchestrate/m1.py` candidate graph. Historical actual offline
FP32 operations retain their recorded profile/source limits; they do not qualify all families.
Consume amended AC owned reads, executable policy admission, shared producer binding and
`ClaimOwner` lifetime. Prior UM functionality/validation remains complete. Original review and
operator-reference provenance remains with the coordinator.

[D4](../../design/D4-method-catalog.md) owns methods and their operation contracts,
[D6](../../design/D6-orchestration-metrics-policies.md) execution/cancellation/policy,
[D1](../../design/D1-knowledge-representation.md) candidate/evidence meaning and
[D2](../../design/D2-schema-and-guidelines.md) releases,
and D5 publication. M1-00 resolves architectural authority changes before dependent effects.
Extend existing operations and run/task fencing rather than introduce a second service, lease
system, workflow engine or candidate store.

The [semantic companion](semantic-contracts-and-evidence.md) owns fields/outcomes/evidence,
[preparation/context](linguistic-preparation-and-source-contexts.md) supplies mapped model input,
[assembly/interpretation](record-assembly-and-bounded-interpretation.md) consumes raw candidates,
and [evaluation/qualification](evaluation-qualification-and-gap-driven-expansion.md) owns independent
release evidence. Runtime admission does not decide semantic acceptance.

| Inspected baseline | Reuse and concrete gap |
| --- | --- |
| [orchestrate/semantic.py](../../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py), `run_source_methods`, `_close_source_resources` | Bound release/source/configuration execution, retained task claims and all-owned-resource teardown. Executable policy applicability and owned reads now govern this route. JIT claims span custody/preparation through synchronized terminal settlement; integrate the CPU profile into this existing owner rather than add a lease loop. |
| [orchestrate/runner.py](../../../python/corpus-structure/src/corpus_structure/orchestrate/runner.py), method registry and source-step grouping | Reuse task/step/result ownership and compatible batching. Reuse the implemented bounded `GlinerWorker` supervisor and candidate producer. Finish aggregate CPU admission/ordinary workload evidence, with no fictional `agent.opus` tasks for CPU extraction. |
| [statistics policy](../../../domains/statistics/policies.yaml) and [methods](../../../domains/statistics/methods.yaml) | The ordinary phase-0 policy remains separate. `orchestrate/m1.py` and `domains/statistics/m1-methods.yaml` supply an explicit retained CPU candidate policy with `policy_propose=False`; finish evaluated acceptance/publication without adding an LLM fallback. |
| [observations.py](../../../python/corpus-structure/src/corpus_structure/semantic/observations.py), `bind_result` | Source-bound immutable results and actual coverage remain the persistence seam; M1-02/03 add family evidence/diagnostic meaning. |
| [analytics.py](../../../python/corpus-structure/src/corpus_structure/semantic/analytics.py), `CapturedPacket`, `AnalysisScope` | Reuse typed columnar input and lazy-result lifetimes for candidate joins and coverage aggregation, with CPU settings coordinated by the run. |

The workload is retained statistics-first English source views with five released family subsets,
mixed prose/table/formula contexts and repeated windows. Share one model residency and reuse
preparation; avoid a pool per pack and a full checkpoint per decoder wrapper. Batch compatible
schema/length work, reduce projected input before inference, and preserve separate logical
observations when physical calls are fused. Guards bound failure exposure but do not establish
ordinary supported CPU/RSS fit; actual retained-source execution must establish that premise.

## M1-06: CPU-only policy, admission and lifecycle

**Remaining target.** Consume M1-02's outcome/provenance/resource contract, M1-00's authority decisions
and M1-01's supported population. Scheduling design need not wait for every pack; working
integration uses actual method/result boundaries. M1-07 consumes its admission and resident-profile
lifecycle, while final publication and consumer adoption stay with M1-11/12.

Extend the implemented retained-only CPU candidate graph through evaluated interpretation and
publication without general LLM extraction. Explicit method allowlists and recorded terminal routing enforce
the boundary; disabling an LLM flag while a fallback still queues `agent.opus` is insufficient.
Do not require completion of an unrelated automated agent journey to run the CPU policy. Reference
authoring/evaluator assistance retain separate identities and are not extraction fallback. Source
readiness, completed extraction and selected published knowledge remain distinct operation results.

Reuse the implemented run-owned `GlinerWorker` with its bounded request/reply frames and one
resident checkpoint/profile; finish integrated admission and recovery evidence.
The worker initializes lazily on first admitted model demand and stays resident while compatible
work remains. Admission accounts for input/context bytes and model work as well as queue count;
a row bound alone cannot bound detached full-text or tensor buffers. Batch only compatible
effective profile/schema/operation inputs with suitable length buckets. Preserve per-context/window
mapping and report identities across batching, and qualify any batch behavior that changes outputs.
Routine method execution occurs outside publication transactions.

One coordinator sets the aggregate CPU/resource policy across spaCy, Torch/BLAS, analytical
engines, preprocessing and inference. Per-library thread caps are inputs to that policy, not proof
of an aggregate bound. Begin without extra model workers or nested preprocessing process pools;
increase only after actual combined memory/thread evidence justifies it. Do not keep a full
corpus of contexts, Arrow buffers, Python candidate objects and model batches live together.
Project/filter in owned analytical scopes, stream bounded batches, and release backing buffers
after their last lazy consumer. DuckDB memory limits are not process RSS limits, and Arrow
row/batch/readahead counts are not byte limits. Finish or abort a result before another operation
reuses its owned connection. These constraints reuse
[DuckDB §§3–5](../../libraries/analytical_infrastructure/duckdb_2.md) and
[Arrow §§2, 4–5, 8](../../libraries/analytical_infrastructure/pyarrow.md), not a new analytics service.

Model residency and safe interruption justify a persistent worker boundary. Reuse the existing
source executor's owned child/supervision patterns where their contract fits: the parent retains
task leases/heartbeat/fencing and database handles; the worker receives typed detached input and
returns typed results. No live connection crosses the process boundary. Use the M1 CPU supervisor already implemented, while retaining its distinct model lifecycle
rather than claiming PDF supervision alone supplies it. The exact
placement/module is local judgment; protection against cancellation during native work is required.

On cancellation or lost ownership, stop admission, cancel queued work, terminate/drain owned
in-flight work as appropriate, join it and perform bounded escalation if needed before propagating
cancellation. Attempt every independent owned closer even when another fails; preserve completed
immutable reports and individual teardown errors. A failed closer remains an owned failure, not
a passed terminal run. Stale workers cannot persist results or publish; existing task fences
remain authoritative. A timeout retains the operation/context/profile and reason, never an
empty-success substitute.

Retry has one owner in the existing task lifecycle. Restart repeats the smallest incomplete
logical unit under the same effective identity, reuses completed immutable reports and creates
new attempt receipts. No separate automatic retry loop in the GLiNER adapter multiplies attempts.
Schema/checkpoint/context changes create new dependent computations. A preparation or inference
failure never replaces the earlier accepted cut. Publication later rechecks its pinned premises
under `consolidate_cut`; no worker holds a database transaction during inference or solving.

The source executor's `maintained_claims` / `ClaimOwner.settle` is the shared lifetime owner.
Claim only imminent execution batches; preparation/custody cannot occur outside renewal. Preserve
short per-task durable completions, synchronized active-set retirement and exact receipt replay
under uncertain commit. Do not keep publication locks while later source preparation blocks.
For interactive agent producers, the shared compatible binding drives policy, queue, packets,
submission, automation and coverage from immutable method/configuration/unit identity (I01).
CPU methods consume their declared operation/configuration contracts; do not force them through
an agent-only binding or fabricate agent tasks. Protocol success,
completed observation and CPU model execution establish different outcomes. AC-CA01's unsupported
public queue mode remains an AC prerequisite; reference adjudication is independently supported.

### Completion conditions for M1-06

Focused tests use controlled workers for admission saturation/backpressure, incompatible-profile
queue separation, child failure, lost lease, cancellation during startup/inference/return,
multiple cleanup failures and restart idempotence. Assert that no LLM extraction task is queued
by the CPU policy and that completed observations survive cancellation before publication.
These controls qualify lifecycle semantics only; a fake worker is never local inference evidence.

Actual CPU runs on the M1-01 retained population must record package/profile, CPU/wall time,
peak process/aggregate memory where applicable, thread settings, queue/batch/context/schema sizes,
candidate counts, cold/warm initialization, cache outcome, timeouts and restart behavior. Choose
the supported resource envelope from this evidence; protective refusals alone do not establish fit.
M1-13/14 owns assembled qualification and denominator accounting. No numerical throughput claim
is made by this plan.

## M1-07: governed deployment profile, schema packs and candidate operations

**Remaining target.** Reuse the existing strict profiles/packs and mapped source reports;
consume M1-03's working observation/field evidence binding, M1-05's working mapped
contexts/routing, M1-06's working CPU worker/admission and M1-01's isolated references. Interface
and pack design may proceed earlier once those contracts settle; real provider qualification
requires their integrated path. Assemblers consume observations, not accepted facts returned by
the model.

### Exact profile and local environment

Use `AutoExtractor.from_pretrained` with `fastino/gliner2.5-base-v1` FP32 CPU as the initial
reference. The reviewed package is `gliner2` 2.1.0; the existing adapter pins the exact
package, immutable checkpoint/tokenizer artifacts and local dependency closure. The base config
inspected by the source review was revision `54785d51df8d86a0d8f2eb212fec15871aad2c4d`, and multi
`cf5593a5d45e3bbf204b9df621b13b1c0cf25ee3`; inspection is not deployment selection or weight
qualification. Retain the hashed offline selected artifact from the existing operation receipts; requalify
changed profiles before activation rather than treating the inspected revision as deployed weights. Python 3.14
compatibility was operator-confirmed in the proposal, but the exact pinned product environment,
selected operations have historical local execution receipts. Complete final-source head/profile
and integrated CPU qualification for the operations actually released.

The deployment manifest binds weights/config/tokenizer, package and dependency versions, word
splitter identity/restoration recipe, operation signatures, enabled heads/effective pool settings,
precision/device, schema/validator/profile versions, window/overlap/threshold/batch policy and
runtime resource controls. Saved weights/config/tokenizer do not save the complete runtime policy.
Use qualified lazy method-boundary imports; do not promise base-package import is Torch-free from
extras metadata. The tagged `local` extra includes PEFT despite lazy adapter imports. `gliner2[local]==2.1.0` is already pinned. Any further selected exact dependency change follows
repository pin policy; this revision performs no installation.

### One owned schema family

Derive pack shapes from M1-02 released role/field definitions and bind authored descriptions,
prompts and development-only examples as versioned extraction policy under the same owner.
The seven packs remain A routing, B definitions, C quantities/comparisons, D formula context,
E qualified assertions, F procedures (shadow), and G tables. The five released families use their
corresponding packs plus shared routing/mentions. No general LLM, hosted fallback or new custom
model pipeline per family is selected.

Admit registry input through strict `SchemaInput`/`Schema.from_dict()` and reject unsupported
keys. Builder kwargs are not equivalent strict admission. Round-trip the supported declarative
subset with `to_dict()` before reuse; bind separately versioned callable `RegexValidator` objects
under the same owner because their executable behavior is not fully serialized there. Domain
invariants stay in the domain release, not this schema builder. Keep field order in the digest
because it is model input.

Select `structure(..., mode="natural", anchor=...)` explicitly. Anchor definitions on the term,
measurements on quantity, assertions on predicate/statement and formula-symbol records on their
declared occurrence role. Prefer extracted scalar `optional_one` even when final domain acceptance
requires the field. `required_one` can force a low-scoring candidate past ordinary field threshold,
and `one_or_more` does not guarantee nonempty output; outer completeness checks remain required.
Native scalar `ABSENT` does not mean source-unstated. Use same-field exclusivity only when one
source candidate legitimately belongs to one instance: exclusive scalars use native assignment,
exclusive lists choose their strongest instance. Shared unit/header/condition evidence remains
reusable. This is not global cross-field/group/window semantic optimization. Pin actual threshold
wiring: reviewed high-level record extraction forwards one threshold into anchor/field/object
decode then formats fields; do not expose independent knobs the selected high-level API cannot
independently apply.

### Operations and diagnostics

Use compact combined `extract` where compatible to co-produce mentions, attributes, classifications
and grouped candidates. `AttributeGroup` observes selected mentions; join attributes by source
occurrence, never array position. Missing mentions require proposal/selection diagnosis before
attribute tuning. A negation attribute needs separately resolved scope. Compare separate packs
when schema competition or context needs differ. Retain per-window observations before highest-score
duplicate merging; local relation endpoints must coexist in a window and native long JointIE
does not create cross-window edges. Word, character, subword, proposal and record capacity limits
remain separately recorded.

`Classifier(model)` and `JointIE(model)` may wrap the already resident compatible boundary model;
verify head/operation support rather than loading another checkpoint automatically. Use multi-label
sigmoid semantics for mixed content roles, with explicit `class_act`, `cls_threshold` and `top_k`.
Softmax requires a genuinely exclusive task. Set explicit Classifier infeasibility behavior:
default `on_infeasible="relax"` cannot authorize record acceptance. Retain feasibility/violations
and actual search limits; JointIE typed local edges/lattices are candidates, not global identity.
Native and outer applications of a constraint share premises/evidence lineage.

Keep exposed raw alternatives, score kind, group/window identity, active checkpoint heads/pool
controls and available suppression/count/abstention signals. Missing diagnostics remain unavailable.
The reviewed base/multi configs use shared pools with `pool_size=192`, `pool_boundary_top_k=32`,
`min_pool_per_query=8`, `candidate_budget=192`, start/end top-k 24 and zero candidate/query attention
layers. Treat those as source observations to check against the actual immutable profile, not
defaults silently imposed on small/later checkpoints. Shared pools couple label recall. Keep
`adaptive_threshold=False` initially; count-guided entity/grouped selection and record formation
are distinct paths. Null/count scores neither certify record completeness nor provide independent
votes or outer unresolved probability.

Literal fields reconstruct against the M1-05 interval map before normalization. Classified enum
outputs retain classification and record association: anchor offsets or `(0,0)` never become
literal enum evidence. Preserve cue anchors independently. Pin GLiNER word splitting separately
from spaCy and transformer tokenization, restore it after `save_pretrained`/reload, and prevent
mutation during incompatible in-flight work. Custom splitter tuples `(token,start,end)` refer
to original text; combining marks, lowercasing and zero-width joiners need exact coordinate tests.
`SchemaTransformer.transform_record()` is a preprocessing seam, not inference, and can append
punctuation; return its synthetic delta to the context map and refuse unmappable anchors.

### Reuse without changing meaning

Distinguish resident weights, reusable annotation/context preparation, model encodings, scores,
decoded candidates and interpretation. They have different validity scopes. Observation reuse
binds source/context/schema/operation/weights/adapter/tokenizer/splitter/precision/configuration
and actual consumed dependencies. Prompt/example changes invalidate schema-conditioned encoding.
Shape-valid hidden states do not establish provenance: exact encoded batch, query/mask/order and
profile must match. Prefer combined public operations and short-lived scoped reuse with a concrete
consumer; no persistent generic hidden-state cache is selected.

For `Classifier.score`/`decode`, re-decode only with a matching compiled-schema fingerprint.
Supported search/configuration or `active` selection changes can reuse scores; changed schema
constraints alter that fingerprint and require public re-scoring. JointIE lattice reuse has its
own qualified contract, not interchangeable Classifier scores. Re-decoding is one evidence
lineage. Changed weights/adapter invalidate affected states; future adapter switching requires
exclusive admission across every in-flight operation/cache using the old adapter. It is not a
current M1 adapter-training requirement.

### Completion conditions for M1-07

Focused adapter/schema/map tests cover strict admission/round trip, validator binding, field-order
digest changes, cardinality versus outer missingness, shared evidence under exclusivity, misleading
enum offsets, splitter restoration/Unicode, synthetic punctuation, fingerprint rejection, missing
head/import failure, explicit infeasible/empty/truncated/error dispositions and retry identity.
Use independently specified source positions and expected meanings. These controls do not
establish checkpoint accuracy or that a low-level operation executes.

Actual local FP32 CPU qualification must run retained statistics examples for every selected
operation/head through mapped contexts, bound observations and the worker. Cover several records
per passage, nested/long spans, repeated strings, note/header sharing, formula context and explicit
no-output/infeasible/truncated/resource/error cases. Record the exact resolved profile and raw
per-window outputs/available diagnostics. Compare base/small, combined/separate and broad/routed
when needed for release choices using correct complete records and evidence, plus CPU/RSS effects.
Small is a resource challenger, not a silent fallback. An operation that cannot run or has no
required head remains blocked by that named prerequisite; a mocked response is never passed.
Final five-family gates and consumer journeys belong to M1-13/14.

## Conditional investigations: choose by failure stage

| Trigger and question | Settling evidence, branches and activation boundary |
| --- | --- |
| Natural grouping misses a real anchor or anchors are unstable | Compare natural plus deterministic assembly with `mode="latent"` when another field can seed, and `mode="anchorless"` when no reliable field identifies instances. Evaluate full records/qualifiers at matched precision or coverage and actual CPU. Promote per pack only; no learned slot identity and no inference-only resizing of trained `record_instance_queries`. |
| Located rule/parser spans are absent from native proposals | Qualify `score_explicit_spans()` with exact half-open model-word alignment under the same encoding/query/mask contract. Inspect returned source mapping, scoring and downstream full records. Shared-pool injection consumes capacity and can raise: fail explicitly, or separately identify smaller contexts/qualified partitions of requests. Smaller batch size alone cannot repair per-document overflow. Never round spans or discard requests as negatives. |
| Dense-span losses persist inside an adequate candidate pool on supported tasks | Compare `adaptive_threshold=True` with baseline; retain its union of threshold and count-guided selections, candidate effects and full-record false positives/CPU. Keep default off without a net evaluated benefit. It cannot recover missing boundaries/truncated input or become a record-count certificate. |
| Candidate capture is adequate but local attachments remain wrong | Compare typed `JointIE` with native records and deterministic assembly using justified relation constraints and fixed source scope. Preserve feasibility/lattice/search diagnostics. Adopt only for that local gap; cross-window identity remains outer interpretation. |
| CPU or live working set fails the supported envelope | Compare smaller checkpoint first under family gates, then demonstrated relevant batching/internal execution strategies or BF16/FP16 against FP32. `quantize("bf16")`/`quantize("fp16")` are dtype changes, not integer compression. `export_mode` is an internal boundary execution strategy, not ONNX. Shape-changing representation/attention/pool modules must match saved weights. |
| Persistent measured gap survives schema/context/budget repair and suitable labels exist | Route specialization as a bounded separately selected action: native `TrainingDataset.validate(raise_on_error=False)`, `stats()`, explicit offset/negative/nested supervision, and injection-off `dry_run_recall_steps` diagnose proposal loss. Default `on_capacity_exceeded="raise"`; any skip/truncation keeps denominators/reasons. Compare supervised/LoRA/DoRA only after data/target selection; do not make training a default M1 dependency. |

For specialization, `occurrence_policy` is ambiguous training-target policy, not runtime
coreference; prefer explicit half-open occurrence offsets. A literal-entity helper such as
`find_unalignable_entities()` is not a universal structured validator. Pin
`dedupe_contained_entity_spans` so nested gold is not silently removed. Injection-off diagnostics
perform no ordinary weight update and cannot qualify pretrained accuracy or replace family gates.
NCCL/DDP availability does not imply a CPU distributed route. Decide-340M, Decide-1B, multilingual,
safety/PII and hosted/Transformers interfaces remain scoped follow-ons requiring their own demand,
head/parity and population evidence; none is automatic fallback or part of five-family delivery.

## Mechanism sources and evidence limits

Context7 on 2026-11-03 resolved `/fastino-ai/gliner2` and confirmed boundary natural-anchor and
combined/long-operation orientation; its returned examples track `main`, so they do not qualify
the selected exact tag or the low-level bridge. Carry the reviewed consequential tagged sources:
[schema](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py),
[record specifications](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/records.py),
[record assignment](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/records.py),
[boundary preprocessing](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/boundary_preprocessing.py),
[boundary engine](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/engine.py),
[Classifier engine](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/classification/engine.py),
[fingerprint compiler](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/classification/compiler.py),
[JointIE engine](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/joint_ie/engine.py), and
[hidden-state admission](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/base.py).
The [deployment supplemental reconciliation](../../target-pipeline-design/gliner-deployment.md#supplemental-capability-integration)
locates the immutable checkpoint configurations and explains source-level limits.

This document preserves those reviewed source conclusions and plans exact-environment execution;
it does not newly certify upstream code or checkpoint quality. Remaining checks and comparisons above
are **Planned**; earlier adapter/actual-operation receipts retain their bounded applicability. Product tests, dependency changes, model inference, runtime probes and database
operations for this plan-writing contribution are **not_run**. Use the coordinator's package
state and evidence links for subsequent execution and qualification.

The [AC improvement review](../../plan_improvement_reviews/audit-closure_2026-11-03.md) I01–I03
and [AC completion audit](../audit-closure_2026-11-03.md#12-completion-audit--claimed-integrated-slices)
constrain the reused foundation. The coordinator alone owns their M1 dependency impact and
current evidence applicability. New checks are selected for unresolved obligations; historical
passes are not promoted to final-source or whole-milestone qualification.
