# M1 protected feature-fit targets and native collation

Verified 2026-11-04. Standing: **Tested**, bounded source/target preparation and
native collation only. No model was loaded, encoder/forward call executed, loss
computed, training run started, weights written or adoption established.

Baseline: main `1e631ba7c9a6877d40a0eab7f6e81ddef0b4b99a`, frozen
`release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`,
installed `gliner2==2.1.0`, existing checkpoint revision
`54785d51df8d86a0d8f2eb212fec15871aad2c4d`. Concurrent changes remain untouched.
The coordinator reports unchanged-release native125 recovery passed; this inquiry
does not claim that separate recovery or any protected grade as its own check.

## Prepared result

[training-targets.jsonl](training-targets.jsonl) contains **48 positive examples,
118 distinct C records**: 1 definition, 26 assertions, 10 measurements, 80 table
records and 1 formula-context record. These are representable positives, with
explicit per-record states, cues and extractive ABSENT values where independently
annotated. There are **no no-record negative examples** in this file. Raw JSONL
preserves declaration insertion order, source context strings and explicit character
spans; it must not be rewritten with a sorted-key canonical serializer.

[training-target-origins.jsonl](training-target-origins.jsonl) retains protected
pass/digest origins, exact context and pack fingerprints, source/word/source mapping
receipts, genuine pieces and synthetic whitespace gaps. Native scope/table/cell
fields remain native-location sidecars from the protected record and retained source
custody; they are never converted into invented extractive strings.

All 48 saved examples were **reloaded** and passed native `InputExample` and
`TrainingDataset.validate()`. Deterministic native gold-building collation preserved
118 instances, every annotated source span/choice/ABSENT target, and all field
cardinality/exclusivity/anchor metadata. It retained every released description and
the same ordered schema tokens as the actual released pack. This is target-fidelity
evidence; it is not model-loss, learning, inference or efficacy evidence.

## Frozen inputs and permitted reads

The only label acquisition was `open_runtime_engine(Settings(), purpose='fit')`
followed by `evaluate.record_references.read_fitting_references(conn, set_id=1)`.
The protected capability returned C passes **23 and 24**, bound to source views
22 and 23 and `feature_fit`. Pass23 has zero records; pass24 has 270. The returned
JSON and its stored pass digests are retained in
[feature-fit-protected.json](feature-fit-protected.json); it is the protected
capability response, not a claim to recover the original submitted byte formatting.
No author A/B/C folders, other reference sets, Forbes/NIST labels, predictions or
grades were read. The capability response includes its frozen sampling metadata;
only its two returned feature-fit authored label payloads supply targets.

Run14 source views22/23, raw task36/37, annotation task34/35 and completed cut13
were reconstructed through `BoundReader` and the archived release. Actual stored
`M1Config` parameters, `consume_annotations`, `prepare_source` and `configured_packs`
were reused. No annotation recomputation, PDF/OCR/recognition or model extraction
ran. [source-reconstruction.json](source-reconstruction.json) pins task input and
configuration hashes, annotation dependencies, exact parameters, region dispositions
and allowed raw-report metadata. [source-contexts.jsonl](source-contexts.jsonl)
retains all **148** actual bounded contexts and their source intervals.

SQL projected only raw-report context identity/digest, consumed-text hash, pack
fingerprint and effective-profile reference. It never fetched predicted groups,
raw decoder JSON or grades. All **294** actual model report receipts matched the
reconstructed context digest, exact released pack and consumed-text SHA256, with
their referenced effective profiles present. Other retained report entries are
structural, limited or otherwise lack model report metadata. See
[context-verification.jsonl](context-verification.jsonl).

All five local checkpoint artifacts were SHA256-verified against the stored
configuration; only its tokenizer was loaded, using `local_files_only=True` and
offline Hugging Face/Transformers settings. Torch was bounded to four CPU threads,
one interop thread; parent numerical environment to one thread. No GPU or model
weights were loaded. Weight-file reads for hashing do not instantiate a model.

## Coverage and explicit loss boundaries

| Family | Protected C records | Complete exact model-role mapping | Emitted positives |
| --- | ---: | ---: | ---: |
| definition | 14 | 2 | 1 |
| assertion | 56 | 38 | 26 |
| measurement | 32 | 14 | 10 |
| table | 80 | 80 | 80 |
| formula_context | 88 | 9 | 1 |
| Total | 270 | 143 | 118 |

