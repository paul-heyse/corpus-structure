"""Source-only segmentation and formula-neighborhood preparation; no model calls."""
import os
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
import json
import sys
import argparse
from bisect import bisect_left
from collections import Counter,defaultdict
from dataclasses import asdict
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import torch
from transformers import AutoTokenizer
from gliner2.processor import SchemaTransformer
from gliner2.inference.schema import Schema
from gliner2.processing.targets import char_span_to_word_boundaries,word_boundaries_to_char_span
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import anchor_identity,evidence_set_identity
from corpus_structure.semantic.source_contexts import NativeSourceContext,SourceSlice,SyntheticText,SourceInterval,ContextRefused
from corpus_structure.methods.m1_source import M1Config,configured_packs
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.ingest.annotations import AnnotationProfile

HERE=Path(__file__).resolve().parent
ALIGN=HERE.parent/'2026-11-04_m1-training-alignment'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',default='attempt-001')
parser.add_argument('--expanded-chars',type=int,default=2048)
parser.add_argument('--expanded-pieces',type=int,default=64)
parser.add_argument('--expanded-codepoints-only',action='store_true')
args=parser.parse_args()
OUT=HERE/args.output
OUT.mkdir(exist_ok=False)
torch.set_num_threads(4);torch.set_num_interop_threads(1)
def dump(name,rows):
    (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n' for r in rows))
def digest(path):return sha256(path.read_bytes()).hexdigest()
class UnicodeCodepoints:
    """Native callable: every non-whitespace source codepoint, original offsets."""
    def __call__(self,text,lower=True):
        for index,char in enumerate(text):
            if not char.isspace():yield (char.lower() if lower else char,index,index+1)

configuration=json.loads((ALIGN/'source-reconstruction.json').read_text())
cfg=M1Config.model_validate(configuration[0]['params'])
cfg.profile().verify_artifacts()
checkpoint=json.loads((cfg.snapshot/'config.json').read_text())
tokenizer=AutoTokenizer.from_pretrained(str(cfg.snapshot),local_files_only=True)
processors={name:SchemaTransformer(tokenizer=tokenizer,word_splitter=splitter) for name,splitter in [('whitespace','whitespace'),('codepoints',UnicodeCodepoints())]}
references=json.loads((ALIGN/'feature-fit-protected.json').read_text())
assert [r['pass_id'] for r in references]==[23,24]
assert all(r['sampling']['partition']=='feature_fit' for r in references)
gold=[r for ref in references for r in ref['authored']['records']]
stored={(r['source_view_id'],r['index']):r for r in map(json.loads,(ALIGN/'source-contexts.jsonl').read_text().splitlines())}
base={};expanded={};packs={};source_receipts=[];expansion_receipts=[]
with open_runtime_engine(Settings(),'m1-source-boundary-fit',purpose='read') as engine,engine.connect() as conn:
    prepared=open_release(conn,references[0]['authored']['release_id'])
    reader=BoundReader(conn,14,prepared,13,analysis=False)
    for metadata in configuration:
        source_id=metadata['source_view_id']
        local_cfg=M1Config.model_validate(metadata['params'])
        profile=AnnotationProfile(local_cfg.sentences)
        view=reader.source_view(source_id)
        annotations,errors,annotation=consume_annotations(reader,view,profile)
        product=prepare_source(view,profile=profile,max_chars=2048,max_pieces=64,max_annotation_chars=local_cfg.max_annotation_chars,reader=reader,persisted_annotations=annotations,annotation_errors=errors)
        source_packs=configured_packs(prepared,local_cfg)
        source_receipts.append(dict(source_view_id=source_id,annotations=len(annotations),annotation_input_hash=annotation['input_hash'],annotation_configuration_hash=annotation['configuration_hash'],errors=errors,projection_digest=view.ref.projection_digest,source_key=view.ref.key,annotation_digest=sha256(canonical_bytes(annotation)).hexdigest()))
        # Existing persisted paragraph/list/caption blocks are source custody;
        # neither gold labels nor producer output select or crop these blocks.
        blocks=sorted([a for a in annotations if a.kind in {'paragraph','list_item','caption'} and view.text[a.block_start:a.block_end].strip()],key=lambda a:(a.block_start,a.block_end,a.block_id))
        for index,selection in enumerate(product.selections):
            context=selection.context(product.source,max_chars=2048,max_pieces=64,related=product.related,preparation=product.preparation)
            key=(source_id,index)
            assert context.dependency_digest==stored[key]['context_id'] and context.text==stored[key]['text']
            base[key]=context;packs[key]={family:source_packs[family] for family in selection.families}
            if selection.families!=('formula_context',):continue
            direct=[p for p in view.pieces if p['kind']=='native_text' and p['item_ref']==selection.region]
            receipt=dict(source_view_id=source_id,index=index,primary_formula=selection.region,policy='whole-native-block-neighbors-1',max_chars=args.expanded_chars,max_pieces=args.expanded_pieces,selection_independent_of_gold=True)
            if not direct:
                receipt.update(outcome='blocked',reason='primary formula has no native projection pieces');expansion_receipts.append(receipt);continue
            first,last=direct[0]['start'],direct[-1]['end']
            containing=[(i,b) for i,b in enumerate(blocks) if b.block_start<=first<last<=b.block_end]
            if not containing:
                receipt.update(outcome='blocked',reason='no complete persisted native block contains primary formula');expansion_receipts.append(receipt);continue
            center,block=min(containing,key=lambda x:(x[1].block_end-x[1].block_start,x[1].block_id))
            selected=[block];left=center-1;right=center+1;stopped=set();limits=[]
            def construct(chosen):
                ordered=sorted(chosen,key=lambda b:(b.block_start,b.block_end,b.block_id))
                pieces=[]
                for b in ordered:
                    if pieces:pieces.append(SyntheticText('\n','whole native paragraph separator; no evidence'))
                    pieces.append(SourceSlice(source_id,b.block_start,b.block_end))
                return NativeSourceContext(product.source,(),tuple(pieces),'formula_context','whole-native-block-neighbors-1','nearest coherent whole native blocks around primary formula; semantic attachment unresolved',max_chars=args.expanded_chars,max_pieces=args.expanded_pieces,version=2,preparation=product.preparation)
            try:new_context=construct(selected)
            except ContextRefused as error:
                receipt.update(outcome='blocked',reason=str(error));expansion_receipts.append(receipt);continue
            # Breadth one block on each side, then the next, without skipping
            # an oversized nearest neighbor to reach a semantically convenient one.
            while len(stopped)<2:
                progress=False
                for direction in ('preceding','following'):
                    if direction in stopped:continue
                    candidate_index=left if direction=='preceding' else right
                    if not 0<=candidate_index<len(blocks):stopped.add(direction);continue
                    candidate=blocks[candidate_index]
                    if direction=='preceding':left-=1
                    else:right+=1
                    if any(not (candidate.block_end<=b.block_start or b.block_end<=candidate.block_start) for b in selected):
                        stopped.add(direction);limits.append(dict(direction=direction,block=candidate.block_id,reason='overlapping native block; no arbitrary duplicate/crop'));continue
                    try:proposal=construct([*selected,candidate])
                    except ContextRefused as error:
                        stopped.add(direction);limits.append(dict(direction=direction,block=candidate.block_id,reason=str(error)));continue
                    selected.append(candidate);new_context=proposal;progress=True
                if not progress and len(stopped)==2:break
            expanded[key]=new_context
            receipt.update(outcome='prepared',context_id=new_context.dependency_digest,chars=len(new_context.text),intervals=len(new_context.intervals),selected_blocks=[dict(block_id=b.block_id,kind=b.kind,start=b.block_start,end=b.block_end,text_digest=b.text_digest) for b in sorted(selected,key=lambda b:b.block_start)],limits=limits)
            expansion_receipts.append(receipt)
assert len(base)==148
dump('source-reconstruction.jsonl',source_receipts)
dump('formula-expansion.jsonl',expansion_receipts)
dump('expanded-contexts.jsonl',[dict(source_view_id=key[0],index=key[1],context_id=c.dependency_digest,text=c.text,intervals=[asdict(i) for i in c.intervals],original_primary_formula=stored[key]['selection']['region']) for key,c in expanded.items()])

budgets=[];token_maps={}
for variant,contexts in [('original',base),('expanded',expanded)]:
    for key,context in contexts.items():
        for segmentation,processor in processors.items():
            if variant=='expanded' and args.expanded_codepoints_only and segmentation!='codepoints':continue
            tokens=list(processor.word_splitter(context.text,lower=True))
            token_maps[variant,key,segmentation]=([t[1] for t in tokens],[t[2] for t in tokens])
            for family,pack in packs[key].items():
                if variant=='expanded' and family!='formula_context':continue
                native=processor.transform_record(context.text,pack.compile(),max_len=None)
                source_words=len(native.start_token_idx)
                prefix=len(native.text_tokens)-source_words
                budgets.append(dict(variant=variant,segmentation=segmentation,source_view_id=key[0],index=key[1],family=family,context_id=context.dependency_digest,chars=len(context.text),source_word_tokens=source_words,prefix_tokens=prefix,model_word_tokens=len(native.text_tokens),subwords=len(native.input_ids),facade_word_bound_pass=source_words<=512,facade_subword_bound_pass=len(native.input_ids)<=2048,checkpoint_source_word_bound_pass=source_words<=checkpoint['max_len'],native_input_text_delta=native.text[len(context.text):],pack_fingerprint=pack.fingerprint))
dump('native-budgets.jsonl',budgets)

def source_span(context,aa):
    ranges=[]
    for a in aa:
        if a.get('space')!='selected_projection' or a.get('precision')!='exact':raise ValueError('not_exact_projection_anchor')
        matches=[]
        for interval in context.intervals:
            if not isinstance(interval,SourceInterval) or interval.source.source_view_id!=a['pin']['source_view_id']:continue
            pointer=json.loads(interval.item_locator.removeprefix('pdf:'))['pointer']
            if interval.cell_index is not None and interval.source_field=='cell_text':pointer+=f'/data/table_cells/{interval.cell_index}'
            if pointer!=a['pointer'] or not interval.source_start<=a['start']<a['end']<=interval.source_end:continue
            start=interval.model_start+a['start']-interval.source_start;end=start+a['end']-a['start']
            if context.text[start:end]==a['source_piece']:matches.append((start,end))
        if len(matches)!=1:raise ValueError('gold_piece_not_uniquely_in_context')
        ranges.append(matches[0])
    if not ranges:raise ValueError('no_exact_gold_literal_or_cue')
    if ranges!=sorted(ranges):raise ValueError('gold_piece_order_differs')
    a,b=ranges[0][0],ranges[-1][1]
    reading=context.read_span(a,b,prepared=prepared,policy='synthetic-whitespace-1',literal=context.text[a:b])
    wanted=[(x['pin']['source_view_id'],x['start'],x['end'],x['source_piece']) for x in aa]
    got=[(p.source.source_view_id,p.start,p.end,p.quote) for p in reading.pieces]
    if got!=wanted:raise ValueError('bounding_span_adds_real_text')
    return a,b,reading

attempts=[];record_results=[]
for record in gold:
    assert all(anchor_identity(a)==a['anchor_id'] for a in record['anchors'])
    assert all(evidence_set_identity(e)==e['set_id'] for e in record['evidence_sets'])
    fields={f['role']:f for f in record['fields']};anchors={a['anchor_id']:a for a in record['anchors']};sets={s['set_id']:s for s in record['evidence_sets']}
    model_fields=next(json.loads(pack.declaration_json)['structures'][record['family']]['fields'] for key,group in packs.items() for family,pack in group.items() if family==record['family'])
    literal_roles=[];class_absent=[]
    for definition in model_fields:
        name=definition['name'];role=name.removesuffix('__state').removesuffix('__cue');field=fields.get(role)
        if name.endswith('__state'):continue
        if field is None:literal_roles.append((name,None));continue
        if definition.get('choices'):
            if field['state']!='present':class_absent.append(name)
            continue
        if name.endswith('__cue'):
            ss=[sets[s] for s in field.get('evidence_sets',[]) if sets[s]['usage']=='classification_cue']
            if field['state']!='present' and not ss:continue
        elif field['state']!='present':continue
        else:ss=[sets[s] for s in field.get('evidence_sets',[]) if sets[s]['usage']=='literal']
        literal_roles.append((name,[anchors[a] for s in ss for a in s['anchors']]))
    for variant in ('original','expanded'):
        contexts=base if variant=='original' else expanded
        if variant=='expanded' and record['family']!='formula_context':continue
        for segmentation in processors:
            if variant=='expanded' and args.expanded_codepoints_only and segmentation!='codepoints':continue
            results=[]
            for key,context in contexts.items():
                if key[0]!=record['pin']['source_view_id'] or record['family'] not in packs[key]:continue
                successes=[];errors=[]
                for role,aa in literal_roles:
                    try:
                        if aa is None:raise ValueError('released_role_missing_from_gold')
                        start,end,reading=source_span(context,aa)
                        starts,ends=token_maps[variant,key,segmentation]
                        words=char_span_to_word_boundaries(start,end,starts,ends)
                        roundtrip=word_boundaries_to_char_span(*words,starts,ends)
                        if roundtrip!=(start,end):
                            errors.append(dict(role=role,reason='word_roundtrip_changes_gold_bounds',gold=[start,end],roundtrip=roundtrip));continue
                        reread=context.read_span(*roundtrip,prepared=prepared,policy='synthetic-whitespace-1')
                        if reading.original_pieces!=reread.original_pieces:raise ValueError('source_token_source_changed')
                        successes.append(dict(role=role,chars=[start,end],tokens=words,token_width=words[1]-words[0],source_pieces=[dict(source_view_id=p.source.source_view_id,start=p.start,end=p.end,quote=p.quote) for p in reading.pieces],reading=reading.receipt()))
                    except (ValueError,ContextRefused) as error:errors.append(dict(role=role,reason=str(error)))
                # Preserve primary occurrence identity as a separate stronger
                # ceiling; broad representability alone does not establish attachment.
                primary_matches=True
                if record['family']=='formula_context':
                    formula_sets=[s for s in record['evidence_sets'] if s['role']=='formula' and s['usage']=='literal']
                    formula_pointers={anchors[a]['pointer'] for s in formula_sets for a in s['anchors']}
                    primary_matches=stored[key]['selection']['region'] in formula_pointers
                result=dict(record_id=record['record_id'],family=record['family'],source_view_id=key[0],index=key[1],variant=variant,segmentation=segmentation,context_id=context.dependency_digest,successes=successes,errors=errors,classified_absent_gaps=class_absent,source_roles_exact=not errors,baseline_strict_mappable=not errors and not class_absent,primary_formula_matches=primary_matches)
                results.append(result)
                if successes or not errors:attempts.append(result)
            best=min(results,key=lambda r:(len(r['errors']),-len(r['successes']),r['index'])) if results else None
            complete=[r for r in results if r['baseline_strict_mappable']]
            source_complete=[r for r in results if r['source_roles_exact']]
            primary_complete=[r for r in complete if r['primary_formula_matches']]
            record_results.append(dict(record_id=record['record_id'],family=record['family'],source_view_id=record['pin']['source_view_id'],variant=variant,segmentation=segmentation,source_roles_exact=bool(source_complete),baseline_strict_mappable=bool(complete),primary_strict_mappable=bool(primary_complete),complete_contexts=[r['index'] for r in complete],primary_complete_contexts=[r['index'] for r in primary_complete],classified_absent_gaps=class_absent,best_diagnostic=None if best is None else dict(index=best['index'],errors=best['errors'],success_roles=[x['role'] for x in best['successes']])))
dump('mapping-attempts.jsonl',attempts);dump('record-mapping.jsonl',record_results)
counts=[]
for variant in ('original','expanded'):
    for segmentation in processors:
        rs=[r for r in record_results if r['variant']==variant and r['segmentation']==segmentation]
        if not rs:continue
        bs=[b for b in budgets if b['variant']==variant and b['segmentation']==segmentation]
        counts.append(dict(variant=variant,segmentation=segmentation,records=len(rs),source_roles_exact=sum(r['source_roles_exact'] for r in rs),baseline_strict_mappable=sum(r['baseline_strict_mappable'] for r in rs),primary_strict_mappable=sum(r['primary_strict_mappable'] for r in rs),strict_families=dict(Counter(r['family'] for r in rs if r['baseline_strict_mappable'])),best_error_causes=dict(Counter(e['reason'] for r in rs if not r['source_roles_exact'] for e in (r['best_diagnostic'] or {}).get('errors',[]))),budgets=dict(groups=len(bs),max_source_words=max((b['source_word_tokens'] for b in bs),default=0),max_subwords=max((b['subwords'] for b in bs),default=0),facade_word_overflow=sum(not b['facade_word_bound_pass'] for b in bs),facade_subword_overflow=sum(not b['facade_subword_bound_pass'] for b in bs),checkpoint_word_overflow=sum(not b['checkpoint_source_word_bound_pass'] for b in bs))))
assert next(c for c in counts if c['variant']=='original' and c['segmentation']=='whitespace')['baseline_strict_mappable']==143
summary=dict(outcome='passed',scope='exact source/target representation and native tokenizer preparation only',base_contexts=len(base),expanded_formula_contexts=len(expanded),formula_expansion_outcomes=dict(Counter(r['outcome'] for r in expansion_receipts)),counts=counts,checkpoint_max_len=checkpoint['max_len'],boundary_settings=checkpoint['boundary_head'],no_model_loaded=True,no_forward=True,no_db_writes=True,no_adoption=True)
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(OUT/'input-receipts.json').write_text(json.dumps(dict(verified_at=datetime.now(timezone.utc).isoformat(),executed_script_sha256=digest(Path(__file__)),inputs={name:digest(ALIGN/name) for name in ('feature-fit-protected.json','source-contexts.jsonl','source-reconstruction.json')},snapshot=str(cfg.snapshot),checkpoint_config_sha256=digest(cfg.snapshot/'config.json'),checkpoint_max_len_unit='source word tokens before choice-prefix/schema encoding'),indent=2))
(OUT/'probe-executed.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(summary,ensure_ascii=False,indent=2))
