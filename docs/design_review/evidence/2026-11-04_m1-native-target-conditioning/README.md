# Native fixed-schema boundary target conditioning

**Tested · 2026-11-04.** Installed **GLiNER2 2.1.0** can construct zero-record negatives and
ABSENT classified-role targets through its native lower-level boundary target builder while
retaining the exact released inference conditioning and field metadata. **Nine metadata-only
cases passed.** No model was loaded, forward or loss computed, training started, DB accessed,
PDF processed, held-out labels acquired or product code changed. This establishes representation,
not numerical learning feasibility, accuracy, benefit or an adopted training integration.

The stock native JSONL/`InputExample` limitations identified by the
[training-alignment inquiry](../2026-11-04_m1-training-alignment/README.md) remain. This result
uses a different boundary: independently prepared inference schema/encoding plus explicit native
structure labels. It does not repair JSONL or make its default collator preserve this conditioning.
The coordinator owns target-contract changes and any later processor adapter or training scope.

## Native route and observed cases

The probe used `Schema.from_dict(actual_released_pack)` and
`SchemaTransformer.collate_fn_inference(..., architecture="boundary", build_targets=False,
error_policy="raise", max_len=None)`. It independently checked this preparation against
`SchemaTransformer.transform_record` for the same released schema and actual context. No gold
record was supplied during schema, text, prefix or input-ID preparation.

It then called the exported native
`gliner2.processing.boundary_preprocessing.build_boundary_batch_metadata` with those same
`schema_tokens_list`, `task_types`, `text_word_counts` and native `record_metadata`, but separate
`structure_labels`, `build_targets=True`, `is_training=False`, `max_gold_per_query=64` and
`on_capacity_exceeded="raise"`. The native layouts, targets and record specs were attached to the
native `PreprocessedBatch` using its dataclass fields. All model-facing input IDs, attention masks,
text/schema tokens, query routes and coordinate mappings remained byte-for-byte equal as serialized
metadata. Field cardinality, exclusivity and declared anchors also remained equal to the released
pack. Existing native punctuation normalization was retained, including its final `.` suffix.

| Actual control | Target shape | Observed native result |
| --- | --- | --- |
| Source22, definition | `[0, []]` and empty group `[]` | 0 real records; 9 queries; 59 prefix tokens |
| Source22, assertion | same two forms | 0 real records; 20 queries; 123 prefix tokens |
| Source22, measurement | same two forms | 0 real records; 19 queries; 116 prefix tokens |
| Safe feature-fit assertion, source23/context4 | 3 explicit instances | 3 records; original 123-token inference prefix, not three repeated prefixes |
| Actual nonpresent classified definition role, source23/context14 | field `[]` and native `[(-1, -1)]` | 1 record; `relation_type` ABSENT, unchanged choices and 59-token prefix; existing `relation_type__state="unstated"` retained |

For zero-record samples, every mention mask and real record mask was false, while group and field
masks still declared the full released tasks. Native `targets.records` is **None** when the entire
batch has no records; the padded record target tensor has one allocation slot whose record mask is
false. That allocation is not a phantom gold record. Both native count-zero and empty-group forms
preserved the same queries, specifications and inference conditioning.

For the nonpresent classified role, empty `RecordFieldTarget.values` is native ABSENT. It is
separate from semantic state labels. The source annotation already supplied `unstated` for the
role's distinct `__state` field; the probe preserved that label and its original choice set. It did
not invent `ABSENT`, `NO_RECORD`, `unstated` or another label inside `relation_type.choices`.
`relation_type` retained `optional_one` cardinality. Both absence encodings generated the same empty
field target, with the role/query and all choice-prefix tokens still present. Actual literal spans
were checked for exact character→word-boundary→character round trips; existing choice labels mapped
to the unchanged native prefix using the processor's case-insensitive selection semantics.

The full per-case receipts, native masks, field targets, schema tokens, prefix tokens, specifications
and conditioning digests are under [attempt-002/](attempt-002/). The concise result is
[summary.json](attempt-002/summary.json). These are probes, not a newly admitted training corpus.
In particular, the isolated nonpresent-role control does not establish complete-context annotation
coverage or remove the alignment inquiry's grouping, overlap and capacity exclusions.

