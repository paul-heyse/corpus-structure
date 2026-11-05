"""Rollback-only native refusal controls around the real four-statement public run.

Controlled C edits are temporary fault injections, not newly authored statistical
judgments. No models, PDFs, persistent source/grade mutations or default changes.
"""
from __future__ import annotations
import argparse
import json
from hashlib import sha256
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from corpus_structure.core.provenance import code_commit
from corpus_structure.evaluate.structural_assessment import StructuralEvaluationFrame, create_structural_reference_set, record_structural_reference_pass
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import OperationBinding, create_run, create_task, seal_cut, start_run
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding
from corpus_structure.settings import Settings

RAW=Path(__file__).with_name('raw')


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--public-run',type=int,required=True);parser.add_argument('--bindings',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
 bindings=json.loads((RAW/args.bindings).read_bytes())['structural_admission']; checks={}
 with open_runtime_engine(Settings(),'pce-public-native-negative-controls',purpose='maintenance') as engine:
  with engine.connect() as conn:
   tx=conn.begin()
   try:
    source=dict(conn.execute(text('SELECT * FROM ops.run WHERE id=:r'),{'r':args.public_run}).mappings().one())
    completed=dict(conn.execute(text('SELECT * FROM ops.completed_result WHERE run_id=:r'),{'r':args.public_run}).mappings().one())
    release=source['release_id']; project=source['project_id']; cut=completed['cut_id']; realization=completed['output_realization_id']
    prepared=open_release(conn,release);runtime=prepare_runtime_binding(prepared)
    if runtime.runtime_id!=source['runtime_id']:raise ValueError('package/runtime changed before native control')
    tasks=[dict(r) for r in conn.execute(text('SELECT t.* FROM ops.cut_task c JOIN ops.task t ON t.id=c.task_id WHERE c.cut_id=:c ORDER BY t.id'),{'c':cut}).mappings()]
    original=conn.execute(text('SELECT * FROM data.project WHERE project_id=:p'),{'p':project}).mappings().one()
    def candidates(run=args.public_run,selected_cut=cut,selected_project=project,selected_release=release):
     return conn.scalar(text('SELECT data.structural_publication_candidates(:p,:r,:run,:cut)'),{'p':selected_project,'r':selected_release,'run':run,'cut':selected_cut})
    assert len(candidates())==4
    checks['actual_positive_policies']=4
    def refuse(name,action):
     try:
      with conn.begin_nested(): action()
     except DBAPIError as error:
      if getattr(error.orig,'sqlstate',None)!='23514':raise
      checks[name]='refused23514'
     else:raise AssertionError('native refusal missing: '+name)
    refuse('foreign_project',lambda:candidates(selected_project='native-foreign-project'))
    refuse('foreign_release',lambda:candidates(selected_release='release:native-foreign'))
    refuse('foreign_cut',lambda:candidates(selected_cut=0))
    def clone(selected_bindings,selected_tasks=tasks):
     dependencies=json.loads(source['dependencies']);dependencies['structural_admission']=selected_bindings
     binding=OperationBinding(release,source['input_realization_id'],source['input_revision'],canonical_bytes(dependencies))
     run=create_run(conn,project_id=project,binding=binding,kind=source['kind'],options={**source['options'],'structural_private':True},code_commit=code_commit(),prepared=prepared,runtime_binding=runtime)
     start_run(conn,run,prepared=prepared)
     for task in selected_tasks:
      target=create_task(conn,run_id=run,config_id=task['method_config_id'],stage=task['stage'],unit_type=task['unit_type'],unit_id=task['unit_id'],unit_key=task['unit_key'],packet_hash=task['packet_hash'],input_hash=task['input_hash'])
      assert conn.scalar(text("SELECT status='reused' FROM ops.task WHERE id=:id"),{'id':target})
     selected_cut=seal_cut(conn,run,'native-negative-final',final=True)
     return run,selected_cut
    def modified_c(judgment,bind_current):
     witness=bindings[0]; rows=conn.execute(text('SELECT * FROM eval.structural_reference_pass WHERE set_id=:id ORDER BY id'),{'id':witness['set_id']}).mappings().all()
     a=max((r for r in rows if r['pass_kind']=='A'),key=lambda r:r['id']);b=max((r for r in rows if r['pass_kind']=='B'),key=lambda r:r['id']);c=max((r for r in rows if r['pass_kind']=='C'),key=lambda r:r['id'])
     payload=json.loads(bytes(c['authored']));payload['cases'][0]['judgment']=judgment
     payload['cases'][0]['explanation']='Native rollback fault injection only; copied expected value is not a fresh semantic judgment.'
     authored=canonical_bytes(payload)
     identity=record_structural_reference_pass(conn,set_id=witness['set_id'],pass_kind='C',actor='native-negative-control-C',authored=authored,parents=(a['id'],b['id']))
     if not bind_current:return candidates()
     changed=[dict(r) for r in bindings];changed[0].update(c_pass_id=identity,c_content_digest=sha256(authored).hexdigest())
     run,selected_cut=clone(changed);return candidates(run,selected_cut)
    refuse('stale_C',lambda:modified_c('supported',False))
    refuse('unsupported_C',lambda:modified_c('unsupported',True))
    refuse('ambiguous_C',lambda:modified_c('ambiguous',True))
    changed=[dict(r) for r in bindings];changed[0].update({k:bindings[1][k] for k in ('set_id','c_pass_id','c_content_digest','frame_digest')})
    def foreign_frame():
     run,selected_cut=clone(changed);return candidates(run,selected_cut)
    refuse('foreign_frame',foreign_frame)
    dossier_binding=next(b for b in bindings if b['policy_id']=='independent-structural-dossier-1')
    dossier_task=next(t for t in tasks if conn.scalar(text("SELECT body->'structural_product'->>'kind' FROM ops.task_result WHERE task_id=:id"),{'id':t['reused_task_id'] or t['id']})=='dossier')
    def missing_upstream():
     run,selected_cut=clone([dossier_binding],[dossier_task]);return candidates(run,selected_cut)
    refuse('missing_selected_upstream',missing_upstream)
    def wrong_real_upstream():
     from types import SimpleNamespace
     from corpus_structure.core.method import UnitRef
     from corpus_structure.core.vocab import TaskUnitType
     from corpus_structure.methods.structural_products import StructuralProductsConfig, StructuralProductsMethod
     from corpus_structure.orchestrate.registry import canonical_numbers
     from corpus_structure.core.evidence import config_key
     from corpus_structure.semantic.observations import bind_result
     from corpus_structure.semantic.operations import record_method, claim_tasks, complete_task
     from corpus_structure.semantic.structural_products import StructuralProductReport
     from corpus_structure.semantic.structural_admission import structural_statement
     method=StructuralProductsMethod()
     reports=[StructuralProductReport.model_validate(conn.scalar(text("SELECT body->'structural_product' FROM ops.task_result WHERE task_id=:t"),{'t':task['reused_task_id'] or task['id']})) for task in tasks]
     mean=next(r for r in reports if r.definition is not None and any(p.passage_id=='nist-sample-mean-usage' and p.passage_id==r.definition.usage_id for p in r.inputs.passages))
     dossier=next(r for r in reports if r.dossier is not None); assert dossier.dossier is not None
     members=tuple(m.model_copy(update={'relation_product_id':mean.product_id}) if m.role=='exception' else m for m in dossier.dossier.members)
     bad=dossier.model_copy(update={'dossier':dossier.dossier.model_copy(update={'members':members})})
     assert bad.product_id!=dossier.product_id and structural_statement(bad)==structural_statement(dossier)
     frame_row=conn.execute(text('SELECT frame FROM eval.structural_reference_set WHERE id=:id'),{'id':dossier_binding['set_id']}).scalar_one()
     frame=StructuralEvaluationFrame.model_validate(frame_row).model_copy(update={'product_ids':(bad.product_id,)})
     group=create_structural_reference_set(conn,project_id=project,release_id=release,frame=frame)
     original_c=conn.scalar(text('SELECT authored FROM eval.structural_reference_pass WHERE id=:id'),{'id':dossier_binding['c_pass_id']})
     payload=json.loads(bytes(original_c));payload['frame_digest']=frame.identity
     payload['cases'][0]['explanation']='Native rollback wrong-predecessor fault injection; copied expectation is not new independent semantic quality.'
     authored=canonical_bytes(payload);parents=[]
     for kind in ('A','B','C'):
      identity=record_structural_reference_pass(conn,set_id=group,pass_kind=kind,actor='native-wrong-link-control-'+kind,authored=authored,parents=tuple(parents) if kind=='C' else ())
      if kind!='C':parents.append(identity)
     witness={**dossier_binding,'product_id':bad.product_id,'set_id':group,'c_pass_id':identity,'c_content_digest':sha256(authored).hexdigest(),'frame_digest':frame.identity}
     dependencies=json.loads(source['dependencies']);dependencies['structural_admission']=[witness];dependencies['native_negative_control']='wrong-real-predecessor'
     binding=OperationBinding(release,source['input_realization_id'],source['input_revision'],canonical_bytes(dependencies))
     run=create_run(conn,project_id=project,binding=binding,kind=source['kind'],options={**source['options'],'native_negative_control':True},code_commit=code_commit(),prepared=prepared,runtime_binding=runtime)
     start_run(conn,run,prepared=prepared)
     for index,report in enumerate([bad if r.dossier is not None else r for r in reports]):
      cfg=StructuralProductsConfig(report=report,structural_input_digest=report.inputs.identity);params=cfg.model_dump(mode='json',exclude_none=True)
      key=config_key(method.name,method.version,canonical_numbers(params));config=record_method(conn,method,'native-link-control-'+str(index),params,key,prepared=prepared)
      unit_key='native-link-control:'+report.product_id
      task=create_task(conn,run_id=run,config_id=config,stage='structural',unit_type='run',unit_key=unit_key,input_hash=sha256(method.input_digest(None,cfg).bytes).hexdigest(),fresh=True)
      claim=claim_tasks(conn,run_id=run,config_id=config,holder='native-link-control',prepared=prepared)[0]
      state=conn.execute(text('SELECT input_hash,invocation_key FROM ops.task WHERE id=:id'),{'id':task}).mappings().one()
      result=method.run((SimpleNamespace(ref=UnitRef(TaskUnitType.RUN,unit_key=unit_key)),),cfg,None)[0]
      envelope=bind_result(prepared,source=unit_key,method=method.name,operation_version=method.version,configuration_hash=key,input_hash=state['input_hash'],invocation_key=state['invocation_key'],result=result).model_dump(mode='json')
      complete_task(conn,task_id=task,attempt=claim.attempt,holder=claim.holder,prepared=prepared,observations=(),outcome='done',envelope=envelope)
     selected_cut=seal_cut(conn,run,'native-wrong-link-final',final=True)
     return candidates(run,selected_cut)
    refuse('wrong_but_real_selected_upstream',wrong_real_upstream)
    # Validate the same real rows, then inject staged-only faults; source tables stay immutable.
    conn.execute(text('CREATE TEMP TABLE sp_structural_assertion (LIKE data.structural_assertion INCLUDING DEFAULTS) ON COMMIT DROP'))
    conn.execute(text('INSERT INTO pg_temp.sp_structural_assertion SELECT * FROM data.structural_assertion WHERE release_id=:r AND realization_id=:z'),{'r':release,'z':realization})
    def validate():return conn.scalar(text('SELECT data.validate_structural_assertions(:r,:z)'),{'r':release,'z':realization})
    validate();checks['exact_staged_rows']='passed'
    for name,mutation in [('statement',"UPDATE pg_temp.sp_structural_assertion SET statement_json='{}'"),('sources',"UPDATE pg_temp.sp_structural_assertion SET sources_json='[]'"),('origin','UPDATE pg_temp.sp_structural_assertion SET origin_task_id=origin_task_id+1000000'),('missing_rows','DELETE FROM pg_temp.sp_structural_assertion')]:
     def tamper(mutation=mutation):
      conn.execute(text(mutation));return validate()
     refuse('staged_'+name,tamper)
    validate();assert len(candidates())==4
    assert dict(original)==dict(conn.execute(text('SELECT * FROM data.project WHERE project_id=:p'),{'p':project}).mappings().one())
   finally:tx.rollback()
 result={'outcome':'passed','public_run_id':args.public_run,'checks':checks,'scope':'native rollback fault injection; no new source semantic judgments','defaults_activated':False}
 with (RAW/args.out).open('xb') as out:out.write(canonical_bytes(result)+b'\n')
 print(json.dumps(result))


if __name__=='__main__':main()
