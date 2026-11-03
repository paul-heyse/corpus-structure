# Installed GLiNER2 operation adapter contracts

**Source-inspected, 2026-11-03.** Bounded integration research for M1-07; no new inference,
accuracy, resource-fit, worker or assembled qualification claim. The environment's distribution
metadata reports `gliner2==2.1.0`. Installed paths below are relative to
`.venv/lib/python3.14/site-packages/gliner2/`. `installed-source-sha256.json` identifies inspected
code independently of the package version. Concurrent production work was read only.

Context7 was the first documentation lookup: resolved `/fastino-ai/gliner2`, then queried
combined structured extraction and constrained classification/JointIE. Its returned examples cite
upstream `main`, so the installed source is the controlling evidence here. Documentation leads:
[combined](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/4-combined.md),
[classification](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/14-constrained_classification.md),
[JointIE](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/15-joint_ie.md).

## Loading and effective identity

**Observed defect:** `auto.py:111-145` splits Hub options, uses them for the top-level config,
then forwards only model options to the architecture loader. A repo-name call with `revision=`
therefore does not establish that weights/encoder config/tokenizer use that revision. In addition,
`models/base.py:36-58`, `load_extractor_tokenizer`, accepts no revision/local-only options.
Use an acquired immutable snapshot **directory** as `AutoExtractor.from_pretrained` input; retain
the checkpoint ID, revision and file hashes externally. Preserve the original CPU attempt's
actual-operation result while narrowing its revision-custody claim; the coordinator owns repeats.

On the concrete boundary snapshot route, `models/boundary/model.py:2184-2252` loads top-level
config, `encoder_config/config.json`, tokenizer and top-level checkpoint weights from that
directory. It supplies explicit encoder config and tokenizer to the constructor. The constructor
at `:1225-1253` calls `_load_encoder` with that config; `models/base.py:630` takes
`AutoModel.from_config`, so `config.model_name=microsoft/deberta-v3-base` does not cause a separate
backbone weight fetch on this route. Standard attention must remain explicit. Offline execution
can independently check no remote resolution; no such execution was performed in this inquiry.

The inspected cached base config at revision `54785d51df8d86a0d8f2eb212fec15871aad2c4d` declares
boundary architecture; records, relations, abstention and count enabled; shared pool192,
pool-boundary-top-k32, min-pool-per-query8, candidate-budget192; start/end-top-k24;
record-instance-queries32, relation-head/tail32, relation-pair-cap64; adaptive-threshold false;
flat overlap. These are configuration observations, not learned-quality evidence. Capture the
actual resident `model.config`/`boundary_settings`, enabled modules, dtype/device and splitter,
plus exact package/dependency versions and artifact hashes. Do not substitute dataclass defaults.

## Registry admission and combined operation

Use `Schema.from_dict(declaration)` (`inference/schema.py:520-631`), which invokes strict
`SchemaInput` (`schema_model.py:21-25,169`). Keys are `entities`, `structures`, `classifications`,
`relations`, `entity_attributes`. Supplying a raw dict directly to `extract` is a different,
internal-schema path and does not invoke this strict registry admission.