**127** records lack a complete faithful representation in the bounded contexts.
Located roles may lie outside a context, a scalar bounding span may include real
text outside the gold pieces, welded word boundaries may broaden a gold span, or
a nonpresent classified role may lack a strict `ChoiceField` ABSENT representation.
Every original gold record remains in
[final-record-disposition.jsonl](final-record-disposition.jsonl), with source,
family, record identity and role/reason diagnostics; detailed candidate mappings
remain in [mapping-attempts.jsonl](mapping-attempts.jsonl).

**25** further mapped records have no emitted complete safe native group. A selected
context is enriched with every completely mapped same-family C record it contains;
if an incomplete C reading has an overlapping released natural-anchor span, that
entire context/family example is excluded. Shared captions/headers without that
record's natural anchor do not create phantom instances. Excluded records never
become negative targets, and no broadening, normalization, fabricated joins or
partial-record substitution is used to increase coverage.

There were 62 candidate context/family groups. Native strict training collation
completed **60** with zero instance-count, target or field-contract mismatches;
12 completed groups were excluded for overlapping incomplete anchors. **Two**
groups failed `TargetCapacityError`: source23 context133 measurement had108 gold
spans in query14, context140 assertion had90 in query17, against the actual
checkpoint's `max_gold_per_query=64` (`training_candidate_budget=192`). No truncation,
skipping or capacity increase was applied. Failures remain in
[collation-failures.jsonl](collation-failures.jsonl). Numeric model loss is **not_run**.

## Conditioning and no-record negative gaps

Native training collation has remaining conditioning variation even with all
`SamplingConfig` removal/synthetic-label probabilities zero and field shuffling
disabled: it randomly omits descriptions and reorders choice prefixes. Descriptions
were omitted in 29/60 completed training-collation groups. These were not silently
treated as the exact inference conditioning.

The native processor's deterministic branch
`collate_fn_inference(..., architecture='boundary', build_targets=True)` was used
only to construct and inspect GOLD tensors, without invoking inference or a model.
It retains all descriptions and the actual released ordered schema tokens in48/48
saved examples. Native JSON structures repeat choice prefixes for each record:
**37/48** saved multi-record examples therefore have a larger prefix than the
single-declaration inference pack; **11/48** have exactly the same prefix and schema
tokens. See [deterministic-native-targets.jsonl](deterministic-native-targets.jsonl)
and [native-check-summary.json](native-check-summary.json). Fields and label choices
are preserved; exact whole conditioning is not claimed for the37 expanded prefixes.

The explicit zero-record source22 supplied the sole tested negative source. Actual
native collation was checked for definition/assertion/measurement with these shapes:

| Native representation | Observed result | Full released-pack negative? |
| --- | --- | --- |
| Empty `json_structures` plus metadata | Zero records, zero field queries; strict validation rejects no-task input | No |
| One all-null field dictionary | Zero records and9/20/19 field queries; strict validation passes, but every choice prefix disappears | No |
| Choice `value=[]` placeholders | Full choice prefix, one phantom record; strict ChoiceField validation fails | No |
| Choice `value=None` placeholders | Full choice prefix, one phantom record; strict ChoiceField validation fails | No |

[negative-collation.jsonl](negative-collation.jsonl) preserves serialized inputs,
native targets and validation errors. No invented `NO_RECORD`, `unstated` or other
semantic state label was used to force zero-record supervision. The inspected
2.1.0 `processor.py` JSON/choice preprocessing and `training/data.py` formats do not
provide a faithful full-pack negative among these native representations. This is
a bounded inspected API gap, not a claim that every possible extension is impossible.

Default training data loading is another distinct gap: `validate_data=True` calls
`InputExample.sanitize()` and replaces raw records with `to_dict()`, which strips
per-field cardinality/exclusivity metadata. Strict native validation alone does not
establish a no-sanitation guarantee. The raw records here preserve that metadata;
do not replace them with `TrainingDataset.to_records()` as the trainer input.

## Is a positive-only bounded experiment legitimate?

**Proposed:** yes, as a separately authorized learning/feasibility experiment over
these48 complete positive contexts. Native boundary and record losses can consume
them; all within-example states, cues and ABSENT fields remain independently
annotated. The lack of zero-record examples does not make a complete positive
record false. It does leave no-record rejection learning, broader precision,
calibration, generalization and benefit unresolved. No masked/incomplete gold
context may be added as a negative, and no protected calibration/final labels may
be used to select weights, steps, thresholds or schemas.

