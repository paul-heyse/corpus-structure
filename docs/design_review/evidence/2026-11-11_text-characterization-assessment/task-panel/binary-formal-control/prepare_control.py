"""One source-only binary formal control; no parser/normalizer or answer reads."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import author_packet, decode_frame
from corpus_structure.evaluate.record_references import source_binding
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
PANEL=HERE.parent.parent/'panel'
RUN=496
CUT=614
VIEW=577
POINTER='#/texts/10583'
OPPORTUNITY='binary-formal-written-order-control'
QUESTION=(
    'Independently characterize the typed written operator and the two distinct written '
    'operand occurrences in this complete exact original binary formula. Required family '
    'formal.math; semantic task formal; role scheme formal-children-v1. Assess directed '
    'left/right operand identity and meaningful written order, preserving the variable atom '
    'and original coordinates. Declare the inspected focus and honest witness or complete_slots '
    'boundary. The question supplies no normalized identity, operator value or expected AST. '
    'Do not solve the expression, commute operands, infer scientific meaning or add grouping '
    'beyond the written binary expression; unresolved recognition remains explicit.'
)


def write(name,value):
    (HERE/name).write_bytes(canonical_bytes(value)+b'\n')


def prepare(conn):
    inventory=json.loads((PANEL/'source-inventory.json').read_bytes())
    if inventory['run']!=RUN or inventory['cut']!=CUT:
        raise ValueError('source capture differs from original inventory')
    source=next(row for row in inventory['views'] if row['view_id']==VIEW)
    selected=None
    for position,block in enumerate(source['blocks']):
        for label,extent in zip(block['labels'],block['extents'],strict=True):
            if extent['native_pointer']==POINTER:
                text=block['text'][extent['start']-block['start']:extent['end']-block['start']]
                if label!='formula' or text!='k-1':
                    raise ValueError('exact original binary formula changed')
                selected=dict(pointer=POINTER,context_owner=block['pointer'],text=text,start=extent['start'],end=extent['end'],extents=[extent],labels=[label])
                owner_position=position
    if selected is None:raise ValueError('original formula occurrence is absent')
    base=source['base_document']
    pin=dict(source=source_binding(conn,source_run_id=RUN,source_view_id=VIEW,source_cut_id=CUT),native_product_task_id=base['task_id'],product_key=base['product_key'],product_digest=base['content_digest'],projection_digest=source['projection_digest'],recipe_digest=source['recipe_digest'],source_view_id=VIEW)
    question=dict(opportunity_id=OPPORTUNITY,facet='source_capture',required_family='formal.math',semantic_task='formal',role_scheme='formal-children-v1',question=QUESTION,view_id=VIEW,unit_key=source['unit_key'],block=selected)
    packet={key:source[key] for key in ('view_id','unit_key','title','section_pointer','ancestors','base_document','projection_digest','recipe_digest','text_length','source_health')}
    packet.update(source_only=True,questions=[question],original_context_blocks=source['blocks'][max(0,owner_position-1):owner_position+2])
    write('source-view-577.json',packet)
    frame=dict(unit=source['unit_key'],release_id=inventory['release'],guideline_version='characterization-reference-2',rubric_version='chapter-facet-task-semantics-1',context_policy='complete-original-binary-formula-and-focal-source-context-1',operation_question=OPPORTUNITY+' [required_family=formal.math; task=formal; role_scheme=formal-children-v1]: '+QUESTION,operation_version='text-characterization-binary-formal-control-1',domain='statistics',direction='source_first',pin=pin,anchor_ids=[],related_pins=[],anchor_scopes=[dict(pin=pin,space='selected_projection',pointer=POINTER,precision='exact',start=selected['start'],end=selected['end'])],contribution_ids=[],source_group='grinstead-snell',partition='development',inspected_scope='One complete original binary formula with its authentic source-local prose/hierarchy context; no producer output, normalized value, parse or other author answer inspected.',opportunities=[dict(opportunity_id=OPPORTUNITY,extents=selected['extents'],facet='source_capture',source_state='uninspected')],exposure_history=['shared-full-book-development','source-only-binary-formal-control-selection'],characterization_view=None,selected_layers=[],outputs=None)
    wire=dict(protocol='source-operation-frame-3',evaluation_frame=frame,captured_coordinates=[],context_dependency_digest=None)
    decode_frame(wire)
    manifest=dict(version='tc10-source-binary-formal-control-1',project=inventory['project'],source_run=RUN,source_cut=CUT,release_id=inventory['release'],source_only=True,producer_outputs_inspected=False,reference_answers_inspected=False,normalization_or_parse_run=False,selection='Complete original three-character ASCII binary formula, one operator and two distinct written operands; no unparenthesized operator-chain association ambiguity. Selected by original source form only, not producer success.',guideline_version='characterization-reference-2',rubric_version='chapter-facet-task-semantics-1',source_views=[dict(source_view_id=VIEW,unit_key=source['unit_key'],title=source['title'],packet='source-view-577.json')],opportunities=[question],preserved_reference_sets=[40,41,42,43],semantic_answers_authored=False,inherited_source_limits='display partial; inline/cell unknown; no strengthened source-health claim')
    write('manifest.json',manifest)
    sampling=dict(seed=0,cohort='tc10-source-binary-formal-control-1',strata={source['unit_key']:'unambiguous-original-binary-expression'},inclusion_probabilities={source['unit_key']:1.0},provenance=dict(source_only=True,producer_outputs_inspected=False,reference_answers_inspected=False,manifest_sha256=sha256(canonical_bytes(manifest)+b'\n').hexdigest(),selection=manifest['selection'],probability_meaning='Certain membership in this one selected control only; no book-wide accuracy inference.'))
    write('sample.json',dict(sampling=sampling,frames={source['unit_key']:wire}))
    print(json.dumps(dict(frames=1,source_view=VIEW,original_pointer=POINTER)))


def packets(conn):
    frozen=json.loads((HERE/'frozen-reference-set.json').read_bytes())
    index=[]
    for unit in frozen['units']:
        packet=author_packet(conn,unit['unit_id'])
        if packet.get('selected_outputs'):raise ValueError('source-only control exposes producer output')
        name=f"author-unit-{unit['unit_id']}.json"
        write(name,packet)
        index.append(dict(unit_id=unit['unit_id'],unit_key=unit['unit_key'],packet=name,bytes=len(canonical_bytes(packet))+1))
    write('author-packets.json',dict(set_id=frozen['set_id'],source_only=True,packets=index))
    print(json.dumps(dict(set_id=frozen['set_id'],units=[u['unit_id'] for u in index],packet_bytes=sum(u['bytes'] for u in index))))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','packets'])
    args=parser.parse_args()
    with open_runtime_engine(Settings(),'tc10-binary-formal-source-control',purpose='evaluate') as engine,engine.connect() as conn:
        (prepare if args.action=='prepare' else packets)(conn)
