"""Artifact-only diagnosis of source availability versus scalar contiguity gaps."""
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
SCENARIO=HERE/'attempt-002'
OUT=SCENARIO/'source-gap-classification'
OUT.mkdir(exist_ok=False)
references=json.loads((HERE.parent/'2026-11-04_m1-training-alignment/feature-fit-protected.json').read_text())
gold={r['record_id']:r for ref in references for r in ref['authored']['records']}
projection=references[1]['source_frame']['source_views'][0]['projection']
contexts=[json.loads(x) for x in (SCENARIO/'expanded-contexts.jsonl').read_text().splitlines()]
results=[r for r in map(json.loads,(SCENARIO/'record-mapping.jsonl').read_text().splitlines()) if r['variant']=='expanded' and r['segmentation']=='codepoints']
attempts=[r for r in map(json.loads,(SCENARIO/'mapping-attempts.jsonl').read_text().splitlines()) if r['variant']=='expanded' and r['segmentation']=='codepoints']

def map_piece(anchor,context):
    matches=[]
    for i in context['intervals']:
        if 'source' not in i or i['source']['source_view_id']!=anchor['pin']['source_view_id']:continue
        pointer=json.loads(i['item_locator'].removeprefix('pdf:'))['pointer']
        if i['cell_index'] is not None and i['source_field']=='cell_text':pointer+=f"/data/table_cells/{i['cell_index']}"
        if pointer!=anchor['pointer'] or not i['source_start']<=anchor['start']<anchor['end']<=i['source_end']:continue
        a=i['model_start']+anchor['start']-i['source_start'];b=a+anchor['end']-anchor['start']
        if context['text'][a:b]==anchor['source_piece']:matches.append([a,b])
    return matches

source_failures=[];primary_failures=[]
for result in results:
    record=gold[result['record_id']];anchors={a['anchor_id']:a for a in record['anchors']}
    role_anchors={}
    for evidence in record['evidence_sets']:
        if evidence['usage'] not in ('literal','classification_cue'):continue
        role=evidence['role']+('__cue' if evidence['usage']=='classification_cue' else '')
        role_anchors.setdefault(role,[]).extend(anchors[a] for a in evidence['anchors'])
    formula_pointers={a['pointer'] for a in role_anchors['formula']}
    primary_contexts=[c['index'] for c in contexts if c['source_view_id']==result['source_view_id'] and c['original_primary_formula'] in formula_pointers]
    if not result['primary_strict_mappable']:
        primary_attempts=[a for a in attempts if a['record_id']==result['record_id'] and a['primary_formula_matches']]
        nearest=min(primary_attempts,key=lambda a:(len(a['errors']),-len(a['successes']),a['index'])) if primary_attempts else None
        primary_failures.append(dict(record_id=result['record_id'],source_view_id=result['source_view_id'],gold_formula_pointers=sorted(formula_pointers),actual_primary_contexts=primary_contexts,co_present_in_other_formula_context=result['baseline_strict_mappable'],classification='no actual native primary-formula selection for these gold formula pointers' if not primary_contexts else 'required role outside all complete primary-matching bounded contexts',best_primary_errors=None if nearest is None else nearest['errors']))
    if result['source_roles_exact']:continue
    per_context=[]
    for context in contexts:
        per_role={}
        for role,aa in role_anchors.items():
            missing=[a['anchor_id'] for a in aa if len(map_piece(a,context))!=1]
            per_role[role]=dict(all_pieces_available=not missing,missing_anchors=missing)
        per_context.append(dict(index=context['index'],all_required_pieces_available=all(r['all_pieces_available'] for r in per_role.values()),roles=per_role))
    all_available=[x['index'] for x in per_context if x['all_required_pieces_available']]
    relevant_attempts=[a for a in attempts if a['record_id']==result['record_id']]
    scalar_gap_contexts=[a['index'] for a in relevant_attempts if any(e['reason']=='bounding_span_adds_real_text' for e in a['errors'])]
    nearest=min(per_context,key=lambda c:sum(len(r['missing_anchors']) for r in c['roles'].values()))
    role_receipts=[]
    for role,status in nearest['roles'].items():
        if status['all_pieces_available']:continue
        aa=role_anchors[role]
        pieces=[]
        for a in aa:
            if a['anchor_id'] not in status['missing_anchors']:continue
            anywhere=[c['index'] for c in contexts if len(map_piece(a,c))==1]
            source_matches=projection['text'][a['start']:a['end']]==a['source_piece']
            assert source_matches
            pieces.append(dict(anchor_id=a['anchor_id'],pointer=a['pointer'],start=a['start'],end=a['end'],quote=a['source_piece'],confirmed_in_frozen_source_projection=source_matches,available_in_generated_contexts=anywhere))
        role_receipts.append(dict(role=role,missing_in_nearest_context=pieces,has_context_with_all_role_pieces=any(c['roles'][role]['all_pieces_available'] for c in per_context)))
    source_failures.append(dict(record_id=result['record_id'],source_view_id=result['source_view_id'],all_piece_available_contexts=all_available,scalar_real_interposition_contexts=scalar_gap_contexts,nearest_context=nearest['index'],classification='scalar facade prevents a complete piece-list representation' if all_available else 'required source pieces are not jointly available in any generated bounded context',role_receipts=role_receipts,per_context_availability=per_context))

for name,rows in [('remaining-five.jsonl',source_failures),('remaining-thirteen-primary.jsonl',primary_failures)]:
    (OUT/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
summary=dict(outcome='passed',scope='existing artifacts only; no new native probe/context generation/model/DB work',remaining_source_records=len(source_failures),source_failure_classes=dict(Counter(r['classification'] for r in source_failures)),source_failure_roles=dict(Counter(r['role'] for x in source_failures for r in x['role_receipts'])),remaining_primary_records=len(primary_failures),primary_failure_classes=dict(Counter(r['classification'] for r in primary_failures)),co_present_in_other_formula_context=sum(r['co_present_in_other_formula_context'] for r in primary_failures),all_missing_quotes_confirmed_in_frozen_source=True,scalar_only_remedies_for_remaining_five=sum(bool(r['all_piece_available_contexts']) for r in source_failures),native_list_route='ZERO_OR_MORE/ONE_OR_MORE gives distinct span values; scalar alternatives do not represent ordered discontinuous TextSequence; future pack/assembly policy only, not adopted or collated here')
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
(OUT/'executed.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(summary,indent=2))
