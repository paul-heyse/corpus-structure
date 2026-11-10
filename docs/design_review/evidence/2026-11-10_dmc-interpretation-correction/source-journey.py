"""Real retained PDF source → authored records/reviews → pinned CLI/MCP consumers.

Run only after coordinated development admission: uv run python source-journey.py RELEASE.
Creates new private runs through ordinary source-task completion; preserves run487/cut604.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import anyio
from fastmcp import Client
from sqlalchemy import select,text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_sources import prepare_structural_sources,StructuralPassageSelection
from corpus_structure.semantic.record_contracts import anchor_identity,evidence_set_identity,record_identity,interpretation_identity
from corpus_structure.semantic.interpretations import lookup_terms,metadata_binding
from corpus_structure.serve.interpretation_authoring import author_interpretations
from corpus_structure.serve.record_results import RecordRequest,serve_record_results
from corpus_structure.semantic.interpretation_queries import TerminologySelection,collect_interpretation_uses,measurement_groups
from corpus_structure.settings import Settings

HERE=Path(__file__).parent
RAW=HERE/'raw';RAW.mkdir(exist_ok=True)


def cli_answer(name,*arguments):
    completed=subprocess.run(['uv','run','ci',*map(str,arguments),'--json'],capture_output=True,text=True)
    (RAW/(name+'.stdout.json')).write_text(completed.stdout)
    (RAW/(name+'.stderr.txt')).write_text(completed.stderr)
    if completed.returncode:
        raise RuntimeError(f'{name} refused with status {completed.returncode}; retained stdout/stderr')
    return json.loads(completed.stdout)


def source_reference(engine,run_id,view_id,start,end):
    captured=prepare_structural_sources(engine,[StructuralPassageSelection(run_id=run_id,source_view_id=view_id,passage_id='inspection',start=start,end=end,scope='selected original source passage')])
    return captured.sources[0].model_dump(mode='json')


def source_target(conn,*,run_id,record_id,role,phrase):
    query=text('''SELECT cr.cut_id,cr.release_id,cr.output_realization_id,z.data_revision,r.project_id,s.source_view_id,s.interpretation_id,a.anchor_id,a.start,a.end,a.source_piece
    FROM ops.completed_result cr JOIN ops.run r ON r.id=cr.run_id
    JOIN data.realization z ON z.realization_id=cr.output_realization_id AND z.release_id=cr.release_id
    JOIN data.source_record s ON s.realization_id=z.realization_id AND s.release_id=z.release_id
    JOIN data.record_field_evidence fe ON fe.realization_id=s.realization_id AND fe.release_id=s.release_id AND fe.record_id=s.record_id AND fe.interpretation_id=s.interpretation_id
    JOIN data.record_evidence_member em ON em.realization_id=fe.realization_id AND em.release_id=fe.release_id AND em.record_id=fe.record_id AND em.interpretation_id=fe.interpretation_id AND em.set_id=fe.set_id
    JOIN data.record_anchor a ON a.realization_id=em.realization_id AND a.release_id=em.release_id AND a.record_id=em.record_id AND a.interpretation_id=em.interpretation_id AND a.anchor_id=em.anchor_id
    WHERE cr.run_id=:run AND s.record_id=:record AND fe.role=:role AND a.precision='exact' AND position(:phrase in a.source_piece)>0''')
    rows=conn.execute(query,dict(run=run_id,record=record_id,role=role,phrase=phrase)).mappings().all()
    assert len(rows)==1,'source field focus must be independently unambiguous'
    row=rows[0]
    ref=dict(project_id=row['project_id'],run_id=run_id,cut_id=row['cut_id'],release_id=row['release_id'],realization_id=row['output_realization_id'],data_revision=row['data_revision'],record_id=record_id,interpretation_id=row['interpretation_id'],source_view_id=row['source_view_id'])
    start=row['start']+row['source_piece'].index(phrase)
    return ref,dict(role=role,anchor_id=row['anchor_id'],start=start,end=start+len(phrase),source_piece=phrase)


def term_payload(prepared,ref,focus,field,value):
    candidates=lookup_terms(prepared,field,browse=True)
    return dict(source_record=ref,vocabulary_release=prepared.release_id,metadata_digest=candidates['metadata_digest'],lookup_policy='released-lexical-1',decisions=[dict(field=field,focus=focus,candidates=candidates['candidates'],outcome='selected',selected_value=value,mapping_predicate='http://www.w3.org/2004/02/skos/core#exactMatch',mapping_direction='source_to_term',assessment='Explicit source wording identifies this mathematical distribution concept; this retained private interpretation does not establish scientific truth or global identity.',reviewer='Codex source-reviewed authoring')])


def authored_measurement(prepared,projection,source):
    text_=projection['text'];offset=text_.index('1000 hours')
    sentence_start=text_.rfind('\n',0,offset)+1;sentence_end=text_.find('\n',offset)
    sentence=text_[sentence_start:sentence_end]
    assert 'lightbulbs' in sentence and 'lifetime' in sentence
    piece=next(p for p in projection['pieces'] if p.get('item_ref') and p['start']<=offset<p['end'])
    pointer=piece['item_ref']
    pin=dict(source=projection['_source_key'],native_product_task_id=source['native_task_id'],product_key=source['native_product_key'],product_digest=source['native_content_digest'],projection_digest=source['projection_digest'],recipe_digest=source['recipe_digest'],source_view_id=source['source_view_id'])
    occurrence=dict(pin=pin,space='native',pointer=pointer,precision='item')
    occurrence['anchor_id']=anchor_identity(occurrence)
    anchors=[occurrence];sets=[];fields=[]
    values={'referent':'lightbulbs','property':'exponential lifetime','original_value':'1000','unit':'hours'}
    definition=prepared.index.definitions['MeasurementRecordFields']
    for prop in definition.properties:
        if prop.name in ('family','occurrence_recipe'):continue
        role=prop.name;kind={'value_role':'classified','normalized_value':'normalized'}.get(role,'literal')
        role_type=prepared.index.definitions[prop.range]
        field=dict(role=role,kind=kind,meaning_changing='MeaningChangingRecordField' in role_type.ancestors,evidence_status='unavailable',state='unresolved' if role=='value_role' else 'inapplicable' if role=='normalized_value' else 'unstated',reason='Not explicitly stated or classified by this source; no numeric role/basis/normalization inferred.')
        if role in values:
            literal=values[role];start=text_.index(literal,sentence_start,sentence_end)
            owner=next(p for p in projection['pieces'] if p.get('item_ref') and p['start']<=start and p['end']>=start+len(literal))
            anchor=dict(pin=pin,space='selected_projection',pointer=owner['item_ref'],precision='exact',start=start,end=start+len(literal),source_piece=literal)
            anchor['anchor_id']=anchor_identity(anchor);anchors.append(anchor)
            support=dict(role=role,ordering='ordered',usage='literal',anchors=(anchor['anchor_id'],));support['set_id']=evidence_set_identity(support);sets.append(support)
            field.pop('reason')
            field.update(state='present',evidence_status='available',original=literal,value=dict(kind='text',text=literal),evidence_sets=(support['set_id'],))
        fields.append(field)
    record=dict(contract='MeasurementRecordFields',family='measurement',occurrence_recipe='source-anchor-membership-1',pin=pin,occurrence_anchors=(occurrence['anchor_id'],),standing='candidate',policy_version='dmc-explicit-source-authoring-1',fields=fields,anchors=anchors,evidence_sets=sets)
    record['record_id']=record_identity(prepared.release_id,record);record['interpretation_id']=interpretation_identity(record)
    return record,sentence


async def main(release,attempt=None,resume=None):
    global RAW
    if attempt is not None:
        RAW=HERE/'raw'/attempt
        RAW.mkdir(exist_ok=False)
    settings=Settings()
    prior={r['name']:r for r in json.loads(Path(resume).read_bytes())} if resume else {}
    receipts=[]
    with open_runtime_engine(settings,'dmc-source-journey',purpose='write') as engine:
        with read_snapshot(engine) as conn:
            prepared=open_release(conn,release)
            normal=source_target(conn,run_id=487,record_id='record:742a9101cf2048e0c0c6d1da24011b9d6f93d4de9cdac15cd118b623edd645a9',role='term',phrase='normal distribution')
            variance=source_target(conn,run_id=487,record_id='record:13d0019d160034f9c529f09c2c5d55ae27213e55d06447f2b09d4ad55d5c8df6',role='defining_text',phrase='variance')
            original_run=dict(conn.execute(select(table('ops.run')).where(table('ops.run').c.id==487)).mappings().one())
            original_result=dict(conn.execute(select(table('ops.completed_result')).where(table('ops.completed_result').c.run_id==487)).mappings().one())
            old=conn.execute(select(table('data.project')).where(table('data.project').c.project_id==normal[0]['project_id'])).mappings().one()
        mcp_settings=Settings(runtime={'default_project':normal[0]['project_id']})
        for name,(ref,focus),field,value in (('normal',normal,'distribution_family','normal'),('variance',variance,'distribution_attribute','variance')):
            source=source_reference(engine,487,ref['source_view_id'],focus['start'],focus['end'])
            with read_snapshot(engine) as conn:
                projection=conn.scalar(select(table('kb.source_view').c.projection).where(table('kb.source_view').c.id==ref['source_view_id']))
                context_start=max(0,focus['start']-350);context_end=min(len(projection['text']),focus['end']+350)
                (RAW/(name+'-reviewed-source-context.json')).write_bytes(canonical_bytes(dict(source=source,context_start=context_start,context_end=context_end,text=projection['text'][context_start:context_end])))
            payload=term_payload(prepared,ref,focus,field,value)
            config=dict(source=source,reviews=[payload])
            if name in prior:
                result={k:v for k,v in prior[name].items() if k!='name'}
                config=json.loads((Path(resume).parent/(name+'-authored-input.json')).read_bytes())
                assert config['source']==source and config['reviews'][0]['source_record']==ref
                assert config['reviews'][0]['decisions'][0]['focus']==focus
            else:
                (RAW/(name+'-authored-input.json')).write_bytes(canonical_bytes(config))
                result=author_interpretations(engine,prepared,kind='terminology',configuration=config,settings=settings)
            (RAW/(name+'-authored-input.json')).write_bytes(canonical_bytes(config))
            review_release=result['release_id']
            receipts.append(dict(name=name,**result));(RAW/'source-journey-runs.json').write_bytes(canonical_bytes(receipts))
            selection=TerminologySelection(review_run_id=result['run_id'],review_cut_id=result['cut_id'],vocabulary_release=review_release,field=field,value=value,mapping_predicate='http://www.w3.org/2004/02/skos/core#exactMatch')
            with read_snapshot(engine) as conn:
                page=serve_record_results(conn,RecordRequest(run_id=487,record_id=ref['record_id'],terminology=selection,page_bytes=32*1024**2))
                assert page.matching_records==1 and page.records[0].terminology_reviews
                uses=collect_interpretation_uses(conn,source_run_id=487,review_run_id=result['run_id'],review_cut_id=result['cut_id'],vocabulary_release=review_release,member=value)
                assert uses['complete'] and len(uses['items'])==1
            (RAW/(name+'-filtered-record.json')).write_text(page.model_dump_json())
            (RAW/(name+'-known-uses.json')).write_bytes(canonical_bytes(uses))
            cli_page=cli_answer(name+'-cli-records','interpretations','records',487,result['run_id'],result['cut_id'],review_release,field,'--value',value,'--mapping-predicate','http://www.w3.org/2004/02/skos/core#exactMatch','--page-bytes',32*1024**2)
            assert cli_page['matching_records']==1 and cli_page['records'][0]['terminology_reviews']
            contribution_id=page.records[0].terminology_reviews[0]['contribution_id']
            review=cli_answer(name+'-cli-review','interpretations','review',result['run_id'],result['cut_id'],'--contribution',contribution_id)
            from corpus_structure.intervene.semantic_server import build_semantic_server
            async with Client(build_semantic_server(settings=Settings(runtime={'default_project':ref['project_id']}))) as client:
                reply=await client.call_tool('records',dict(request=RecordRequest(run_id=487,record_id=ref['record_id'],terminology=selection,page_bytes=32*1024**2).model_dump(mode='json')))
                assert not reply.is_error and reply.structured_content==page.model_dump(mode='json')
                inspected=await client.call_tool('inspect_terminology_review',dict(review_run=result['run_id'],review_cut=result['cut_id'],contribution_ids=[contribution_id]))
                assert not inspected.is_error and inspected.structured_content==review
                (RAW/(name+'-mcp-review.json')).write_bytes(canonical_bytes(inspected.structured_content))
        with read_snapshot(engine) as conn:
            projection=conn.scalar(select(table('kb.source_view').c.projection).where(table('kb.source_view').c.id==456))
            projection=dict(projection)
            projection['_source_key']=conn.scalar(select(table('kb.source_view').c.key).where(table('kb.source_view').c.id==456))
        offset=projection['text'].index('1000 hours')
        source=source_reference(engine,487,456,offset,offset+len('1000 hours'))
        record,sentence=authored_measurement(prepared,projection,source)
        record_config=dict(source=source,records=[record]);(RAW/'measurement-record-input.json').write_bytes(canonical_bytes(record_config))
        if 'authored_measurement' in prior:
            authored={k:v for k,v in prior['authored_measurement'].items() if k!='name'}
            record_config=json.loads((Path(resume).parent/'measurement-record-input.json').read_bytes())
            record=record_config['records'][0]
            (RAW/'measurement-record-input.json').write_bytes(canonical_bytes(record_config))
        else:
            authored=cli_answer('measurement-source-authoring','interpretations','author',release,'source_records',RAW/'measurement-record-input.json')['body']
        receipts.append(dict(name='authored_measurement',**authored));(RAW/'source-journey-runs.json').write_bytes(canonical_bytes(receipts))
        with read_snapshot(engine) as conn:
            ref,focus=source_target(conn,run_id=authored['run_id'],record_id=record['record_id'],role='unit',phrase='hours')
        source=source_reference(engine,487,456,focus['start'],focus['end'])
        digest,_=metadata_binding(prepared)
        payload=dict(source_record=ref,focus=focus,vocabulary_release=release,metadata_digest=digest,outcome='selected',unit='HOUR',quantity_kind='TIME',basis_status='unknown',assessment='Source states lifetime in hours. Numeric role, empirical status, reference basis and numerical equivalence remain unassessed.',reviewer='Codex source-reviewed authoring',numerical_equivalence='unassessed')
        config=dict(source=source,reviews=[payload]);(RAW/'measurement-recognition-input.json').write_bytes(canonical_bytes(config))
        if 'measurement_recognition' in prior:
            recognized={k:v for k,v in prior['measurement_recognition'].items() if k!='name'}
            previous=json.loads((Path(resume).parent/'measurement-recognition-input.json').read_bytes())
            assert previous==config
        else:
            recognized=author_interpretations(engine,prepared,kind='measurement',configuration=config,settings=settings)
        receipts.append(dict(name='measurement_recognition',**recognized));(RAW/'source-journey-runs.json').write_bytes(canonical_bytes(receipts))
        with read_snapshot(engine) as conn:
            groups=measurement_groups(conn,source_run_id=authored['run_id'],review_run_id=recognized['run_id'],review_cut_id=recognized['cut_id'])
            assert groups['complete'] and groups['groups'][0]['unit']=='HOUR' and groups['groups'][0]['quantity_kind']=='TIME'
            assert groups['groups'][0]['basis_status']=='unknown'
            unit_uses=collect_interpretation_uses(conn,source_run_id=authored['run_id'],review_run_id=recognized['run_id'],review_cut_id=recognized['cut_id'],vocabulary_release=release)
            assert unit_uses['complete'] and {(r['field'],r['selected_value']) for r in unit_uses['items']}=={('unit','HOUR'),('quantity_kind','TIME')}
            (RAW/'measurement-known-uses.json').write_bytes(canonical_bytes(unit_uses))
            after=conn.execute(select(table('data.project')).where(table('data.project').c.project_id==normal[0]['project_id'])).mappings().one_or_none()
            assert dict(old or {})==dict(after or {})
            assert original_run==dict(conn.execute(select(table('ops.run')).where(table('ops.run').c.id==487)).mappings().one())
            assert original_result==dict(conn.execute(select(table('ops.completed_result')).where(table('ops.completed_result').c.run_id==487)).mappings().one())
        (RAW/'measurement-groups.json').write_bytes(canonical_bytes(groups))
        cli_groups=cli_answer('measurement-cli-groups','interpretations','measurements',authored['run_id'],recognized['run_id'],recognized['cut_id'])
        assert cli_groups['body']==groups
        from corpus_structure.intervene.semantic_server import build_semantic_server
        async with Client(build_semantic_server(settings=mcp_settings)) as client:
            reply=await client.call_tool('group_measurement_interpretations',dict(source_run=authored['run_id'],review_run=recognized['run_id'],review_cut=recognized['cut_id']))
            assert not reply.is_error and reply.structured_content['body']==groups
        comparison=cli_answer('pinned-exclusion-comparison','research','compare-exclusions','--before-run',487,'--after-run',487,'--max-rows',10000,'--max-bytes',8*1024**2)
        async with Client(build_semantic_server(settings=mcp_settings)) as client:
            reply=await client.call_tool('compare_identity_exclusions',dict(before_run=487,after_run=487,max_rows=10000,max_bytes=8*1024**2))
            (RAW/'pinned-exclusion-comparison-mcp.json').write_bytes(canonical_bytes(reply.structured_content))
            left=json.loads(canonical_bytes(reply.structured_content));right=json.loads(canonical_bytes(comparison))
            for side in ('before','after'):
                left['comparison'][side]['binding'].pop('capture_id')
                right['comparison'][side]['binding'].pop('capture_id')
            assert not reply.is_error and left==right
        from corpus_structure.semantic.portable_interpretation import export_interpretation_contract
        package=RAW/'offline-contract'
        if package.exists():raise ValueError('evidence package already exists; retain prior attempt and use a fresh folder')
        exported=export_interpretation_contract(prepared,package)
        instance=dict(kind='proposal',semantic_type='terminology.interpretation',effect='retain_private',assessment_event='local-contribution-1',question='interpret.terminology',value=term_payload(prepared,*normal,'distribution_family','normal'))
        path=RAW/'offline-input.json';path.write_bytes(canonical_bytes(instance))
        script=Path(__file__).parents[4]/'examples/offline_interpretation.py'
        completed=subprocess.run([sys.executable,'-I',str(script),str(package),str(path),'--expected-digest',exported['manifest_digest']],capture_output=True,text=True)
        (RAW/'offline-preflight.stdout.json').write_text(completed.stdout)
        (RAW/'offline-preflight.stderr.txt').write_text(completed.stderr)
        assert completed.returncode==0
        assert json.loads(completed.stdout)['outcome']=='passed'
        result=dict(outcome='passed',release=release,source_run=487,source_cut=604,source_sentence=sentence,receipts=receipts,checks=['normal-and-variance-filter','retained-review-cli-mcp-parity','cli-mcp-shared-read','bound-use-survey','genuine-hours-record','recognized-time-hour-group','independent-offline-preflight','pinned-exclusion-cli-mcp-parity','protected-project-unchanged'])
        (RAW/'source-journey-result.json').write_bytes(canonical_bytes(result));print(json.dumps(result))


if __name__=='__main__':anyio.run(main,*sys.argv[1:])