## Concrete API composition

For one sample with one released record family, the zero-record core is:

```python
batch = processor.collate_fn_inference(
    [(text, released_schema)], architecture="boundary",
    build_targets=False, error_policy="raise", max_len=None,
    max_gold_per_query=64, on_capacity_exceeded="raise",
)
labels = [[[0, []]]]  # batch -> group -> [count, explicit instances]
layouts, targets, specs = build_boundary_batch_metadata(
    schema_tokens_list=batch.schema_tokens_list,
    task_types=batch.task_types,
    structure_labels=labels,
    text_lengths=batch.text_word_counts,
    record_metadata_list=[batch.original_schemas[0]["record_metadata"]],
    is_training=False, build_targets=True,
    max_gold_per_query=64, on_capacity_exceeded="raise",
)
gold_batch = dataclasses.replace(
    batch, query_layouts=layouts, targets=targets,
    record_specs=specs, structure_labels=labels,
)
```

A positive instance supplies a list of fields in the concrete query/specification order. Native
structure-label spans use inclusive **word-token** endpoints, including the exact choice-prefix
offset. The native builder converts them into half-open `RecordFieldTarget` coordinates. An empty
field list or `(-1,-1)` supplies native absence. Labels never need to be inserted into the released
schema to manufacture an instance or its prefix.

The native builder preserves supplied specifications; it does not independently establish that
an annotation is true, complete, source-located or compatible with required-field cardinality.
`validate_target_graph` checks identities and coordinate bounds but does not replace independent
annotation/cardinality validation. The probe explicitly checked its selected controls against the
released field contracts and existing source-alignment receipts. Future ingestion must retain those
obligations and existing capacity refusal rather than treating accepted tensors as sufficient truth.

## Public and private boundaries; remaining trainer integration

The route uses public-named native APIs: `Schema.from_dict`,
`SchemaTransformer.transform_record`, `SchemaTransformer.collate_fn_inference` and the explicitly
exported `build_boundary_batch_metadata`. `PreprocessedBatch`, `RecordSpec`, `RecordTarget` and
`RecordFieldTarget` are native dataclasses, not bespoke loss representations. The processing-module
function and `structure_labels` layout are lower-level implementation contracts pinned here to
2.1.0; the tutorials do not promise a stable high-level training-file interchange format for them.
No private function was called or patched by the probe.

The source inspection covered private helpers `_build_sample_records`, `_pack_record_targets`,
`_iter_inclusive_spans`, `_add_boundary_metadata`, `_resolve_gold`, `_create_dataloader`, and native
record-loss consumers to understand their contracts. The library itself calls these helpers normally.
The probe did not call a model, loss or trainer. Reading a native loss implementation does not
establish that the prepared targets produce a finite or useful numerical loss.

The **stock trainer path is not wired for this two-stage target input**:

- `ExtractorTrainer.train(...)` accepts raw data, constructs an `ExtractorDataset`, then its private
  `_create_dataloader` constructs `ExtractorCollator` itself. There is no `collate_fn`, ready-made
  loader or preprocessed-batch argument on the inspected trainer constructor or `train` signature.
- `ExtractorCollator.__call__` sends training batches to `processor.collate_fn_train`, which sets
  training mode and performs the JSON-derived/schema-sampling route. Merely calling the direct
  target builder elsewhere does not change this route. Default validation/sanitation can also
  strip richer raw field metadata, as the prior alignment inquiry established.
- There **is** a supported `ExtractorTrainer(..., processor=...)` argument. A future explicit
  processor wrapper can use that seam while leaving the trainer and native losses unchanged.
  This is a proposed adapter route, not an already implemented stock configuration switch.

The inspected trainer/collator requires that wrapper to provide:

1. `collate_fn_train(batch, ...)`, returning a native `PreprocessedBatch`. It must prepare fixed
   released `Schema` conditioning without gold, map the separate independently validated labels
   into that exact coordinate/query frame, then call the native boundary builder with targets.
   It must preserve caller capacity, strict-error and max-length settings rather than silently
   truncate, fall back, drop fields or resample the fixed schema.
