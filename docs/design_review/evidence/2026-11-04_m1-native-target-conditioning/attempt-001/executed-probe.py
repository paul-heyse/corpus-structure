"""No-model fixed-schema target construction using installed native boundary APIs."""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false',
                  CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  OPENBLAS_NUM_THREADS='1')

from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import json
import shutil

import torch
from transformers import AutoTokenizer
from gliner2.inference.schema import Schema
from gliner2.processor import SchemaTransformer
from gliner2.processing.boundary_preprocessing import build_boundary_batch_metadata
from gliner2.processing.targets import char_span_to_word_boundaries, word_boundaries_to_char_span

HERE = Path(__file__).resolve().parent
ALIGNMENT = HERE.parent / '2026-11-04_m1-training-alignment'


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def conditioning(batch):
    return dict(input_ids=batch.input_ids.tolist(), attention_mask=batch.attention_mask.tolist(),
        mapped_indices=batch.mapped_indices, text_tokens=batch.text_tokens,
        schema_tokens_list=batch.schema_tokens_list, task_types=batch.task_types,
        schema_counts=batch.schema_counts, text_word_indices=batch.text_word_indices.tolist(),
        text_word_mask=batch.text_word_mask.tolist(), text_word_counts=batch.text_word_counts,
        query_marker_indices=batch.query_marker_indices.tolist(),
        query_marker_mask=batch.query_marker_mask.tolist(), query_group_index=batch.query_group_index.tolist(),
        original_lengths=batch.original_lengths, original_texts=batch.original_texts,
        start_mappings=batch.start_mappings, end_mappings=batch.end_mappings)


