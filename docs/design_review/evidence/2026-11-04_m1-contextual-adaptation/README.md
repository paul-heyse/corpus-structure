> **Stopped by operator,2026-11-04.** Attempt002 ended after101completed optimizer updates,
> with102finite forwards before KeyboardInterrupt during the next backward call. Wrapper exit130;
> all three observed PID/start identities absent. No final checkpoint/result or adoption, no restart.
> [operator-stop.json](attempt-002/operator-stop.json) and the retained failure/external-settlement
> receipts own the terminal outcome; any preparation/in-progress prose below is historical.

# Contextual native CPU FP32 adaptation

2026-11-04. **Approved bounded experiment; actual one-epoch training in progress.**
`attempt-002` consumes the finalized contextual-targets/attempt-004:261 rows,239 unique
decoder-visible C readings, all original270 ledger entries, with31 exclusions retained.
The239 decoder readings differ from226 readings with a primary-custody route; neither count
establishes assembled capture. Dataset SHA256 is
`a98a7cdaaae94a755ca61441770ef7551a9572d9e4497a3ac40288d7b3f35a2b`.
The exact frozen format2 processor is15494 bytes with SHA256
`b0ecf2152aebfe4023496b8a01fc96d7d24c35b9a6a6d6b14a00a7a24ea94d95`.
Current production profile is `78871269cc270839a432a0d7a36cbc09e325de1cc87f64e6fe6bae215514e3e7`,
bound to completed source/annotation run22/finalcut23 and release
`release:407d64d35766538fcb4d270f0a4e0ad5192a364349e4a667a84bc3c2a5b6bd25`.

Failed `attempt-001` remains retained: two finite optimizer updates, then an evidence-hook
error on the native `records=None` representation of a genuine-zero row. No checkpoint
was produced or adopted. The hook was corrected to accept that representation only when
the independent frozen target count and actual native record-mask count are both zero;
two zero representations, one positive case and five invalid-membership refusals passed
pure controls. `attempt-002` starts from the untouched pinned base, never those partial
weights. Failed001's external settlement found all three observed process identities absent.

This folder owns one experimental full-dataset learning epoch from that passed frozen dataset.
It owns no runtime/domain change,
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
includes record specifications and original native schemas in addition to encoder/query tokens.
The exact format2 wrapper preserves definition fragments as distinct native values and latent
assertion formation. `dedupe_contained_entity_spans=False` prevents contained-span sanitation.
Bounds remain4096 source words and schema-conditioned subwords, native max-gold64 and
candidate/training-candidate budgets192, with errors raised.
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

The coordinator explicitly selected finalized004 and authorized the one epoch after actual
v2 native interface and warm request cancellation checks passed. The runner uses the actual
production registry constructor and the immutable executed format2 processor snapshot.
The earlier format1 scaffold's input
validation passed118 rows/205 represented readings with65 exclusions; this is a scaffold/input
check, not selection of that dataset for learning. Its freeze, raw bytes, complete270 ledger,
reload/origin membership, source/package/configuration and field-order checks passed without
importing a model or accessing a database ([receipt](preparation-plan-001.log)).

AST parsing and side-effect-free imports of both scripts passed; neither imported Torch,
GLiNER2 or SQLAlchemy ([receipt](preparation-import-001.log)). Isolated Ruff F checks and CLI
help also passed. These preparation checks do not establish native training behavior.

The actual selected commands (reuse requires unused output names and coordinator scope) are:

```bash
uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/train_epoch.py plan --dataset docs/design_review/evidence/2026-11-04_m1-contextual-targets/attempt-004

uv run python docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py --interval 0.5 --out docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/resources-002.jsonl -- uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/train_epoch.py train --dataset docs/design_review/evidence/2026-11-04_m1-contextual-targets/attempt-004 --attempt attempt-002

uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/finalize_run.py --attempt attempt-002 --resources docs/design_review/evidence/2026-11-04_m1-contextual-adaptation/resources-002.jsonl
```

`plan` validates frozen files and prints the intended input identity without model loading.
`train` refuses an existing attempt folder and checks each actual collation/forward against
the frozen full-conditioning and native-target receipts. The native sampler may reorder
examples; every admitted sample must appear exactly once. `finalize_run.py` verifies observed
PID/start-tick identities and the runner have settled after the wrapper exits; polling limits
and unavailable PSS remain explicit. It never signals another process.

A complete finite epoch establishes numerical/call/settlement behavior on this admitted
subset. It establishes no M1 completion, quality gate, generalization, calibration or adoption.