2. `collate_fn_inference(batch, ...)`, including the `build_targets` keyword used for supervised
   evaluation, with targets kept independent from model-facing conditioning.
3. `change_mode(is_training=...)`, because the trainer changes processor mode around its training
   and evaluation loops. Wrapper preparation must retain its deliberate fixed-schema behavior;
   model training/evaluation state remains a separate concern.

The collator forwards `architecture`, `max_len`, `max_gold_per_query`,
`on_capacity_exceeded`, `dedupe_contained_entity_spans`, and sometimes `error_policy` and
`ignore_missing_entities`; its evaluation branch also forwards `build_targets`. A wrapper must
honor these callable requirements and preserve native `.to(device)`/mask behavior. Its raw data
transport must carry the released pack identity and independent labels through the loader without
passing them through the defective JSON-instance conditioning path. The coordinator must settle
that explicit transport/adapter contract. No wrapper, monkeypatch, custom loss, trainer fork or
training step was created here. Serialization, worker lifecycle, actual forward/loss and training
integration remain **not_run**.

## Inputs, primary sources and commands

Only existing feature-fit preparation artifacts supplied labels: protected pass23's zero-record
source22 context, one safe emitted three-record assertion group from pass24, and one pass24 record
whose sole mapped-role error was the strict ChoiceField nonpresent gap. The selected record/context
origins are in [selected-control-origins.json](attempt-002/selected-control-origins.json).
No new protected capability, DB query, author folder, calibration/final label, prediction or grade
was read. Existing schema and source contexts came from the alignment inquiry's frozen run14 inputs.
The local tokenizer was loaded offline from that recorded checkpoint snapshot; weights were not
loaded. CPU threads were bounded to four, interop and parent numerical threads to one.

Context7 was first: `/fastino-ai/gliner2`, queried separately for native fixed-schema boundary target
metadata and trainer collator integration. Its current-main results provide orientation; installed
2.1.0 controls the conclusions. Exact installed files were copied unchanged into
[raw/installed-2.1.0/](raw/installed-2.1.0/), with SHA-256 and line counts in
[source-receipts.json](attempt-002/source-receipts.json). Key source locations:

- `processing/boundary_preprocessing.py:455–677`: exported builder and independent `build_targets`;
  `:174–226`: native absence and per-instance field target construction.
- `processing/targets.py:74–100`: native absent-field/record contracts; `:374–518`: padded targets,
  strict capacity handling and zero-record `records=None` representation.
- `processor.py:404–552`: train/inference collation and native metadata attachment;
  `:553–574`: deterministic single-record transform;
  `:906–940`: schema-prefix construction per JSON occurrence.
- `processing/records.py:36–55,221+`: cardinalities and native specification compilation;
  `processing/layouts.py:108+`: target validation coverage.
- `training/trainer.py:512–575,692–700,1526–1562,1565+`: callable processor seam, internally selected
  collator and trainer input route. `training/data.py` supplies the stock file/object loader.
- `models/boundary/records.py:1011–1055,1450+`: native absent assignment and record-loss consumers;
  inspected only, not executed.

Upstream topic references are the
[boundary preprocessing source](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/boundary_preprocessing.py),
[processor](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processor.py), and
[trainer](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/trainer.py).

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-native-target-conditioning/probe_targets.py
uv run python docs/design_review/evidence/2026-11-04_m1-native-target-conditioning/probe_targets.py attempt-002
uv run python docs/design_review/evidence/2026-11-04_m1-native-target-conditioning/freeze_receipts.py
```

The first command **failed** because the harness assumed `targets.records` was a list for a fully
negative batch; native 2.1.0 intentionally returns None. Its log and executed source remain in
`attempt-001.log` and `attempt-001/executed-probe.py`. The corrected harness accepts native None
only as zero records while independently checking all native real-record masks. The second command
**passed** all nine cases; `attempt-002.log` retains its output. The tokenizer emits a checkpoint-type
warning during its config resolution; no model constructor or weight-loading call appears in this
probe. Native source files were not modified. Local `.gitattributes` routes raw/source receipts,
JSON/JSONL and logs through Git LFS. The freeze command records final owned bytes without finalizing
an accepted evidence record; the coordinator owns acceptance and broader integration.
