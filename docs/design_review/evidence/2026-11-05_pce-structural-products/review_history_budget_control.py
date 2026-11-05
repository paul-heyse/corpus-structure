"""Rollback-only native preflight control; final148deployment is separately qualified."""
from __future__ import annotations
import json
from pathlib import Path
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from corpus_structure.evaluate.review_assessments import iter_assessment_review_rows
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

path=Path('python/corpus-structure/src/corpus_structure/semantic/sql/review_assessments.sql')
prepared=prepare_sql(path.read_text(),source=str(path)); names={'review_history_preflight','operation_review_history_bounded','structural_review_history_bounded'}
checks={}
with open_runtime_engine(Settings(),'pce-history-native-budget-control',purpose='maintenance') as engine:
 with engine.connect() as conn:
  tx=conn.begin()
  try:
   for index,statement in enumerate(prepared.statements):
    node=statement.stmt
    if isinstance(node,ast.CreateFunctionStmt) and node.funcname[-1].sval in names:
     conn.exec_driver_sql(prepared.excerpt(index))
   for group,set_id,receipt in ((False,18,6),(True,3,5)):
    project=conn.scalar(text('SELECT project_id FROM eval.'+('structural_reference_set' if group else 'reference_set')+' WHERE id=:id'),{'id':set_id})
    for label,bounds in (('rows',{'max_rows':1}),('bytes',{'max_bytes':128})):
     try:
      with conn.begin_nested(): list(iter_assessment_review_rows(conn,project_id=project,set_id=set_id,exposure_receipt_id=receipt,group=group,**bounds))
     except DBAPIError as refused:
      assert getattr(refused.orig,'sqlstate',None)=='23514'
      assert 'before capture' in str(refused.orig)
      checks[f'{group}-{label}']='native_refused23514_before_capture'
     else:raise AssertionError('native bound did not refuse before client capture')
    rows=list(iter_assessment_review_rows(conn,project_id=project,set_id=set_id,exposure_receipt_id=receipt,group=group))
    assert any(row['kind']=='pass' for row in rows)
    checks[f'{group}-default-complete']=len(rows)
  finally:tx.rollback()
result={'outcome':'passed','checks':checks,'scope':'rollback-only new native budget functions on actual retained cohorts; permanent148admission pending'}
with Path(__file__).with_name('raw').joinpath('review-history-budget-148.json').open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
