"""Authorized protected import/publication of two frozen independently supported attachments.

No provider execution. Expected cases are immutable original author bytes with only
frame_digest rebound; publication tasks must reuse exact completed producer task800.
"""
from __future__ import annotations
import argparse
import json
from hashlib import sha256
from pathlib import Path
from sqlalchemy import select,text
from sqlalchemy.exc import DBAPIError
from corpus_structure.evaluate.record_references import assign_origin
from corpus_structure.evaluate.structural_assessment import StructuralAuthoredReference,StructuralEvaluationFrame,create_structural_reference_set,record_structural_reference_pass,score_structural_reference
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding,create_run,create_task,start_run
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_run
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import RetainedComponentRef,RetainedStructuralRef,StructuralProductReport
from corpus_structure.serve.structural_products import StructuralRequest,serve_structural_products
from corpus_structure.serve.review_bundle import ReviewSelection,export_review_bundle,verify_review_bundle
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
GS=HERE.parents[2]
C=PARENT/'adjudicator-c'
PROJECT='wce-gs120-method-development-20261106'
RUN=160
CUT=210
TASK=800
RELEASE='release:cb08727ec668c048998c82db31ef0e1242d714ca23e2b0f2a223eb88c6061a29'
POSITIVES=('1260f6b3c5b66b10b7d058303de67975cf8e98c4fa748d69c8d788f258aa5989','dd40f6c3f4447b2a25797110af22a04d16d1b35b1ed08f88f9c1922332d515d5')
ACTORS={'A':'independent-source-author:A','B':'independent-B:/root/baseline_definition_review_b','C':'adjudicator-C:/root/baseline_output_adjudication_c'}

def read(p):return json.loads(p.read_bytes())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def retain(p,value):p.write_bytes(canonical_bytes(value)+b'\n')

def source():
    inspection=read(GS/'consumer-transports/named160-cli.json')
    transport=read(GS/'assessment/run160-exact-transport001.json')
    assert inspection['run_id']==RUN and inspection['cut_id']==CUT and inspection['release_id']==RELEASE
    assert transport['outcome']=='passed' and transport['complete_report_bytes_equal'] and transport['all_original_source_pins_equal']
    report=StructuralProductReport.model_validate(inspection['reports'][0]);assert report.product_id==transport['product_id']
    raw=read(GS/'assessment/run160-final-named001/task-800.json');assert raw['origin_task_id']==TASK and raw['selected_task_id']==TASK
    assert StructuralProductReport.model_validate(raw['body']['structural_product'])==report
    return inspection,report