def main():
    folder = HERE / 'attempt-001'
    folder.mkdir(exist_ok=False)
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    assert version('gliner2') == '2.1.0'
    import gliner2
    library = Path(gliner2.__file__).parent
    source_files = ('processor.py', 'processing/boundary_preprocessing.py', 'processing/records.py',
        'processing/targets.py', 'processing/layouts.py', 'models/boundary/records.py',
        'inference/schema.py', 'training/data.py', 'training/trainer.py')
    source_receipts = []
    for relative in source_files:
        source = library / relative
        target = HERE / 'raw' / 'installed-2.1.0' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        source_receipts.append(dict(path=relative, sha256=sha256(source.read_bytes()).hexdigest(),
                                    lines=len(source.read_text().splitlines())))
    input_names = ('source-contexts.jsonl', 'source-reconstruction.json', 'training-targets.jsonl',
                   'training-target-origins.jsonl', 'mapping-attempts.jsonl', 'freeze-receipts.jsonl')
    input_receipts = [dict(path=str(ALIGNMENT / name), sha256=sha256((ALIGNMENT / name).read_bytes()).hexdigest())
                      for name in input_names]
    dump(folder / 'source-receipts.json', dict(at=datetime.now(timezone.utc).isoformat(),
        libraries={name: version(name) for name in ('gliner2', 'torch', 'transformers')},
        installed_sources=source_receipts, inputs=input_receipts,
        context7=dict(library='/fastino-ai/gliner2', queries=[
            'Lower-level fixed-schema boundary metadata, zero records and native ABSENT',
            'ExtractorTrainer custom collator/preprocessed boundary batches'],
            limit='main docs supplied orientation; exact installed2.1.0 governs contracts'),
        model_loaded=False, forward=False, loss=False, training=False, db_access=False))
    contexts = {(row['source_view_id'], row['index']): row for row in rows(ALIGNMENT / 'source-contexts.jsonl')}
    cfg = json.loads((ALIGNMENT / 'source-reconstruction.json').read_text())[0]['params']
    snapshot = Path(cfg['snapshot'])
    model_config = json.loads((snapshot / 'config.json').read_text())
    max_gold = model_config['boundary_head']['max_gold_per_query']
    assert max_gold == 64
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True)
    processor = SchemaTransformer(tokenizer=tokenizer, word_splitter='whitespace')
    saved = rows(ALIGNMENT / 'training-targets.jsonl')
    origins = rows(ALIGNMENT / 'training-target-origins.jsonl')
    positive_index = next(index for index, row in enumerate(saved) if len(row['output']['json_structures']) > 1)
    positive = saved[positive_index]
    positive_origin = origins[positive_index]
    absent = next(row for row in rows(ALIGNMENT / 'mapping-attempts.jsonl') if row.get('errors')
        and all(error['reason'] == 'nonpresent classified role has no strict ChoiceField ABSENT representation'
                for error in row['errors']))
    assert absent['pass_id'] == 24 and absent['source_view_id'] == 23
    absent_roles = [error['role'] for error in absent['errors']]
    for role in absent_roles:
        assert absent['target'][role + '__state']['value'] != 'present'
        assert role not in absent['target']
    dump(folder / 'selected-control-origins.json', dict(
        zero=dict(source_view_id=22, index=0, context_id=contexts[22, 0]['context_id'],
                  label_origin='protected feature-fit pass23 zero records, as retained alignment authority'),
        multi_record=dict(ordinal=positive_index, origin=positive_origin),
        absent=dict(pass_id=absent['pass_id'], content_digest=absent['content_digest'],
                    record_id=absent['record_id'], source_view_id=23, index=absent['index'],
                    context_id=absent['context_id'], roles=absent_roles,
                    states={role: absent['target'][role+'__state']['value'] for role in absent_roles})))
    outcomes = []

    def run_case(name, context, family, target_records, *, empty_group=False, absent_sentinel=False):
        declaration = context['packs'][family]['declaration']
        schema = Schema.from_dict(declaration)
        batch = processor.collate_fn_inference([(context['text'], schema)],
            architecture='boundary', build_targets=False, max_len=None, error_policy='raise',
            max_gold_per_query=max_gold, on_capacity_exceeded='raise')
        transformed = processor.transform_record(context['text'], Schema.from_dict(declaration), max_len=None)
        assert batch.schema_tokens_list[0] == transformed.schema_tokens_list
        assert batch.input_ids[0, :batch.original_lengths[0]].tolist() == transformed.input_ids
        assert batch.text_tokens[0] == transformed.text_tokens
        assert len(batch.task_types[0]) == 1 and batch.task_types[0][0] == 'json_structures'
        spec = batch.record_specs[0][0]
        prefix_count = len(batch.text_tokens[0]) - len(batch.start_mappings[0])
        prefix = batch.text_tokens[0][:prefix_count]
        native_metadata = batch.original_schemas[0]['record_metadata']
        declared_fields = declaration['structures'][family]['fields']
        assert [field.name for field in spec.fields] == [field['name'] for field in declared_fields]
        for field, wanted in zip(spec.fields, declared_fields, strict=True):
            assert field.cardinality.value == wanted['cardinality']
            assert field.exclusive == wanted.get('exclusive', False)
        initial_conditioning = conditioning(batch)
        labels = []
        expected = []
        for record in target_records:
            instance = []
            expected_record = []
            for field in spec.fields:
                assert field.name in record, field.name
                value = record[field.name]
                if value is None:
                    assert field.allows_absent, field.name
                    spans = [(-1, -1)] if absent_sentinel else []
                    wanted = []
                elif 'choices' in value:
                    assert value['value'] in value['choices']
                    spans = [(index, index) for index, token in enumerate(prefix)
                             if token.lower() == value['value'].lower()]
                    assert spans, field.name
                    wanted = [(start, end+1) for start, end in spans]
                else:
                    assert context['text'][value['start']:value['end']] == value['text']
                    start, end = char_span_to_word_boundaries(value['start'], value['end'],
                        batch.start_mappings[0], batch.end_mappings[0])
                    assert word_boundaries_to_char_span(start, end, batch.start_mappings[0],
                        batch.end_mappings[0]) == (value['start'], value['end'])
                    spans = [(start+prefix_count, end+prefix_count-1)]
                    wanted = [(start+prefix_count, end+prefix_count)]
                instance.append(spans)
                expected_record.append(dict(role=field.name, expected=wanted, absent=value is None))
            labels.append(instance)
            expected.append(expected_record)
        group_labels = [] if empty_group else [len(labels), labels]
        structure_labels = [[group_labels]]
        layouts, targets, specs = build_boundary_batch_metadata(
            schema_tokens_list=batch.schema_tokens_list, task_types=batch.task_types,
            structure_labels=structure_labels, text_lengths=batch.text_word_counts,
            is_training=False, build_targets=True, max_gold_per_query=max_gold,
            record_metadata_list=[native_metadata], on_capacity_exceeded='raise',
            original_texts=batch.original_texts, original_schemas=batch.original_schemas)
        assert targets is not None
        assert specs == batch.record_specs and layouts == batch.query_layouts
        attached = replace(batch, query_layouts=layouts, targets=targets,
                           record_specs=specs, structure_labels=structure_labels)
        assert conditioning(attached) == initial_conditioning
        assert conditioning(batch) == initial_conditioning
        assert len(targets.records[0]) == len(target_records)
        assert int(targets.record_targets[2].sum()) == len(target_records)
        assert int(targets.record_targets[4].sum()) == len(spec.fields)
        assert int(attached.query_marker_mask.sum()) == len(spec.fields)
        checks = []
        for record, wants in zip(targets.records[0], expected, strict=True):
            for field, want in zip(spec.fields, wants, strict=True):
                actual = [span for alternatives in record.field_for_query(field.query_id).values
                          for span in alternatives]
                assert actual == want['expected'], (name, field.name, actual, want)
                checks.append(dict(role=field.name, actual=actual, expected=want['expected'],
                                   absent=want['absent'], cardinality=field.cardinality.value))
        if not target_records:
            assert not bool(targets.mention_mask.any())
            assert not bool(targets.record_targets[1].any())
            assert not bool(targets.record_targets[2].any())
            assert len(spec.fields) > 0
        receipt = dict(name=name, outcome='passed', source_view_id=context['source_view_id'],
            context_index=context['index'], context_id=context['context_id'], family=family,
            gold_records=len(target_records), native_records=len(targets.records[0]),
            real_record_mask_count=int(targets.record_targets[2].sum()),
            query_count=len(spec.fields), choice_prefix_tokens=prefix,
            prefix_count=prefix_count, schema_tokens=batch.schema_tokens_list[0],
            conditioning_sha256=digest(initial_conditioning), conditioning_unchanged=True,
            exact_transform_record_input_ids=True, record_metadata=native_metadata,
            specs={key: asdict(value) for key, value in specs[0].items()},
            structure_labels=structure_labels, native_record_targets=[asdict(item) for item in targets.records[0]],
            packed_record_mask=targets.record_targets[2].tolist(),
            packed_field_mask=targets.record_targets[4].tolist(),
            packed_group_mask=targets.record_targets[8].tolist(),
            mention_mask_count=int(targets.mention_mask.sum()),
            native_absent_checks=checks, source_text_sha256=sha256(context['text'].encode()).hexdigest(),
            consumed_text_sha256=sha256(batch.original_texts[0].encode()).hexdigest(),
            consumed_text_suffix=batch.original_texts[0][len(context['text']):])
        dump(folder / (name + '.json'), receipt)
        outcomes.append(receipt)

    zero = contexts[22, 0]
    assert zero['text'] == 'Chapter 5'
    for family in ('definition', 'assertion', 'measurement'):
        run_case('zero-' + family + '-count0', zero, family, [])
        run_case('zero-' + family + '-empty-group', zero, family, [], empty_group=True)
    context = contexts[positive_origin['source_view_id'], positive_origin['index']]
    assert positive['input'] == context['text']
    family = positive_origin['family']
    run_case('multi-positive-fixed-prefix', context, family,
             [record[family] for record in positive['output']['json_structures']])
    context = contexts[absent['source_view_id'], absent['index']]
    target = dict(absent['target'], **{role: None for role in absent_roles})
    run_case('nonpresent-choice-empty-list', context, absent['family'], [target])
    run_case('nonpresent-choice-native-sentinel', context, absent['family'], [target], absent_sentinel=True)
    summary = dict(outcome='passed', at=datetime.now(timezone.utc).isoformat(), gliner2=version('gliner2'),
        cases=len(outcomes), zero_cases=sum(item['gold_records']==0 for item in outcomes),
        positive_control_records=next(item['gold_records'] for item in outcomes if item['name']=='multi-positive-fixed-prefix'),
        nonpresent_classified_roles=absent_roles, exact_inference_conditioning_all=True,
        field_cardinality_exclusivity_all=True, no_phantom_zero_records=True,
        native_absence_preserves_semantic_states=True,
        model_loaded=False, forward=False, loss=False, training=False,
        db_access=False, heldout_access=False, max_gold_per_query=max_gold,
        limits=['metadata-only; no numerical or optimizer/trainer integration claim',
            'current JSONL and strict ChoiceField limitations remain',
            'unmodified trainer does not expose a collator/preprocessed-batch argument; processor injection exists',
            'target builder preserves supplied specifications; caller still owns faithful gold/cardinality/span validation'])
    dump(folder / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
