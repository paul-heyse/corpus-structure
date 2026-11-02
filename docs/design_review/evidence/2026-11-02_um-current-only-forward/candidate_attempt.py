"""Bounded rollback-only current native/ordinary candidate discovery."""
import argparse,json,traceback
from pathlib import Path
from sqlalchemy import create_engine,text
from corpus_structure.semantic.migrations import current_revision,upgrade
from corpus_structure.semantic.native_candidate import prepare_series_candidate
from corpus_structure.semantic.alembic_native import NativeTransitionOp
parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
out=Path(__file__).with_name('raw')/args.attempt;out.mkdir(exist_ok=False)
engine=create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434')
with engine.connect() as conn:
 tx=conn.begin()
 try:
  provenance=conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
  assert provenance[0]==14010645 and provenance[1]=='paul' and '1dbfc2773c354652b64626aaa56eac35' in provenance[2],provenance
  assert current_revision(conn)=='semantic_pdf_retire_20261101'
  upgrade(conn,'semantic_pdf_header_20261102')
  candidate,authoring=prepare_series_candidate(conn,owned_authoring=True)
  ops=candidate.upgrade_ops.ops
  summary=[{'kind':type(op).__name__,'identity':op.identity.qualified if isinstance(op,NativeTransitionOp) else getattr(op,'table_name',None),'children':[type(x).__name__ for x in getattr(op,'ops',())]} for op in ops]
  out.joinpath('candidate.json').write_text(json.dumps(summary,indent=2))
  print('PASSED native candidate discovery',len(ops),'operations',len(authoring.desired),'desired')
  print(json.dumps(summary))
 except BaseException:
  out.joinpath('failure.txt').write_text(traceback.format_exc());raise
 finally:tx.rollback()
 assert current_revision(conn)=='semantic_pdf_retire_20261101'
 assert conn.scalar(text('SELECT current_user'))=='paul'
 print('PASSED rollback restored82 + caller role')
engine.dispose()
