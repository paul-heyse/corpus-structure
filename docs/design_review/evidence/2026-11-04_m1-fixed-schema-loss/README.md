# Fixed-schema native loss and one-step processor integration

**Tested · 2026-11-04.** Three actual CPU FP32 loss-only forwards passed with finite native losses
and no weight changes. After a bounded inactive-cap integration correction, **exactly one** native
trainer forward/backward/AdamW step passed on a fixed same-family positive/zero batch through the
supported `ExtractorTrainer(processor=...)` seam. This is numerical and callable integration evidence.
It establishes no useful learning, recall, accuracy, calibration, generalization or product adoption.

All work stayed in this evidence folder. Installed `gliner2==2.1.0`, the exact existing local base
checkpoint and its whitespace splitter were retained. CPU model threads=4, parent numerical
threads=1, interop=1, FP32, offline, no LoRA/AMP, no sanitation and no actual truncation. No native
source, production, tests, plans, database, PDF or held-out data were changed or used. Native final
checkpoint writes were explicitly authorized and remain isolated under `run-003/native/final/`.
The coordinator owns accepted records, target-contract changes and broader integration.

## Explicit supported processor seam

[fixed_schema_processor.py](fixed_schema_processor.py) is an experimental composition wrapper
passed via the native trainer's `processor=` constructor argument. It does not replace or patch
native trainer, collator, model or loss methods. Native `ExtractorDataset` supports raw dictionaries;
with `validate_data=False`, the actual loader preserved the separate payload's values and insertion
order. The payload contains the frozen released schema and independent target records, with explicit
experimental format and identity digests. This is an evidence-only adapter contract, not a change to
stock JSONL/`InputExample` semantics or an adopted product input format.

The wrapper exposes `collate_fn_train`, `collate_fn_inference` and `change_mode`. It prepares the
frozen released `Schema` through native deterministic inference preprocessing **without gold**,
then maps the separately validated labels into that concrete word-token/query frame. It calls native
`build_boundary_batch_metadata(..., build_targets=True)` and attaches its native targets/specifications
to the native `PreprocessedBatch`. There is no custom loss, invented state label, gold-conditioned
schema prefix or monkeypatch. Native target cardinality, exclusivity, required anchors, exact source
span round trips and role/choice insertion order are checked without dropping or broadening targets.
Capacity remains **64 gold spans/query**, with native `on_capacity_exceeded='raise'` and unchanged
candidate settings. An explicit overflowing batch was not run; this establishes preservation of the
strict native capacity route on the bounded actual batch, not a new overflow qualification.

Actual pre-forward receipts verify the full input IDs, attention/text/schema tokens, query routes and
coordinates equal the uncapped deterministic preparation. The native processor remains in inference
preparation mode while the **model** runs in training mode. Those choices are deliberately separate:
native record auxiliary loss is gated on `model.training`, while deterministic preprocessing need
not perform the stock training collator's sampling or per-record prefix expansion.

## Three loss-only controls

The samples were declared before model loading in
[run-001/predeclared-samples.json](run-001/predeclared-samples.json), using existing frozen feature-fit
alignment artifacts. They are the same actual controls as the preceding
[native-target inquiry](../2026-11-04_m1-native-target-conditioning/README.md):

| Actual feature-fit control | Native records | Native total loss | Record-field contribution |
| --- | ---: | ---: | --- |
| Source22/context0 genuine zero, assertion schema | 0 | 403.8828125 | Not applicable; no record target |
| Source23/context14 definition, actual nonpresent classified `relation_type` | 1 | 326.98858642578125 | 0; gold anchor absent from uninjected candidate pool |
| Source23/context4 complete safe assertion positive | 3 | 1390.0643310546875 | 0; all three gold anchors absent from uninjected candidate pool |

