"""Source-only formal nomination correction over unchanged original coordinates.

Read only original source selection/cache and its source-only frame bindings. The
existing native create guard reauthenticates frozen source pins and opportunities;
protected author packets supply original context. No normalization, parsing, model
call, primary-product read, reference pass or expected answer is performed here.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import author_packet, decode_frame
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
PANEL=HERE.parent.parent/'panel'
QUESTIONS=(
    (23,'formal-symbol-normalized-identity',
     'Independently characterize the symbol/variable occurrence in this exact original formula. '
     'Required family formal.math. Assess its source-preserving normalized identifier identity '
     'under the public symbol-occurrence-v1 and tex.token_form contract, retaining original '
     'spelling, source occurrence, subscript attachment and any recognition uncertainty. '
     'A scalar formal.normalized expectation may express the independently determined identity; '
     'do not treat an ASCII Identifier: field, a scientific referent or an incidental producer '
     'node name as this question. No expected normalized string is supplied.'),
    (24,'formal-written-comparison-structure',
     'Independently characterize the written comparison operator(s) and directed, ordered '
     'operand structure in this exact original formula. Required family formal.math; semantic '
     'task formal; role scheme formal-children-v1. Use the public operator/atom values and '
     'explicit ordered roles where inspected source supports them, preserving original '
     'coordinates, written operand sides/order and uncertainty. Judge only the declared '
     'inspected focus/slots or positive witness. Do not infer an interval object, solve an '
     'inequality, rewrite equivalent algebra or supply a scientific interpretation. No '
     'expected operator values, normalized strings or AST are supplied.'),
)


def write(name,value):
    (HERE/name).write_bytes(canonical_bytes(value)+b'\n')


def prepare():
    original=json.loads((PANEL/'manifest.json').read_bytes())
    old_sample=json.loads((PANEL/'sample.json').read_bytes())
    inventory=json.loads((PANEL/'source-inventory.json').read_bytes())
    indexed={view['view_id']:view for view in inventory['views']}
    frames={};questions=[];selected=[]
    for number,key,question_text in QUESTIONS:
        prior=original['opportunities'][number-1]
        if prior['opportunity_id']!=f'ch01-source_capture-{number}':
            raise ValueError('prior formal source opportunity changed')
        block=deepcopy(prior['block'])
        if block['labels']!=['formula']:
            raise ValueError('formal supplement requires original formula-labeled item')
        wire=deepcopy(old_sample['frames'][prior['unit_key']])
        frame=wire['evaluation_frame']
        if frame['direction']!='source_first' or frame['outputs'] is not None:
            raise ValueError('original source frame exposes producer population')
        pin=frame['pin']
        if pin['source_view_id']!=prior['view_id'] or pin['projection_digest']!=block['extents'][0]['projection']:
            raise ValueError('original source coordinates differ from frozen source pin')
        revised=dict(opportunity_id=key,prior_source_opportunity_id=prior['opportunity_id'],prior_question_number=number,facet=prior['facet'],required_family='formal.math',question=question_text,view_id=prior['view_id'],unit_key=prior['unit_key'],block=block)
        source=indexed[prior['view_id']]
        owner=block.get('context_owner',block['pointer'])
        position=next(i for i,b in enumerate(source['blocks']) if b['pointer']==owner)
        packet={k:source[k] for k in ('view_id','unit_key','title','section_pointer','ancestors','base_document','projection_digest','recipe_digest','text_length','source_health')}
        packet.update(source_only=True,questions=[revised],original_context_blocks=source['blocks'][max(0,position-1):position+2])
        write(f"source-view-{prior['view_id']}.json",packet)
        frame.update(guideline_version='characterization-reference-2',rubric_version='chapter-facet-task-semantics-1',context_policy='unchanged-original-formula-and-focal-source-context-1',operation_question=key+' [required_family=formal.math]: '+question_text,operation_version='text-characterization-formal-supplement-1',opportunities=[dict(opportunity_id=key,extents=block['extents'],facet=prior['facet'],source_state='uninspected')],anchor_scopes=[dict(pin=pin,space='selected_projection',pointer=e['native_pointer'],precision='exact',start=e['start'],end=e['end']) for e in block['extents']],inspected_scope='Exact original formula occurrence and authenticated original focal source/hierarchy context. Source coordinates are unchanged from the earlier opportunity; no formal parse/normalization or expected answer inspected.',exposure_history=[*frame['exposure_history'],'source-only-formal-nomination-family-correction'])
        decode_frame(wire)
        frames[prior['unit_key']]=wire
        questions.append(revised)
        selected.append(dict(source_view_id=prior['view_id'],unit_key=prior['unit_key'],title=source['title'],packet=f"source-view-{prior['view_id']}.json",prior_question_number=number,prior_source_opportunity_id=prior['opportunity_id'],opportunity_id=key))
    manifest=dict(version='tc10-source-formal-supplement-1',project=original['project'],source_run=original['source_run'],source_cut=original['source_cut'],release_id=original['release_id'],source_only=True,producer_outputs_inspected=False,reference_answers_inspected=False,normalization_or_parse_run=False,guideline_version='characterization-reference-2',rubric_version='chapter-facet-task-semantics-1',selection='Exact original Q23/Q24 source occurrences, unchanged extents; corrected formal.math questions under public nomination and task contracts before corresponding chapter NLP.',prior_population_disposition=dict(reference_sets=[40,41],question_numbers=[23,24],disposition='Original questions and source opportunities remain immutable and unassessed for frame/family mismatch. Formula-labeled items are formal.math, not ordinary Identifier: or Range field nominations; written inequalities are not inferred interval objects. No silent case-family override.'),source_views=selected,opportunities=questions,semantic_answers_authored=False,inherited_source_limits=original['inherited_source_limits'])
    write('manifest.json',manifest)
    write('sample.json',dict(sampling=dict(seed=0,cohort='tc10-source-formal-supplement-1',strata={key:'original-formula-occurrence' for key in frames},inclusion_probabilities={key:1.0 for key in frames},provenance=dict(source_only=True,producer_outputs_inspected=False,reference_answers_inspected=False,manifest_sha256=sha256(canonical_bytes(manifest)+b'\n').hexdigest(),selection=manifest['selection'],probability_meaning='Certain membership in two selected source opportunities only; no book-wide accuracy inference.')),frames=frames))
    print(json.dumps(dict(frames=len(frames),source_views=[v['source_view_id'] for v in selected],prior_questions=[23,24])))


def packets():
    receipt=json.loads((HERE/'frozen-reference-set.json').read_bytes())
    index=[]
    with open_runtime_engine(Settings(),'tc10-source-formal-supplement',purpose='evaluate') as engine,engine.connect() as conn:
        for unit in receipt['units']:
            packet=author_packet(conn,unit['unit_id'])
            if packet.get('selected_outputs'):
                raise ValueError('source-only formal supplement exposed producer outputs')
            name=f"author-unit-{unit['unit_id']}.json"
            write(name,packet)
            index.append(dict(unit_id=unit['unit_id'],unit_key=unit['unit_key'],packet=name,bytes=len(canonical_bytes(packet))+1))
    write('author-packets.json',dict(set_id=receipt['set_id'],source_only=True,packets=index))
    print(json.dumps(dict(set_id=receipt['set_id'],units=[u['unit_id'] for u in index],packet_bytes=sum(u['bytes'] for u in index))))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','packets'])
    args=parser.parse_args()
    (prepare if args.action=='prepare' else packets)()
