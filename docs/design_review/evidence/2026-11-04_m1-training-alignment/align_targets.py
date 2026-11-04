"""Bounded exact C-target mapping and native collation; never execute a model."""
import os
import sys
sys.dont_write_bytecode=True
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, fields
from hashlib import sha256
from pathlib import Path
import torch
from transformers import AutoTokenizer
from gliner2.processor import SchemaTransformer, SamplingConfig
from gliner2.processing.targets import char_span_to_word_boundaries, word_boundaries_to_char_span
from gliner2.training.data import InputExample, TrainingDataset
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import SourceInterval
from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity
import prepare_contexts as source

HERE=Path(__file__).resolve().parent
torch.set_num_threads(4)
torch.set_num_interop_threads(1)
random.seed(0)
refs=json.loads((HERE/'feature-fit-protected.json').read_text())
assert [r['pass_id'] for r in refs]==[23,24]
assert all(r['sampling']['partition']=='feature_fit' for r in refs)
cfg=source.cfg
cfg.profile().verify_artifacts()
checkpoint_config=json.loads((cfg.snapshot/'config.json').read_text())
max_gold=checkpoint_config['boundary_head']['max_gold_per_query']
tokenizer=AutoTokenizer.from_pretrained(str(cfg.snapshot),local_files_only=True)
sampling=SamplingConfig(**{f.name: False if f.type is bool or f.name.startswith('shuffle') else 0.0 for f in fields(SamplingConfig) if f.name!='max_num_labels'})
processor=SchemaTransformer(tokenizer=tokenizer,sampling_config=sampling,word_splitter='whitespace')
# Description selection and classification-prefix order are stochastic even with
# zero sampling probabilities; record their effective realization in every batch.
def dump(path,rows):
    # Object insertion order conditions native queries and descriptions. A
    # canonical sorted-key writer silently changes that contract on reload.
    (HERE/path).write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n' for x in rows))

def anchor_ranges(context, anchors):
    ranges=[]
    for anchor in anchors:
        if anchor['space']!='selected_projection' or anchor['precision']!='exact':
            raise ValueError('gold span is not an exact selected-projection anchor')
        matches=[]
        for interval in context.intervals:
            if not isinstance(interval,SourceInterval): continue
            if interval.source.source_view_id!=anchor['pin']['source_view_id']: continue
            if interval.source_start<=anchor['start']<anchor['end']<=interval.source_end:
                locator=json.loads(interval.item_locator.removeprefix('pdf:'))
                pointer=locator['pointer']
                if interval.cell_index is not None and interval.source_field=='cell_text':
                    pointer+=f'/data/table_cells/{interval.cell_index}'
                if pointer!=anchor['pointer']: continue
                start=interval.model_start+anchor['start']-interval.source_start
                end=start+anchor['end']-anchor['start']
                if context.text[start:end]==anchor['source_piece']: matches.append((start,end))
        if len(matches)!=1: raise ValueError('gold piece not uniquely present in this bounded context')
        ranges.append(matches[0])
    if not ranges: raise ValueError('no exact gold literal/cue anchors')
    if ranges!=sorted(ranges): raise ValueError('gold piece ordering differs from context')
    start,end=ranges[0][0],ranges[-1][1]
    reading=context.read_span(start,end,prepared=source.prepared,policy='synthetic-whitespace-1',literal=context.text[start:end])
    expected=[(a['pin']['source_view_id'],a['start'],a['end'],a['source_piece']) for a in anchors]
    actual=[(p.source.source_view_id,p.start,p.end,p.quote) for p in reading.pieces]
    if actual!=expected: raise ValueError('bounding span includes real text outside the gold pieces')
    tokens=list(processor.word_splitter(context.text,lower=True))
    starts=[t[1] for t in tokens]; ends=[t[2] for t in tokens]
    word_span=char_span_to_word_boundaries(start,end,starts,ends)
    roundtrip=word_boundaries_to_char_span(*word_span,starts,ends)
    if roundtrip!=(start,end):
        raise ValueError(f'word boundary broadens gold chars {(start,end)} to {roundtrip}')
    reread=context.read_span(*roundtrip,prepared=source.prepared,policy='synthetic-whitespace-1')
    if reread.original_pieces!=reading.original_pieces: raise ValueError('source-token-source roundtrip differs')
    return dict(text=context.text[start:end],start=start,end=end),dict(reading=reading.receipt(),source_pieces=expected,word_span=word_span)

