import sys,json
from pathlib import Path
from sqlalchemy import text
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.artifact_identity import ArtifactScoringPolicy,ArtifactIdentityProduct,score_pairs,pair_candidates
from corpus_structure.methods.artifact_identity import discover_identity_records
from corpus_structure.settings import Settings
sys.path.insert(0,'python/corpus-structure/tests/semantic')
from test_artifact_identity_native import artifact_helper_sql
p=json.loads(Path('/home/paul/corpus-structure/docs/design_review/evidence/2026-11-06_wce-gs120/source-packets/source-packet.json').read_bytes())
inputs=StructuralInput.model_validate(dict(question='Artifact candidate development',scope='shared GS120',inventory_id='gs120-artifacts',policy_id='artifact-candidate-1',sources=p['sources'],passages=p['passages'],dependencies=list(dict.fromkeys('native:'+str(s['native_task_id']) for s in p['sources']))))
policy=ArtifactScoringPolicy(prior=.1,code_m=.9,code_u=.01,title_m=.8,title_u=.05)
bindings=[dict(native_content_digest=d,source_work=p['source_manifest']['parent_sha256'],provenance='authenticated-gs120-parent-manifest') for d in sorted({s.native_content_digest for s in inputs.sources})]
cfg=dict(work_bindings=bindings,policy=policy.model_dump(mode='json'),title_threshold=70,external_pairs=[],exclusions=[])
records=[]
with open_runtime_engine(Settings(),'wce-artifact-rollback-check',purpose='maintenance') as engine,engine.connect() as conn:
    tx=conn.begin()
    try:
        conn.exec_driver_sql(artifact_helper_sql(),execution_options={'no_parameters':True})
        for source in inputs.sources:
            frame=native_source_frame(load_source_view(conn,source.source_view_id,analysis=False),())
            records.extend(discover_identity_records(frame,inputs,source.identity,p['source_manifest']['parent_sha256']))
        cohort={}
        for record in sorted(records,key=lambda r:r.contribution_id):cohort.setdefault((record.occurrence_id,record.artifact.source_work,record.artifact.artifact_kind),record)
        records=tuple(cohort.values())
        expected=[r.model_dump(mode='json',exclude_none=True) for r in records]
        actual=conn.scalar(text('SELECT ops.artifact_source_records(CAST(:i AS jsonb),CAST(:c AS jsonb))'),dict(i=inputs.model_dump_json(exclude_none=True),c=json.dumps(cfg)))
        if actual!=expected:
            print('record-counts',len(actual),len(expected))
            for a,b in zip(actual,expected):
                if a!=b:
                    print('native',json.dumps(a));print('python',json.dumps(b));break
            raise AssertionError('native source cohort differs')
        pairs=score_pairs(records,pair_candidates(records),policy)
        product=ArtifactIdentityProduct(records=records,pairs=pairs,policy=policy,source_mapping_provenance=('authenticated-gs120-parent-manifest',))
        conn.execute(text('SELECT ops.validate_artifact_identity(CAST(:i AS jsonb),CAST(:c AS jsonb),CAST(:p AS jsonb))'),dict(i=inputs.model_dump_json(exclude_none=True),c=json.dumps(cfg),p=product.model_dump_json(exclude_none=True)))
        from copy import deepcopy
        from sqlalchemy.exc import DBAPIError
        payload=product.model_dump(mode='json',exclude_none=True)
        statement=text('SELECT ops.validate_artifact_identity(CAST(:i AS jsonb),CAST(:c AS jsonb),CAST(:p AS jsonb))')
        def check(candidate,configuration=cfg,selected=inputs):
            conn.execute(statement,dict(i=selected.model_dump_json(exclude_none=True),c=json.dumps(configuration),p=json.dumps(candidate)))
        mutants=[]
        for key,value in [('title','invented caption'),('scope','invented scope')]:
            bad=deepcopy(payload);bad['records'][0]['artifact'][key]=value;mutants.append((key,bad))
        for key in ('contribution_id','occurrence_id'):
            bad=deepcopy(payload);bad['records'][0][key]='forged';mutants.append((key,bad))
        for key,value in [('candidate_routes',['external_pairs']),('lexical_score',.314),('model_probability',.2),('model_id','forged')]:
            bad=deepcopy(payload);bad['pairs'][0][key]=value;mutants.append((key,bad))
        bad=deepcopy(payload);bad['pairs'].pop();mutants.append(('missing-pair',bad))
        bad=deepcopy(payload);bad['records'].pop();mutants.append(('missing-source-record',bad))
        for label,bad in mutants:
            try:
                with conn.begin_nested():check(bad)
            except DBAPIError as exc:
                assert getattr(exc.orig,'sqlstate',None)=='23514',(label,str(exc))
            else:raise AssertionError('forgery accepted: '+label)
            print('refused',label)
        for invalid in (0,1):
            bad=deepcopy(payload);configuration=deepcopy(cfg);bad['policy']['prior']=invalid;configuration['policy']['prior']=invalid
            try:
                with conn.begin_nested():check(bad,configuration)
            except DBAPIError as exc:assert getattr(exc.orig,'sqlstate',None)=='23514'
            else:raise AssertionError('invalid probability accepted')
            print('refused policy boundary',invalid)
        unavailable=ArtifactIdentityProduct(policy=policy,unbound_source_ids=tuple(s.source_view_id for s in inputs.sources))
        unbound_cfg={**cfg,'work_bindings':[]}
        check(unavailable.model_dump(mode='json',exclude_none=True),unbound_cfg)
        print('passed all-source-unbound diagnostic')
        first=records[0];citation=first.citations[0];oldpassage=next(p for p in inputs.passages if p.passage_id==citation.passage_id)
        passage=oldpassage.model_copy(update=dict(start=citation.start,end=citation.end,text=citation.text))
        reference=next(s for s in inputs.sources if s.identity==citation.source_ref)
        singleton_inputs=inputs.model_copy(update=dict(sources=(reference,),passages=(passage,)))
        frame=native_source_frame(load_source_view(conn,reference.source_view_id,analysis=False),())
        singleton_records=discover_identity_records(frame,singleton_inputs,reference.identity,p['source_manifest']['parent_sha256'])
        assert len(singleton_records)==1
        singleton=ArtifactIdentityProduct(records=singleton_records,policy=policy,source_mapping_provenance=('authenticated-gs120-parent-manifest',))
        check(singleton.model_dump(mode='json',exclude_none=True),cfg,singleton_inputs)
        print('passed singleton/no-candidate diagnostic')
        print('passed',len(records),'source records',len(pairs),'frozen-model pairs; 12 refusals and2 diagnostics')
    finally:tx.rollback()
