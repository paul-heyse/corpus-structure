"""Rehearse actual frozen82->91, current guard/function flows and rollback on owned author DB."""
from __future__ import annotations
import argparse,io,json,traceback,re
from types import SimpleNamespace
from pydantic import BaseModel
class ControlConfig(BaseModel):pass
from hashlib import sha256
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations,ops
from sqlalchemy import CheckConstraint,MetaData,create_engine,literal,select,text,insert
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable
from corpus_structure.semantic import PreparationProfile,ResolvedDependencies,SourceArtifact,SourceBundle,prepare_release
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID,metadata,table
from corpus_structure.semantic.operations import OperationBinding,OperationConflict,create_run,record_method,create_task,claim_tasks,complete_task,end_source_run,hold_agent_result,seal_cut
from corpus_structure.semantic.migrations import current_revision,upgrade
from corpus_structure.semantic.native_candidate import candidate_admission_sql,prepare_series_candidate,series_native_definitions
from corpus_structure.semantic.native_objects import NativeAuthoringError,NativeObject,admit_native,execute_native_sql,native_owner,observe_native
from corpus_structure.semantic.execution_admission import admit_execution_release
from corpus_structure.semantic.native_products import current_admission_fields
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic import _operation_calls as calls
from corpus_structure.semantic._operation_ids import RealizationId,ReleaseId
from corpus_structure.semantic.publication import PublicationBatch,stage_batch
parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
OUT=Path(__file__).with_name('raw')/args.attempt;OUT.mkdir(exist_ok=False)
SRC=Path('python/corpus-structure/src/corpus_structure')
PG=dialect(paramstyle='named')
def hashes():return {str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(SRC.rglob('*')) if p.is_file() and p.suffix in {'.py','.yaml','.json','.sql'}}
def quote(value):return str(literal(value).compile(dialect=PG,compile_kwargs={'literal_binds':True}))
def leaves(operation):
 if isinstance(operation,ops.OpContainer):
  for child in operation.ops:yield from leaves(child)
 else:yield operation
def ordinary_sql(operation):
 buffer=io.StringIO();offline=Operations(MigrationContext.configure(dialect=PG,opts={'as_sql':True,'output_buffer':buffer,'literal_binds':True}))
 offline.invoke(operation)
 relation=operation.schema+'.'+operation.table_name
 return "DO $owned_ddl$ DECLARE prior text:=current_user; owner_name text; migration_name text; BEGIN SELECT pg_get_userbyid(nspowner) INTO migration_name FROM pg_namespace WHERE nspname='sem'; SELECT pg_get_userbyid(relowner) INTO owner_name FROM pg_class WHERE oid=to_regclass("+quote(relation)+"); IF owner_name IS NULL OR owner_name NOT IN ('corpus_sem_publisher',migration_name) THEN RAISE EXCEPTION 'unsupported ordinary DDL owner'; END IF; EXECUTE format('SET LOCAL ROLE %I',owner_name); EXECUTE "+quote(buffer.getvalue())+"; EXECUTE format('SET LOCAL ROLE %I',prior); END $owned_ddl$;\n"
