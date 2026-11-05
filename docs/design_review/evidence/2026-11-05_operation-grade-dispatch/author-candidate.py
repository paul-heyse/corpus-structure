"""Derive/install/admit the operation-grade repair on an owned clone and roll back."""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import traceback
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path.cwd() / "scripts"))

from alembic.migration import MigrationContext
from alembic.operations import Operations

from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.semantic import execution_admission
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.migrations import current_revision, upgrade
from corpus_structure.semantic.native_candidate import (
    candidate_admission_sql,
    prepare_series_candidate,
    series_native_definitions,
)
from corpus_structure.semantic.native_objects import admit_native
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, server_url


def main():
    out = Path(__file__).with_name(sys.argv[1])
    out.mkdir(exist_ok=False)
    receipt = {"outcome": "failed", "stage": "acquire", "persistent_deployment": False}
    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    name = f"cs_sem_op_grade_author_{os.getpid()}_{uuid4().hex[:8]}"
    try:
        with server.database(name, server.template) as engine:
            with engine.begin() as conn:
                upgrade(conn, "semantic_runtime_20261105")
            with engine.connect() as conn:
                transaction = conn.begin()
                try:
                    receipt["stage"] = "derive"
                    predecessor = current_revision(conn)
                    script, authoring = prepare_series_candidate(conn, owned_authoring=True)
                    operations = script.upgrade_ops
                    assert operations is not None
                    native = [item for item in operations.ops if isinstance(item, NativeTransitionOp)]
                    role = conn.exec_driver_sql("SELECT current_user").scalar_one()
                    source = _native_candidate_python(
                        operations, "SET LOCAL ROLE " + conn.dialect.identifier_preparer.quote(role)
                    )
                    admission = candidate_admission_sql(
                        conn, series_native_definitions(conn), authoring.desired,
                        retire=frozenset(item.identity for item in native if item.after is None),
                    )
                    state = {
                        "version": 1, "predecessor": predecessor,
                        "operations": [item.payload() for item in native],
                        "desired": [item.payload() for item in authoring.desired],
                    }
                    (out / "native_candidate.py").write_text(source)
                    (out / "native_operations.json").write_bytes(canonical_bytes(state))
                    (out / "native_admission.sql").write_text(admission)
                    receipt |= {"predecessor": predecessor, "native_operations": len(native),
                                "total_operations": len(operations.ops), "stage": "install"}
                    namespace = {}
                    exec(compile(source, "candidate.py", "exec"), namespace)
                    with Operations.context(MigrationContext.configure(conn)):
                        namespace["upgrade"]()
                    admit_native(conn, authoring.desired)
                    receipt["stage"] = "rollback"
                finally:
                    transaction.rollback()
                assert current_revision(conn) == "semantic_runtime_20261105"
                # Prospective Python verifier is generated from exact candidate declarations.
                path = Path(execution_admission.__file__)
                code = path.read_text()
                for name, key in (("execution_contract_descriptor", "_DESCRIPTOR_SHA256"),
                                  ("require_execution_release", "_REQUIRE_SHA256")):
                    item = next(item for item in state["desired"]
                        if item["identity"]["schema"] == "data"
                        and item["identity"]["name"] == name)
                    digest = sha256(item["catalog"]["body"].encode()).hexdigest()
                    code, count = re.subn(rf'{key} = "[0-9a-f]+"', f'{key} = "{digest}"', code)
                    assert count == 1
                path.write_text(code)
                importlib.reload(execution_admission)
                receipt |= {"outcome": "passed", "stage": "rolled_back"}
    except BaseException as error:
        receipt |= {"outcome": "failed", "error": str(error), "traceback": traceback.format_exc()}
        raise
    finally:
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({key: value for key, value in receipt.items() if key != "traceback"}))


if __name__ == "__main__":
    main()
