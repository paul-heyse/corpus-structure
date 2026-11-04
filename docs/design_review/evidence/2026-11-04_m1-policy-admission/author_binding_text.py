"""Preserve canonical JSON lexical bytes in admission's immutable transport field."""
import sys
from pathlib import Path
from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.native_candidate import candidate_admission_sql,prepare_series_candidate,series_native_definitions
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
out=Path(__file__).parent/sys.argv[1];out.mkdir(exist_ok=False)
physical="""ALTER TABLE data.record_admission ALTER COLUMN binding_json TYPE TEXT
USING CASE WHEN jsonb_typeof(binding_json)='string' THEN binding_json#>>'{}'
 ELSE data.canonical_json(binding_json) END;
"""
with open_runtime_engine(Settings(),'m1-binding-text-author',purpose='maintenance') as e,e.connect() as c:
 tx=c.begin()
 try:
  predecessor=current_revision(c);assert predecessor=='semantic_m1_jsonb_20261104'
  c.exec_driver_sql(physical)
  script,authoring=prepare_series_candidate(c,owned_authoring=True)
  native=[op for op in script.upgrade_ops.ops if isinstance(op,NativeTransitionOp)]
  ordinary=[op for op in script.upgrade_ops.ops if not isinstance(op,NativeTransitionOp)]
  state=canonical_bytes(dict(version=1,predecessor=predecessor,operations=[op.payload() for op in native],desired=[op.payload() for op in authoring.desired]))
  admission=candidate_admission_sql(c,series_native_definitions(c),authoring.desired)
  rendered=_native_candidate_python(script.upgrade_ops,'SET LOCAL ROLE '+c.dialect.identifier_preparer.quote(c.exec_driver_sql('SELECT current_user').scalar_one()))
  (out/'native_operations.json').write_bytes(state)
  (out/'native_admission.sql').write_text(admission)
  (out/'native_candidate.py').write_text(rendered)
  (out/'physical.sql').write_text(physical)
  (out/'ordinary-operations.txt').write_text('\n'.join(repr(op.to_diff_tuple()) for op in ordinary))
  print('passed',len(native),'native',len(ordinary),'ordinary',len(authoring.desired),'managed; rolled back persistent authoring')
 finally:tx.rollback()
