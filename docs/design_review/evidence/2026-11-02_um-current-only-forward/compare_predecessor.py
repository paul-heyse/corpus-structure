"""Compare bounded frozen predecessor normalization against the owned author catalog."""
import difflib,json
from pathlib import Path
from sqlalchemy import create_engine,text
from corpus_structure.semantic.migrations import current_revision,upgrade
from corpus_structure.semantic.native_candidate import _source_guard_predecessors
from corpus_structure.semantic.native_objects import prepare_native_authoring,observe_native
OUT=Path(__file__).with_name('raw')/'source-predecessor-comparison.json';assert not OUT.exists()
engine=create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434')
with engine.connect() as conn:
 tx=conn.begin()
 try:
  p=conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
  assert p[0]==14010645 and p[1]=='paul' and '1dbfc2773c354652b64626aaa56eac35' in p[2]
  assert current_revision(conn)=='semantic_pdf_retire_20261101'
  upgrade(conn,'semantic_pdf_header_20261102')
  definitions,_=_source_guard_predecessors(conn)
  objects=prepare_native_authoring(conn,definitions,owned_authoring=True).desired
  differences=[]
  for obj in objects:
   expected=obj.expected_catalog(conn);actual=observe_native(conn,obj.identity)
   if expected!=actual:
    changed={k:dict(expected=expected.get(k),actual=(actual or {}).get(k)) for k in set(expected)|set(actual or {}) if expected.get(k)!=(actual or {}).get(k)}
    differences.append(dict(identity=obj.identity.qualified,source=obj.source,changed=changed))
  OUT.write_text(json.dumps(differences,sort_keys=True,indent=2));print(json.dumps([(x['identity'],list(x['changed'])) for x in differences]))
 finally:tx.rollback()
 assert current_revision(conn)=='semantic_pdf_retire_20261101'
 print('PASSED rollback restored82')
engine.dispose()
