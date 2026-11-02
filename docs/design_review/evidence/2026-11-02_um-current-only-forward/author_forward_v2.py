"""Author and rehearse the current-only forward on the single retained owned database.

Outputs are candidate witnesses, not a production freeze. The coordinator supplies the
final source boundary before a separate frozen-wrapper rehearsal.
"""
from __future__ import annotations
import argparse,io,json,traceback
from hashlib import sha256
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations,ops
from sqlalchemy import CheckConstraint,MetaData,create_engine,literal,select,text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable
from corpus_structure.semantic import PreparationProfile,ResolvedDependencies,SourceArtifact,SourceBundle,prepare_release
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID,metadata
from corpus_structure.semantic.migrations import current_revision,upgrade
from corpus_structure.semantic.native_candidate import candidate_admission_sql,prepare_series_candidate,series_native_definitions
from corpus_structure.semantic.native_objects import NativeAuthoringError,admit_native,execute_native_sql,native_owner,observe_native
from corpus_structure.semantic.native_products import current_admission_fields
from corpus_structure.semantic.releases import persist_release
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
 checks=[]
 for relation in sorted(metadata.tables.values(),key=lambda item:item.fullname):
  if not any(isinstance(c,CheckConstraint) for c in relation.constraints):continue
  temporary=relation.to_metadata(MetaData(),schema='pg_temp',name='um_current_physical_reference');temporary._prefixes=['TEMPORARY']
  execute_native_sql(conn,str(CreateTable(temporary,include_foreign_key_constraints=[]).compile(dialect=PG)))
  checks.extend(dict(relation=relation.fullname,name=r.name,expression=r.expression) for r in conn.execute(text("SELECT conname AS name,pg_get_expr(conbin,conrelid) AS expression FROM pg_constraint WHERE conrelid='pg_temp.um_current_physical_reference'::regclass AND contype='c' ORDER BY conname")))
  execute_native_sql(conn,'DROP TABLE pg_temp.um_current_physical_reference')
 checks.sort(key=lambda item:(item['relation'],item['name']))
 fields=current_admission_fields()
 return 'INSERT INTO sem.physical_contract(physical_id,checks,source_digest) VALUES('+quote(PHYSICAL_MODEL_ID)+','+quote(canonical_bytes(checks).decode())+'::jsonb,'+quote(fields['physical_checks_source_digest'])+');\n'
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
engine=create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434')
with engine.connect() as conn:
 tx=conn.begin()
 try:
  provenance=conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
  assert provenance[0]==14010645 and provenance[1]=='paul' and '1dbfc2773c354652b64626aaa56eac35' in provenance[2],provenance
  assert current_revision(conn)=='semantic_pdf_retire_20261101'
  upgrade(conn,'semantic_pdf_header_20261102')
  with native_owner(conn,'corpus_sem_publisher'):persist_release(conn,bundle,dependencies,profile,prepared)
  candidate,authoring=prepare_series_candidate(conn,owned_authoring=True)
  native=[op for op in candidate.upgrade_ops.ops if isinstance(op,NativeTransitionOp)]
  operations=Operations(MigrationContext.configure(conn));before=[];retire=[];seen_native=False;dropped=[]
  for operation in candidate.upgrade_ops.ops:
   if isinstance(operation,NativeTransitionOp):
    seen_native=True;operations.invoke(operation);continue
   for leaf in leaves(operation):
    sql=ordinary_sql(leaf)
    (retire if seen_native else before).append(sql)
    execute_native_sql(conn,sql)
    if isinstance(leaf,ops.DropTableOp):dropped.append(leaf.schema+'.'+leaf.table_name)
  with native_owner(conn,'corpus_sem_publisher'):
   physical=physical_reference(conn);execute_native_sql(conn,physical)
  admit_native(conn,authoring.desired)
  for identity in authoring.retire:assert observe_native(conn,identity) is None,identity
  assert len(dropped)==36,len(dropped)
  assert all(conn.scalar(text('SELECT to_regclass(:name)'),dict(name=name)) is None for name in dropped)
  with native_owner(conn,'corpus_sem_publisher'):
   conn.execute(text('SELECT data.require_execution_release(:release)'),dict(release=prepared.release_id))
  print('PASSED current compiler14/execution23 archive + physical/native admission as publisher (session migration owner)',flush=True)
  empty,again=prepare_series_candidate(conn,predecessor=authoring.desired,owned_authoring=True)
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
  admission=candidate_admission_sql(conn,series_native_definitions(conn),authoring.desired,retire=authoring.retire,predecessor=authoring.predecessor)
  state=dict(version=1,predecessor='semantic_pdf_header_20261102',operations=[op.payload() for op in native],desired=[obj.payload() for obj in authoring.desired])
  artifacts={'native.json':canonical_bytes(state),'before.sql':''.join(before).encode(),'retire.sql':''.join(retire).encode(),'physical.sql':physical.encode(),'admission.sql':admission.encode(),'sources.json':canonical_bytes(captured)}
  assert hashes()==captured,'source window changed'
  for name,content in artifacts.items():OUT.joinpath(name).write_bytes(content)
  report=dict(outcome='passed',release=prepared.release_id,physical_id=PHYSICAL_MODEL_ID,native_operations=len(native),desired=len(authoring.desired),retirements=[x.qualified for x in sorted(authoring.retire,key=lambda x:x.qualified)],dropped=sorted(dropped),ordinary_before=len(before),ordinary_after=len(retire),drift=drift,artifacts={name:sha256(content).hexdigest() for name,content in artifacts.items()})
  OUT.joinpath('result.json').write_bytes(canonical_bytes(report));print(json.dumps(report),flush=True)
 except BaseException:
  OUT.joinpath('failure.txt').write_text(traceback.format_exc());raise
 finally:tx.rollback()
 assert current_revision(conn)=='semantic_pdf_retire_20261101'
 assert conn.scalar(text('SELECT current_user'))=='paul'
 print('PASSED outer rollback restored82 + caller role',flush=True)
engine.dispose()