def prepare():
    inspection,report=source();archive=HERE/'original';archive.mkdir(exist_ok=True)
    original={};names={'A':'A.authored.original.json','B':'B.authored.original.json','C':'C.authored.json'}
    for kind,name in names.items():
        data=(C/name).read_bytes();target=archive/(kind+'.authored.original.json')
        if target.exists():assert target.read_bytes()==data
        else:target.write_bytes(data)
        original[kind]=json.loads(data)
    proposal=StructuralEvaluationFrame.model_validate(read(C/'frame.proposed-run152.json'))
    assert proposal.inputs==report.inputs and proposal.product_ids==(report.product_id,)
    frame=proposal.model_copy(update={'exposure_history':(*proposal.exposure_history,'Root authorized2026-11-06 run160/cut210/task800 exact report/source transport from run152; original author cases unchanged. Only two independent supported attachments authorized for narrow publication.')})
    references={}
    for kind,old in original.items():
        value=dict(old,frame_digest=frame.identity)
        assert {k:v for k,v in value.items() if k!='frame_digest'}=={k:v for k,v in old.items() if k!='frame_digest'}
        ref=StructuralAuthoredReference.model_validate(value);references[kind]=ref
        retain(HERE/(kind+'.authored.rebound.json'),value)
        comparison=score_structural_reference(frame,ref,report.model_dump(mode='json',exclude_none=True))
        assert all(x['outcome']=='match' for x in comparison['cases'] if x['judgment']=='supported')
        retain(HERE/(kind+'.comparison.json'),comparison)
    mapping=read(C/'adjudication-case-correspondence.json');parents={k:{c.case_id:c for c in references[k].cases} for k in 'AB'}
    for case in references['C'].cases:
        for author in 'AB':
            parent=parents[author][mapping[case.case_id][author]]
            assert (case.component_id,case.facet,case.path)==(parent.component_id,parent.facet,parent.path)
    actual_supported={c.component_id for c in references['C'].cases if c.facet=='public_statement' and c.judgment=='supported'}
    assert actual_supported==set(POSITIVES)
    retain(HERE/'frame.final160.json',frame.model_dump(mode='json',exclude_none=True))
    retain(HERE/'frame-rebinding.json',{'outcome':'passed','run_id':RUN,'cut_id':CUT,'selected_task_id':TASK,'release_id':RELEASE,'product_id':report.product_id,'frame_digest':frame.identity,'root_transport_file':str(GS/'assessment/run160-exact-transport001.json'),'root_transport_sha256':digest(GS/'assessment/run160-exact-transport001.json'),'authors':{k:{'actor':ACTORS[k],'original_sha256':digest(archive/(k+'.authored.original.json')),'original_frame_digest':original[k]['frame_digest'],'rebound_sha256':digest(HERE/(k+'.authored.rebound.json')),'only_changed_field':'frame_digest','cases_exactly_preserved':True} for k in 'ABC'},'adjudication_correspondence':mapping,'publication_selection':list(POSITIVES),'other_components':'private; no added judgment or vote','limits':'Exact narrow source attribution, no scientific truth, condition completeness or whole-report correctness.'})
    return report,frame,references

