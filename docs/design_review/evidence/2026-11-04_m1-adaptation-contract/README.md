# Conditional native GLiNER2.5 adaptation contracts for M1

Research date: 2026-11-04. Standing: **Proposed** options grounded in inspected
2.1.0 implementation; no new inference, training or performance qualification.
Baseline examined: main `1e631ba7c9a6877d40a0eab7f6e81ddef0b4b99a`, native 124,
coordinator-named release `bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`.
The coordinator supplied run 14's capture summary; this inquiry did not reread its
predictions, independent author answers, Forbes/NIST results or reference labels.

This is preparatory capability research for conditional O02/O05/O11. Independent
protected evaluation must first establish the actual remaining capture/attachment
gap. Nothing here adopts training, changes M1's architecture or waives admission.

Context7 was the first documentation lookup, resolving `/fastino-ai/gliner2` and
querying record supervision, training/LoRA/recall diagnostics, and supplied-span
alignment separately. The repository's `docs/libraries/parsing/gliner2.md` sections
3.3/3.5, 6.3, 8.1–8.5 and addendum record/pool/training/splitter sections supplied
orientation. Exact installed source controls consequential claims below.
[`source-receipts.json`](source-receipts.json) records hashes/line counts for fourteen
installed source files and byte-identical comparisons with five upstream v2.1.0
files. No model modules were imported for this research.

## Smallest coherent routes, conditional on the observed failure

| Independently established gap | Native route worth distinguishing | What it can settle; remaining boundary |
| --- | --- | --- |
| Desired spans exist among candidates but final grouping misses or misattaches them | Inspect native candidate and record-assignment logits; compare an anchor consistent with the intended instance, then `latent` if no stable anchor exists | Separates discovery from assignment. Anchor/schema changes create a new prediction context and need fresh fit; they are not repairs proven by API acceptance. |
| Desired exact spans never enter proposals | `score_explicit_spans` on source-derived candidates versus injection-off proposal diagnostics | Distinguishes inability to propose from low scoring. Supplied candidates must be available at inference from the same allowed source universe, not from held-out labels. |
| Multiple fields collectively identify an instance and no single field is reliable | `structure(name, mode="latent")`, or `mode="anchorless"` with no anchor | Native alternatives before deciding on training, but learned behavior of these modes is not established for this workload. Anchorless remains candidate-dependent and capacity-bounded. |
| Persistent boundary, role, state or assignment errors after input/configuration alternatives are assessed | Native supervised `ExtractorTrainer` with grouped, independently annotated structures | Can train the relevant prediction heads. No learning benefit, data sufficiency, CPU feasibility or calibrated semantics follows from available APIs. |

The smallest training route would reuse the native dataset, collator, boundary and
record losses rather than add a teacher or independent grouping model. It is only
coherent if labels identify complete record instances and the intended roles/states,
not just a bag of source spans. The smallest inference change depends on the error:
supplied-span scoring does not repair assignments; latent grouping does not recover
a field missing from every candidate pool. Keep diagnostic alternatives bounded to
the actual failure rather than adopting all facilities together.

## Record modes, pools and supplied spans

`Schema.structure(name, mode="natural", anchor="term")` uses each detected anchor
candidate as an instance seed. In `latent` mode a learned selector chooses seeds
from field candidates; it removes the nominated-anchor requirement, not candidate
discovery. In `anchorless` mode learned instance queries attend to candidate states
and predict object/no-object and field assignments. `record_instance_queries`
bounds learned slot capacity; increasing it changes parameter shapes and is not a
free inference-only recall knob. `natural` requires an anchor field; `latent` and
`anchorless` must not set one. Native assignment includes an ABSENT alternative,
which is distinct from any semantic state label. See
[schema](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py)
and [records](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/records.py)
(`RecordHead`, `_assign_logits`, `forward_group`, `decode_group`).

There are per-query and shared candidate pools. The active checkpoint settings,
not dataclass defaults, determine which route runs. Shared pooling includes learned
candidate/query attention; switching a trained checkpoint to another pool is not
semantically neutral. Candidate budgets can change proposal coverage, while
thresholds/overlap can change selection. Added capacity or lower thresholds do not
establish usable output. Preserve raw candidate scores and distinguish nomination,
pair scoring, object selection and assignment in any diagnostic.

Concrete public primitives in `models/boundary/model.py`:

- `encode(preprocessed_batch) -> EncodedBatch` exposes text/query states and layouts.
- `score_candidates(batch, return_auxiliary_logits=True)` returns
  `CandidateTensorBatch` plus start/end/inside logits. Candidate tensors include
  indices `[B,Q,C,2]`, pair/proposal logits, masks and optional candidate states.
- `score_explicit_spans(encoded, indices, valid_mask=None)` accepts half-open
  **encoded word-token** boundaries `[B,Q,C,2]`, with mask `[B,Q,C]`, and returns
  logits `[B,Q,C]`. They are not raw-character or tokenizer-subword indices.