Example declaration shape (pack labels/fields remain the semantic owner's responsibility):

```python
{
    "entities": ["quantity", "statistical concept"],
    "entity_attributes": {
        "role": {"labels": ["estimate", "uncertainty"],
                 "multi_label": True, "threshold": 0.5,
                 "applies_to": ["quantity"]}
    },
    "structures": {
        "measurement": {
            "mode": "natural", "anchor": "quantity",
            "fields": [
                {"name": "quantity", "dtype": "str", "cardinality": "optional_one"},
                {"name": "unit", "dtype": "str", "cardinality": "optional_one"},
                {"name": "kind", "dtype": "str", "choices": ["mean", "median"],
                 "cardinality": "optional_one"}
            ]
        }
    },
    "classifications": [{"task": "content_roles", "labels": ["definition", "measurement"],
                         "multi_label": True, "class_act": "sigmoid", "cls_threshold": 0.5,
                         "top_k": 2}],
    "relations": ["qualifies"]
}
```

Call `model.extract(text, schema, threshold=..., include_confidence=True,
include_spans=True, max_len=..., overlap_policy=...)` (`inference/runtime.py:1609-1632`).
`batch_extract(texts, schemas, batch_size=..., num_workers=0, ...)` at `:253-375` accepts a
single schema or one per text. One combined boundary call decodes records, relations, entities
with attributes, and classifications (`models/boundary/engine.py:252-348`). This composes the
selected native heads without a second checkpoint or custom decoder. Compare separate compact
pack calls when shared-pool competition differs; physical fusion does not erase logical reports.

Natural grouping is explicit: `Schema.structure` at `schema.py:270`, `StructureBuilder.field`
at `:128`, and strict `StructureInput` at `schema_model.py:58-87`. The strict model silently
defaults a missing natural anchor to the first declared field, so the registry must require an
explicit anchor itself. Preserve field **list order** in the digest. `to_dict` at `schema.py:633`
round-trips declarative policy; executable regex validators require a separate identity/binding.
Use optional scalar cardinality and outer completeness checks. Native record decode receives
the same operation threshold for anchor/field/object at `boundary/engine.py:1484-1490`; per-field
thresholds also filter formatting. No independent public anchor/object threshold knobs follow.

## Literal, classified and attribute evidence

Literal fields are formatted from mapped character boundaries and original text at
`models/boundary/engine.py:1312-1358`. Reconstruct every returned literal against the exact input
and its existing source interval map before normalization. Synthetic terminal punctuation is
possible: `processor.py:609-616` normalizes missing sentence punctuation. Reject unmappable spans.

**Enum outputs are classified fields.** Installed code has more branches than the short deployment
reference implies: prefix enum spans can initially receive anchor coordinates or `(0,0)` at
`boundary/engine.py:1243-1310`; local literal choice recovery at `:1361-1439` can return actual
cue positions; the final `_decode_choice_field` fallback at `:813-919` returns labels/confidence
without offsets. Thus `include_spans=True` does not guarantee enum source spans. Preserve classified
status and record association even when offsets exist. An independently reconstructing source cue
may be retained as cue evidence, never assumed from the presence of `start/end` alone.

`Schema.entity_attributes` (`schema.py:377`) requires previously declared entities. Boundary
attribute scoring (`boundary/engine.py:532-646`) scores the selected entity spans; groups attach
as `{label,confidence}` or lists thereof. Multi-label uses sigmoid and its threshold; exclusive
groups use softmax argmax. It cannot recover a suppressed mention or establish negation scope.
Join attributes to grouped literal fields by context/window plus exact span occurrence and type,
never result-array position or equal normalized strings.

## Additional native wrappers and diagnostics

`Classifier(model)` (`classification/engine.py:71`) and `JointIE(model)` (alias of
`JointIEEngine`, `joint_ie/engine.py:134`) wrap the resident compatible model; constructor `.to`
and `.eval` effects mean admission must prevent incompatible in-flight mutations.

For constrained classification, use `ClassificationSchema` and per-call `ClassificationConfig`.
The default `on_infeasible="relax"` is explicit in `classification/engine.py:36-46`; choose a
declared behavior and retain `feasible`, `violations`, objective, decoder and exactness
(`classification/result.py:60-116`). `score` plus `decode` preserves raw label alternatives;
`decode` checks schema fingerprint at `engine.py:169-177`. That fingerprint is SHA256 of the
complete schema `to_dict` (`compiler.py:182-184`), including constraints. It is **not** checkpoint,
text, tokenizer, splitter, precision or encoding identity; the adapter supplies those premises.
Schema changes require public re-scoring. Combined `Schema.classification` is the simpler
unconstrained route and does not provide constrained-wrapper feasibility diagnostics.

`JointIE.score`/`batch_score` expose candidate scores/lattices; `extract` adds native graph
selection (`joint_ie/engine.py:213-252,328-414`). `JointResult.feasible` distinguishes an
infeasible empty assignment (`joint_ie/result.py:67-75`). Entity IDs are local result IDs.
Do not assume a public `JointIE.decode` equivalent to Classifier: installed graph decode is
`_decode`. Native long text merges duplicate local fragments and cannot create cross-window
relations (`joint_ie/long_text.py:14-22`). Its final constructor at `:77` does not propagate
fragment feasibility. Preserve per-window native results before any long-text merge; use the
existing mapped-context/window owner rather than collapsing diagnostic provenance there.

Public `extract(format_results=False)` skips presentation formatting only: it still returns
decoded results (`inference/runtime.py:353-375`), not proposal/null/count tensors. Search coverage:
`inference/{runtime,schema}.py`, `models/boundary/{engine,model,pool,proposal}.py`,
`models/outputs.py`, classification engine/scoring/result and JointIE engine/result/lattice.
No structured high-level overflow/suppression/abstention report was found on this surface.
Mark those diagnostics **unavailable**, not false/zero, unless a separately qualified low-level
operation captures them. `ExtractorOutput` has candidates/null logits/count Poisson log-rates
(`models/outputs.py:223-237`); `BoundaryExtractorModel.forward(... collect_diagnostics=...)`
at `boundary/model.py:1850` is a lower-level path. Access alone does not justify rebuilding
the high-level decoder or duplicating inference. Explicit-span shared-pool overflow raises at
`boundary/model.py:411-415`; this does not establish ordinary candidate-pool completeness.

`processor.transform_record(text, schema, max_len=...)` at `processor.py:553` is native preparation,
not inference. Word truncation is at `:713-720`; the formatted result has no matching truncation
receipt. A thin adapter should use native preparation to refuse oversized work or retain declared
truncation before inference, using the same input/schema/splitter. Keep word, character, subword,
proposal and record limits distinct. Avoid a second custom preprocessing/decoding framework.

## Suggested thin boundaries and remaining work

1. Compile a released pack through strict schema admission; retain ordered effective declaration,
   descriptions/prompts/examples, callable validators, operation and threshold policy identities.
2. Resolve the immutable snapshot and resident profile; serialize compatible work with one owner.
3. Invoke the native combined operation, or explicitly selected native Classifier/JointIE wrapper.
4. Retain each raw per-window payload and exposed diagnostics; normalize into source-bound
   observations, literal/classified distinction and association IDs using existing binding.
5. Leave retry, CPU supervision, resource admission, cross-window reconciliation, semantic
   acceptance and publication with their existing owners.

Checks: source reads/searches and distribution metadata inspection **passed**. Model invocation,
new CPU operation, database writes, environment changes and product tests **not_run**. All-head
checkpoint operation/quality, supported CPU envelope and assembled source reports remain open.

Files authored by this research assignment: this README and `installed-source-sha256.json` only.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Installed GLiNER adapter source contracts](records/m1.gliner-adapter-source-contract.json) | M1-07 | passed | — | 2026-11-03 |
<!-- evidence-index:end -->
