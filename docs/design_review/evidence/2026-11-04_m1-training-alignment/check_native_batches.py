"""No-forward native target verification of the bounded emitted raw dataset."""
import os
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import json
from pathlib import Path
from dataclasses import asdict
from hashlib import sha256
from collections import Counter
import torch
from transformers import AutoTokenizer
from gliner2.processor import SchemaTransformer
from gliner2.training.data import TrainingDataset, InputExample
from gliner2.processing.targets import char_span_to_word_boundaries
from gliner2.inference.schema import Schema
from corpus_structure.semantic.identity import canonical_bytes

HERE=Path(__file__).resolve().parent
torch.set_num_threads(4);torch.set_num_interop_threads(1)
inputs=[json.loads(x) for x in (HERE/'training-targets.jsonl').read_text().splitlines()]
origins=[json.loads(x) for x in (HERE/'training-target-origins.jsonl').read_text().splitlines()]
configuration=json.loads((HERE/'source-reconstruction.json').read_text())[0]['params']
snapshot=Path(configuration['snapshot'])
config=json.loads((snapshot/'config.json').read_text())
processor=SchemaTransformer(tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True),word_splitter='whitespace')
strict_report=TrainingDataset([InputExample.from_dict(x) for x in inputs]).validate()
results=[]
contexts={(r['source_view_id'],r['index']):r for r in map(json.loads,(HERE/'source-contexts.jsonl').read_text().splitlines()) if 'packs' in r}
for ordinal,(row,origin) in enumerate(zip(inputs,origins,strict=True)):
    assert row['input']==contexts[origin['source_view_id'],origin['index']]['text']
    # This is the native processor's deterministic GOLD-building branch. No
    # model, encoder, extract call, inference engine or loss step exists here.
    batch=processor.collate_fn_inference([(row['input'],row['output'])],architecture='boundary',build_targets=True,max_len=None,error_policy='raise',max_gold_per_query=config['boundary_head']['max_gold_per_query'],on_capacity_exceeded='raise')
    spec=next(iter(batch.record_specs[0].values()))
    native_records=batch.targets.records[0]
    prefix=len(batch.text_tokens[0])-len(batch.start_mappings[0])
    checks=[]
    for native_record,structured in zip(native_records,row['output']['json_structures'],strict=True):
        target=structured[origin['family']]
        for field in spec.fields:
            value=target[field.name]
            actual=[s for alternatives in native_record.field_for_query(field.query_id).values for s in alternatives]
            if value is None:okay=not actual
            elif 'choices' in value:okay=bool(actual) and all(b==a+1 and a<prefix and batch.text_tokens[0][a].lower()==value['value'].lower() for a,b in actual)
            else:
                a,b=char_span_to_word_boundaries(value['start'],value['end'],batch.start_mappings[0],batch.end_mappings[0])
                okay=actual==[(a+prefix,b+prefix)]
            checks.append(dict(role=field.name,equal=okay,actual=actual))
    expected=[x for x in row['output']['json_structures']]
    descriptions=row['output']['json_descriptions'][origin['family']]
    pack=contexts[origin['source_view_id'],origin['index']]['packs'][origin['family']]['declaration']
    inference_preparation=processor.transform_record(row['input'],Schema.from_dict(pack),max_len=None)
    inference_prefix=len(inference_preparation.text_tokens)-len(inference_preparation.start_token_idx)
    result=dict(ordinal=ordinal,source_view_id=origin['source_view_id'],index=origin['index'],family=origin['family'],context_id=origin['context_id'],input_sha256=sha256(row['input'].encode()).hexdigest(),records=len(native_records),record_count_equal=len(native_records)==len(expected),target_checks=checks,all_targets_equal=all(c['equal'] for c in checks),descriptions_retained=all(d in batch.schema_tokens_list[0][0][2] for d in descriptions.values()),schema_tokens=batch.schema_tokens_list[0],specs={k:asdict(v) for k,v in batch.record_specs[0].items()},native_records=[asdict(r) for r in native_records],prefix_tokens=batch.text_tokens[0][:prefix],original_input_unchanged_in_jsonl=True,collator_suffix=batch.original_texts[0][len(row['input']):],subwords=batch.original_lengths[0],word_count=batch.text_word_counts[0])
    assert result['record_count_equal'] and result['all_targets_equal'] and result['descriptions_retained']
    result['field_contract_equal']=all(f.cardinality.value==row['output']['record_metadata'][origin['family']]['fields'][f.name]['cardinality'] and f.exclusive==row['output']['record_metadata'][origin['family']]['fields'][f.name]['exclusive'] for f in spec.fields)
    result['actual_pack_schema_tokens_equal']=batch.schema_tokens_list[0]==inference_preparation.schema_tokens_list
    result['actual_pack_prefix_equal']=batch.text_tokens[0][:prefix]==inference_preparation.text_tokens[:inference_prefix]
    result['actual_pack_prefix_count']=inference_prefix
    result['target_prefix_count']=prefix
    result['exact_actual_pack_conditioning']=result['actual_pack_schema_tokens_equal'] and result['actual_pack_prefix_equal']
    assert result['field_contract_equal']
    results.append(result)