def import_references():
    if (HERE/'protected-reference-receipt.json').exists():return read(HERE/'protected-reference-receipt.json')
    report,frame,refs=prepare();inventory=read(HERE/'origin-inventory001.json');uris=tuple(inventory['source_uris']);assert len(uris)==12
    with open_runtime_engine(Settings(),'gs120-native160-protected-import',purpose='evaluate') as engine,engine.begin() as conn:
        # Authoritative retained custody check precedes any protected reference mutation.
        row=conn.execute(text('''SELECT r.project_id,r.release_id,c.final,t.status,t.id selected_task_id,m.origin_task_id,result.body
          FROM ops.run r JOIN ops.input_cut c ON c.run_id=r.id JOIN ops.cut_task m ON m.cut_id=c.id
          JOIN ops.task t ON t.id=m.task_id JOIN ops.task_result result ON result.task_id=m.origin_task_id
          WHERE r.id=:run AND c.id=:cut AND t.id=:task'''),{'run':RUN,'cut':CUT,'task':TASK}).mappings().one()
        assert row['project_id']==PROJECT and row['release_id']==RELEASE and row['final'] and row['status']=='done' and row['origin_task_id']==TASK
        assert StructuralProductReport.model_validate(row['body']['structural_product'])==report
        assign_origin(conn,project_id=PROJECT,origin_group='grinstead-snell',partition='development',source_uris=uris,provenance={'source':'Root-authorized existing physical191-310 source URI set; one book origin, exposed development assessment','source_uri_inventory_sha256':digest(HERE/'origin-inventory001.json'),'held_out':False})
        origins=[dict(r) for r in conn.execute(text('''SELECT m.source_uri,g.origin_group,g.partition FROM eval.reference_origin_source m JOIN eval.reference_origin_group g ON g.project_id=m.project_id AND g.origin_group=m.origin_group WHERE m.project_id=:p AND m.source_uri=ANY(:u) ORDER BY m.source_uri'''),{'p':PROJECT,'u':list(uris)}).mappings()]
        assert len(origins)==12 and all(r['origin_group']=='grinstead-snell' and r['partition']=='development' for r in origins)
        set_id=create_structural_reference_set(conn,project_id=PROJECT,release_id=RELEASE,frame=frame)
        ids={}
        for kind in 'AB':ids[kind]=record_structural_reference_pass(conn,set_id=set_id,pass_kind=kind,actor=ACTORS[kind],authored=(HERE/(kind+'.authored.rebound.json')).read_bytes())
        binding={'protocol':'gs120-C-exact-native-parent-binding-1','state':'native_A_B_stored_in_pending_import_transaction_before_C_attachment','set_id':set_id,'frame_digest':frame.identity,'candidate_run_id':RUN,'candidate_cut_id':CUT,'candidate_task_id':TASK,'product_id':report.product_id,'C_actor':ACTORS['C'],'C_original_sha256':digest(HERE/'original/C.authored.original.json'),'C_rebound_sha256':digest(HERE/'C.authored.rebound.json'),'parents':[{'pass_kind':k,'pass_id':ids[k],'actor':ACTORS[k],'original_sha256':digest(HERE/'original'/(k+'.authored.original.json')),'authored_sha256':digest(HERE/(k+'.authored.rebound.json'))} for k in 'AB'],'parent_argument':[ids['A'],ids['B']],'case_correspondence':read(C/'adjudication-case-correspondence.json'),'authority':'SQL exact native parent argument, not fabricated IDs; original differing historical alternatives preserved.'}
        retain(HERE/'C-parent-binding-before-attachment.json',binding)
        ids['C']=record_structural_reference_pass(conn,set_id=set_id,pass_kind='C',actor=ACTORS['C'],authored=(HERE/'C.authored.rebound.json').read_bytes(),parents=(ids['A'],ids['B']))
        stored=conn.execute(select(table('eval.structural_reference_pass')).where(table('eval.structural_reference_pass').c.id==ids['C'])).mappings().one()
        assert list(stored['parents'])==[ids['A'],ids['B']] and bytes(stored['authored'])==(HERE/'C.authored.rebound.json').read_bytes()
        receipt={'outcome':'passed','set_id':set_id,'frame_digest':frame.identity,'pass_ids':ids,'actors':ACTORS,'c_content_digest':stored['content_digest'],'C_exact_parent_ids':list(stored['parents']),'origin_assignments':origins,'product_id':report.product_id,'candidate_run':RUN,'candidate_cut':CUT,'candidate_selected_task':TASK,'producer_reexecuted':False,'publication':'not_yet_requested_by_this_phase'}
    retain(HERE/'protected-reference-receipt.json',receipt)
    return receipt

def admissions():
    r=read(HERE/'protected-reference-receipt.json')
    return [dict(product_id=r['product_id'],component_id=component,set_id=r['set_id'],c_pass_id=r['pass_ids']['C'],c_content_digest=r['c_content_digest'],frame_digest=r['frame_digest'],policy_id='independent-definition-component-1') for component in POSITIVES]

def create_reuse_run(engine,selected_admissions,label):
    with engine.begin() as conn:
        job=dict(conn.execute(select(table('ops.run')).where(table('ops.run').c.id==RUN)).mappings().one());task=dict(conn.execute(select(table('ops.task')).where(table('ops.task').c.id==TASK)).mappings().one())
        prepared=open_release(conn,RELEASE);runtime=runtime_binding_for_run(conn,RUN,prepared)
        deps=json.loads(bytes(job['dependencies']));deps['structural_admission']=selected_admissions
        run=create_run(conn,project_id=PROJECT,binding=OperationBinding(RELEASE,job['input_realization_id'],job['input_revision'],canonical_bytes(deps)),kind='full',options=job['options'],code_commit=job['code_commit'],guideline=job['guideline'],phase=job['phase'],prepared=prepared,runtime_binding=runtime)
        start_run(conn,run,prepared=prepared)
        selected=create_task(conn,run_id=run,config_id=task['method_config_id'],stage=task['stage'],unit_type=task['unit_type'],input_hash=task['input_hash'],unit_id=task['unit_id'],unit_key=task['unit_key'],packet_hash=task['packet_hash'])
        reused=conn.scalar(select(table('ops.task').c.reused_task_id).where(table('ops.task').c.id==selected))
        assert reused==TASK,'must reuse exact completed producer task800; provider execution is forbidden'
    return {'run_id':run,'selected_task_id':selected,'origin_task_id':TASK,'label':label,'admissions':selected_admissions,'producer_reexecuted':False}

