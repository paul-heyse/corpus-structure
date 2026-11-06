"""Lower frozen A source selections to the released citation ABI; never project actual statements."""
from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import platform

from author_literals import ROWS, SCOPE
from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference,
    StructuralEvaluationFrame,
)
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.semantic.identity import canonical_bytes

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[6]
BASE = ROOT / 'docs/design_review/evidence/2026-11-06_wce-gs120'
PACKETS = BASE / 'source-recovery/attempt001/source-packets'
LITERALS_SHA256 = 'ff528ee543e22a61e5a119a35632f6c92445babfc277a0f855547426481a1c3a'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def write(name, value):
    (OUT / name).write_bytes(canonical_bytes(value) + b'\n')


assert digest(OUT / 'author_literals.py') == LITERALS_SHA256
raw_path = BASE / 'assessment/run152-current-named001/task-605.json'
assert digest(raw_path) == 'f744bf8f458d543e0bc5d96620b6010e60d3282e2a05f59d2aec27da71aa1d2c'
report = StructuralProductReport.model_validate(json.loads(raw_path.read_text())['body']['structural_product'])
inputs = report.inputs.model_dump(mode='json', exclude_none=True)
views = {}
for path in sorted(PACKETS.glob('grinstead*.json')):
    packet = json.loads(path.read_text())
    for index, view in enumerate(packet['views']):
        views[view['passage']['passage_id']] = (path, packet, index, view)
assert len(views) == 48
frame = StructuralEvaluationFrame.model_validate(dict(
    inputs=inputs, operation='definition_components', direction='output_first',
    rubric_version='gs120-A-narrow-attachment-1',
    rubric_text='Independent A source support of four literal public statements. Supported means the narrow term/content attachment and interpretation are justified in the cited source context; unsupported cases retain corrected alternatives. Whole-report completeness and scientific truth are unassessed.',
    product_ids=[report.product_id], partition='development',
    source_groups=[dict(source_ref=s.identity, origin_group='grinstead-snell-physical191-310') for s in report.inputs.sources],
    opportunities=[dict(opportunity_id='A-'+r['name'], passage_id=r['passage_id'], facet='public_statement', source_state='stated') for r in ROWS] + [dict(opportunity_id='A-whole-report-completeness', passage_id=ROWS[0]['passage_id'], facet='completeness', source_state='uninspected')],
    inspected_scope='Only four current named components: marginal totals, normal density, P(X<Y) subject, and historical instead-of-defining contrast; original run152/cut204/task605. GS120 physical191-310 inventory, not exhaustive source recall or all-report semantic approval.',
    exposure_history=['Previously exposed development corpus and own earlier A current-named-review; original run152 output inspected. No B/C expected alternatives read before A literal freeze.'],
))
source_by_identity = {s.identity: s.model_dump(mode='json', exclude_none=True) for s in report.inputs.sources}
passage_by_id = {p.passage_id: p.model_dump(mode='json', exclude_none=True) for p in report.inputs.passages}


def span_citation(view, selected):
    passage = {k:v for k,v in view['passage'].items() if v is not None}
    assert passage == passage_by_id[passage['passage_id']]
    assert passage['text'][selected['start']:selected['end']] == selected['text']
    assert selected['end'] - selected['start'] == len(selected['text'])
    source = {k:v for k,v in view['source'].items() if k not in {'run_id','cut_id','release_id','result_revision','source_view_id','native_task_id'}}
    raw_source = {k:v for k,v in source_by_identity[passage['source_ref']].items() if k not in {'run_id','cut_id','release_id','result_revision','source_view_id','native_task_id'}}
    assert source == raw_source
    return dict(source=source, **{k:v for k,v in passage.items() if k not in {'source_ref','passage_id','start','end','text'}}, **selected)


