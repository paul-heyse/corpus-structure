"""Actual native participant guard over retained005 envelopes; no new judgments."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.settings import Settings

raw=Path(__file__).with_name('raw')
source=Path('python/corpus-structure/src/corpus_structure/semantic/sql/structural_publication.sql').read_text()
start=source.index('    -- An input frame is a candidate/context inventory')
end=source.index('   END LOOP;',start)
guard=source[start:end]
reports={name:StructuralProductReport.model_validate_json((raw/f'production-{name}-005.json').read_bytes()) for name in ('normal','mean','comparison','dossier')}
by_id={r.product_id:r for r in reports.values()}
dossier=reports['dossier']; assert dossier.dossier is not None
checks={}
with open_runtime_engine(Settings(),'pce-dossier-participation-control',purpose='maintenance') as engine:
 with engine.connect() as conn:
  tx=conn.begin()
  try:
   def execute(member,upstream):
    # Anonymous block uses the unchanged production guard and parameterized JSON literals.
    from sqlalchemy import String
    dialect=conn.dialect
    def literal(value):return dialect.statement_compiler(dialect,None).render_literal_value(canonical_bytes(value).decode(),String())+'::jsonb'
    prefix='DECLARE upstream record; report jsonb; member jsonb; BEGIN SELECT '+literal(upstream.model_dump(mode='json',exclude_none=True))+' product INTO upstream; report:='+literal(dossier.model_dump(mode='json',exclude_none=True))+'; member:='+literal(member.model_dump(mode='json',exclude_none=True))+';\n'
    body=prefix+guard+'\n END;'
    delimiter='$pce_control$'
    while delimiter in body: delimiter=delimiter[:-1]+'x$'
    conn.exec_driver_sql('DO '+delimiter+body+delimiter+';')
   for member in dossier.dossier.members:
    execute(member,by_id[member.relation_product_id])
    checks[member.member_id]='passed'
   exception=next(m for m in dossier.dossier.members if m.role=='exception')
   try:
    with conn.begin_nested(): execute(exception,reports['mean'])
   except DBAPIError as refused:
    assert getattr(refused.orig,'sqlstate',None)=='23514'
    assert 'did not participate' in str(refused.orig)
    checks['wrong_but_real_definition_predecessor']='refused23514'
   else:raise AssertionError('wrong-but-real selected predecessor was accepted')
   context_only=exception.model_copy(update={'passage_id':'nist-ci-interpretation','role':'open_question'})
   try:
    with conn.begin_nested(): execute(context_only,reports['comparison'])
   except DBAPIError as refused:
    assert getattr(refused.orig,'sqlstate',None)=='23514'
    assert 'did not participate' in str(refused.orig)
    checks['comparison_unused_input_context']='refused23514'
   else:raise AssertionError('comparison input inventory was treated as semantic participation')
  finally:tx.rollback()
result={'outcome':'passed','checks':checks,'scope':'actual production native participant guard; not whole public admission or independent source quality'}
with (raw/(sys.argv[1] if len(sys.argv)>1 else 'dossier-participation-148.json')).open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
