"""Rollback-only authoring of an owned105 successor, with exact dependency-check migration."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import CheckConstraint, inspect

sys.path.insert(0, str(Path.cwd() / "scripts"))
from native_test_support import PgAdmin, server_url
from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import current_revision, upgrade
from corpus_structure.semantic.native_candidate import (
    candidate_admission_sql, prepare_series_candidate, series_native_definitions,
)
from corpus_structure.settings import Settings

out = Path(__file__).parent / sys.argv[1]
out.mkdir(exist_ok=False)
settings = Settings()
server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
name = f"cs_m1_prepare_author_{os.getpid()}_{uuid4().hex[:8]}"
with server.database(name, server.template) as engine:
    with engine.begin() as conn:
        upgrade(conn, "semantic_ac_attribute_20261103")
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            predecessor = current_revision(conn)
            assert predecessor == "semantic_ac_attribute_20261103"
            checks = inspect(conn).get_check_constraints("task_dependency", schema="ops")
            old = [c for c in checks if "kind" in c["sqltext"]]
            assert len(old) == 1 and "source_view_product" not in old[0]["sqltext"]
            new = [c for c in table("ops.task_dependency").constraints
                   if isinstance(c, CheckConstraint) and "source_view_product" in str(c.sqltext)]
            assert len(new) == 1
            quote = conn.dialect.identifier_preparer.quote
            physical = (
                f'ALTER TABLE ops.task_dependency DROP CONSTRAINT {quote(old[0]["name"])};\n'
                f'ALTER TABLE ops.task_dependency ADD CONSTRAINT {quote(str(new[0].name))} '
                f'CHECK ({new[0].sqltext});\n'
            )
            original_role = conn.exec_driver_sql("SELECT current_user").scalar_one()
            owner = conn.exec_driver_sql(
                "SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid='ops.task_dependency'::regclass"
            ).scalar_one()
            assert owner in {"corpus_sem_writer", "corpus_sem_publisher"}
            conn.exec_driver_sql("SET LOCAL ROLE " + quote(owner))
            conn.exec_driver_sql(physical)
            conn.exec_driver_sql("SET LOCAL ROLE " + quote(original_role))
            script, authoring = prepare_series_candidate(conn, owned_authoring=True)
            native = [op for op in script.upgrade_ops.ops if isinstance(op, NativeTransitionOp)]
            ordinary = [op for op in script.upgrade_ops.ops if not isinstance(op, NativeTransitionOp)]
            (out / "ordinary-operations.txt").write_text("\n".join(repr(op.to_diff_tuple()) for op in ordinary))
            print("ordinary classes", [type(op).__name__ for op in ordinary], flush=True)
            role = conn.exec_driver_sql("SELECT current_user").scalar_one()
            rendered = _native_candidate_python(script.upgrade_ops, "SET LOCAL ROLE " + quote(role))
            compile(rendered, "prospective106.py", "exec")
            state = canonical_bytes(dict(version=1, predecessor=predecessor,
                operations=[op.payload() for op in native],
                desired=[item.payload() for item in authoring.desired]))
            admission = candidate_admission_sql(conn, series_native_definitions(conn), authoring.desired,
                retire=frozenset(op.identity for op in native if op.after is None))
        finally:
            transaction.rollback()
(out / "native_operations.json").write_bytes(state)
(out / "native_admission.sql").write_text(admission)
(out / "physical.sql").write_text(physical)
(out / "physical-owner.json").write_text(json.dumps(dict(owner=owner)))
(out / "native_candidate.py").write_text(rendered)
print(json.dumps(dict(outcome="passed", predecessor=predecessor, native_operations=len(native),
                     physical_changes=1, database_disposed=True)))
