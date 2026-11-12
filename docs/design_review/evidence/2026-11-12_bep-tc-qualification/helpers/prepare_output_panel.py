"""Select a small exposed output-first population from the exact final book view.

This is selection, not reference authorship. No model calls, gold/pass reads, scoring,
latest-product resolution or source-first panel changes occur here. Native protected
reference creation remains the existing golden operation-create owner.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate.characterization_assessment import LayerProjection, pin_key
from corpus_structure.evaluate.operation_assessment import author_packet, decode_frame
from corpus_structure.evaluate.record_references import source_binding
from corpus_structure.semantic.characterization_store import read_layer, read_layer_manifest, read_view
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
OUTPUT=None
from qualify_consumers import verifier
CAPTURE=496
CUT=614
PROJECT='nce-grinstead-snell-full-book'
FACETS=(
    'native_fidelity','formal_structure','predicates_roles','operators_scope',
    'attachment_binding','choice_compatibility','provider_questions',
    'coverage_failure','retained_consumer_fidelity','host_choice_questions','referent_choice_questions',
)
QUESTIONS={
    'native_fidelity':'For this exact retained spaCy native.block, independently specify the complete original block tokenization under native_reference kind tokenization, preserving the declared atom policy and original ordered real source extents. The frozen native.block is the output population identity; the original text supplies the independent expectation. Preserve unalignable/uninspected scope and unavailable native evidence, without substituting another provider or inferring source completeness.',
    'formal_structure':'Assess the retained formal structure against its exact original formula/identifier/quantity source, preserving operand/subscript order, boundaries, original representation, interpretation alternatives and recognition limits.',
    'predicates_roles':'Assess this retained predicate/role structure against its source and witness context. Distinguish grammatical and semantic roles, implicit participants and unresolved interpretation; assess the complete declared local graph.',
    'operators_scope':'Assess the retained operator and target/scope graph against the source. Preserve quantification, negation, modality, attachment, shared targets and unresolved alternatives instead of forcing one reading.',
    'attachment_binding':'Assess this exact retained declared_binding_site relation and its witness closure against the original occurrences under task binding / contextual-source-hypotheses-1. Preserve directed binder-to-explicit-variable-site identity, source-local boundaries and private hypothesis standing; distinguish proposed, unresolved and source-supported relationships.',
    'choice_compatibility':'Assess this actual retained packed choice group, members and compatibility/correlation constraints against the source and declared stage. Distinguish object-level disjunction, interpretive uncertainty and unknown compatibility; do not expand Cartesian readings.',
    'provider_questions':'Assess this actual retained provider answer against its exact released question, candidates, source scope and witness context. Preserve observed/unobserved answer fields, alternatives, abstention and dependence; provider output is not source truth.',
    'coverage_failure':'Assess what this exact retained incomplete/unavailable family coverage row actually claims about eligible, examined and unexamined original scope. Distinguish an operational diagnostic from a source-semantic false negative and keep unknown scope explicit.',
    'retained_consumer_fidelity':'Assess the exact retained output identity, source occurrences, native scheme and witness/choice dependencies in this protected read. Native fidelity and retained identity are separate explicit graph projections; do not infer source correctness from successful retention.',
}

QUESTIONS['host_choice_questions']='Assess this exact retained host-choice answer against original source and its frozen native candidates. Preserve qualifier-to-host direction, explicitly compatible host sets, missing candidate, no-match, insufficient evidence and withholding; never treat a model choice as source truth.'
QUESTIONS['referent_choice_questions']='Assess this exact retained referent-choice answer against original source and frozen typed alternatives. Preserve mention-to-antecedent direction, distinct occurrences, missing candidate, no-match, insufficient evidence and withholding; do not relabel binder-site evidence as anaphora.'


def write(name,value):
    path=OUTPUT/name
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_bytes(canonical_bytes(value)+b'\n')


def capture_release(captured,bound):
    if (not captured or captured['id']!=CAPTURE or
        captured['project_id']!=PROJECT or bound['project']!=captured['project_id'] or
        not isinstance(captured['release_id'],str) or not captured['release_id']):
        raise ValueError('output panel capture run/project/release metadata differs')
    return captured['release_id']


def frame_outputs(items):
    distinct={}
    for item in items:
        output=item['output']
        key=canonical_bytes([output['layer'],output['collection'],output['local_id']])
        distinct.setdefault(key,output)
    return list(distinct.values())


def qualifies(facet,collection,row):
    family=row.get('family','')
    if facet in {'host_choice_questions','referent_choice_questions'}:
        selected='character_host_choice_v1' if facet=='host_choice_questions' else 'character_referent_choice_v1'
        return collection=='annotations' and 'model_answer' in row and family==selected
    if facet=='native_fidelity':return collection=='annotations' and row.get('kind')=='native.block' and family=='spacy.tokens'
    if facet=='formal_structure':return collection in {'terms','annotations'} and family=='formal.math' and ('formal' in row or collection=='terms')
    if facet=='predicates_roles':return collection=='terms' and family=='construction.predication' and row.get('kind')=='predicate'
    if facet=='operators_scope':return collection=='terms' and family in {'construction.scope','meaning.scope'} and row.get('kind') in {'operator','binder'}
    if facet=='attachment_binding':return collection=='roles' and family=='context.binding' and row.get('scheme')=='contextual-source-hypotheses-1' and row.get('role')=='declared_binding_site'
    if facet=='choice_compatibility':return collection=='choices'
    if facet=='provider_questions':return collection=='annotations' and 'model_answer' in row
    if facet=='coverage_failure':return collection=='coverage' and row['outcome'] not in {'complete','empty'}
    if facet=='retained_consumer_fidelity':return collection=='annotations' and 'native_token' in row and family.startswith('hanlp.')
    return False


def relevant(facet,families):
    if facet=='host_choice_questions':return 'character_host_choice_v1' in families
    if facet=='referent_choice_questions':return 'character_referent_choice_v1' in families
    if facet=='native_fidelity':return any(f.startswith('spacy.') for f in families)
    if facet=='retained_consumer_fidelity':return any(f.startswith('hanlp.') for f in families)
    if facet=='formal_structure':return 'formal.math' in families
    if facet=='predicates_roles':return 'construction.predication' in families
    if facet=='operators_scope':return bool({'construction.scope','meaning.scope'} & set(families))
    if facet=='attachment_binding':return 'context.binding' in families
    if facet=='provider_questions':return any(f.startswith('character_') for f in families)
    if facet=='choice_compatibility':return any(f.startswith(('formal.','construction.','context.','meaning.','character_')) for f in families)
    return facet=='coverage_failure'


def real_extents(values):
    keys=('source_view_id','projection','native_pointer','start','end')
    return [{key:value[key] for key in keys} for value in values
            if not value.get('synthetic',False) and all(key in value for key in keys)
            and value['start']<value['end']]


def scope_extents(body,row,collection,sources):
    if collection=='coverage':
        selected=[]
        for identity in body['source_scope']['source_view_ids']:
            source=sources[identity]
            selectors=[s for field in ('eligible','examined','unexamined') for s in row.get(field,[]) if s['projection']==source['projection_digest']]
            for piece in source['projection']['pieces']:
                if piece['kind']!='native_text':continue
                for selector in selectors:
                    start=max(piece['start'],selector.get('start',piece['start']))
                    end=min(piece['end'],selector.get('end',piece['end']))
                    if start<end:
                        selected.append(dict(source_view_id=identity,projection=source['projection_digest'],native_pointer=piece['item_ref'],start=start,end=end))
        # Coverage with no eligible selector still has a declared source scope, but
        # must not be disguised as an ordinary correct-empty semantic output.
        if not selected:
            for identity in body['source_scope']['source_view_ids']:
                source=sources[identity]
                selected.extend(dict(source_view_id=identity,projection=source['projection_digest'],native_pointer=p['item_ref'],start=p['start'],end=p['end']) for p in source['projection']['pieces'] if p['kind']=='native_text')
    else:
        occurrence={o['local_id']:o['extents'] for o in body.get('occurrences',[])}
        selected=row['extents'] if collection=='occurrences' else [e for key in row.get('occurrences',[]) for e in occurrence[key]]
    return list({canonical_bytes(e):e for e in real_extents(selected)}.values())


def prepare(conn,bound):
    runs=table('ops.run')
    captured=conn.execute(select(runs.c.id,runs.c.project_id,runs.c.release_id)
                          .where(runs.c.id==CAPTURE)).mappings().one_or_none()
    source_release=capture_release(captured,bound)
    view_pin=ProductReference(**bound['view'])
    view=read_view(conn,view_pin,run_id=bound['run_id'])
    if view.base_document != verifier.ORIGINAL:
        raise ValueError('output-first view does not preserve original integrated source')
    source,membership=table('kb.source_view'),table('ops.run_source_view')
    sources={row['id']:row for row in conn.execute(select(source).join(membership,membership.c.source_view_id==source.c.id).where(membership.c.run_id==CAPTURE)).mappings()}
    if len(sources)!=316 or set(view.payload['source_scope']['source_view_ids'])!=set(sources):
        raise ValueError('final combined document must select the exact frozen316 views')
    selected=[];skips=[];missing=set(FACETS)
    for value in view.payload.get('active_layers',view.payload['layers']):
        if not missing:break
        pin=ProductReference(**value)
        manifest=read_layer_manifest(conn,pin)
        header=manifest.payload
        if set(header['source_scope']['source_view_ids'])-set(sources):
            raise ValueError('active layer scope escapes original source capture')
        # A bounded packet is a functional consumer constraint. Prefer small original
        # natural units; record this exposed purposive restriction, never infer accuracy.
        if any(len(sources[i]['projection']['text'])>12000 for i in header['source_scope']['source_view_ids']):
            skips.append(dict(facet=None,layer=value,reason='source natural unit exceeds explicit12000 character packet limit'))
            continue
        body=None;projection=None
        for facet in FACETS:
            if facet not in missing or not relevant(facet,header['operation']['produced_families']):continue
            if facet=='coverage_failure' and not any(qualifies(facet,'coverage',r) for r in header['coverage']):continue
            if body is None:
                body=read_layer(conn,pin,max_bytes=64*1024**2).payload
                def load(dependency):
                    return body if pin_key(dependency)==pin_key(value) else read_layer(conn,ProductReference(**dependency),max_bytes=64*1024**2).payload
                projection=LayerProjection(load)
            for collection in ('annotations','terms','roles','choices','coverage'):
                candidates=[row for row in body.get(collection,[]) if qualifies(facet,collection,row)]
                for row in candidates:
                    local=row['family'] if collection=='coverage' else row['local_id']
                    extents=scope_extents(body,row,collection,sources)
                    # Choices can carry their occurrence only in the connected graph.
                    try:
                        graph=projection.graph(value,'@coverage:'+local if collection=='coverage' else local,max_bytes=131072)
                    except ValueError as error:
                        skips.append(dict(facet=facet,layer=value,collection=collection,local_id=local,reason=str(error)))
                        continue
                    if not extents:
                        extents=list({canonical_bytes(e):e for n in graph['nodes'] for e in real_extents(n['value'].get('extents',[]))}.values())
                    if not extents:continue
                    if collection!='coverage' and sum(e['end']-e['start'] for e in extents)>1600:
                        skips.append(dict(facet=facet,layer=value,collection=collection,local_id=local,reason='direct extents exceed explicit1600 character packet limit'))
                        continue
                    identities=sorted({e['source_view_id'] for e in extents})
                    if set(identities)-set(sources):raise ValueError('selected output escapes original source capture')
                    witness_sources={e['source_view_id'] for n in graph['nodes'] for e in real_extents(n['value'].get('extents',[]))}
                    selected.append(dict(facet=facet,question=QUESTIONS[facet],output=dict(layer=value,collection=collection,local_id=local),family=row.get('family'),extents=extents,source_views=identities,witness_source_views=sorted(witness_sources),retained_value=row,graph_preview_bytes=len(canonical_bytes(graph))))
                    missing.remove(facet)
                    break
                if facet not in missing:break
    by_unit=defaultdict(list)
    for item in selected:by_unit[item['source_views'][0]].append(item)
    frames={}
    def source_pin(identity,*,focal=False):
        row=sources[identity];base=view.base_document
        return dict(source=source_binding(conn,source_run_id=CAPTURE,source_view_id=identity,source_cut_id=CUT) if focal else row['key'],native_product_task_id=base.task_id,product_key=base.product_key,product_digest=base.content_digest,projection_digest=row['projection_digest'],recipe_digest=row['recipe_digest'],source_view_id=identity)
    for identity,items in by_unit.items():
        pin=source_pin(identity,focal=True)
        related=sorted({s for item in items for s in (*item['source_views'],*item['witness_source_views'])}-{identity})
        opportunities=[dict(opportunity_id='output-'+item['facet'],extents=item['extents'],facet='provider_questions' if item['facet'] in {'host_choice_questions','referent_choice_questions'} else item['facet'],source_state='uninspected') for item in items]
        frame=dict(unit=sources[identity]['key'],release_id=source_release,guideline_version='characterization-candidate-reference-3',rubric_version='chapter-facet-task-semantics-1',context_policy='exact-retained-output-with-protected-witness-context-1',operation_question='\n'.join('output-'+item['facet']+': '+item['question'] for item in items),operation_version='text-characterization-output-panel-2',domain='statistics',direction='output_first',pin=pin,anchor_ids=[],related_pins=[source_pin(s) for s in related],anchor_scopes=[],contribution_ids=[],source_group='grinstead-snell',partition='development',inspected_scope='Exact frozen producer output population, original source extents and protected interpretation-only witness closure; no reference answers inspected.',opportunities=opportunities,exposure_history=['shared-full-book-development','producer-output-selection'],characterization_view=view_pin.values(),selected_layers=list({canonical_bytes(item['output']['layer']):item['output']['layer'] for item in items}.values()),outputs=frame_outputs(items))
        wire=dict(protocol='source-operation-frame-3',evaluation_frame=frame,captured_coordinates=[],context_dependency_digest=None)
        decode_frame(wire)
        frames[sources[identity]['key']]=wire
    manifest=dict(version='bep-tc-output-panel-selection-1',source_run=CAPTURE,source_cut=CUT,source_release_id=source_release,view_release_id=view.payload['release_id'],project=PROJECT,view=view_pin.values(),binding_sha256=sha256(canonical_bytes(bound)).hexdigest(),selection='First bounded matching actual output per facet in frozen active-layer/collection order; purposive exposed development panel; at most12000 source chars per involved natural unit,1600 direct noncoverage occurrence chars,128KiB graph preview. No correct/incorrect outcome filter.',facets=list(FACETS),selected=selected,missing_facets=sorted(missing),skipped_graphs=skips,semantic_answers_authored=False)
    write('manifest.json',manifest)
    write('sample.json',dict(sampling=dict(seed=0,cohort='bep-tc-output-first-facet-and-choice-panel-1',strata={key:'retained-output-facets' for key in frames},inclusion_probabilities={key:1.0 for key in frames},provenance=dict(selection=manifest['selection'],probability_meaning='Certain membership within explicitly selected panel only; no book-wide accuracy inference.',manifest_sha256=sha256(canonical_bytes(manifest)+b'\n').hexdigest(),producer_outputs_inspected=True,reference_answers_inspected=False)),frames=frames))
    print(json.dumps(dict(units=len(frames),outputs=len(selected),missing_facets=sorted(missing))))


def packets(conn,set_id):
    units=table('eval.reference_unit')
    index=[]
    for row in conn.execute(select(units.c.id,units.c.unit_key).where(units.c.set_id==set_id).order_by(units.c.id)).mappings():
        packet=author_packet(conn,row['id'])
        name=f"author-unit-{row['id']}.json"
        write(name,packet)
        index.append(dict(unit_id=row['id'],unit_key=row['unit_key'],packet=name,bytes=len(canonical_bytes(packet))+1))
    if not index:raise ValueError('protected reference set has no units')
    write('author-packets.json',dict(set_id=set_id,packets=index,reference_answers_authored=False))
    print(json.dumps(dict(set_id=set_id,packets=len(index),bytes=sum(r['bytes'] for r in index))))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['select','packets'])
    parser.add_argument('--set-id',type=int)
    parser.add_argument('--binding',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    bound,_pin=verifier.binding(args.binding)
    OUTPUT=args.output
    OUTPUT.mkdir(parents=True,exist_ok=True)
    if args.action=='select' and (OUTPUT/'sample.json').exists():parser.error('output already contains frozen selection; use a new output directory')
    if args.action=='packets' and args.set_id is None:parser.error('packets requires exact --set-id')
    with open_runtime_engine(Settings(),'tc11-output-first-selection',purpose='evaluate' if args.action=='packets' else 'read') as engine,engine.connect() as conn:
        conn.exec_driver_sql('SET TRANSACTION READ ONLY')
        prepare(conn,bound) if args.action=='select' else packets(conn,args.set_id)
