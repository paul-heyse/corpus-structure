"""Freeze two source-only binder/site opportunities, never authored relations.

Only the original source inventory, authenticated source views, source binding and
public frame schema are read. No characterization, primary outputs or reference
passes are imported/read. Protected reference creation uses the existing CLI owner.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import author_packet, decode_frame
from corpus_structure.evaluate.record_references import source_binding
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parent.parent
RUN=496
CUT=614
PROJECT='nce-grinstead-snell-full-book'
RELEASE='release:c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189'
SELECTION=((477,'#/texts/21771','binder-site-declaration-probability'),(479,'#/texts/5005','binder-site-declaration-random-numbers'))
QUESTION=(
    'For the overt declaration in this original block, independently identify its written binder cue '
    'and explicit variable site(s), and assess the directed declared_binding_site hypothesis from cue '
    'to site. Required family context.binding; semantic task binding; role scheme '
    'contextual-source-hypotheses-1. Preserve hypothesis standing, distinct source-local binder '
    'identity, original ordered extents and the boundary of this declaration context. Judge only '
    'the explicitly inspected local slot(s), using witness or complete_slots honestly; unresolved '
    'or inapplicable source remains explicit. This question does not ask for an anaphoric antecedent '
    'or a scientific relationship, and does not assert that a producer family is available.'
)


def write(name,value):
    (HERE/name).write_bytes(canonical_bytes(value)+b'\n')


def prepare(conn):
    inventory=json.loads((EVIDENCE/'panel'/'source-inventory.json').read_bytes())
    if inventory['run']!=RUN or inventory['cut']!=CUT or inventory['release']!=RELEASE:
        raise ValueError('source inventory differs from exact frozen source capture')
    indexed={view['view_id']:view for view in inventory['views']}
    frames={};opportunities=[];selected=[]
    for identity,pointer,key in SELECTION:
        original=indexed[identity]
        block=next(block for block in original['blocks'] if block['pointer']==pointer)
        if not block['text'].startswith('Let X be '):
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
        question=dict(opportunity_id=key,facet='attachment_binding',required_family='context.binding',semantic_task='binding',role_scheme='contextual-source-hypotheses-1',relation='declared_binding_site',question=QUESTION,view_id=identity,unit_key=original['unit_key'],block=block)
        position=next(i for i,b in enumerate(original['blocks']) if b['pointer']==pointer)
        packet=dict(source_only=True,view_id=identity,unit_key=original['unit_key'],title=original['title'],section_pointer=original['section_pointer'],base_document=base.values(),projection_digest=view.ref.projection_digest,recipe_digest=view.ref.recipe_digest,source_health=view.health,questions=[question],original_context_blocks=original['blocks'][max(0,position-1):position+2],ancestors=original['ancestors'])
        write(f'source-view-{identity}.json',packet)
        opportunity=dict(opportunity_id=key,extents=block['extents'],facet='attachment_binding',source_state='uninspected')
        scopes=[dict(pin=pin,space='selected_projection',pointer=extent['native_pointer'],precision='exact',start=extent['start'],end=extent['end']) for extent in block['extents']]
        frame=dict(unit=original['unit_key'],release_id=RELEASE,guideline_version='characterization-reference-2',rubric_version='chapter-facet-task-semantics-1',context_policy='original-native-declaration-block-and-focal-view-source-only-1',operation_question=key+' [required_family=context.binding; task=binding; role_scheme=contextual-source-hypotheses-1; relation=declared_binding_site]: '+QUESTION,operation_version='text-characterization-binder-supplement-1',domain='statistics',direction='source_first',pin=pin,anchor_ids=[],related_pins=[],anchor_scopes=scopes,contribution_ids=[],source_group='grinstead-snell',partition='development',inspected_scope='Selected original declaration block and authenticated focal source/hierarchy context. No relation answer, producer output, candidate parse or other author answer inspected.',opportunities=[opportunity],exposure_history=['shared-full-book-development','source-only-binder-supplement-selection'],characterization_view=None,selected_layers=[],outputs=None)
        wire=dict(protocol='source-operation-frame-3',evaluation_frame=frame,captured_coordinates=[],context_dependency_digest=None)
        decode_frame(wire)
        frames[original['unit_key']]=wire
        opportunities.append(question)
        selected.append(dict(source_view_id=identity,unit_key=original['unit_key'],title=original['title'],original_block_pointer=pointer,source_packet=f'source-view-{identity}.json',opportunity_id=key))
    manifest=dict(version='tc10-source-binder-supplement-1',project=PROJECT,source_run=RUN,source_cut=CUT,release_id=RELEASE,source_only=True,producer_outputs_inspected=False,reference_answers_inspected=False,selection='Two original Let X declarations in distinct Probability/Random Numbers section scopes, selected from original source inventory before chapter NLP; equal spelling does not collapse local source identity.',guideline_version='characterization-reference-2',rubric_version='chapter-facet-task-semantics-1',prior_population_disposition=dict(reference_sets=[40,41],question_numbers=[15,22],disposition='Original anaphoric-antecedent questions retain their immutable wording and source opportunities. context.binding declares binder-to-explicit-variable-site hypotheses, so it does not supply a directed-antecedent assessment contract. Preserve unavailable contract, not a language error; this supplement adds two distinct applicable source questions.'),source_views=selected,opportunities=opportunities,semantic_answers_authored=False,population_claim='Two purposive source opportunities only; no exhaustive binding accuracy claim.',inherited_source_limits='display partial; inline/cell unknown; original source health unchanged')
    write('manifest.json',manifest)
    sampling=dict(seed=0,cohort='tc10-source-binder-supplement-1',strata={key:'explicit-source-declaration' for key in frames},inclusion_probabilities={key:1.0 for key in frames},provenance=dict(selection=manifest['selection'],source_only=True,producer_outputs_inspected=False,reference_answers_inspected=False,manifest_sha256=sha256(canonical_bytes(manifest)+b'\n').hexdigest(),probability_meaning='Certain membership within selected two-opportunity panel; no random sampling or book-wide accuracy inference.'))
    write('sample.json',dict(sampling=sampling,frames=frames))
    print(json.dumps(dict(frames=len(frames),opportunities=len(opportunities),source_view_ids=[s[0] for s in SELECTION])))


def packets(conn):
    frozen=json.loads((HERE/'frozen-reference-set.json').read_bytes())
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
    args=parser.parse_args()
    with open_runtime_engine(Settings(),'tc10-source-binder-supplement',purpose='evaluate') as engine,engine.connect() as conn:
        (prepare if args.action=='prepare' else packets)(conn)
