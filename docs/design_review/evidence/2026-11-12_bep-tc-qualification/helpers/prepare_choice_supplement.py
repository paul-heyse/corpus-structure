"""Prepare source-only host/referent opportunities, never authored answers.

Only the original source inventory, authenticated source views, source binding and
public frame schema are read. No characterization, primary outputs or reference
passes are imported/read. Protected reference creation uses the existing CLI owner.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import re
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import author_packet, decode_frame
from corpus_structure.evaluate.record_references import source_binding
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parents[1] / "2026-11-11_text-characterization-assessment"
OUTPUT=None
RUN=496
CUT=614
PROJECT='nce-grinstead-snell-full-book'
RELEASE='release:c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189'
SELECTION=(
    (739,'#/texts/22521','host-qualifier-maze','host_choice','character_host_choice_v1','with equal probability'),
    (477,'#/texts/7120','host-condition-coin','host_choice','character_host_choice_v1','Unless we have reason'),
    (765,'#/texts/9145','referent-gambler','referent_choice','character_referent_choice_v1','She'),
    (488,'#/texts/152','referent-it-control','referent_choice','character_referent_choice_v1','it'),
)
QUESTION=(
    'Independently characterize the exact source-level host or antecedent question for the specified '
    'focus, using original source/hierarchy only. For host_choice, identify the directed qualifier-to-host '
    'relation or explicitly compatible host set. For referent_choice, identify the directed mention-to-'
    'antecedent relation; do not equate expletive language with a missing referent. Preserve source '
    'ambiguity, insufficient evidence and no source-supported relation. Do not invent candidate IDs: '
    'references use exact source occurrences, and candidate coverage is assessed separately after '
    'production freezes its ordinary alternatives. Missing candidate and no-match are distinct '
    'provider dispositions; no output answer, candidate parse or other author answer was inspected.'
)


def write(name,value):
    (OUTPUT/name).write_bytes(canonical_bytes(value)+b'\n')


def prepare(conn):
    inventory=json.loads((EVIDENCE/'panel'/'source-inventory.json').read_bytes())
    if inventory['run']!=RUN or inventory['cut']!=CUT or inventory['release']!=RELEASE:
        raise ValueError('source inventory differs from exact frozen source capture')
    indexed={view['view_id']:view for view in inventory['views']}
    frames={};opportunities=[];selected=[]
    for identity,pointer,key,task,family,focus in SELECTION:
        original=indexed[identity]
        block=next(block for block in original['blocks'] if block['pointer']==pointer)
        if focus not in block['text']:
            raise ValueError('selected literal source declaration changed')
        view=load_source_view(conn,identity,analysis=False)
        if view.ref.projection_digest!=original['projection_digest'] or view.ref.recipe_digest!=original['recipe_digest'] or view.ref.native_product.values()!=original['base_document']:
            raise ValueError('original source inventory differs from authenticated source')
        for extent in block['extents']:
            if view.text[extent['start']:extent['end']]!=block['text'][extent['start']-block['start']:extent['end']-block['start']]:
                raise ValueError('selected original extent text differs')
        logical=source_binding(conn,source_run_id=RUN,source_view_id=identity,source_cut_id=CUT)
        base=view.ref.native_product
        pin=dict(source=logical,native_product_task_id=base.task_id,product_key=base.product_key,product_digest=base.content_digest,projection_digest=view.ref.projection_digest,recipe_digest=view.ref.recipe_digest,source_view_id=identity)
        match = re.search(r'(?<!\w)' + re.escape(focus) + r'(?!\w)', block['text'])
        if match is None:raise ValueError('exact focus occurrence unavailable')
        lo,hi=block['start']+match.start(),block['start']+match.end()
        focus_extents=[{**e,'start':max(e['start'],lo),'end':min(e['end'],hi)} for e in block['extents'] if max(e['start'],lo)<min(e['end'],hi)]
        question=dict(focus_extents=focus_extents,opportunity_id=key,facet='provider_questions',required_family=family,semantic_task=task,role_scheme='model-question-source-v1',focus_text=focus,question=QUESTION,view_id=identity,unit_key=original['unit_key'],block=block)
        position=next(i for i,b in enumerate(original['blocks']) if b['pointer']==pointer)
        packet=dict(source_only=True,view_id=identity,unit_key=original['unit_key'],title=original['title'],section_pointer=original['section_pointer'],base_document=base.values(),projection_digest=view.ref.projection_digest,recipe_digest=view.ref.recipe_digest,source_health=view.health,questions=[question],original_context_blocks=original['blocks'][max(0,position-1):position+2],ancestors=original['ancestors'])
        write(f'source-view-{identity}.json',packet)
        opportunity=dict(opportunity_id=key,extents=block['extents'],facet='provider_questions',source_state='uninspected')
        scopes=[dict(pin=pin,space='selected_projection',pointer=extent['native_pointer'],precision='exact',start=extent['start'],end=extent['end']) for extent in block['extents']]
        frame=dict(unit=original['unit_key'],release_id=RELEASE,guideline_version='characterization-candidate-reference-3',rubric_version='source-question-choice-semantics-1',context_policy='original-native-question-block-and-focal-view-source-only-1',operation_question=f'{key} [required_family={family}; task={task}; role_scheme=model-question-source-v1; focus={focus!r}; focus_extents={json.dumps(focus_extents,sort_keys=True)}]: '+QUESTION,operation_version='text-characterization-choice-supplement-1',domain='statistics',direction='source_first',pin=pin,anchor_ids=[],related_pins=[],anchor_scopes=scopes,contribution_ids=[],source_group='grinstead-snell',partition='development',inspected_scope='Selected original question block and authenticated focal source/hierarchy context. No relation answer, producer output, candidate parse or other author answer inspected.',opportunities=[opportunity],exposure_history=['shared-full-book-development','source-only-host-referent-supplement-selection'],characterization_view=None,selected_layers=[],outputs=None)
        wire=dict(protocol='source-operation-frame-3',evaluation_frame=frame,captured_coordinates=[],context_dependency_digest=None)
        decode_frame(wire)
        frames[original['unit_key']]=wire
        opportunities.append(question)
        selected.append(dict(source_view_id=identity,unit_key=original['unit_key'],title=original['title'],original_block_pointer=pointer,source_packet=f'source-view-{identity}.json',opportunity_id=key))
    manifest=dict(version='tc10-source-choice-supplement-1',project=PROJECT,source_run=RUN,source_cut=CUT,release_id=RELEASE,source_only=True,producer_outputs_inspected=False,reference_answers_inspected=False,selection='Four original source blocks selected for overt qualifier, conditional scope, pronominal reference and potential expletive/unresolved reference; no candidate/output selection or expected answers.',guideline_version='characterization-candidate-reference-3',rubric_version='source-question-choice-semantics-1',source_views=selected,opportunities=opportunities,semantic_answers_authored=False,population_claim='Four purposive source opportunities only; no exhaustive host/referent accuracy claim.',inherited_source_limits='display partial; inline/cell unknown; original source health unchanged')
    write('manifest.json',manifest)
    sampling=dict(seed=0,cohort='tc10-source-choice-supplement-1',strata={key:'source-host-referent-question' for key in frames},inclusion_probabilities={key:1.0 for key in frames},provenance=dict(selection=manifest['selection'],source_only=True,producer_outputs_inspected=False,reference_answers_inspected=False,manifest_sha256=sha256(canonical_bytes(manifest)+b'\n').hexdigest(),probability_meaning='Certain membership within selected four-opportunity panel; no random sampling or book-wide accuracy inference.'))
    write('sample.json',dict(sampling=sampling,frames=frames))
    print(json.dumps(dict(frames=len(frames),opportunities=len(opportunities),source_view_ids=[s[0] for s in SELECTION])))


def packets(conn):
    frozen=json.loads((OUTPUT/'frozen-reference-set.json').read_bytes())
    index=[]
    for unit in frozen['units']:
        packet=author_packet(conn,unit['unit_id'])
        if packet.get('selected_outputs'):
            raise ValueError('source-only supplement exposed producer outputs')
        name=f"author-unit-{unit['unit_id']}.json"
        write(name,packet)
        index.append(dict(unit_id=unit['unit_id'],unit_key=unit['unit_key'],packet=name,bytes=len(canonical_bytes(packet))+1))
    write('author-packets.json',dict(set_id=frozen['set_id'],source_only=True,packets=index))
    print(json.dumps(dict(set_id=frozen['set_id'],units=[r['unit_id'] for r in index],packet_bytes=sum(r['bytes'] for r in index))))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','packets'])
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    OUTPUT=args.output
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.action=='prepare' and (OUTPUT/'sample.json').exists():
        parser.error('output already contains a selection; preserve it and use a new directory')
    with open_runtime_engine(Settings(),'tc10-source-binder-supplement',purpose='evaluate') as engine,engine.connect() as conn:
        conn.exec_driver_sql('SET TRANSACTION READ ONLY')
        (prepare if args.action=='prepare' else packets)(conn)
