# M1 native one-step numerical feasibility

Status: active, 2026-11-04. Numerical outcome **not_run** until the bounded native
process completes and its retained result is inspected. No efficacy, calibration,
held-out assessment or product adoption is claimed.

The authorized experiment uses the exact existing local GLiNER2.5 checkpoint and
gliner2==2.1.0, offline, CPU4/parent1/interop1, full FP32, no LoRA, one complete safe
feature-fit positive, batch1 and exactly one optimizer step. It does not read
held-out labels or predictions, write the database, or change product policy.

`one_step.py` selects the smallest previously verified native input by subword count
from the frozen alignment dataset. Native strict collation preserves all targets;
raw already-validated dictionaries bypass the trainer's sanitizing loader. Native
description/prefix variation is retained in the actual-forward batch receipt.

Command in progress:

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py --interval 0.5 --out docs/design_review/evidence/2026-11-04_m1-training-feasibility/resources-001.jsonl -- uv run python docs/design_review/evidence/2026-11-04_m1-training-feasibility/one_step.py
```

The existing external process-tree sampler captures the execution separately.
The native trainer has no no-save switch and writes its final checkpoint; the
authorized output remains isolated under `run-001/native/final/`. It is not selected
by product configuration. Root owns final maintenance and broader acceptance.
