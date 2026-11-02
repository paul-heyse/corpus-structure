"""Read-only catalog inventory after rollback-only frozen82→90 replay."""
import json
from pathlib import Path
from sqlalchemy import create_engine,text
from corpus_structure.semantic.migrations import current_revision,upgrade
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.source_view_native import _admission_descriptor
from corpus_structure.semantic.migrations import ALEMBIC_DIR
OUT=Path(__file__).with_name('raw');OUT.mkdir(exist_ok=True)
engine=create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434')
with engine.connect() as conn:
 tx=conn.begin()
 try:
  provenance=conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
  assert provenance[0]==14010645 and provenance[1]=='paul' and '1dbfc2773c354652b64626aaa56eac35' in provenance[2],provenance
  assert current_revision(conn)=='semantic_pdf_retire_20261101'
  upgrade(conn,'semantic_pdf_header_20261102')
  old=_admission_descriptor(ALEMBIC_DIR.joinpath('versions/semantic_pdf_header_20261102_admission.sql').read_text())
  removed=sorted(set(old['physical_relations'])-set(metadata.tables))
  funcs=[dict(r) for r in conn.execute(text("""SELECT p.oid::regprocedure::text signature,pg_get_function_result(p.oid) result,pg_get_userbyid(p.proowner) owner,pg_get_functiondef(p.oid) definition FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('ops','kb','data','sem','eval') ORDER BY p.oid::regprocedure::text""")).mappings()]
  deps=[dict(r) for r in conn.execute(text("""SELECT pg_describe_object(d.classid,d.objid,d.objsubid) dependent,pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid) provider,d.deptype FROM pg_depend d WHERE d.refclassid='pg_class'::regclass AND d.refobjid=ANY(SELECT to_regclass(n) FROM unnest(CAST(:names AS text[])) n) ORDER BY 1,2"""),dict(names=removed)).mappings()]
  result=dict(provenance=list(provenance),removed=removed,functions=funcs,dependencies=deps)
  OUT.joinpath('author90-inventory.json').write_text(json.dumps(result,sort_keys=True,indent=2))
  print('PASSED provenance + frozen82→90; removed',len(removed),'functions',len(funcs),'dependencies',len(deps))
 finally:tx.rollback()
 assert current_revision(conn)=='semantic_pdf_retire_20261101'
 assert conn.scalar(text('SELECT current_user'))=='paul'
 print('PASSED rollback restored82 + caller role')
engine.dispose()