def completed_info(conn,run,selected,report):
    row=conn.execute(text('''SELECT j.id run_id,j.project_id,j.release_id,c.cut_id,b.data_revision result_revision,o.runtime_id runtime_fingerprint
       FROM ops.run j JOIN ops.completed_result c ON c.run_id=j.id
       JOIN data.batch b ON b.release_id=c.release_id AND b.realization_id=c.output_realization_id AND b.batch_id=c.batch_id
       JOIN ops.task t ON t.id=:task JOIN ops.run o ON o.id=:origin_run WHERE j.id=:run'''),{'run':run,'task':selected,'origin_run':RUN}).mappings().one()
    base={k:row[k] for k in ['project_id','run_id','cut_id','release_id','result_revision','runtime_fingerprint']};base.update(product_id=report.product_id,selected_task_id=selected,origin_task_id=TASK)
    structural=RetainedStructuralRef.model_validate(base)
    components=[RetainedComponentRef.model_validate(dict(base,component_id=x,operation_id='structure.definition_components',operation_version='5',dependencies=report.inputs.dependencies)) for x in POSITIVES]
    # Read actual native retained predecessor resolvers under the ordinary reader.
    for ref in components:
        value=conn.scalar(text('SELECT ops.resolve_retained_component(CAST(:r AS jsonb))'),{'r':canonical_bytes(ref.model_dump(mode='json')).decode()});assert value['component']['component_id']==ref.component_id
    full=conn.scalar(text('SELECT ops.resolve_retained_structural_report(CAST(:r AS jsonb))'),{'r':canonical_bytes(structural.model_dump(mode='json')).decode()});assert len(full['public_assertions'])==2
    return {'run_id':run,'cut_id':row['cut_id'],'selected_task_id':selected,'origin_task_id':TASK,'result_revision':row['result_revision'],'runtime_fingerprint':row['runtime_fingerprint'],'structural_reference':structural.model_dump(mode='json'),'component_references':[r.model_dump(mode='json') for r in components],'published_support_assertions':full['public_assertions']}

def publish():
    if (HERE/'publication-result.json').exists():return read(HERE/'publication-result.json')
    import_references();_,report=source()
    with open_runtime_engine(Settings(),'gs120-native160-narrow-publication',purpose='write') as engine:
        created=read(HERE/'publication-run-created.json') if (HERE/'publication-run-created.json').exists() else create_reuse_run(engine,admissions(),'two independently supported source-attributed attachments')
        retain(HERE/'publication-run-created.json',created)
        result=finalize_bound_run(engine,created['run_id'],'gs120-independent-narrow-publication:'+str(created['run_id']))
    with open_runtime_engine(Settings(),'gs120-native160-ordinary-reader',purpose='read') as engine,read_snapshot(engine) as conn:
        page=serve_structural_products(conn,StructuralRequest(run_id=created['run_id'],include_publication=True,include_support=True))
        assert len(page.public_assertions)==2 and page.reports[0].standing=='private_proposal'
        expected={canonical_bytes(c.expected) for c in StructuralAuthoredReference.model_validate_json((HERE/'C.authored.rebound.json').read_bytes()).cases if c.judgment=='supported' and c.facet=='public_statement'}
        retain(HERE/'ordinary-reader-inspection.json',page.model_dump(mode='json'))
        refs=completed_info(conn,created['run_id'],created['selected_task_id'],report)
        assert {canonical_bytes(v['statement']) for v in refs['published_support_assertions']}==expected
    retain(HERE/'published-predecessor-references.json',refs)
    receipt=dict(outcome='passed',publication_run=created['run_id'],publication_cut=refs['cut_id'],selected_task=created['selected_task_id'],origin_task=TASK,producer_run=RUN,producer_cut=CUT,public_assertions=2,private_components_without_new_public_support=33,producer_reexecuted=False,predecessor_references_file=str(HERE/'published-predecessor-references.json'),scope='Two independently supported narrow source-attributed definition/explanation attachments only; full scope, recognition, scientific truth and whole report correctness not established.')
    retain(HERE/'publication-result.json',receipt);return receipt