The smallest existing-library route is the existing local `AutoExtractor` checkpoint
and native `ExtractorTrainer` in full FP32, with the raw JSONL/list-of-dictionaries
as input, after the strict/reload/collation validation above. Avoid a new teacher,
grouping model, LoRA dependency or custom loss merely to run this bounded experiment.
For a first separately authorized **one-step feasibility** experiment, native knobs
can bound it to `max_steps=1`, `batch_size=1`, `gradient_accumulation_steps=1`,
`num_workers=0`, `fp16=False`, `bf16=False`, `use_lora=False`, `max_len=None`,
`strict_training=True`, `on_capacity_exceeded='raise'`, `allow_invalid_samples=False`,
`skip_step_errors=False`, `ignore_nonfinite_losses=False`, `validate_data=False`,
`eval_strategy='no'`, `save_best=False`, `early_stopping=False`,
`report_to_wandb=False`, and a frozen seed. `validate_data=False` preserves the raw
already-validated metadata; it does not waive the checks above. CPU must be forced
at process launch because the native trainer otherwise automatically selects CUDA.
Use existing CPU4/parent1 policy, no mixed precision, no hidden max-length cap, and
retain checkpoint max-gold/candidate capacities. A future output directory and any
weight writes require that separate training authorization.

Set the processor's native `SamplingConfig` removal/synthetic probabilities to zero
and shuffling flags false, as in `align_targets.py`, so complete task/role labels are
not randomly dropped. Description/prefix variation described above remains native
training behavior and must be an explicit experiment assumption. The trainer offers
no `TrainingConfig` switch for exact deterministic description/prefix conditioning;
its deterministic gold-building branch proves representation, not an already-wired
exact-conditioning training route. A one-step result would establish only numerical
feasibility; selecting a learning budget or claiming improvement needs separate
feature-fit decisions and protected independent reassessment. No numeric learning
rate or number of epochs is selected by this preparation.

## Commands, sources and retained attempts

- **passed**: `uv run python docs/design_review/evidence/2026-11-04_m1-training-alignment/inspect_inputs.py`
  — protected fit acquisition and read-only metadata inventory. Its preliminary
  `task-configs.json` has a duplicated SQL `id` name; use `source-reconstruction.json`
  as the final task/config authority.
- **passed**, final source/target preparation:
  `uv run python docs/design_review/evidence/2026-11-04_m1-training-alignment/align_targets.py`
  — final log [attempt-alignment-005.log](attempt-alignment-005.log). Expected native
  capacity failures remain recorded; they are exclusions, not a successful loss run.
- **passed**, final saved-data check:
  `uv run python docs/design_review/evidence/2026-11-04_m1-training-alignment/check_native_batches.py`
  — [attempt-native-check-003.log](attempt-native-check-003.log).
- **passed**: `uv run python docs/design_review/evidence/2026-11-04_m1-training-alignment/freeze_receipts.py`
  — [freeze-receipts.jsonl](freeze-receipts.jsonl) freezes owned input/output bytes,
  source/library hashes, baseline and origin identities. Refresh after any
  coordinator formatting changes to these scripts.
- Model forward/loss, training, new inference, grading, DB writes and assembled
  product qualification: **not_run**. Root owns maintenance and integration.

Context7 was first: `/fastino-ai/gliner2`, explicit structured-span training/alignment
and full-schema no-record negatives were queried separately. The fetched tutorials
describe multiple dictionaries for multiple records and entity negatives, but do
not settle these structured-choice negative cases. Exact installed 2.1.0 sources
control the results; span-era tutorial suggestions about substring validation do
not replace boundary round trips. Relevant library orientation was
`docs/libraries/parsing/gliner2.md` §§8.1–8.5 and addendum training/splitter sections;
the companion [adaptation contract](../2026-11-04_m1-adaptation-contract/README.md)
and its source receipts were read. No online model acquisition occurred.

Failed/intermediate attempt logs and `attempt-001-results` through
`attempt-004-results` remain. The first preparation attempt omitted the native
`release:` prefix; early harness diagnostics used the wrong validation-report key
and a default32 capacity before inspecting the checkpoint's actual64. Table
pointer mapping was then aligned to production's parent-table/cell address.
The last correction preserved JSON object insertion order and reloaded the saved
targets. Earlier counts, sorted-key artifacts and their logs are superseded by
the final named outputs, never silently treated as final evidence.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Protected development target alignment and native collation](records/m1.feature-fit-alignment3.json) | M1-07 | partial | — | 2026-11-04 |
<!-- evidence-index:end -->
