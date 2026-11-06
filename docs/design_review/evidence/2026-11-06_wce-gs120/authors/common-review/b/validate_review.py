"""Literal integrity checks only; never a validator of semantic agreement/correctness."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FRAME_SHA = '850142fe59133abe0f221c142709f15579bb974e407536ee2c04cf33dbc58f15'
STATUSES = {'supported','unsupported','ambiguous','unassessed'}

def load(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

frame, digest = load(ROOT/'authors/c/source-adjudication/common-source-cases.json')
require(digest == FRAME_SHA, 'frozen frame hash mismatch')
review, _ = load(HERE/'review.json')
require(review['input_frame']['sha256'] == FRAME_SHA, 'review frame provenance mismatch')
require(len(frame['cases']) == len(review['cases']) == 32, 'case count mismatch')
require([c['id'] for c in review['cases']] == [c['id'] for c in frame['cases']], 'case IDs/order mismatch')
require(len({c['id'] for c in review['cases']}) == 32, 'duplicate cases')
packets = {}
for key, entry in frame['source_packets'].items():
    packet, sha = load(ROOT/entry['path'])
    require(sha == entry['sha256'], f'{key}: original packet hash mismatch')
    receipt = review['source_packets'][key]
    require(receipt['sha256'] == receipt['verified_sha256'] == sha, f'{key}: review packet hash mismatch')
    for field in ['protocol','source_pdf','source_pdf_sha256','parent_pdf_sha256','parent_physical_pages','page_map']:
        require(receipt[field] == packet[field], f'{key}: {field} provenance mismatch')
    packets[key] = packet

anchor_count = role_count = edge_count = facet_count = 0
for original, c in zip(frame['cases'],review['cases'],strict=True):
    ident = c['id']
    for field in ['facet','source_packet','source_view_id','passage_id','pages','anchors']:
        require(c[field] == original[field], f'{ident}: altered question-frame location {field}')
    packet = packets[c['source_packet']]
    views = [v for v in packet['views'] if v['native_view']['id'] == c['source_view_id']]
    require(len(views) == 1, f'{ident}: view not unique')
    view = views[0]
    require(view['passage']['passage_id'] == c['passage_id'], f'{ident}: passage mismatch')
    text = view['passage']['text']
    items = {i['self_ref']:i for i in view['native_context']['items']}
    anchors = c['anchors']
    for name, anchor in anchors.items():
        start,end = anchor['span']
        require(0 <= start < end <= len(text), f'{ident}/{name}: invalid codepoint span')
        require(text[start:end] == anchor['quote'], f'{ident}/{name}: literal quote mismatch')
        pointer = anchor['native_pointer']
        require(pointer in items, f'{ident}/{name}: native pointer missing')
        pieces = [p for p in view['native_context']['pieces'] if p.get('item_ref') == pointer]
        require(any(p['start'] <= start and end <= p['end'] for p in pieces), f'{ident}/{name}: span outside native piece')
        if 'cell_index' in anchor:
            cells = items[pointer]['data']['table_cells']
            index = anchor['cell_index']
            require(0 <= index < len(cells), f'{ident}/{name}: invalid cell index')
            require(cells[index]['text'] == anchor['quote'], f'{ident}/{name}: native cell text mismatch')
            require(any(p.get('cell_index') == index and p['start'] <= start and end <= p['end'] for p in pieces), f'{ident}/{name}: cell piece mismatch')
        pages = anchor.get('physical_pages',c['pages'])
        require(set(pages).issubset(packet['parent_physical_pages']), f'{ident}/{name}: pages outside packet')
        anchor_count += 1

    def evidence(row):
        require(row['judgment'] in STATUSES, f'{ident}: bad judgment')
        require(bool(row['reason']), f'{ident}: missing reason')
        require(bool(row['evidence']), f'{ident}: missing evidence')
        require(all(a in anchors for a in row['evidence']), f'{ident}: unknown evidence anchor')

    require(len(c['role_judgments']) == len(original['expected']['roles']), f'{ident}: omitted roles')
    for proposed,row in zip(original['expected']['roles'],c['role_judgments'],strict=True):
        require(row['role'] == proposed['role'] and row['anchor'] == proposed['anchor'], f'{ident}: changed role target')
        require(row['anchor'] in anchors, f'{ident}: unknown role anchor')
        require(bool(row['scope']), f'{ident}: missing role scope')
        evidence(row); role_count += 1
    for row in c.get('additional_role_judgments',[]):
        require(row['anchor'] in anchors and bool(row['role']), f'{ident}: invalid additional role')
        evidence(row); role_count += 1
    require(len(c['relation_judgments']) == len(original['expected']['relations']), f'{ident}: omitted relations')
    for proposed,row in zip(original['expected']['relations'],c['relation_judgments'],strict=True):
        for field in ['type','head','tail']:
            require(row[field] == proposed[field], f'{ident}: changed proposed relation {field}')
        require(row['conditions'] == proposed.get('conditions',[]), f'{ident}: changed proposed conditions')
    for row in [*c['relation_judgments'],*c['corrections']]:
        require(row['head'] in anchors and row['tail'] in anchors, f'{ident}: unknown directed endpoint')
        require(all(a in anchors for a in row['conditions']), f'{ident}: unknown condition endpoint')
        require(bool(row['scope']) and bool(row['type']), f'{ident}: missing edge type/scope')
        evidence(row); edge_count += 1
    require(bool(c['facet_judgments']), f'{ident}: missing facet assessment')
    for row in [*c['facet_judgments'],*c['missing_facets']]:
        require(bool(row['facet']), f'{ident}: missing facet name')
        evidence(row); facet_count += 1

result = {'outcome':'passed','date':'2026-11-06','command':'python docs/design_review/evidence/2026-11-06_wce-gs120/authors/common-review/b/validate_review.py',
    'cases':32,'source_packets':len(packets),'literal_anchors':anchor_count,
    'typed_roles':role_count,'directed_edges_including_corrections':edge_count,'facets_including_missing':facet_count,
    'frame_sha256':FRAME_SHA,
    'scope':'Frame and packet hashes/provenance, quote spans, native item/cell locations, coverage of proposed roles/edges, directed endpoint/condition/evidence references. No semantic correctness, consensus or full-source-capture claim.'}
(HERE/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