Each call used `model.train(True)` inside `torch.no_grad()` with explicit
`gold_injection_prob=0.0`. No optimizer existed for these calls and no gradients accumulated.
All returned native component losses were finite; full named-parameter hashes before and after the
three calls were identical. Native target masks retained the zero record count, actual ABSENT role
and independent `relation_type__state="unstated"`, and all three complete positive records.

**Limit:** the uninjected native pools missed the required gold anchors. Native record-field losses
were therefore zero; these forwards do **not** demonstrate a nonzero ABSENT assignment gradient.
They demonstrate faithful target/conditioning transport and finite native boundary loss. No gold
candidate was injected to disguise this limitation. The isolated ABSENT record was used only for
loss representation, not promoted into a complete training context or added to the optimizer batch.
Complete-context grouping/overlap exclusions remain under the alignment owner.

Actual batches, losses, masks, anchor-presence observations and executed bytes are retained as
`run-001/loss-only-*-actual-batch.json`, `run-001/loss-only-*-loss.json`, and
`run-001/*-executed.py.txt`. Loss-only calls were not repeated after their passing gate.

## One actual mixed optimizer step

The optimizer batch was fixed before any model result: the safe **three-record assertion positive**
and genuine **zero-record heading**, using the same released assertion schema. Native raw data
loading preserved field and choice order. The actual batch had source-word counts **164 and 3**,
encoded lengths **1397 and 1220**, and native record masks `[[true,true,true],[false,false,false]]`.
Every role query/cardinality/exclusivity and the one-declaration inference prefix survived.

The native trainer substitutes `model.config.max_len` when `TrainingConfig.max_len=None`. Its exact
inherited cap was **4096 source words**, not an encoder subword cap. The first trainer attempt
stopped before its forward because the initial wrapper rejected any non-None cap. The coordinator
accepted the concrete requirement—no actual truncation—and the wrapper now preprocesses the full
source uncapped, rejects any source-word count exceeding the requested native cap, and records that
4096 is inactive for these samples. The checkpoint/config was not resized, patched or overridden.
Actual input IDs and coordinates remain equal to uncapped preparation.

[train_one_step.py](train_one_step.py) loaded the unchanged base afresh, verified its named parameters
equal the prior base, reused the three passing loss receipts, and executed one native training step.
The constructor call was `ExtractorTrainer(model, config, processor=wrapper)`. Configuration retained
`max_steps=1`, batch2, accumulation1, seed0, FP32, no evaluation/dry-run recall, no LoRA, unchanged
whitespace/candidate capacities, strict errors, no sanitation or skipped samples, no AMP, no compile
and no gradient checkpointing. Native default encoder/task rates **1e-5/5e-4**, weight decay **0.01**,
and a constant schedule with no warmup were numerical feasibility controls, not fitted recommendations.

The one step used the native trainer's declared **training-only gold injection=1.0** at step0.
That is ordinary native supervised training, separate from the uninjected loss-only controls and
any inference pool. No inference or post-update candidate assessment was performed.

Observed result, retained in [run-003/result.json](run-003/result.json):

- One actual trainer forward, one backward and one optimizer pre/post event; populated optimizer
  state steps were exactly `[1]`. No other optimizer step occurred across the attempts.
- Native total loss **2126.4833984375**, requiring gradients, with native record-field loss
  **8.663796424865723**. All returned scalar components were finite; no dropped auxiliary-loss
  warning was recorded.
- **302** gradient tensors were finite; **279** had nonzero entries. Native clipped-gradient norm
  **71307.96875** was finite. All final parameters were finite.
- **302** named parameter tensors changed. Native weight decay can contribute to change; this does
  not establish useful learning. Base snapshot artifacts were independently reverified unchanged.
- The native trainer saved its authorized final checkpoint, approximately **746.5 MiB**, isolated in
  `run-003/native/final/`. Its complete file hashes are in the result receipt. No product profile or
  registry selects it; optimizer-resumable checkpoint behavior is not claimed.

## Retained failures and exact commands