def mapped_record(record,context,pack):
    declaration=json.loads(pack.declaration_json)['structures'][record['family']]
    gold={f['role']:f for f in record['fields']}
    anchors={a['anchor_id']:a for a in record['anchors']}
    sets={s['set_id']:s for s in record['evidence_sets']}
    result={}; receipts={}; errors=[]
    # Native and normalized fields stay under their structural/transform owner.
    for declaration_field in declaration['fields']:
        name=declaration_field['name']; role=name.removesuffix('__state').removesuffix('__cue')
        field=gold.get(role)
        if field is None:
            errors.append(dict(role=name,reason='released model role missing from gold record')); continue
        if name.endswith('__state'):
            result[name]=dict(value=field['state'],choices=declaration_field['choices']); continue
        if name.endswith('__cue'):
            selected=[sets[k] for k in field.get('evidence_sets',[]) if sets[k]['usage']=='classification_cue']
            aa=[anchors[k] for s in selected for k in s['anchors']]
            if not aa:
                if field['state']=='present': errors.append(dict(role=name,reason='present classification lacks independently located cue'))
                else: result[name]=None
                continue
        elif declaration_field.get('choices'):
            if field['state']=='present':
                value=field['value']['label']
                if value not in declaration_field['choices']: errors.append(dict(role=name,reason='gold label outside released choices'))
                else: result[name]=dict(value=value,choices=declaration_field['choices'])
            else:
                # Raw collation can encode [] but strict ChoiceField cannot;
                # retain as a mapping gap rather than dropping the choices.
                errors.append(dict(role=name,reason='nonpresent classified role has no strict ChoiceField ABSENT representation'))
            continue
        elif field['state']!='present': result[name]=None; continue
        else:
            selected=[sets[k] for k in field.get('evidence_sets',[]) if sets[k]['usage']=='literal']
            aa=[anchors[k] for s in selected for k in s['anchors']]
        try:
            result[name],receipts[name]=anchor_ranges(context,aa)
        except ValueError as error: errors.append(dict(role=name,reason=str(error)))
    return result,receipts,errors

def schema_for(family,declaration,instances):
    return dict(json_structures=[{family:x} for x in instances],
      record_metadata={family:dict(mode=declaration['mode'],anchor=declaration['anchor'],fields={f['name']:dict(cardinality=f['cardinality'],exclusive=f.get('exclusive',False)) for f in declaration['fields']})},
      json_descriptions={family:{f['name']:f['description'] for f in declaration['fields'] if f.get('description')}})

def collate(text,schema):
    batch=processor.collate_fn_train([(text,schema)],architecture='boundary',max_len=None,error_policy='raise',max_gold_per_query=max_gold,on_capacity_exceeded='raise')
    specs=batch.record_specs[0]
    records=batch.targets.records[0] if batch.targets.records else []
    return batch,dict(original_text_unchanged=batch.original_texts[0]==text,original_text_sha256=sha256(batch.original_texts[0].encode()).hexdigest(),
      schema_tokens=batch.schema_tokens_list[0],structure_labels=batch.structure_labels[0],record_specs={k:asdict(v) for k,v in specs.items()},records=[asdict(r) for r in records],
      mention_pairs=batch.targets.mention_pairs.tolist(),mention_mask=batch.targets.mention_mask.tolist(),record_target_masks=batch.targets.record_targets[2].tolist() if batch.targets.record_targets else [],
      text_tokens=batch.text_tokens[0],start_mappings=batch.start_mappings[0],end_mappings=batch.end_mappings[0],subwords=batch.original_lengths[0],text_words=batch.text_word_counts[0],original_schemas=batch.original_schemas)

checks=[]
context_wire={(r['source_view_id'],r['index']):r for r in source.contexts if 'context_id' in r}
for receipt in source.receipts:
    for report in receipt['reports']:
        if 'context_id' not in report: continue
        wire=context_wire[receipt['source_view_id'],report['context']]
        consumed=wire['text']+('' if wire['text'].endswith(('.','!','?')) else '.')
        check=dict(source_view_id=receipt['source_view_id'],index=report['context'],family=report['family'],context_equal=report['context_id']==wire['context_id']==report['context_digest'],pack_equal=report['pack']==wire['packs'][report['family']]['fingerprint'],consumed_equal=sha256(consumed.encode()).hexdigest()==report['preparation']['consumed_text_sha256'],effective_profile_present=report['effective_profile_ref'] in receipt['effective_profiles'])
        checks.append(check)
dump('context-verification.jsonl',checks)
assert all(all(v for k,v in c.items() if k.endswith(('_equal','_present'))) for c in checks)