Explicit scoring bypasses proposal top-k but retains compatibility and reranking.
In shared mode it injects the requested spans into a shared pool, recomputes that
pool's scores and raises if legal requested spans do not fit. Pool composition can
affect scores. It does not accept a ready-made native group or automatically run
record assignment on externally supplied records. Direct `RecordHead` use consumes
candidate states, query layouts and `RecordSpec`; that is a lower-level integration,
not an interchangeable high-level `extract` argument. See
[model.py:276](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py#L276),
`:372–419`, `:1630`, `:2105–2150`, and `models/outputs.py`.

Current `GlinerPack.compile` expressly allows only natural structures with explicit
anchors (`methods/gliner.py:145–165`). Latent/anchorless therefore require an
explicitly versioned pack/adapter change before product use; native library support
alone does not make them accepted by the current repository facade.

## Exact training representation and semantic states

Native entry points are `InputExample`, `Structure`, `ChoiceField`,
`TrainingDataset` in `gliner2.training.data`, and `ExtractorTrainer(model, config)`
with `trainer.train(train_data=..., eval_data=...)`. JSONL uses:

```python
{
    "input": exact_supplied_context_text,
    "output": {
        "json_structures": [
            {"definition": {
                "term": {"text": term_text, "start": a, "end": b},
                "defining_text": {"text": clause_text, "start": c, "end": d},
                "term__state": {"value": annotated_state, "choices": state_labels},
                "relation_type__cue": {"text": cue_text, "start": e, "end": f},
                # Include other declared family fields and their independently
                # annotated states/cues under the same instance, where applicable.
            }},
            # A second same-family record is another dictionary, not parallel lists.
        ],
        "record_metadata": {
            "definition": {"mode": "natural", "anchor": "term"}
        },
        "json_descriptions": {"definition": field_descriptions},
    },
}
```

This is an API shape with variables, not authored training data or gold judgments.
Explicit spans use original-input half-open Python-string character offsets, with
`text[start:end] == annotated_text`. Surface strings otherwise supervise every
matching occurrence, so repeated words require explicit location annotations for
the intended attachment. Choices live in schema-prefix tokens; they are labels,
not source-text evidence. `ChoiceField(value, choices)` serializes to the value/
choices mapping. Descriptions condition the model; they do not establish semantics.
Training metadata belongs in `output.record_metadata`, not fields named `mode` or
`anchor`. Mode defaults to natural and absent anchor defaults to first field, so
declare the anchor explicitly. See
[data.py:485–625](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/data.py#L485),
`:981–1065` and [training-data tutorial](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/8-train_data.md).

Required released family roles must remain in the annotation contract. A null or
empty field trains extractive absence according to its record specification; it
does not mean `unstated`, `inapplicable` or `unresolved`. Those states require
independent judgments over the exact inspected scope, anchored to the same record.
`__cue` needs actual source wording or an explicitly absent cue annotation; do not
copy a state/classification label into a source span. Alternative readings and
ambiguous attachment need their own declared annotation treatment, not silently
converted negatives. Source inspection and downstream admission remain separate.

To represent record cardinality/exclusivity, raw `record_metadata[family].fields`
supports `cardinality` and `exclusive` (`processing/records.py:compile_record_specs`).
The convenient `Structure.get_record_metadata` serializes only mode/anchor/
occurrence policy: it does not preserve this richer field metadata. In addition,
the trainer's default `validate_data=True` passes records through
`DataLoader_Factory._validate_records`, which calls `InputExample.sanitize()` and
replaces records with `example.to_dict()`: it can remove invalid fields and strip
metadata not represented by `InputExample`. A faithful future route must inspect
the effective serialized/collated annotations before training. Native strict
`InputExample.validate`/`TrainingDataset.validate` plus error-raising collation are
available; merely enabling loader validation is not a no-change guarantee.
Avoid inventing a new parallel validation framework to hide that distinction.

Entity negatives require an explicitly declared label with an empty list, e.g.
`entities={role_type: []}`; `entities={}` does not mean negative for every label.
Described entity types with no mentions are inserted as negative labels. This
does not settle a no-record negative-example representation for every structured
family; no such example was collated here. Unknown/uninspected content must not
become a negative. Entity attribute inference uses `AttributeGroup`, but the
documented training format has no separate attribute-annotation field. Per-record
choices/cues above are the directly represented record-supervision route; an
attribute-based redesign would require its own mapping assessment.

No teacher LLM is required by these APIs. If adaptation becomes authorized, only
independently authored, scope-located **feature-fit/training** annotations may
provide targets. Calibration origins remain out of weight/threshold/schema selection
as governed by the accepted split; final origins and answers remain sealed. Do not
use reference spans to manufacture an inference-time candidate pool. Freeze the
source contexts, candidate-generation policy, exclusions, profile/schema identity
and annotation origin assignment; a changed model/schema/pool/splitter produces
a changed candidate universe needing corresponding fit/calibration assessment.

## Word splitting and the offset trap

`WhitespaceTokenSplitter` is a regex tokenizer, not `str.split()`. Its ordered
alternatives recognize URLs, emails, @mentions, Unicode word runs (including marks
and joiners) with internal hyphens/underscores, then each remaining non-whitespace
character. Punctuation often becomes separate tokens. A welded alphabetic run such
as `IfXis` stays one token; a long hyphen-joined identifier can also stay one token.
Backslash math commands are not parsed for mathematical meaning by this regex.
Lowercasing changes token values only; offsets still index the original string.

`CharLevelSplitter` also keeps `[A-Za-z0-9@._\-+]+` runs together. Switching to
`word_splitter="char"` is therefore not a generic fix for welded Latin words.
A custom callable is allowed with `(text, lower=True) -> (token,start,end)` yields;
it must preserve original-string coordinates and not normalize the source itself.
Changing splitting changes available boundaries and the learned input distribution.
See [word_splitter.py](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/word_splitter.py).

Crucially, explicit character annotation does **not** guarantee exact word-boundary
supervision. `processor._resolve_span` checks the character substring, then
`char_span_to_word_boundaries` accepts endpoints inside tokens and maps to containing
tokens (`processing/targets.py:128–176`). Such an annotation can broaden during
conversion. Preserve exact source-to-token-to-source identity for intended targets
and supplied candidates; do not relabel a broadened token span as the annotated
substring. A valid native output can still be mapped to its actual larger source
span, with the mismatch retained for interpretation.

`find_unalignable_entities(text, entities)` diagnoses listed literal **entity**
values using the native splitter/search. It excludes prefix choice selections and
does not independently validate explicit record-span round trips, grouping,
meaning attachment or source-state correctness. The default
`dedupe_contained_entity_spans=True` removes contained entity-query matches in
boundary training, not arbitrary record fields; use `False` only if independently
intended nested entity supervision requires it. Output overlap policy is another
distinct choice (`flat`, `nested`, `longest`) and the current worker admits flat.

## Native training, CPU and adapters

The full-model route loads a compatible local boundary checkpoint with
`AutoExtractor.from_pretrained`, then uses `TrainingConfig(use_lora=False, ...)` and
`ExtractorTrainer`. Encoder/task learning rates are distinct; native boundary and
record losses already exist. CPU FP32 is supported by trainer source, but the
trainer auto-selects CUDA when visible; a CPU-only job needs process visibility
control, not an assumed `TrainingConfig(device="cpu")` field. Explicit
`fp16=False, bf16=False` avoids boundary mixed-precision defaults; the CPU path
disables mixed precision and calls `model.float()`. No CPU training feasibility or
resource measurement was performed. `num_workers=0` and native CPU thread settings
would make a future bounded CPU process explicit; no such job is authorized here.

LoRA uses `TrainingConfig(use_lora=True, lora_r=..., lora_alpha=...,
lora_target_modules=[...], save_adapter_only=True)`. The trainer first freezes
**all** existing parameters, then trains resolved adapters. Explicit architecture-
aware target aliases include `extractive_head`, `record_head`, `classification_head`,
`relation_head`, and `all_task_heads`; the boundary model reports classifier,
boundary head, enabled record decoder and relation scorer as task modules. A record
attachment gap cannot be assumed addressed by encoder-only adapters or legacy
span-head target defaults. LoRA modifies targeted linear modules, not every learned
parameter such as all instance embeddings. Full fine-tuning changes the broader
parameter set; it also carries a larger CPU/memory burden. No comparative learning
benefit is established. See [lora_targets.py](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/lora_targets.py)
and [boundary apply_lora](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py#L1352).

Boundary `apply_lora` returns a PEFT `PeftModel`. Adapter-only trainer output is
PEFT-native `adapter_config.json` plus `adapter_model.safetensors`; it requires the
compatible immutable base. Explicit PEFT composition is the consequential loading
contract. GLiNER-defined `load_adapter`/`unload_adapter` convenience implementations
are in the span model, not the boundary implementation; inherited Transformers
interfaces and their parity were not established here. Do not copy span-era
adapter-switching examples as a boundary guarantee. Runtime adapter switching also
mutates model state and cannot change the current run-owned worker's profile silently.

With `save_adapter_only=False`, trainer source merges adapters for full saving and
then unmerges to continue training. A self-contained full export is conceptually
closer to the existing worker than adapter composition, but resulting architecture,
file set, dtype, exact base/export loading and extract behavior would still require
verification; no export was attempted. Current `GlinerProfile` accepts exactly five
hash-qualified full-checkpoint files and `load_model` verifies CPU FP32, boundary,
standard attention, whitespace splitting and no adaptive threshold. Adding PEFT
files to that snapshot would be refused. See `methods/gliner.py:35–132,320–370`
and [trainer checkpoint saving](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/trainer.py#L2104).

## What native validation establishes

`InputExample.validate`/`TrainingDataset.validate` check shape and locatability;
plain string checks are case-insensitive substring checks. Explicit spans additionally
check exact substring equality. Token alignment/collation, capacity and later
association remain separate. Native `on_capacity_exceeded="raise"`,
`allow_invalid_samples=False`, `strict_training=True`, no truncation (`max_len=None`)
and sufficient `max_gold_per_query`/training budgets prevent known silent-loss
paths when used consistently; they do not prove semantic completeness of labels.

Gold-candidate injection (`gold_injection_start/end/hold_frac`) lets the reranker
and assignment losses see annotated positives even when ordinary proposal discovery
misses them. Consequently training loss or injected-candidate recall is not native
inference recall. `TrainingConfig(dry_run_recall_steps=N, ...)` makes `trainer.train`
run a bounded injection-off proposal diagnostic and return before weight updates.
It uses the training loader (which is shuffled), `model.eval()`, `no_grad()` and
`gold_injection_prob=0.0`, accumulating proposal metrics from at most N batches.
This is not a comprehensive independent evaluation by default.

`gate_recall` defaults to 0.97; `gate_long_recall` defaults to 0.93 for the 9-plus-
word-token bucket. They are configurable diagnostic cutoffs, not model capability
claims or M1's acceptance criterion. The implementation treats a missing long bucket
as recall 1.0 for gate comparison, so absence of long-span observations must not
be reported as demonstrated long-span recall. Metrics can compare per-query/shared
pool diagnostics. A passing proposal-oracle recall only says annotated gold spans
were present among generated candidates under that sample/configuration; it does
not establish pair-score selection, group attachment, clause semantics, precision,
state calibration, no-record specificity, source completeness or final quality.
See [trainer.py:1397–1478,1595–1627](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/trainer.py#L1397).

## Runtime versus semantic release

`orchestrate/m1.py:224–231` loads `m1-methods.yaml` as the explicit runtime method
registry. `semantic/regeneration.py:103–121` composes `methods.yaml` and its listed
operation artifacts, not `m1-methods.yaml`, into release input. Thus a compatible
checkpoint/revision/hash/threshold/description **configuration** change can
conceptually retain the semantic release while producing a new method-config,
profile, pack, computation and run identity. Merely relocating identical snapshot
bytes does not change profile fingerprint; artifact/revision changes do. One worker
cannot switch profiles within a run (`m1_source.py:_resident`).

This is not an existing generic checkpoint-override command:
`bind_record_policy` explicitly binds only `feature_instances` and
`record_acceptance`, validates their released shape and release applicability, and
requires calibration for acceptance. It does not bind checkpoint/pool/splitter
overrides. Current `M1Config` has checkpoint metadata, threshold and descriptions,
but no generic boundary-setting, record-mode or adapter fields. Those alternatives
need explicit compatible registry/facade changes. No config mutation was made here.

A new semantic release is required if the implementation changes a released role,
semantic state, reading/inspection meaning, occurrence identity, feature contract,
admission obligation or a source implementation included in trusted release inputs.
Finite parameter compatibility does not exempt code/declaration changes from their
actual release dependencies. A distinct trained checkpoint does not itself require
inventing a new domain schema, but its profile/prediction universe changes and old
feature/calibration/evaluation evidence cannot be automatically reused. Check the
accepted applicability and exact source/context identity, not just equal release ID.

## Formula custody and remaining uncertainties

`m1_source.py:_structural_groups` obtains formula occurrence custody from the native
formula owner; `_formula_matches_primary` attaches a supplement only through the
actual decoder formula span. That structural occurrence identity is not a learned
claim that a nearby declaration explains a symbol, nor proof of a domain/assumption
or symbol-to-meaning association. Preserve formula identity and located source
spelling separately from learned relation proposals and interpretation.

Still unresolved: independently measured family-specific error distribution;
whether candidate nomination versus selection/attachment dominates; latent and
anchorless fit with these weights; source-boundary alignment after any splitting
change; complete structured negatives; trustworthy per-record state supervision;
adapter/full-export loading parity and CPU training feasibility. Native enum
fallback and shared candidate context also remain relevant to state interpretation.
Those questions must not be settled from run counts or this source inspection.

Checks: tagged-source comparisons **passed** (five fetched files match installed
bytes); targeted source reading **passed**. Inference, data-author answer inspection,
training, DB reads/writes, provider/PDF/OCR requests, dependency changes and product
qualification **not_run**. Only this new README and source-receipts file were
written; coordinator owns decision integration and turn-end.
