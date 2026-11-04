# M1 native one-step numerical feasibility

Verified 2026-11-04. Standing: **Tested**, bounded numerical feasibility only.
Outcome **passed**: exactly one native forward/backward and one AdamW optimizer
update completed on CPU in FP32. No efficacy, calibration, held-out assessment or
product adoption is claimed. Native candidate discovery after adaptation remains
**not_run** by this worker.

The authorized experiment uses the exact existing local GLiNER2.5 checkpoint and
gliner2==2.1.0, offline, CPU4/parent1/interop1, full FP32, no LoRA, one complete safe
feature-fit positive, batch1 and exactly one optimizer step. It does not read
held-out labels or predictions, write the database, or change product policy.

`one_step.py` selects the smallest previously verified native input by subword count
from the frozen alignment dataset. Native strict collation preserves all targets;
raw already-validated dictionaries bypass the trainer's sanitizing loader. Native
description/prefix variation is retained in the actual-forward batch receipt.

Command, **passed** (exit0), with the existing external sampler:

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py --interval 0.5 --out docs/design_review/evidence/2026-11-04_m1-training-feasibility/resources-001.jsonl -- uv run python docs/design_review/evidence/2026-11-04_m1-training-feasibility/one_step.py
```

The existing external process-tree sampler captures the execution separately.
The native trainer has no no-save switch and writes its final checkpoint; the
authorized output remains isolated under `run-001/native/final/`. It is not selected
by product configuration. Root owns final maintenance and broader acceptance.

## Numerical receipt

[run-001/result.json](run-001/result.json) retains the native trainer result,
observed hooks, parameter digests and complete checkpoint file hashes. Actual
root-module forward count, optimizer pre-hook count and optimizer post-hook count
were each1; every populated optimizer state had step1. The loss was
**441.7489929199219**, required gradients and was finite. All302 gradient tensors
were finite;279 had a nonzero gradient. The native clipped-gradient norm was finite.
**302** named parameter tensors changed, and all final parameters were finite.
Parameter change includes native weight decay; a changed tensor alone does not
establish useful learning. The model contains193,581,591 parameters.

The single sample was chosen before model execution by minimum verified native
subword count and ordinal among the48 safe positive rows. It is alignment ordinal16,
source23/context97, one complete formula-context C record from protected pass24,
with641 subwords. This choice bounds numerical work; it is not selected by a model
score or by apparent semantic ease. Its exact context, pack, gold and source/word
mapping origins are retained in [run-001/selected-origin.json](run-001/selected-origin.json).

The native training collator actually retained every description in this fixed-seed
realization. All ordered role queries and raw schema metadata survived; no
sanitization, truncation, incomplete-reading masking, capacity expansion or invented
negative was used. The actual native batch is
[run-001/actual-forward-batch.json](run-001/actual-forward-batch.json). Native
description selection and choice-prefix ordering still vary by seed; this passing
realization is not a claim that the default trainer always reproduces exact
inference conditioning. The broader alignment's37 multi-record prefix expansions
and full-pack no-record-negative gap remain open.

The native trainer does not expose a no-save switch and unconditionally saved the
final full checkpoint, reported746.5MiB. Existing disk availability was checked
read-only before execution. The base snapshot was not modified. The resulting
candidate is isolated under `run-001/native/final/`; no product registry points to it.
Full optimizer state is not claimed to be a resumable checkpoint.

The native configuration fixed `max_steps=1`, batch1, accumulation1, no eval,
CPU4/parent1/interop1, full FP32, no LoRA/AMP, seed0, native strict errors, unchanged
gold/candidate budgets, and no max-length truncation. The already-validated raw
dict bypassed only the loader's sanitizing rewrite. Native default encoder/task
learning rates1e-5/5e-4 and weight decay0.01 were used for this numerical check,
with a constant scheduler and no warmup. These are not fitted or recommended
efficacy hyperparameters. No diagnostic recall forward or extra optimizer step ran.

## Resource scope and byte custody

The script's timed span was6.17s, including model loading, parameter hashing and
checkpoint writing. [resources-001.jsonl](resources-001.jsonl) sampled the separate
wrapped process tree for10.01s: peak complete sampled PSS5,235,438KiB, peak summed
RSS5,260,384KiB, observed CPU delta16.33s, and peak14 tree threads. Those thread
counts include launcher/runtime helpers; the model reported Torch4 and interop1.
One of20 samples lacked complete PSS. Short-lived or reparented processes may be
missed, and summed RSS double-counts shared pages. Aggregate resource qualification
is **not established** by this one-sample experiment.

[run-001/input-receipt.json](run-001/input-receipt.json) captured the executed script
SHA256 at launch, input hashes, exact checkpoint profile, package versions and
selection policy. The byte-identical executed source is preserved separately as
[run-001/one-step-executed.py.txt](run-001/one-step-executed.py.txt), SHA256
`960a666d8d095b4fa74fffc4f3c42cf0e64e1e2fe0a7332d7ccaef83430c68ea`.
The `.txt` suffix preserves the executed bytes across later root formatting of the
working script. Its hash was explicitly compared with the launch receipt before
handoff. Raw before/after parameter hashes retain the update observation.

Context7-first GLiNER2 research and exact installed training sources were already
read for the alignment. PyTorch hook documentation was additionally resolved through
`/pytorch/pytorch/v2.14.1` before inspecting installed
`torch/optim/optimizer.py`. Optimizer hooks only observed gradients/state and
returned no modified arguments. No native library or trainer method was patched.
The actual GLiNER2 processor source is `gliner2/processor.py`.

No held-out/calibration labels or predictions, DB writes, provider/PDF/OCR work,
product edits, tests, policy fitting or adoption occurred. A changed candidate
universe needs separately scoped injection-off candidate assessment and protected
independent grading before any benefit claim.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [One native CPU FP32 optimizer step on a faithful source record](records/m1.native-one-step.json) | M1-07 | passed | — | 2026-11-04 |
<!-- evidence-index:end -->