record_audit=[]; attempts=[]; eligible=defaultdict(list); complete_candidates=defaultdict(list); sidecars=[]
for reference in refs:
    for record in reference['authored']['records']:
        assert all(anchor_identity(a)==a['anchor_id'] for a in record['anchors'])
        assert all(evidence_set_identity(e)==e['set_id'] for e in record['evidence_sets'])
        origin=dict(pass_id=reference['pass_id'],content_digest=reference['content_digest'],record_id=record['record_id'],source_view_id=record['pin']['source_view_id'],family=record['family'])
        candidates=[]
        for key,context in source.live_contexts.items():
            if key[0]!=origin['source_view_id'] or record['family'] not in context_wire[key]['packs']: continue
            pack=source.live_packs[key][record['family']]
            target,receipts,errors=mapped_record(record,context,pack)
            # Store every candidate containing at least one exact gold literal piece.
            if receipts or not errors:
                entry=dict(**origin,index=key[1],context_id=context.dependency_digest,target=target,mappings=receipts,errors=errors)
                attempts.append(entry)
            if not errors:
                candidates.append((key,target,receipts))
                complete_candidates[key,record['family']].append((record,target,receipts,origin))
        if candidates:
            # Deterministic smallest exact actual context, never prediction-selected.
            key,target,mappings=min(candidates,key=lambda x:(len(source.live_contexts[x[0]].text),x[0][1]))
            eligible[key,record['family']].append((record,target,mappings,origin))
            record_audit.append(dict(**origin,status='mapped_complete',index=key[1],context_id=source.live_contexts[key].dependency_digest))
        else:
            relevant=[x for x in attempts if x['record_id']==record['record_id']]
            reasons=Counter(e['reason'] for x in relevant for e in x['errors'])
            record_audit.append(dict(**origin,status='excluded',reasons=dict(reasons) or {'no bounded family context contains an exactly word-aligned gold literal role':1}))
dump('record-alignment.jsonl',record_audit);dump('mapping-attempts.jsonl',attempts)

# Enrich each selected context with every complete same-family C record present
# there. Selecting a smallest context for one record must not erase its neighbors.
eligible={key:complete_candidates[key] for key in eligible}

dataset=[];collated=[];failed=[]
for (key,family),rows in sorted(eligible.items()):
    context=source.live_contexts[key]; pack=source.live_packs[key][family]
    declaration=json.loads(pack.declaration_json)['structures'][family]
    # Do not publish a partial-family example: any overlapping but excluded C
    # instance would otherwise become accidental negative supervision.
    all_family=[r for ref in refs for r in ref['authored']['records'] if r['pin']['source_view_id']==key[0] and r['family']==family]
    excluded_overlaps=[]
    for r in all_family:
        if any(a['record_id']==r['record_id'] for a,_,_,_ in rows): continue
        anchor_role=declaration['anchor']
        primary_sets=[s for s in r['evidence_sets'] if s['role']==anchor_role and s['usage']=='literal']
        primary_ids={a for s in primary_sets for a in s['anchors']}
        for a in r['anchors']:
            if a['anchor_id'] not in primary_ids: continue
            if a.get('space')!='selected_projection' or a.get('precision')!='exact': continue
            if any(isinstance(i,SourceInterval) and i.source.source_view_id==a['pin']['source_view_id'] and i.source_start<a['end'] and i.source_end>a['start'] for i in context.intervals):
                excluded_overlaps.append(r['record_id']);break
    schema=schema_for(family,declaration,[r[1] for r in rows])
    metadata=dict(source_view_id=key[0],index=key[1],family=family,context_id=context.dependency_digest,pack_fingerprint=pack.fingerprint,gold_records=[r[3] for r in rows],excluded_overlaps=excluded_overlaps)
    validation=TrainingDataset([InputExample.from_dict(dict(input=context.text,output=schema))]).validate(raise_on_error=False)
    metadata['validation']=validation
    try:
        batch,audit=collate(context.text,schema)
        audit.update(metadata)
        audit['expected_records']=len(rows)
        audit['record_count_equal']=len(batch.targets.records[0])==len(rows)
        # Exact field metadata (including optional anchor cardinality) must survive.
        spec=next(iter(batch.record_specs[0].values()))
        audit['field_universe_equal']=[f.name for f in spec.fields]==[f['name'] for f in declaration['fields']]
        audit['field_contract_equal']=all(f.cardinality.value==d['cardinality'] and f.exclusive==d.get('exclusive',False) for f,d in zip(spec.fields,declaration['fields'],strict=True))
        audit['inputexample_serialization_changed']=InputExample.from_dict(dict(input=context.text,output=schema)).to_dict()!=dict(input=context.text,output=schema)
        audit['target_checks']=[]
        prefix=len(batch.text_tokens[0])-len(batch.start_mappings[0])
        for native_record,row in zip(batch.targets.records[0],rows,strict=True):
            for native_field in spec.fields:
                expected=row[1][native_field.name]
                values=native_record.field_for_query(native_field.query_id).values
                actual_spans=[span for alternatives in values for span in alternatives]
                if isinstance(expected,dict) and 'start' in expected:
                    a,b=row[2][native_field.name]['word_span']; expected_spans=[(a+prefix,b+prefix)]
                    okay=actual_spans==expected_spans
                elif expected is None:
                    expected_spans=[];okay=not actual_spans
                else:
                    expected_spans=expected['value'];okay=bool(actual_spans) and all(b==a+1 and a<prefix and batch.text_tokens[0][a].lower()==expected['value'].lower() for a,b in actual_spans)
                audit['target_checks'].append(dict(record_id=row[0]['record_id'],role=native_field.name,expected=expected_spans,actual=actual_spans,equal=okay))
        audit['all_targets_equal']=all(c['equal'] for c in audit['target_checks'])
        audit['only_released_suffix']=batch.original_texts[0]==context.text+('' if context.text.endswith(('.','!','?')) else '.')
        audit['descriptions_retained']=all(f['description'] in batch.schema_tokens_list[0][0][2] for f in declaration['fields'] if f.get('description'))
        # A useful strict dataset must have no overlapping excluded instance, no
        # record loss, and the exact current field universe.
        usable=validation['invalid']==0 and not excluded_overlaps and audit['record_count_equal'] and audit['field_universe_equal'] and audit['field_contract_equal'] and audit['all_targets_equal'] and audit['only_released_suffix']
        audit['usable']=usable
        collated.append(audit)
        if usable:
            dataset.append(dict(input=context.text,output=schema))
            sidecars.append(dict(**metadata,mappings=[r[2] for r in rows],native_structural_gold=[dict(record_id=r[0]['record_id'],fields=[f for f in r[0]['fields'] if f['kind'] not in ('literal','classified')]) for r in rows]))
    except Exception as error: failed.append(dict(**metadata,error_type=type(error).__name__,error=str(error)))
