"""Independent creation-time trigger capability and success/error cleanup controls."""
import json
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.native_objects import NativeIdentity,execute_native_sql,execute_native_trigger,native_owner,observe_native
OUT=Path(__file__).with_name('raw')/'trigger-acl-control.json';assert not OUT.exists()
engine=create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434')
checks=[]
with engine.connect() as conn:
 tx=conn.begin()
 try:
  provenance=conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
  assert provenance[0]==14010645 and provenance[1]=='paul' and '1dbfc2773c354652b64626aaa56eac35' in provenance[2]
  assert current_revision(conn)=='semantic_pdf_retire_20261101'
  execute_native_sql(conn,'CREATE TEMP TABLE um_current_acl_probe(id bigint)')
  with native_owner(conn,'corpus_sem_publisher'):
   execute_native_sql(conn,"CREATE OR REPLACE FUNCTION sem.um_current_acl_guard() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN NEW; END$$")
   execute_native_sql(conn,'REVOKE ALL ON FUNCTION sem.um_current_acl_guard() FROM PUBLIC')
  identity=NativeIdentity('function','sem','um_current_acl_guard')
  before=observe_native(conn,identity)
  assert not conn.scalar(text("SELECT has_function_privilege('paul','sem.um_current_acl_guard()','EXECUTE')"))
  execute_native_trigger(conn,'CREATE TRIGGER um_current_acl BEFORE INSERT ON pg_temp.um_current_acl_probe FOR EACH ROW EXECUTE FUNCTION sem.um_current_acl_guard()')
  assert observe_native(conn,identity)==before
  assert conn.scalar(text('SELECT current_user'))=='paul'
  execute_native_sql(conn,'INSERT INTO pg_temp.um_current_acl_probe VALUES(1)')
  assert conn.scalar(text('SELECT id FROM pg_temp.um_current_acl_probe'))==1
  checks.append('successful creation/invocation restores exact function ACL and caller role')
  try:
   with conn.begin_nested():
    execute_native_trigger(conn,'CREATE TRIGGER um_current_acl_fail BEFORE INSERT ON pg_temp.um_current_acl_missing FOR EACH ROW EXECUTE FUNCTION sem.um_current_acl_guard()')
  except DBAPIError as error:
   assert error.orig.sqlstate=='42P01',error
   checks.append('original undefined-table refusal retained; failed savepoint removes temporary grant')
  else:raise AssertionError('invalid trigger parent accepted')
  assert observe_native(conn,identity)==before
  assert conn.scalar(text('SELECT current_user'))=='paul'
  try:
   with conn.begin_nested(),native_owner(conn,'corpus_sem_writer'):
    conn.execute(text('SELECT sem.um_current_acl_guard()'))
  except DBAPIError as error:
   assert error.orig.sqlstate=='42501',error
   checks.append('runtime writer still refuses direct EXECUTE with SQLSTATE42501')
  else:raise AssertionError('protected trigger function execution exposed')
  assert observe_native(conn,identity)==before
 finally:tx.rollback()
 assert current_revision(conn)=='semantic_pdf_retire_20261101'
 assert conn.scalar(text('SELECT current_user'))=='paul'
 checks.append('outer rollback restores82 and caller role')
OUT.write_text(json.dumps(dict(outcome='passed',checks=checks),indent=2))
print(json.dumps(dict(outcome='passed',checks=checks)))
engine.dispose()
