# Contextual native CPU FP32 adaptation

2026-11-04. **Approved bounded experiment; scaffold prepared; training not_run.**
This folder owns one experimental full-dataset learning epoch after the contextual-targets
worker supplies its passed, frozen faithful dataset. It owns no runtime/domain change,
production checkpoint adoption, source/reference reauthoring or held-out assessment.

The coordinator approved exactly one epoch over all admitted contextual-targets rows,
batch size1 and gradient accumulation1. The native optimizer retains encoder rate1e-5,
task rate5e-4, weight decay, clipping, linear schedule/warmup and training-only gold-injection
schedule. Seed42 and the native sampler remain explicit. Raw JSON row/dictionary order
is retained in input receipts; the trainer's observed seeded sampling order is recorded.
Batch1 makes every admitted row appear exactly once with no dropped tail. There is no
hyperparameter search, sample repetition or feasibility-only one-step substitute.

The fresh pinned base snapshot is loaded by the current contextual codepoint loader,
using CPU FP32, standard attention,4 intraop threads and1 interop thread. The supported
`ExtractorTrainer(processor=...)` seam reuses the existing evidence-only
`FixedSchemaProcessor`. Original text, field insertion order, complete released schema,
native record specifications and native target masks remain exact. Full conditioning
includes record specifications in addition to encoder/query tokens. Bounds remain4096
source words and schema-conditioned subwords and native max-gold64, with errors raised.
Nothing is sanitized, silently skipped, truncated or expanded. AMP, LoRA, compilation,
extra encoder/candidate capacity, GPU and hosted execution are outside this run.

The original C denominator remains270:14 definitions,56 assertions,32 measurements,
80 table readings and88 formula-context readings. The frozen dataset's represented and
excluded readings remain separate from repeated target instances and example counts.
No excluded reading becomes a negative example. The full ledger and population/exclusion
rules remain owned by `../2026-11-04_m1-contextual-targets/`. Only its protected feature-fit
set1 is consumed; no held-out labels, evaluation data or database access enter training.

Receipts will bind the complete frozen input directory, exact raw dataset bytes,
configuration/profile/base artifacts, processor/runtime/trainer source, every actual
collation's full conditioning and native target digest, sample traversal, finite losses,
gradients, weights and optimizer calls. The final native checkpoint stays isolated under
one unused attempt directory and is not adopted. Existing process-tree sampling captures
cold-start parent/descendant PSS, CPU and thread observations; command status and settlement
are retained independently of numerical success. Failures retain their partial outputs.

Native API/config research used Context7's
[GLiNER2 training tutorial](https://github.com/fastino-ai/gliner2/blob/main/tutorial/9-training.md)
and the installed `gliner2==2.1.0` trainer/data/sampler source. Installed source is authoritative
for the custom processor seam, strict defaults, DataLoader tail behavior and final save.
The current native batch default is2; this experiment explicitly uses1 for bounded long-input
CPU memory. Native learning rates remain unchanged. No evaluation/epoch checkpoint copies
are requested: `eval_strategy="no"`, `save_best=False`; the native final save remains enabled.

Execution is held while the coordinator settles the faithful decoder target population,
additional source neighborhoods and the metadata-only native cardinality/instance challengers.
The scaffold currently consumes the settled fixed-schema processor format1. An adopted change
to that target/processor contract must be reconciled before the epoch; it is not silently
accepted as another input shape. Attempt001's input
validation passed118 rows/205 represented readings with65 exclusions; this is a scaffold/input
check, not selection of that dataset for learning. Its freeze, raw bytes, complete270 ledger,
reload/origin membership, source/package/configuration and field-order checks passed without
importing a model or accessing a database ([receipt](preparation-plan-001.log)).

AST parsing and side-effect-free imports of both scripts passed; neither imported Torch,
GLiNER2 or SQLAlchemy ([receipt](preparation-import-001.log)). Isolated Ruff F checks and CLI
help also passed. These preparation checks do not establish native training behavior.

After the coordinator selects a passed frozen dataset, the intended commands are:

```bash
uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/train_epoch.py plan --dataset docs/design_review/evidence/2026-11-04_m1-contextual-targets/SELECTED_ATTEMPT

uv run python docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py --interval 0.5 --out docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/resources-001.jsonl -- uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/train_epoch.py train --dataset docs/design_review/evidence/2026-11-04_m1-contextual-targets/SELECTED_ATTEMPT --attempt attempt-001

uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/finalize_run.py --attempt attempt-001 --resources docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/resources-001.jsonl
```

`plan` validates frozen files and prints the intended input identity without model loading.
`train` refuses an existing attempt folder and checks each actual collation/forward against
the frozen full-conditioning and native-target receipts. The native sampler may reorder
examples; every admitted sample must appear exactly once. `finalize_run.py` verifies observed
PID/start-tick identities and the runner have settled after the wrapper exits; polling limits
and unavailable PSS remain explicit. It never signals another process.

A complete finite epoch establishes numerical/call/settlement behavior on this admitted
subset. It establishes no M1 completion, quality gate, generalization, calibration or adoption.
