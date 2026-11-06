"""Summarize retained actual receipts only; no DB/provider or production changes."""
from collections import Counter
from datetime import datetime, UTC
from hashlib import sha256
import json
from pathlib import Path
import sys

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
root=HERE/sys.argv[1]
whole=json.loads((root/'result.json').read_bytes())
inventory=json.loads((root/'inventory.json').read_bytes())
expected_views={v['source']['source_view_id']:v for v in inventory['source_views']}
rows=[];pins=[];provider=[];located=[];locate_operations=[];phase_counts=Counter();phase_questions=Counter();decision_counts=Counter();relations=Counter();supports=Counter();portable=[]
for source_id,view in sorted(expected_views.items()):
    directory=root/('source-'+str(source_id))
    path=directory/'result.json'
    if not path.exists():path=directory/'failure.json'
    result=json.loads(path.read_bytes());rows.append(result)
    assert result['source_view_id']==source_id
    assert bool(view['eligible_component_ids']) == (result['outcome']!='not_run')
    pins.append(path)
    if result['outcome']!='passed':continue
    assert result['ordinary_reader_export']=='passed' and result['portable_closure']=='passed'
    for page in json.loads((directory/'locate-definition_terms-pages.json').read_bytes()):
        located.extend(item['row'] for item in page['items'] if item['population']=='contribution')
        locate_operations.extend(item['row'] for item in page['items'] if item['population']=='operation')
    assert len(result['candidate_lists'])==len(result['relationship_decisions'])==len(view['eligible_component_ids'])
    for phase in result['phase_operations']:
        phase_counts[phase['outcome']]+=1
        category='candidate retrieval' if phase['question'].startswith('contextual candidate retrieval') else ('relationship selection' if phase['question']=='contextual relationship selection for located occurrence' else 'overall method')
        phase_questions[(category,phase['outcome'])]+=1
    for decision in result['relationship_decisions']:
        decision_counts[decision['outcome']]+=1
        for edge in decision['selected_edges']:relations[edge['relation']]+=1
        for witness in decision['witnesses']:supports[witness['support_state']]+=1
    for detail in result['encoder_parse_detail']:
        parsed=source_python(detail) if detail.get('kind') else detail
        provider.append(dict(source_view_id=source_id,**{k:v for k,v in parsed.items() if k!='encoder_inputs'}))
    closure=json.loads((directory/'portable-closure.json').read_bytes())
    portable.append(dict(source_view_id=source_id,run_id=result['run']['run_id'],cut_id=result['run']['cut_id'],relations=closure['relations'],completeness=closure['completeness'],original_source_completeness=closure['original_source_completeness']))
    pins.extend([directory/'configuration.json',directory/'source-ready.json',directory/'sealed-cut.json',directory/'completed.json',directory/'portable-closure.json',directory/'review/manifest.json',directory/'locate-definition_terms-export/manifest.json',directory/'retrieve-contextual-export/manifest.json'])
assert len(rows)==48 and len(inventory['all_components'])==35
assert len(inventory['selected_component_ids'])==14 and len(inventory['unselected_component_ids'])==21
assert len({r['source_view_id'] for r in rows})==48
pins.extend([root/'result.json',root/'inventory.json',root/'named-custody.json',root/'named-file-page.json',root/'all-component-references.json',HERE/'run_contextual.py',Path(__file__).resolve()])
summary=dict(protocol='gs120-current-contextual-actual-summary-1',checked_at=datetime.now(UTC).isoformat(),outcome=whole['outcome'],command='uv run python '+str(Path(__file__).relative_to(BASE.parents[3]))+' '+sys.argv[1],scope='GS120 physical191-310; exposed development sources; final named run160 exact35 components and48 original source views.',source_counts=dict(all=48,eligible=10,no_eligible_emitted_definition=38),components=dict(all=35,selected_definitions=14,unselected_explanations=21),source_outcomes=dict(Counter(r['outcome'] for r in rows)),runs=[dict(source_view_id=r['source_view_id'],**r['run']) for r in rows if 'run' in r],term_projection=dict(occurrences=len(located),operations=len(locate_operations),operation_outcomes=dict(Counter(r['outcome'] for r in locate_operations))),phase_outcomes=dict(phase_counts),phase_categories=[dict(phase=key[0],outcome=key[1],count=value) for key,value in sorted(phase_questions.items())],candidate_lists=sum(len(r.get('candidate_lists',())) for r in rows),relationship_decisions=dict(decision_counts),selected_relations=dict(relations),witness_support_states=dict(supports),encoder_records=provider,fresh_vectors=sum(p['fresh_vector_count'] for p in provider),reused_vectors=sum(p['reused_vector_count'] for p in provider),portable_closures=portable,pins=[dict(path=str(p.relative_to(BASE.parents[3])),sha256=sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in pins],limits=['Ordinary registered provider/completion/Reader/export/portable receipts establish only this selected operational scope.', 'The retained definition term witnesses its own original component, so selection is coupled and is not independent usage-to-definition recovery.', 'The candidate budget includes the full14 eligible targets; no retrieval ranking benefit, capture recall, or independent semantic attachment support is measured.', 'Similarity/private defined-by edges assign neither canonical identity nor scientific/public truth.', 'All witness support states and overall semantic quality remain unassessed; explanations are explicitly unselected and no-eligible views do not establish absence of source definitions.'])
(root/'summary.json').write_bytes(canonical_bytes(summary)+b'\n')
print(json.dumps({k:summary[k] for k in ('outcome','source_outcomes','phase_outcomes','candidate_lists','relationship_decisions','selected_relations','witness_support_states','fresh_vectors','reused_vectors')}))
