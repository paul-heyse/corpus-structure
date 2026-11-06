"""Check serialized author B anchors against only the neutral input packets."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parents[1]
ids = set()
pages = []
absent = []
summary = []
refs = views = read = 0
for path in sorted(OUT.glob('packet-*.json')):
    d = json.loads(path.read_text())
    raw = (BASE / d['input_file']).read_bytes()
    s = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == d['input_sha256']
    vm = {v['native_view']['id']: v for v in s['views']}
    assert {v['view_id'] for v in d['coverage']['views']} == set(vm)
    views += len(vm)
    read += sum(len(v['inspected_regions']) for v in d['coverage']['views'])
    for page in d['coverage']['pages']:
        pages.append(page['parent_physical_page'])
        if page['projection_presence'] == 'absent':
            absent.append(page['parent_physical_page'])
    for case in d['cases']:
        assert case['id'] not in ids
        ids.add(case['id'])
        assert case['source_state'] in ['stated', 'unstated', 'unresolved', 'uninspected']
        assert case['judgment'] in ['supported', 'unsupported', 'ambiguous', 'unassessed']
        for e in case['evidence']:
            refs += 1
            v = vm[e['view_id']]
            a, b = e['start'], e['end']
            assert v['passage']['text'][a:b] == e['quote']
            p = e['native_piece']
            assert p in v['native_context']['pieces']
            assert p['start'] == a and p['end'] == b
            item = next(i for i in v['native_context']['items'] if i['self_ref'] == p['item_ref'])
            text = item['data']['table_cells'][p['cell_index']]['text'] if p['source_field'] == 'cell_text' else item['text']
            assert text == e['quote']
            assert e['source'] == v['source']
            assert e['native_view'] == v['native_view']
            expected = [m for m in s['page_map'] if m['excerpt_physical_page'] in
                {q['page_no'] for q in item.get('prov', [])}]
            assert expected and expected == e['page_map']
    summary.append({'packet': path.name, 'cases': len(d['cases']), 'input_sha256': d['input_sha256']})
assert len(summary) == 12
assert sorted(pages) == list(range(191, 311))
receipt = {
    'date': '2026-11-06', 'outcome': 'passed',
    'command': 'python docs/design_review/evidence/2026-11-06_wce-gs120/authors/b/verify_inventory.py',
    'protocol': 'gs120-source-author-1', 'author': 'B', 'packets': summary,
    'case_count': len(ids), 'evidence_anchor_count': refs, 'view_count': views,
    'inspected_native_piece_count': read, 'page_coverage_entries': len(pages),
    'pages_absent_from_projection': absent,
    'checks': ['input SHA256 equality', 'unique case IDs and valid state/judgment vocabulary',
        'all packet views represented in coverage', 'all 120 physical pages represented exactly once',
        'every quote is an exact half-open Unicode passage slice',
        'every quoted span equals its actual native piece',
        'every native text/cell quote equals actual item content',
        'source and native-view identity equality',
        'native provenance pages bind exact supplied page-map entries'],
    'limits': ['Selective source inventory, not census',
        'No original PDFs or original visual regions inspected',
        'Only author B output and neutral source packets used'],
}
(OUT / 'verification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(f'passed: 12 packets, {len(ids)} cases, {refs} exact native-bound anchors, {views} views, {len(pages)} page coverage entries')