1. `attempt-001.log`: **failed** after three passing loss-only forwards and their unchanged-weight
   gate. The trainer's inherited4096 cap met the initial overly strict no-cap wrapper guard before
   any training forward or optimizer action. The original executed wrapper/runner remain under
   `run-001/`.
2. `attempt-002.log`: **failed** before loading a model. The train-only harness compared in-memory
   tuple artifact metadata with its JSON list representation. A serialization-normalized equality
   check corrected this harness issue; its executed bytes/failure remain under `run-002/`.
3. `attempt-003.log`: **passed**, exit0. Reused the passing loss receipts and executed only the
   fresh-base mixed training step. Actual trainer batch is
   [run-003/actual-trainer-batch.json](run-003/actual-trainer-batch.json).

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py --interval 0.5 --out docs/design_review/evidence/2026-11-04_m1-fixed-schema-loss/resources-001.jsonl -- uv run python docs/design_review/evidence/2026-11-04_m1-fixed-schema-loss/run_experiment.py
uv run python docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py --interval 0.5 --out docs/design_review/evidence/2026-11-04_m1-fixed-schema-loss/resources-002.jsonl -- uv run python docs/design_review/evidence/2026-11-04_m1-fixed-schema-loss/train_one_step.py
uv run python docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py --interval 0.5 --out docs/design_review/evidence/2026-11-04_m1-fixed-schema-loss/resources-003.jsonl -- uv run python docs/design_review/evidence/2026-11-04_m1-fixed-schema-loss/train_one_step.py run-003
uv run python docs/design_review/evidence/2026-11-04_m1-fixed-schema-loss/freeze_receipts.py
```

Every script refuses to overwrite its owned run folder. The first commands describe historical
attempts; they are not instructions to repeat the loss passes or optimizer step. The complete
three-attempt accounting is **3 loss-only forwards + 1 trainer forward + 1 optimizer update**.

## Resources, byte custody and API grounding

The existing external sampler observed the final training attempt for **22.01 s**, with peak
complete sampled PSS **13,198,553 KiB**, summed RSS **13,224,664 KiB**, observed CPU delta **49.56 s**,
and peak14 tree threads. Its one incomplete PSS sample, sampling gaps, short-lived/reparented-process
limits and RSS sharing are retained. The experiment's timed script span was **18.23 s**, including
loading, hashing and checkpoint writing. This is a bounded observation, not aggregate resource or
performance qualification. Torch reported CPU4/interop1; tree threads include runtime helpers.
The first loss-only/failed-integration attempt has its separate resource receipt.

Launch receipts hash input artifacts and actual scripts; `.py.txt` snapshots retain the exact
executed bytes through later root formatting. Final manifest
[freeze-receipts.json](freeze-receipts.json) hashes every owned file, including the isolated checkpoint.
Local `.gitattributes` routes JSON/JSONL/logs/native checkpoint files and raw source through LFS.

Context7 was first for GLiNER2 native loss/trainer semantics, followed by exact installed2.1.0 source.
PyTorch observer hooks were researched through `/pytorch/pytorch/v2.14.1`; every hook returned None
and observed counts/gradients without modifying arguments, outputs or updates. Installed native
source snapshots/hashes are under `raw/installed-2.1.0/` and `source-receipts.json`. Relevant owners:
`models/boundary/model.py:1850+` gates native record loss on model training mode;
`training/trainer.py:512–575,692+,1335+,1526+` owns the supported processor seam, raw loader and
inherited max_len; `training/data.py:309+` preserves raw dictionaries when sanitation is disabled.
The preceding target-conditioning folder retains the exact builder/cardinality source snapshots.

No efficacy, training-budget choice, calibration, generalization, complete ABSENT-context training,
post-update inference, held-out assessment, product adoption or whole-M1 qualification follows.
No more training or research grid was run. The coordinator owns the next boundary.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Native fixed-schema processor loss and optimizer integration](records/m1.fixed-schema-loss.json) | M1-07 | passed | — | 2026-11-04 |
<!-- evidence-index:end -->
