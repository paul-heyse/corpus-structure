"""Author native107 in the configured persistent database, rolling back all work."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from sqlalchemy.schema import CreateColumn, CreateTable, AddConstraint
from sqlalchemy import inspect, PrimaryKeyConstraint, ForeignKeyConstraint
from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.native_candidate import candidate_admission_sql, prepare_series_candidate, series_native_definitions
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

out=Path(__file__).parent/sys.argv[1]
out.mkdir(exist_ok=False)
with open_runtime_engine(Settings(),'m1-policy-native-author',purpose='maintenance') as engine,engine.connect() as conn:
 tx=conn.begin()
 try:
  predecessor=current_revision(conn)
  assert predecessor=='semantic_m1_preparation_20261104',predecessor
  assert conn.exec_driver_sql('SELECT count(*) FROM data.record_assertion').scalar_one()==0, 'legacy assertion mapping is not empty; explicit preservation required'
  physical='DO $$ BEGIN IF EXISTS(SELECT FROM data.record_assertion) THEN RAISE EXCEPTION \'legacy assertion mappings require explicit migration\'; END IF; END $$;\n'
  assertion = table('data.record_assertion')
  for name in ['role','reading_id','occurrence_id']:
   physical += 'ALTER TABLE data.record_assertion ADD COLUMN '+str(CreateColumn(assertion.c[name]).compile(dialect=conn.dialect))+';\n'
  inspector = inspect(conn)
  primary = inspector.get_pk_constraint('record_assertion',schema='data')
  physical += 'ALTER TABLE data.record_assertion DROP CONSTRAINT '+conn.dialect.identifier_preparer.quote(primary['name'])+';\n'
  existing = {(tuple(row['constrained_columns']),row['referred_schema'],row['referred_table'],tuple(row['referred_columns'])) for row in inspector.get_foreign_keys('record_assertion',schema='data')}
  for constraint in assertion.constraints:
   signature = (tuple(constraint.column_keys),constraint.referred_table.schema,constraint.referred_table.name,tuple(element.column.name for element in constraint.elements)) if isinstance(constraint,ForeignKeyConstraint) else None
   if isinstance(constraint,PrimaryKeyConstraint) or signature not in existing:
    physical += str(AddConstraint(constraint).compile(dialect=conn.dialect))+';\n'
  physical+=str(CreateTable(table('data.record_assertion_support')).compile(dialect=conn.dialect))+';\n'
  for name in ['instance_digest','evaluation_id','evaluation_digest','probability_lexical','binding_json']:
   physical+='ALTER TABLE data.record_admission ADD COLUMN '+str(CreateColumn(table('data.record_admission').c[name]).compile(dialect=conn.dialect))+';\n'
  for name in ['record_assertion','record_assertion_support']:
   physical+=f'ALTER TABLE data.{name} OWNER TO corpus_sem_publisher;\nGRANT SELECT ON data.{name} TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;\n'
  conn.exec_driver_sql(physical)
  script,authoring=prepare_series_candidate(conn,owned_authoring=True)
  native=[op for op in script.upgrade_ops.ops if isinstance(op,NativeTransitionOp)]
  ordinary=[op for op in script.upgrade_ops.ops if not isinstance(op,NativeTransitionOp)]
  state=canonical_bytes(dict(version=1,predecessor=predecessor,operations=[op.payload() for op in native],desired=[item.payload() for item in authoring.desired]))
  admission=candidate_admission_sql(conn,series_native_definitions(conn),authoring.desired,retire=frozenset(op.identity for op in native if op.after is None))
  role=conn.exec_driver_sql('SELECT current_user').scalar_one()
  rendered=_native_candidate_python(script.upgrade_ops,'SET LOCAL ROLE '+conn.dialect.identifier_preparer.quote(role))
  compile(rendered,'prospective107.py','exec')
  (out/'native_operations.json').write_bytes(state)
  (out/'native_admission.sql').write_text(admission)
  (out/'native_candidate.py').write_text(rendered)
  (out/'physical.sql').write_text(physical)
  (out/'ordinary-operations.txt').write_text('\n'.join(repr(op.to_diff_tuple()) for op in ordinary))
  print(json.dumps(dict(outcome='passed',predecessor=predecessor,native_operations=len(native),ordinary_operations=len(ordinary),managed_objects=len(authoring.desired),persistent_database_retained=True,transaction='rolled_back')))
 finally:tx.rollback()
