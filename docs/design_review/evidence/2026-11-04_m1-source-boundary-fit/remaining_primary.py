"""Diagnose remaining primary-formula role gaps after source-only context generation."""
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'attempt-002'
alignment=HERE.parent/'2026-11-04_m1-training-alignment'
gold={r['record_id']:r for ref in json.loads((alignment/'feature-fit-protected.json').read_text()) for r in ref['authored']['records']}
records=[json.loads(x) for x in (OUT/'record-mapping.jsonl').read_text().splitlines()]
attempts=[json.loads(x) for x in (OUT/'mapping-attempts.jsonl').read_text().splitlines()]
contexts={(c['source_view_id'],c['index']):c for c in map(json.loads,(OUT/'expanded-contexts.jsonl').read_text().splitlines())}
diagnostics=[]
for result in records:
    if result['variant']!='expanded' or result['segmentation']!='codepoints' or result['primary_strict_mappable']:continue
    candidates=[a for a in attempts if a['record_id']==result['record_id'] and a['variant']=='expanded' and a['segmentation']=='codepoints' and a['primary_formula_matches']]
    if not candidates:
        diagnostics.append(dict(record_id=result['record_id'],source_view_id=result['source_view_id'],reason='no primary-matching candidate mapping was retained'));continue
    nearest=min(candidates,key=lambda a:(len(a['errors']),-len(a['successes']),a['index']))
    record=gold[result['record_id']]
    fields={f['role']:f for f in record['fields']};sets={s['set_id']:s for s in record['evidence_sets']};anchors={a['anchor_id']:a for a in record['anchors']}
    context=contexts[result['source_view_id'],nearest['index']]
    intervals=[i for i in context['intervals'] if 'source' in i]
    located=[]
    for error in nearest['errors']:
        role=error['role'].removesuffix('__cue')
        usage='classification_cue' if error['role'].endswith('__cue') else 'literal'
        aa=[anchors[a] for s in fields[role].get('evidence_sets',[]) if sets[s]['usage']==usage for a in sets[s]['anchors']]
        missing=[a for a in aa if not any(i['source']['source_view_id']==a['pin']['source_view_id'] and i['source_start']<=a['start']<a['end']<=i['source_end'] for i in intervals)]
        located.append(dict(role=error['role'],reason=error['reason'],outside_source_pieces=[dict(pointer=a['pointer'],start=a['start'],end=a['end'],source_piece=a['source_piece']) for a in missing]))
    all_exact=[a for a in record['anchors'] if a.get('space')=='selected_projection' and a.get('precision')=='exact']
    diagnostics.append(dict(record_id=result['record_id'],source_view_id=result['source_view_id'],index=nearest['index'],primary_formula=context['original_primary_formula'],co_present_in_some_other_formula_context=result['baseline_strict_mappable'],source_coordinate_context_envelope=[min(i['source_start'] for i in intervals),max(i['source_end'] for i in intervals)],gold_exact_anchor_envelope=[min(a['start'] for a in all_exact),max(a['end'] for a in all_exact)],role_gaps=located))
(OUT/'remaining-primary-records.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in diagnostics))
causes=Counter();roles=Counter()
for x in diagnostics:
    causes.update(set(e['reason'] for e in x.get('role_gaps',[])))
    roles.update(set(e['role'] for e in x.get('role_gaps',[])))
old=[json.loads(x) for x in (HERE/'attempt-001/record-mapping.jsonl').read_text().splitlines()]
old_primary={r['record_id'] for r in old if r['variant']=='expanded' and r['segmentation']=='codepoints' and r['primary_strict_mappable']}
new_primary={r['record_id'] for r in records if r['variant']=='expanded' and r['segmentation']=='codepoints' and r['primary_strict_mappable']}
summary=dict(outcome='passed',remaining_primary_records=len(diagnostics),record_causes=dict(causes),record_roles=dict(roles),co_present_elsewhere=sum(x.get('co_present_in_some_other_formula_context',False) for x in diagnostics),new_primary_records_vs_2048=len(new_primary-old_primary),lost_primary_records_vs_2048=len(old_primary-new_primary),gold_used_only_for_after_generation_diagnostics=True,no_new_context_generated=True)
(OUT/'remaining-primary-summary.json').write_text(json.dumps(summary,indent=2))
(OUT/'remaining-primary-executed.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(summary,indent=2))
