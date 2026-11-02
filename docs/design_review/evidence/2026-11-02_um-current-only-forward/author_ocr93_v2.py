"""Author only the current OCR inventory source successor, rollback to owned82."""
from __future__ import annotations
import argparse,json,traceback
from hashlib import sha256
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine,text
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.migrations import current_revision,upgrade
from corpus_structure.semantic.native_candidate import candidate_admission_sql,prepare_series_candidate,series_native_definitions
from corpus_structure.semantic.native_objects import admit_native
from corpus_structure.semantic.source_view_native import _admission_descriptor
parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
OUT=Path(__file__).with_name('raw')/args.attempt;OUT.mkdir(exist_ok=False)
SRC=Path('python/corpus-structure/src/corpus_structure')
def hashes():return {str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(SRC.rglob('*')) if p.is_file() and p.suffix in {'.py','.yaml','.json','.sql'}}
captured=hashes()
engine=create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434')
with engine.connect() as conn:
 tx=conn.begin()
 try:
  provenance=conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
  assert provenance[0]==14010645 and provenance[1]=='paul' and '1dbfc2773c354652b64626aaa56eac35' in provenance[2],provenance
  assert current_revision(conn)=='semantic_pdf_retire_20261101'
  upgrade(conn,'semantic_report_cache_20261102')
  candidate,authoring=prepare_series_candidate(conn,owned_authoring=True)
  native=candidate.upgrade_ops.ops
  assert native and all(isinstance(item,NativeTransitionOp) for item in native),[type(item).__name__ for item in native]
  changes=[]
  for item in native:
   assert item.before is not None and item.after is not None,item.identity
   keys={key for key in item.before.catalog.keys()|item.after.catalog.keys() if item.before.catalog.get(key)!=item.after.catalog.get(key)}
   assert keys=={'body'},(item.identity,keys)
   changes.append(dict(identity=item.identity.qualified,catalog_changes=sorted(keys)))
  OUT.joinpath('changes.json').write_bytes(canonical_bytes(changes));print(json.dumps(changes),flush=True)
  directive=next(item for item in native if item.identity.qualified=='data.execution_contract_descriptor()')
  before=_admission_descriptor(';\n'.join(directive.before.statements))
  after=_admission_descriptor(';\n'.join(directive.after.statements))
  changed={key for key in before.keys()|after.keys() if before.get(key)!=after.get(key)}
  assert changed=={'model_id','inputs'},changed
  assert {key:value for key,value in directive.before.catalog.items() if key!='body'}=={key:value for key,value in directive.after.catalog.items() if key!='body'}
  operations=Operations(MigrationContext.configure(conn))
  for item in native:operations.invoke(item)
  admit_native(conn,authoring.desired)
  empty,again=prepare_series_candidate(conn,predecessor=authoring.desired,owned_authoring=True)
  assert not empty.upgrade_ops.ops,[type(item).__name__ for item in empty.upgrade_ops.ops]
  admission=candidate_admission_sql(conn,series_native_definitions(conn),authoring.desired,retire=authoring.retire,predecessor=authoring.predecessor)
  state=dict(version=1,predecessor='semantic_report_cache_20261102',operations=[item.payload() for item in native],desired=[item.payload() for item in authoring.desired])
  artifacts={'native.json':canonical_bytes(state),'admission.sql':admission.encode(),'sources.json':canonical_bytes(captured)}
  assert hashes()==captured,'source window changed'
  for name,content in artifacts.items():OUT.joinpath(name).write_bytes(content)
  previous={item['name']:item['sha256'] for item in before['inputs']};current={item['name']:item['sha256'] for item in after['inputs']}
  changed_inputs={name:dict(before=previous.get(name),after=current.get(name)) for name in previous.keys()|current.keys() if previous.get(name)!=current.get(name)}
  report=dict(outcome='passed',native_operations=len(native),native_changes=changes,ordinary_operations=0,desired=len(authoring.desired),descriptor_changed=sorted(changed),prior_model_id=before['model_id'],current_model_id=after['model_id'],changed_inputs=changed_inputs,artifacts={name:sha256(content).hexdigest() for name,content in artifacts.items()})
  OUT.joinpath('result.json').write_bytes(canonical_bytes(report));print(json.dumps(report),flush=True)
 except BaseException:
  OUT.joinpath('failure.txt').write_text(traceback.format_exc());raise
 finally:tx.rollback()
 assert current_revision(conn)=='semantic_pdf_retire_20261101'
 assert conn.scalar(text('SELECT current_user'))=='paul'
 print('PASSED descriptor-only successor, empty native/ordinary candidate, exact owned catalogs, outer rollback82 + caller role',flush=True)
engine.dispose()
