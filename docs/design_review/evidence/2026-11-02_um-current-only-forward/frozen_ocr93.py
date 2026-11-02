"""Rehearse actual frozen82->93, current OCR contract custody and pin/ACL drift refusals."""
from __future__ import annotations
import argparse,json,traceback
from hashlib import sha256
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic import PreparationProfile,ResolvedDependencies,SourceArtifact,SourceBundle,prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.execution_admission import admit_execution_release,ExecutionAdmissionError
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.migrations import current_revision,upgrade
from corpus_structure.semantic.native_candidate import prepare_series_candidate
from corpus_structure.semantic.native_objects import NativeObject,admit_native,execute_native_sql,native_owner
from corpus_structure.semantic.releases import persist_release
parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
OUT=Path(__file__).with_name('raw')/args.attempt;OUT.mkdir(exist_ok=False)
VERSIONS=Path('python/corpus-structure/semantic_alembic/versions')
SRC=Path('python/corpus-structure/src/corpus_structure')
def hashes():return {str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(SRC.rglob('*')) if p.is_file() and p.suffix in {'.py','.yaml','.json','.sql'}}
captured=hashes()
bundle=SourceBundle('current',(SourceArtifact('current',b'''id: https://example.org/current
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
  upgrade(conn,'semantic_report_cache_20261102')
  physical_before=conn.execute(text('SELECT physical_id,source_digest,checks FROM sem.physical_contract ORDER BY physical_id')).all()
  upgrade(conn,'semantic_ocr_inventory_20261102')
  assert current_revision(conn)=='semantic_ocr_inventory_20261102'
  assert conn.execute(text('SELECT physical_id,source_digest,checks FROM sem.physical_contract ORDER BY physical_id')).all()==physical_before
  upgrade(conn,'semantic_ocr_inventory_20261102')
  print('PASSED frozen82->92->93, unchanged physical receipt and repeated Alembic no-op',flush=True)
  state=json.loads(VERSIONS.joinpath('semantic_ocr_inventory_20261102_native.json').read_bytes())
  assert len(state['operations'])==7
  desired=tuple(NativeObject.from_payload(item) for item in state['desired'])
  admit_native(conn,desired)
  with native_owner(conn,'corpus_sem_publisher'):
   persist_release(conn,bundle,dependencies,profile,prepared)
   admit_execution_release(prepared,connection=conn)
  print('PASSED actual current archive + Python body pins/native guard and exact owned-role catalogs (publisher context, session migration owner)',flush=True)
  empty,authoring=prepare_series_candidate(conn,owned_authoring=True)
  assert not empty.upgrade_ops.ops,[type(item).__name__ for item in empty.upgrade_ops.ops]
  print('PASSED current revision native/ordinary candidate empty',flush=True)
  drift=[]
  mutations=[('source_pin',"CREATE OR REPLACE FUNCTION data.execution_contract_descriptor() RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$ SELECT '{}'::jsonb $$"),('acl','GRANT EXECUTE ON FUNCTION ops.read_pdf_published_validation(bigint,text,text) TO PUBLIC')]
  for name,sql in mutations:
   try:
    with native_owner(conn,'corpus_sem_publisher'),conn.begin_nested():
     execute_native_sql(conn,sql);admit_execution_release(prepared,connection=conn)
   except ExecutionAdmissionError as error:
    if name=='source_pin':assert 'native execution deployment differs: data.execution_contract_descriptor()' in str(error)
    else:assert 'native execution kernel differs: ops.read_pdf_published_validation(bigint,text,text)' in str(error)
    drift.append(dict(kind=name,message=str(error)))
   else:raise AssertionError('native admission accepted '+name+' drift')
  admit_native(conn,desired)
  assert conn.scalar(text('SELECT current_user'))=='paul'
  receipt=json.loads(Path(__file__).with_name('raw').joinpath('ocr93-freeze-001.json').read_bytes())
  for artifact in receipt['artifacts'].values():assert sha256(VERSIONS.joinpath(artifact['name']).read_bytes()).hexdigest()==artifact['sha256']
  assert sha256(VERSIONS.joinpath('0093_ocr_inventory_source.py').read_bytes()).hexdigest()==receipt['wrapper_sha256']
  assert hashes()==captured,'source window changed'
  report=dict(outcome='passed',revision=current_revision(conn),release=prepared.release_id,execution_model_id=prepared.execution_model_id,native_operations=7,ordinary_operations=0,desired=len(desired),physical_receipt_unchanged=True,drift=drift,context='publisher guard/catalog checks; session migration owner; actual runtime LOGIN qualification belongs to coordinator',sources=captured,freeze_receipt=receipt)
  OUT.joinpath('result.json').write_bytes(canonical_bytes(report));print(json.dumps({key:value for key,value in report.items() if key!='sources'}),flush=True)
 except BaseException:
  OUT.joinpath('failure.txt').write_text(traceback.format_exc());raise
 finally:tx.rollback()
 assert current_revision(conn)=='semantic_pdf_retire_20261101'
 assert conn.scalar(text('SELECT current_user'))=='paul'
 print('PASSED source-pin/ACL drift refusal, exact ACL restored, outer rollback82 + caller role',flush=True)
engine.dispose()
