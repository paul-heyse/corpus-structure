"""Assemble frozen A record; semantic judgments live in author_expectations.py."""
import hashlib
import json
from pathlib import Path
import shutil
from author_expectations import ROWS

ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
BASE = OUT.parents[2]
PACKETS = BASE / 'source-recovery/attempt001/source-packets'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


inspection_path = BASE / 'current-extraction/named001/structural-inspection.json'
task_path = BASE / 'assessment/run152-current-named001/task-605.json'
inspection = json.loads(inspection_path.read_text())
task = json.loads(task_path.read_text())
components = [c for r in inspection['reports'] if r.get('definition_components')
              for c in r['definition_components']['components']]
assert len(components) == len(ROWS) == 35
views = {}
packet_paths = sorted(PACKETS.glob('grinstead*.json'))
for path in packet_paths:
    packet = json.loads(path.read_text())
    for index, view in enumerate(packet['views']):
        views[view['passage']['passage_id']] = (path, packet, index, view)
assert len(views) == 48
manifest_path = BASE / 'source-manifest.json'
manifest = json.loads(manifest_path.read_text())
shutil.copyfile(inspection_path, OUT / 'original-structural-inspection.json')
write('original-task-605-structural-product.json', task['body']['structural_product'])


def rel(path):
    return str(path.relative_to(ROOT))


assessed = []
for expected, component in zip(ROWS, components, strict=True):
    path, packet, index, view = views[component['term']['passage_id']]
    native = {x.get('self_ref'): x for x in view['native_context']['items']}
    pointers = ['#/texts/' + n for n in expected['native_pointers']]
    evidence = []
    for pointer in pointers:
        item = native[pointer]
        page_numbers = [p['page_no'] for p in item.get('prov', [])]
        map_by_page = {p['excerpt_physical_page']: p for p in packet['page_map']}
        evidence.append(dict(native_pointer=pointer,
                             packet_json_pointer=f'/views/{index}/native_context/items/{view["native_context"]["items"].index(item)}',
                             native_orig_quote=item.get('orig'),
                             converted_quote=item.get('text'),
                             provenance=item.get('prov', []),
                             physical_pages=sorted({map_by_page[n]['parent_physical_page'] for n in page_numbers}),
                             page_pixel_pins=[map_by_page[n] for n in sorted(set(page_numbers))]))
    assert expected['expected_source_quote'] in '\n'.join(e['native_orig_quote'] or '' for e in evidence), expected['number']
    span_checks = {}
    for role in ('term', 'content'):
        span = component[role]
        text = view['passage']['text'][span['start']:span['end']]
        span_checks[role] = dict(outcome='passed' if text == span['text'] else 'failed',
                                 exact_source_slice=text, span=dict(span))
    assessed.append(dict(
        ordinal=expected['number'], component_id=component['component_id'],
        observed_component=component,
        original_task_component=task['body']['structural_product']['definition_components']['components'][expected['number']-1],
        source=dict(packet=rel(path), packet_sha256=digest(path),
                    source_ref=view['passage']['source_ref'], passage_id=view['passage']['passage_id'],
                    source_view_id=view['source']['source_view_id'],
                    native_content_digest=view['source']['native_content_digest'],
                    native_task_id=view['source']['native_task_id'],
                    projection_digest=view['source']['projection_digest'],
                    native_product_key=view['source']['native_product_key'],
                    parent_pdf_sha256=packet['parent_pdf_sha256'],
                    excerpt_pdf_sha256=packet['source_pdf_sha256'],
                    excerpt_source_uri=view['native_view']['source_uri']),
        exact_location_checks=span_checks,
        independently_authored_expectation={k:v for k,v in expected.items() if k not in ('number','native_pointers')},
        native_evidence=evidence,
        assessment_limit='Source-grounded development-corpus reading. Literal checks establish custody and source matches, not scientific truth or production-method correctness.'
    ))
pins = [inspection_path, task_path, manifest_path, PACKETS/'native-parent-map.json', PACKETS/'source-packet.json', *packet_paths]
parent_path = ROOT / manifest['parent']
if parent_path.exists():
    pins.append(parent_path)
write('assessment.json', dict(
    protocol='gs120-current-named-review-A-1', author='A', authored_date='2026-11-06',
    standing='Independent source-grounded assessment; frozen before exposure to B, C or implementation replay judgments.',
    maturity='Tested: literal custody and coverage checks only; semantic judgments are assessed interpretations, not independently established scientific truth.',
    baseline=dict(run_id=152,cut_id=204,task_id=605,component_count=35,source_view_count=48,
                  physical_pages=list(range(191,311)), release_id=inspection['release_id'],
                  parent_pdf_sha256=manifest['parent_sha256'],
                  task_operation_version=task['body']['operation_version'],
                  task_input_hash=task['body']['input_hash'], task_configuration_hash=task['body']['configuration_hash']),
    independence=dict(read_other_current_assessments=False,read_implementation_replay_verdicts=False,
                      production_validator_used=False, output_used_as_semantic_gold=False,
                      expected_content='Manually authored in author_expectations.py after direct source/native-context reading; observed payload is separately preserved.'),
    source_pins=[dict(path=rel(p),sha256=digest(p),bytes=p.stat().st_size) for p in pins],
    scope_limits=['All 35 emitted components assessed individually; packet inventory has 48 views over all 120 pages.',
                  'This is output assessment, not exhaustive source recall annotation: no complete gold inventory of all possible definitions/explanations was authored.',
                  'Native.orig and converted fields were compared at source pointers; native.orig remains extracted source text, not external scientific authority.',
                  'No PDF image reread: no remaining consequential recognition conflict in these judgments required one; unresolved typography/existence facets are named per component.',
                  'No native provider execution, DB writes, production fixes, assembled qualification or proof of benefit.'],
    material_findings=[
        dict(component_ordinal=13,kind='wrong_semantic_subject',description='Y is attached to a formula for P(X<Y); source explicitly makes the probability the subject.'),
        dict(component_ordinal=32,kind='truncated_named_term',description='a set loses of constant density.'),
        dict(component_ordinal=23,kind='dropped_defined_identifier',description='the line loses L.'),
        dict(component_ordinal=22,kind='speech_act_scope_loss',description='Historical instead-of-defining contrast is promoted to a direct definition.'),
        dict(component_ordinal=10,kind='recognition_corruption',description='Converted numerator exponent 1 contradicts native.orig n-1; display includes trailing narrative.'),
        dict(component_ordinal=14,kind='recognition_and_condition_loss',description='Converted expectation display contains invented fragments; absolute-convergence condition is not retained in content.'),
        dict(component_ordinal=20,kind='recognition_corruption',description='Converted conditional-expectation equation adds a duplicate dotted-symbol expression absent from native.orig.')],
    components=assessed))
print(json.dumps({'outcome':'passed','assembled_components':len(assessed),'packet_views':len(views),
                  'exact_location_failures':[(r['ordinal'],k) for r in assessed for k,v in r['exact_location_checks'].items() if v['outcome']!='passed']}))
