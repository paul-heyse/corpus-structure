"""Author a prospective AC forward transition on owned frozen101 clones; never deploy."""
from pathlib import Path
import os
import sys
from uuid import uuid4

from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.migrations import current_revision, upgrade
from corpus_structure.semantic.native_candidate import (
    prepare_series_candidate, candidate_admission_sql, series_native_definitions,
)
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, server_url

settings = Settings()
server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
name = f"cs_sem_ac_author_{os.getpid()}_{uuid4().hex[:8]}"
with server.database(name, server.template) as engine:
        with engine.begin() as initial:
            upgrade(initial, "semantic_m1_records_20261103")
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                predecessor = current_revision(conn)
                script, authoring = prepare_series_candidate(conn, owned_authoring=True)
                operations = script.upgrade_ops
                native = [x for x in operations.ops if isinstance(x, NativeTransitionOp)]
                role = conn.exec_driver_sql("SELECT current_user").scalar_one()
                python = _native_candidate_python(operations, "SET LOCAL ROLE " + conn.dialect.identifier_preparer.quote(role))
                compile(python, "prospective-native.py", "exec")
                admission = candidate_admission_sql(conn, series_native_definitions(conn), authoring.desired,
                    retire=frozenset(item.identity for item in native if item.after is None))
                state = canonical_bytes({"version": 1, "predecessor": predecessor,
                    "operations": [x.payload() for x in native],
                    "desired": [x.payload() for x in authoring.desired]})
            finally:
                transaction.rollback()
out = Path(__file__).with_name(sys.argv[1] if len(sys.argv) > 1 else "candidate-001")
out.mkdir(exist_ok=False)
(out / "native_candidate.py").write_text(python)
(out / "native_operations.json").write_bytes(state)
(out / "native_admission.sql").write_text(admission)
print({"predecessor": predecessor, "native": len(native), "total": len(operations.ops)})
