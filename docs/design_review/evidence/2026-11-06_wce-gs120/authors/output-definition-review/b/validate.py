#!/usr/bin/env python3
"""Read-only frozen-input and exact-quote validator; does not assess semantic truth."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    a_path = HERE / 'assessment.json'
    assessment = json.loads(a_path.read_text())
    checks = []
    def check(ok, label):
        checks.append({'passed': bool(ok), 'check': label})
    packets = {}
    for frozen in assessment['frozen_inputs']:
        path = BASE / frozen['path']
        check(path.is_file() and digest(path) == frozen['sha256'], 'frozen sha256: ' + frozen['path'])
        check(path.is_file() and path.stat().st_size == frozen['bytes'], 'frozen bytes: ' + frozen['path'])
        if frozen['path'].startswith('source-packets/'):
            packets[frozen['path']] = json.loads(path.read_text())
    source = json.loads((BASE / 'baseline003-export001/structural-inspection.json').read_text())
    report = source['reports'][0]
    components = report['definition_components']['components']
    check({k:source[k] for k in assessment['product_identity']} == assessment['product_identity'], 'product identity unchanged')
    check(len(components) == len(assessment['entries']) == assessment['component_count'] == 9, 'all nine components assessed')
    check([c['component_id'] for c in components] == [e['component_id'] for e in assessment['entries']], 'component identities and order unchanged')
    canonical = json.dumps(components, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    check(hashlib.sha256(canonical).hexdigest() == assessment['report_identity']['components_canonical_sha256'], 'component canonical sha256 unchanged')
    views = {v['passage']['passage_id']:(p,j,v) for p,s in packets.items() for j,v in enumerate(s['views'])}
    endpoint_count = quote_count = native_location_count = 0
    for index, entry in enumerate(assessment['entries']):
        original = components[index]
        check(entry['original_component'] == original, 'original component preserved: ' + original['component_id'])
        check(set(entry['facets']) == {'term_role','content_role','directed_attachment','scope_and_conditions'}, 'four facets: ' + original['component_id'])
        check(all(f['verdict'] in assessment['judgment_vocabulary'] for f in entry['facets'].values()), 'facet vocabulary: ' + original['component_id'])
        p, j, v = views[original['term']['passage_id']]
        check(entry['source_identity'] == {'packet':p,'native_view':v['native_view'],'source':v['source']}, 'source identity preserved: ' + original['component_id'])
        check(entry['source_health_as_reported'] == v['native_context']['health'], 'source health states preserved: ' + original['component_id'])
        for role in ['term','content']:
            endpoint = original[role]
            passage = views[endpoint['passage_id']][2]['passage']
            check(passage['text'][endpoint['start']:endpoint['end']] == endpoint['text'], 'emitted endpoint exact quote: ' + original['component_id'] + ' ' + role)
            endpoint_count += 1
        for q in entry['independently_expected']['quotes']:
            s = packets[q['packet']]
            v = s['views'][q['view_index']]
            check(v['passage']['passage_id'] == q['passage_id'] and v['native_view']['id'] == q['source_view_id'], 'quote view identity: ' + q['passage_id'])
            check(v['passage']['text'][q['start']:q['end']] == q['text'], 'expected quote exact: ' + q['passage_id'] + ':' + str(q['start']))
            quote_count += 1
            for loc in q['native_locations']:
                value = s
                for part in loc['packet_json_pointer'].strip('/').split('/'):
                    value = value[int(part)] if isinstance(value,list) else value[part]
                check(value['self_ref'] == loc['self_ref'], 'native self pointer preserved')
                check(value['text'][loc['native_item_text_start']:loc['native_item_text_end']] == q['text'], 'native converted-text quote exact')
                check(value.get('prov',[]) == loc['native_provenance'], 'native original provenance preserved')
                expected_pages = [s['page_map'][pr['page_no']-1]['parent_physical_page'] for pr in value.get('prov',[])]
                check(expected_pages == loc['parent_physical_pages'], 'native physical-page mapping exact')
                native_location_count += 1
    failures = [c for c in checks if not c['passed']]
    receipt = {
        'validator':'independent-output-definition-review-b-quote-hash-1',
        'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'outcome':'passed' if not failures else 'failed',
        'command':'python docs/design_review/evidence/2026-11-06_wce-gs120/authors/output-definition-review/b/validate.py',
        'read_only':True,
        'assessment_sha256':digest(a_path),
        'validator_sha256':digest(Path(__file__).resolve()),
        'frozen_file_count':len(assessment['frozen_inputs']),
        'component_count':len(assessment['entries']),
        'emitted_endpoint_quote_count':endpoint_count,
        'independent_expected_quote_count':quote_count,
        'native_location_count':native_location_count,
        'check_count':len(checks),
        'failures':failures,
        'establishes':'Input immutability, product/component identity, source span quotation, preserved native provenance and mapped physical-page coordinates only.',
        'does_not_establish':'Semantic correctness, scientific truth, corpus completeness, calibration, or publication permission.'
    }
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return int(bool(failures))

if __name__ == '__main__':
    sys.exit(main())