(HERE/'deterministic-native-targets.jsonl').write_text(''.join(canonical_bytes(x).decode()+'\n' for x in results))
collated=[json.loads(x) for x in (HERE/'collated-targets.jsonl').read_text().splitlines()]
failures=[json.loads(x) for x in (HERE/'collation-failures.jsonl').read_text().splitlines()]
records=[json.loads(x) for x in (HERE/'record-alignment.jsonl').read_text().splitlines()]
included={r['record_id'] for origin in origins for r in origin['gold_records']}
disposition=[]
attempts=[json.loads(x) for x in (HERE/'mapping-attempts.jsonl').read_text().splitlines()]
for r in records:
    current=dict(r)
    if r['record_id'] in included:current['training_disposition']='included_in_bounded_raw_targets'
    elif r['status']=='excluded':
        current['training_disposition']='excluded_source_role_alignment'
        relevant=[a for a in attempts if a['record_id']==r['record_id']]
        if relevant:
            nearest=min(relevant,key=lambda a:(len(a['errors']),-len(a['mappings']),a['index']))
            current['nearest_context_diagnostic']=dict(index=nearest['index'],context_id=nearest['context_id'],role_reasons=nearest['errors'])
        else:
            current['nearest_context_diagnostic']=dict(role_reasons=[dict(role='all_present_model_roles',reason='no bounded actual context contains an exactly mapped literal role; no target or negative emitted')])
    else:
        current['training_disposition']='mapped_but_no_complete_safe_native_group'
        current['group_limitations']=[dict(index=g['index'],family=g['family'],overlapping_incomplete_anchor_records=g.get('excluded_overlaps',[]),error=g.get('error'),record_count_equal=g.get('record_count_equal'),all_targets_equal=g.get('all_targets_equal')) for g in collated+failures if any(x['record_id']==r['record_id'] for x in g['gold_records'])]
    disposition.append(current)
(HERE/'final-record-disposition.jsonl').write_text(''.join(canonical_bytes(x).decode()+'\n' for x in disposition))
summary=dict(outcome='passed',scope='native data validation and deterministic gold collation only; no model or forward execution',strict_dataset_validation=strict_report,examples=len(results),record_appearances=sum(r['records'] for r in results),unique_gold_records=len(included),families=dict(Counter(r['family'] for r in results)),dispositions=dict(Counter(r['training_disposition'] for r in disposition)),all_descriptions_retained=True,all_collated_targets_equal=True,all_cardinality_exclusivity_metadata_preserved=True,exact_actual_pack_conditioning_groups=sum(r['exact_actual_pack_conditioning'] for r in results),actual_pack_prefix_changed_groups=sum(not r['actual_pack_prefix_equal'] for r in results),actual_pack_schema_changed_groups=sum(not r['actual_pack_schema_tokens_equal'] for r in results),training_not_authorized=True)
(HERE/'native-check-summary.json').write_bytes(canonical_bytes(summary))
print(json.dumps(summary,indent=2))