def physical_reference(conn):
 checks=[];repairs=[];repair_specs=[]
 prior=conn.scalar(text('SELECT data.execution_contract_descriptor()'))
 old=conn.scalar(text('SELECT checks FROM sem.physical_contract WHERE physical_id=:physical AND source_digest=:digest'),dict(physical=prior['physical_id'],digest=prior['physical_checks_source_digest']))
 assert old is not None,'preceding protected physical contract is absent'
 old_checks={(row['relation'],row['name']):row['expression'] for row in old}
 for relation in sorted(metadata.tables.values(),key=lambda item:item.fullname):
  modeled={str(c.name):c for c in relation.constraints if isinstance(c,CheckConstraint)}
  if not modeled:continue
  temporary=relation.to_metadata(MetaData(),schema='pg_temp',name='um_current_physical_reference');temporary._prefixes=['TEMPORARY']
  execute_native_sql(conn,str(CreateTable(temporary,include_foreign_key_constraints=[]).compile(dialect=PG)))
  current=[dict(relation=relation.fullname,name=r.name,expression=r.expression) for r in conn.execute(text("SELECT conname AS name,pg_get_expr(conbin,conrelid) AS expression FROM pg_constraint WHERE conrelid='pg_temp.um_current_physical_reference'::regclass AND contype='c' ORDER BY conname"))]
  execute_native_sql(conn,'DROP TABLE pg_temp.um_current_physical_reference')
  for check in current:
   actual=conn.scalar(text("SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint WHERE conrelid=to_regclass(:relation) AND conname=:name AND contype='c'"),dict(relation=relation.fullname,name=check['name']))
   if actual!=check['expression']:
    assert actual is not None and old_checks.get((relation.fullname,check['name']))==actual,('unreviewed CHECK predecessor',relation.fullname,check['name'],actual,old_checks.get((relation.fullname,check['name'])))
    drop=ops.DropConstraintOp(check['name'],relation.name,type_='check',schema=relation.schema)
    create=ops.CreateCheckConstraintOp(check['name'],relation.name,str(modeled[check['name']].sqltext),schema=relation.schema)
    repairs.extend((ordinary_sql(drop),ordinary_sql(create)))
    repair_specs.append(dict(relation=relation.fullname,name=check['name'],before=actual,after=check['expression']))
  checks.extend(current)
 checks.sort(key=lambda item:(item['relation'],item['name']))
 fields=current_admission_fields()
 receipt='INSERT INTO sem.physical_contract(physical_id,checks,source_digest) VALUES('+quote(PHYSICAL_MODEL_ID)+','+quote(canonical_bytes(checks).decode())+'::jsonb,'+quote(fields['physical_checks_source_digest'])+');\n'
 return receipt,repairs,repair_specs