dump('training-targets.jsonl',dataset);dump('training-target-origins.jsonl',sidecars);dump('collated-targets.jsonl',collated);dump('collation-failures.jsonl',failed)

# Explicit zero-record source22 is the sole negative used here. Collate native
# representations of that same full pack; never invent a semantic state label.
negative=[]
key=(22,0);context=source.live_contexts[key]
for family,pack in source.live_packs[key].items():
    if family not in context_wire[key]['packs']: continue
    declaration=json.loads(pack.declaration_json)['structures'][family]
    for variant in ('empty_structures','all_null','empty_choice_lists','none_choices'):
        instance={f['name']:None for f in declaration['fields']}
        if variant in ('empty_choice_lists','none_choices'):
            for f in declaration['fields']:
                if f.get('choices'):instance[f['name']]=dict(value=[] if variant=='empty_choice_lists' else None,choices=f['choices'])
        schema=schema_for(family,declaration,[] if variant=='empty_structures' else [instance])
        result=dict(source_view_id=22,index=0,pass_id=23,context_id=context.dependency_digest,family=family,variant=variant,input=context.text,output=schema)
        result['validation']=TrainingDataset([InputExample.from_dict(dict(input=context.text,output=schema))]).validate(raise_on_error=False)
        try:
            batch,audit=collate(context.text,schema)
            result['collated']=audit
            result['record_count']=len(batch.targets.records[0]) if batch.targets.records else 0
            result['field_count']=sum(len(s.fields) for s in batch.record_specs[0].values())
            result['expected_field_count']=len(declaration['fields'])
        except Exception as error:result.update(error_type=type(error).__name__,error=str(error))
        negative.append(result)
dump('negative-collation.jsonl',negative)
summary=dict(standing='preparatory_alignment_not_training',feature_fit_passes=[r['pass_id'] for r in refs],feature_fit_records=len(record_audit),families=dict(Counter(r['family'] for r in record_audit)),record_status=dict(Counter(r['status'] for r in record_audit)),mapped_families=dict(Counter(r['family'] for r in record_audit if r['status']=='mapped_complete')),actual_contexts=len(source.contexts),verified_actual_reports=len(checks),mapped_context_family_groups=len(eligible),collated_groups=len(collated),collation_failures=len(failed),usable_examples=len(dataset),usable_gold_records=sum(len(r['gold_records']) for r in sidecars),excluded_overlap_groups=sum(bool(x['excluded_overlaps']) for x in collated),text_mutated_groups=sum(not x['original_text_unchanged'] for x in collated),field_contract_changed_groups=sum(not x['field_contract_equal'] for x in collated),target_mismatch_groups=sum(not x['all_targets_equal'] for x in collated),descriptions_omitted_groups=sum(not x['descriptions_retained'] for x in collated),max_gold_per_query=max_gold,training_candidate_budget=checkpoint_config['boundary_head']['training_candidate_budget'],no_inference=True,no_model_loaded=True,no_training=True)
(HERE/'alignment-summary.json').write_bytes(canonical_bytes(summary))
print(json.dumps(summary,indent=2))