cases = []
provenance = []
input_paths = {raw_path, BASE/'assessment/run152-current-named001/manifest.json', BASE/'source-manifest.json', PACKETS/'native-parent-map.json', PACKETS/'source-packet.json'}
for row in ROWS:
    path, packet, index, view = views[row['passage_id']]
    assert view['source']['source_view_id'] == row['source_view_id']
    # Metadata identity check only. Expected semantic selections are the frozen literals.
    observed = report.definition_components.components[row['ordinal']-1]
    assert observed.component_id == row['component_id']
    native = {item['self_ref']:item for item in view['native_context']['items']}
    assert row['quote'] in '\n'.join(native[p]['orig'] for p in row['pointers'])
    statement = dict(
        version='structural-public-statement-3', kind='definition_components', scope=SCOPE,
        coverage_limits=[], exclusions=[],
        definition_component=dict(term=span_citation(view,row['term']), content=span_citation(view,row['content']), interpretation=row['interpretation'], scope=SCOPE),
    )
    cases.append(dict(case_id='A-'+row['name'], component_id=row['component_id'], facet='public_statement', path=['public_statement'], expected=statement, source_passages=[row['passage_id']], judgment=row['judgment'], explanation=row['explanation']))
    page_map = {p['excerpt_physical_page']:p for p in packet['page_map']}
    provenance.append(dict(name=row['name'], ordinal=row['ordinal'], component_id=row['component_id'], packet=rel(path), packet_sha256=digest(path), packet_view_pointer=f'/views/{index}', source_view_id=row['source_view_id'], passage_id=row['passage_id'], source_quote=row['quote'], expected_statement_sha256=hashlib.sha256(canonical_bytes(statement)).hexdigest(), judgment=row['judgment'], limits=row['limits'], native_evidence=[dict(pointer=p, orig=native[p]['orig'], converted=native[p]['text'], provenance=native[p].get('prov',[]), parent_physical_pages=sorted({page_map[x['page_no']]['parent_physical_page'] for x in native[p].get('prov',[])})) for p in row['pointers']]))
    input_paths.add(path)
cases.append(dict(case_id='A-whole-report-completeness-unassessed', facet='completeness', path=['definition_components','components'], expected=None, source_passages=[r['passage_id'] for r in ROWS], judgment='unassessed', explanation='No all-report semantic approval, exhaustive recall annotation, scientific-truth judgment, or remaining 31-component attachment decision is supplied. The four bounded cases cannot establish whole-report completeness.'))
reference = StructuralAuthoredReference.model_validate(dict(frame_digest=frame.identity, cases=cases))
write('frame.json',frame.model_dump(mode='json',exclude_none=True))
write('A.authored.json',reference.model_dump(mode='json'))
write('source-provenance.json',dict(protocol='gs120-independent-A-literal-provenance-1', authored_date='2026-11-06', literal_freeze_sha256=LITERALS_SHA256, component_cases=provenance, independent_before_freeze=dict(read_B=False,read_C=False,called_actual_projection=False,generated_expected_from_actual=False), source_pins=[dict(path=rel(p),sha256=digest(p),bytes=p.stat().st_size) for p in sorted(input_paths)], transport_limits=['Original run152 exact source/output pins only. Root must authenticate final-run component/source correspondence before transporting.', 'This frame is independently A-owned; equal semantic cases may be reframed only with explicit retained provenance and unchanged expectations.', 'Negatives contain corrected alternatives for source-grounded comparison, not publication authority.']))
# Validation concerns custody/ABI only; no actual statement projection or scorer call.
reloaded = StructuralAuthoredReference.model_validate_json((OUT/'A.authored.json').read_bytes())
assert reloaded == reference
assert reloaded.frame_digest == StructuralEvaluationFrame.model_validate_json((OUT/'frame.json').read_bytes()).identity
assert [c.judgment for c in reloaded.cases] == ['supported','supported','unsupported','unsupported','unassessed']
write('validation-receipt.json',dict(outcome='passed',checked_at=datetime.now(UTC).isoformat(),python=platform.python_version(),command='uv run python '+rel(OUT/'build_reference.py'), scope='Frozen literals, original raw hash, source-slice/quote/citation consistency, 48-view inventory, typed frame and five cases; no semantic scorer, production projection, providers, or database writes.', artifacts=[dict(path=rel(OUT/name),sha256=digest(OUT/name)) for name in ['author_literals.py','frame.json','A.authored.json','source-provenance.json']], source_run_id=152,cut_id=204,task_id=605, literal_cases=4, whole_report='unassessed'))
print(json.dumps(dict(outcome='passed',frame_digest=frame.identity,reference_sha256=digest(OUT/'A.authored.json'),cases=5)))