captured=hashes()
bundle=SourceBundle('current', (SourceArtifact('current',b'''id: https://example.org/current
name: current
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Report:
  attributes:
   text: {required: true}
'''),))
dependencies=composed_dependencies(ResolvedDependencies());profile=PreparationProfile(version='semantic-2');prepared=prepare_release(bundle,dependencies,profile)
engine=create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434',isolation_level='SERIALIZABLE')
with engine.connect() as conn:
 tx=conn.begin()
 try:
  provenance=conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
  assert provenance[0]==14010645 and provenance[1]=='paul' and '1dbfc2773c354652b64626aaa56eac35' in provenance[2],provenance
  assert current_revision(conn)=='semantic_pdf_retire_20261101'
  upgrade(conn,'semantic_pdf_header_20261102')
  author_report=json.loads(Path(__file__).with_name('raw').joinpath('rehearsal-015/result.json').read_bytes())
  assert prepared.release_id==author_report['release'],'generated pins changed composed determinants'
  upgrade(conn,'semantic_current_only_20261102')
  assert current_revision(conn)=='semantic_current_only_20261102'
  with native_owner(conn,'corpus_sem_publisher'):persist_release(conn,bundle,dependencies,profile,prepared)
  upgrade(conn,'semantic_current_only_20261102')
  print('PASSED actual frozen82->90->91 replay and repeated Alembic no-op',flush=True)
  versions=Path('python/corpus-structure/semantic_alembic/versions')
  state=json.loads(versions.joinpath('semantic_current_only_20261102_native.json').read_bytes())
  native=[NativeTransitionOp.from_payload(item) for item in state['operations']]
  desired=tuple(NativeObject.from_payload(item) for item in state['desired'])
  authoring=SimpleNamespace(desired=desired,retire=tuple(item.identity for item in native if item.after is None))
  operations=Operations(MigrationContext.configure(conn))
  dropped=author_report['dropped']
  admit_native(conn,authoring.desired)
  for identity in authoring.retire:assert observe_native(conn,identity) is None,identity
  assert len(dropped)==36,len(dropped)
  assert all(conn.scalar(text('SELECT to_regclass(:name)'),dict(name=name)) is None for name in dropped)
  with native_owner(conn,'corpus_sem_publisher'):
   admit_execution_release(prepared,connection=conn)
  print('PASSED current compiler14/execution23 archive + physical/native admission as publisher (session migration owner)',flush=True)
  retired_body_references=[]
  for row in conn.execute(text("SELECT n.nspname||'.'||p.proname AS name,pg_get_functiondef(p.oid) AS body FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('sem','data','ops','kb','eval') AND p.prokind IN ('f','p')")):
   for relation in dropped:
    if re.search(r'(?<![A-Za-z_])'+re.escape(relation)+r'\b',row.body):retired_body_references.append(dict(function=row.name,relation=relation))
  assert not retired_body_references,retired_body_references
  print('PASSED remaining function bodies contain none of the 36 retired qualified relations',flush=True)
  with native_owner(conn,'corpus_sem_publisher'):
   conn.execute(insert(table('data.project')).values(project_id='current-forward-control'))
   conn.execute(insert(table('data.realization')).values(realization_id='current-forward-control',release_id=prepared.release_id,project_id='current-forward-control'))
  with native_owner(conn,'corpus_sem_publisher'):
   binding=OperationBinding(prepared.release_id,'current-forward-control',0,b'{}')
   config=record_method(conn,SimpleNamespace(name='current-forward-control',version='1',family='ingest',tier='deterministic',confidence_source=None,unit_type='run',Config=ControlConfig),'default',{},'current-forward-config',prepared=prepared)
   run=create_run(conn,project_id='current-forward-control',binding=binding,kind='full',options={},code_commit='author-rehearsal')
   task=create_task(conn,run_id=run,config_id=config,stage='ingest',unit_type='run',input_hash='cancel-control')
   claim=claim_tasks(conn,run_id=run,config_id=config,holder='forward-control',prepared=prepared)[0]
   assert end_source_run(conn,run,prepared=prepared)==1
   assert end_source_run(conn,run,prepared=prepared)==0
   assert claim_tasks(conn,run_id=run,config_id=config,holder='closed-poller',prepared=prepared)==()
   try:
    with conn.begin_nested():complete_task(conn,task_id=task,attempt=claim.attempt,holder='forward-control',prepared=prepared,observations=[],outcome='empty')
   except OperationConflict:pass
   else:raise AssertionError('late completion accepted after source cancellation')
   assert conn.scalar(select(table('ops.task').c.status).where(table('ops.task').c.id==task))=='cancelled'
   completed_run=create_run(conn,project_id='current-forward-control',binding=binding,kind='full',options={},code_commit='author-rehearsal')
   completed_task=create_task(conn,run_id=completed_run,config_id=config,stage='ingest',unit_type='run',input_hash='completion-control')
   completed_claim=claim_tasks(conn,run_id=completed_run,config_id=config,holder='forward-control',prepared=prepared)[0]
   result=complete_task(conn,task_id=completed_task,attempt=completed_claim.attempt,holder='forward-control',prepared=prepared,observations=[dict(payload_definition='Report',item_key='independent',payload=dict(text='current forward'),kind='reading')])
   assert result.receipt.protocol=='done'
   assert conn.scalar(select(table('kb.observation').c.payload).where(table('kb.observation').c.task_id==completed_task))==dict(text='current forward')
   final_cut=seal_cut(conn,completed_run,'current-forward-final',final=True)
   assert conn.scalar(select(table('ops.run').c.sealed).where(table('ops.run').c.id==completed_run)) is True
   assert claim_tasks(conn,run_id=completed_run,config_id=config,holder='sealed-poller',prepared=prepared)==()
   calls.begin_evaluation(conn,cut_id=final_cut,output_realization_id=RealizationId('current-forward-output'),projection_context=prepared)
   empty_batch=PublicationBatch(prepared.release_id,'current-forward-output','current-forward-batch')
   stage_batch(conn,empty_batch)
   calls.publish_batch(conn,release_id=ReleaseId(prepared.release_id),realization_id=RealizationId('current-forward-output'),batch_id=empty_batch.batch_id,content=empty_batch.content,projection_context=prepared)
   calls.end_stage(conn,projection_context=prepared)
   calls.finish_evaluation(conn,cut_id=final_cut,output_realization_id=RealizationId('current-forward-output'),batch_id=empty_batch.batch_id,projection_context=prepared)
   assert conn.scalar(select(table('ops.completed_result').c.run_id).where(table('ops.completed_result').c.run_id==completed_run))==completed_run
   assert claim_tasks(conn,run_id=completed_run,config_id=config,holder='finished-poller',prepared=prepared)==()
   failed_run=create_run(conn,project_id='current-forward-control',binding=binding,kind='full',options={},code_commit='author-rehearsal')
   assert end_source_run(conn,failed_run,failure=dict(reason='independent control'),prepared=prepared)==0
   assert conn.scalar(select(table('ops.run').c.status).where(table('ops.run').c.id==failed_run))=='failed'
   assert claim_tasks(conn,run_id=failed_run,config_id=config,holder='failed-poller',prepared=prepared)==()
  print('PASSED publisher-context current run/task claim, cancellation + late-completion refusal, observation completion, sealed/finished/failed idle polling',flush=True)
  execute_native_sql(conn,'SET CONSTRAINTS ALL IMMEDIATE')
  empty,again=prepare_series_candidate(conn,owned_authoring=True)
  assert not empty.upgrade_ops.ops,[type(op).__name__ for op in empty.upgrade_ops.ops]
  print('PASSED current native/ordinary candidate empty',flush=True)
  drift=[]
  for name,sql in [('nullable','ALTER TABLE kb.source_view ALTER COLUMN native_build_id DROP NOT NULL'),('acl','GRANT EXECUTE ON FUNCTION ops.read_pdf_published_validation(bigint,text,text) TO PUBLIC'),('check','ALTER TABLE kb.source_view ADD CONSTRAINT um_current_unexpected CHECK (id>0)')]:
   try:
    with conn.begin_nested(),native_owner(conn,'corpus_sem_publisher'):
     execute_native_sql(conn,sql);conn.execute(text('SELECT data.require_execution_release(:release)'),dict(release=prepared.release_id))
   except DBAPIError as error:
    assert error.orig.sqlstate=='23514',(name,error)
    drift.append(dict(kind=name,sqlstate=error.orig.sqlstate,message=str(error.orig).splitlines()[0]))
   else:raise AssertionError('native admission accepted drift: '+name)
  repeated=next(op for op in native if op.before is not None and op.after is not None and op.before!=op.after)
  try:
   with conn.begin_nested():operations.invoke(repeated)
  except NativeAuthoringError as error:assert 'stale native before-state' in str(error)
  else:raise AssertionError('repeated native before-state accepted')
  print('PASSED nullable/ACL/CHECK drift + stale directive refusal',flush=True)
  assert hashes()==captured,'final source window changed'
  receipt=json.loads(Path(__file__).with_name('raw').joinpath('freeze-001.json').read_bytes())
  for artifact in receipt['artifacts'].values():
   assert sha256(versions.joinpath(artifact['name']).read_bytes()).hexdigest()==artifact['sha256']
  assert sha256(versions.joinpath('0091_current_only.py').read_bytes()).hexdigest()==receipt['wrapper_sha256']
  report=dict(outcome='passed',revision=current_revision(conn),release=prepared.release_id,physical_id=PHYSICAL_MODEL_ID,native_operations=len(native),desired=len(desired),dropped=sorted(dropped),drift=drift,context='publisher guard/catalog and function lifecycle; session migration owner; actual runtime LOGIN qualification deferred to coordinator',sources=captured,freeze_receipt=receipt)
  OUT.joinpath('result.json').write_bytes(canonical_bytes(report));print(json.dumps({key:value for key,value in report.items() if key!='sources'}),flush=True)
 except BaseException:
  OUT.joinpath('failure.txt').write_text(traceback.format_exc());raise
 finally:tx.rollback()
 assert current_revision(conn)=='semantic_pdf_retire_20261101'
 assert conn.scalar(text('SELECT current_user'))=='paul'
 print('PASSED outer rollback restored82 + caller role',flush=True)
engine.dispose()