def export():
    result=publish();run=result['publication_run'];target=HERE/'review-bundle'
    if (HERE/'export-verification.json').exists():return read(HERE/'export-verification.json')
    receipt=export_review_bundle(ReviewSelection(structural_selections=(StructuralRequest(run_id=run,include_publication=True,include_support=True),)),target,Settings())
    retain(HERE/'export-receipt.json',receipt);verified=verify_review_bundle(target);retain(HERE/'export-verification.json',verified);return verified

def controls():
    publish();positive=admissions()[0];receipt=[]
    cases=[('whole-report-cannot-borrow-component-support',{k:v for k,v in positive.items() if k!='component_id'}),('unassessed-public-component-no-protected-positive',dict(positive,component_id='fe09701184cd4d61d96caf05661d38e9c13f83afeb4c56ab189c9bb630b225f4')),('negative-probability-subject-refused',dict(positive,component_id='10701a2dec9c4a68f38de709185a24ed667b282bc215f1f506ea94415bcb2846')),('negative-historical-definition-refused',dict(positive,component_id='d5715568638f1b1644d6a105bfb3c152946b02ec01d31f601f9ba5797c9b2fe9'))]
    with open_runtime_engine(Settings(),'gs120-native160-refusal-controls',purpose='write') as engine:
        for name,binding in cases:
            target=HERE/(name+'.json')
            if target.exists():receipt.append(read(target));continue
            createdfile=HERE/(name+'-created.json')
            created=read(createdfile) if createdfile.exists() else create_reuse_run(engine,[binding],name);retain(createdfile,created)
            try:finalize_bound_run(engine,created['run_id'],'gs120-narrow-refusal:'+str(created['run_id']))
            except (DBAPIError,ValueError) as error:
                native=error.orig if isinstance(error,DBAPIError) else error
                row=dict(control=name,outcome='refused',run_id=created['run_id'],selected_task=created['selected_task_id'],origin_task=TASK,reason=str(native),sqlstate=getattr(native,'sqlstate',None),producer_reexecuted=False)
            else:raise AssertionError('unsupported larger effect unexpectedly published: '+name)
            with engine.connect() as conn:
                count=conn.scalar(select(__import__('sqlalchemy').func.count()).select_from(table('data.structural_assertion')).where(table('data.structural_assertion').c.selected_task_id==created['selected_task_id']))
                assert count==0
            retain(target,row);receipt.append(row)
    value={'outcome':'passed','controls':receipt,'producer_reexecuted':False};retain(HERE/'native-refusal-controls.json',value);return value

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','import','publish','export','controls']);args=p.parse_args()
    try:
        result={'outcome':'passed','phase':'prepare','database_writes':'not_run','frame_digest':prepare()[1].identity} if args.phase=='prepare' else {'import':import_references,'publish':publish,'export':export,'controls':controls}[args.phase]()
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except BaseException as e:
        retain(HERE/('failure-'+args.phase+'.json'),{'outcome':'failed','type':type(e).__name__,'message':str(e),'phase':args.phase});raise

if __name__=='__main__':main()
