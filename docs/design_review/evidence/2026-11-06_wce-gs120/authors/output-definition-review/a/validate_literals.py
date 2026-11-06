"""Validate literal/provenance facts only; never semantic roles or attachment judgments."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
review_path = OUT / 'review.json'
r = json.loads(review_path.read_text())
input_checks = []
for declared in r['inputs']:
    actual = hashlib.sha256((ROOT / declared['path']).read_bytes()).hexdigest()
    assert actual == declared['sha256'], declared['path']
    input_checks.append({'path': declared['path'], 'sha256': actual, 'outcome': 'passed'})
base = json.loads((ROOT / 'baseline003-export001/structural-inspection.json').read_text())
actual = base['reports'][0]['definition_components']['components']
assert len(actual) == len(r['components']) == 9
assert {c['component_id'] for c in actual} == {c['component_id'] for c in r['components']}
for c in r['components']:
    i = c['frozen_product']['component_index']
    assert c['prediction'] == actual[i]
    assert c['component_id'] == actual[i]['component_id']
    assert all(c['frozen_product'][k] == base[k] for k in ['release_id','run_id','cut_id','task_ids'])
    assert set(c['facets']) == {'term_role','content_role','directed_attachment_meaning','scope_conditions'}
    for f in c['facets'].values():
        assert f['judgment'] in ['supported','unsupported','ambiguous','unassessed']
        assert f['source_state'] in ['stated','unstated','unresolved','uninspected']

quote_count = 0
native_piece_checks = 0
cache = {}
def walk(node):
    global quote_count, native_piece_checks
    if isinstance(node,dict):
        if {'packet','packet_sha256','passage_id','start','end','text','native_pointers'} <= node.keys():
            path = ROOT / node['packet']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == node['packet_sha256']
            if node['packet'] not in cache:
                cache[node['packet']] = json.loads(path.read_text())
            packet = cache[node['packet']]
            v = next(v for v in packet['views'] if v['passage']['passage_id'] == node['passage_id'])
            assert v['passage']['text'][node['start']:node['end']] == node['text']
            assert node['source_ref'] == v['passage']['source_ref']
            assert node['source_view_id'] == v['native_view']['id']
            for key in ['native_task_id','native_product_key','native_content_digest']:
                assert node[key] == v['native_view'][key]
            items={i['self_ref']:i for i in v['native_context']['items']}
            expected_pieces=[p for p in v['native_context']['pieces'] if p.get('item_ref') and p['start'] < node['end'] and p['end'] > node['start']]
            assert len(expected_pieces) == len(node['native_pointers'])
            for p,declared in zip(expected_pieces,node['native_pointers']):
                assert p['item_ref'] == declared['native_pointer']
                assert p['start'] == declared['piece_start'] and p['end'] == declared['piece_end']
                a=max(node['start'],p['start']);b=min(node['end'],p['end'])
                assert a-p['start'] == declared['item_local_start']
                assert b-p['start'] == declared['item_local_end']
                item=items[p['item_ref']]
                assert item[p['source_field']][a-p['start']:b-p['start']] == v['passage']['text'][a:b]
                expected_pages=[]
                for prov in item.get('prov',[]):
                    n=prov.get('page_no')
                    parent=next((page['parent_physical_page'] for page in packet['page_map'] if page['excerpt_physical_page']==n),None)
                    expected_pages.append({'excerpt_physical_page':n,'parent_physical_page':parent})
                assert expected_pages == declared['pages']
                native_piece_checks+=1
            quote_count+=1
        for value in node.values():walk(value)
    elif isinstance(node,list):
        for value in node:walk(value)
walk(r)
receipt={'protocol':'output-definition-literal-validation-1','reviewer':'output-definition-review-a','date':'2026-11-06','outcome':'passed','command':'python docs/design_review/evidence/2026-11-06_wce-gs120/authors/output-definition-review/a/validate_literals.py','review_sha256':hashlib.sha256(review_path.read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'component_count':len(actual),'facet_judgment_count':sum(len(c['facets']) for c in r['components']),'quote_occurrences_checked':quote_count,'native_piece_checks':native_piece_checks,'inputs':input_checks,'limits':'Literal/provenance validity only; this receipt does not validate role correctness, directed meaning, scientific truth, referenced external contents, or full-corpus performance.'}
(OUT/'literal-validation-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='inputs'},ensure_ascii=False))
