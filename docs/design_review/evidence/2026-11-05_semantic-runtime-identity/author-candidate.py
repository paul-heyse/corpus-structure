"""Derive and actually install/admit a candidate on an owned clone, then roll back."""

from __future__ import annotations

import json
import importlib
import os
import re
import sys
import traceback
from contextlib import nullcontext
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path.cwd() / "scripts"))

from alembic.migration import MigrationContext
from alembic.operations import Operations

from corpus_structure.cli.schema import _native_candidate_python
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


def refresh_admission(state) -> None:
    """Generate the prospective Python verifier from the selected exact native declarations."""
    from corpus_structure.semantic import execution_admission

    path = Path(execution_admission.__file__)
    source = path.read_text()
    for name, key in (
        ("execution_contract_descriptor", "_DESCRIPTOR_SHA256"),
        ("require_execution_release", "_REQUIRE_SHA256"),
    ):
        item = next(item for item in state["desired"]
            if item["identity"]["schema"] == "data" and item["identity"]["name"] == name)
        digest = sha256(item["catalog"]["body"].encode()).hexdigest()
        source, count = re.subn(rf'{key} = "[0-9a-f]+"', f'{key} = "{digest}"', source)
        assert count == 1
    path.write_text(source)
    importlib.reload(execution_admission)


def positive_controls(conn) -> None:
    """Exercise real owner-native effects without claiming restricted-principal qualification."""
    sys.path.insert(0, str(Path.cwd() / "python/corpus-structure/tests"))
    from semantic.operation_scenario_support import prepare_operation_scenario
    from semantic.test_runtime_bindings_native import alternate_runtime, native_run

    from corpus_structure.semantic.operations import OperationBinding, create_run, start_run
    from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_run
    from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding

    prepared = prepare_operation_scenario(SimpleNamespace(begin=lambda: nullcontext(conn)))
    original = conn.exec_driver_sql("SELECT prepared_bytes,manifest_bytes FROM sem.release").one()
    first = prepare_runtime_binding(prepared)
    first_run = create_run(conn, project_id="p",
        binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
        kind="full", options={}, code_commit="candidate-owner-control",
        prepared=prepared, runtime_binding=first)
    second = alternate_runtime(prepared)
    second_run = native_run(conn, prepared, second)
    assert first.runtime_id != second.runtime_id
    assert runtime_binding_for_run(conn, first_run, prepared) == first
    assert runtime_binding_for_run(conn, second_run, prepared) == second
    assert conn.exec_driver_sql("SELECT count(*) FROM sem.runtime_binding").scalar_one() == 2
    assert conn.exec_driver_sql("SELECT prepared_bytes,manifest_bytes FROM sem.release").one() == original
    assert start_run(conn, first_run, prepared=prepared) == first_run


def main() -> None:
    out = Path(__file__).with_name(sys.argv[1])
    out.mkdir(exist_ok=False)
    receipt = {"outcome": "failed", "stage": "acquire", "persistent_deployment": False}
    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    name = f"cs_sem_runtime_author_{os.getpid()}_{uuid4().hex[:8]}"
    try:
        with server.database(name, server.template) as engine:
            with engine.begin() as conn:
                upgrade(conn, "semantic_pce_foundation_20261105")
            with engine.connect() as conn:
                transaction = conn.begin()
                try:
                    receipt["stage"] = "derive"
                    predecessor = current_revision(conn)
                    script, authoring = prepare_series_candidate(conn, owned_authoring=True)
                    operations = script.upgrade_ops
                    if operations is None:
                        raise ValueError("candidate has no upgrade operations")
                    native = [x for x in operations.ops if isinstance(x, NativeTransitionOp)]
                    role = conn.exec_driver_sql("SELECT current_user").scalar_one()
                    source = _native_candidate_python(
                        operations, "SET LOCAL ROLE " + conn.dialect.identifier_preparer.quote(role)
                    )
                    compile(source, "candidate.py", "exec")
                    admission = candidate_admission_sql(
                        conn, series_native_definitions(conn), authoring.desired,
                        retire=frozenset(x.identity for x in native if x.after is None),
                    )
                    state = {
                        "version": 1, "predecessor": predecessor,
                        "operations": [x.payload() for x in native],
                        "desired": [x.payload() for x in authoring.desired],
                    }
                    (out / "native_candidate.py").write_text(source)
                    (out / "native_operations.json").write_bytes(canonical_bytes(state))
                    (out / "native_admission.sql").write_text(admission)
                    refresh_admission(state)
                    receipt |= {"predecessor": predecessor, "native_operations": len(native),
                        "total_operations": len(operations.ops), "stage": "install"}
                    namespace = {}
                    exec(compile(source, "candidate.py", "exec"), namespace)
                    with Operations.context(MigrationContext.configure(conn)):
                        namespace["upgrade"]()
                    receipt["stage"] = "admit"
                    admit_native(conn, authoring.desired)
                    assert conn.exec_driver_sql(
                        "SELECT pg_get_userbyid(relowner)='corpus_sem_publisher' "
                        "FROM pg_class WHERE oid='sem.runtime_binding'::regclass"
                    ).scalar_one()
                    receipt["stage"] = "owner_native_positive_controls"
                    positive_controls(conn)
                    receipt["owner_native_positive_controls"] = "passed"
                    assert conn.exec_driver_sql(
                        "SELECT NOT has_table_privilege('corpus_sem_writer',"
                        "'sem.runtime_binding','INSERT,UPDATE,DELETE,TRUNCATE')"
                    ).scalar_one()
                    assert conn.exec_driver_sql(
                        "SELECT attnotnull=false FROM pg_attribute WHERE "
                        "attrelid='ops.run'::regclass AND attname='runtime_id'"
                    ).scalar_one()
                    receipt["stage"] = "rollback"
                finally:
                    transaction.rollback()
                assert current_revision(conn) == "semantic_pce_foundation_20261105"
                assert conn.exec_driver_sql("SELECT to_regclass('sem.runtime_binding') IS NULL").scalar_one()
                assert conn.exec_driver_sql(
                    "SELECT NOT EXISTS(SELECT FROM pg_attribute WHERE "
                    "attrelid='ops.run'::regclass AND attname='runtime_id' AND NOT attisdropped)"
                ).scalar_one()
                receipt |= {"outcome": "passed", "stage": "rolled_back"}
    except BaseException as error:
        receipt["outcome"] = "failed"
        receipt["error"] = str(error)
        receipt["traceback"] = traceback.format_exc()
        raise
    finally:
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({key: value for key, value in receipt.items() if key != "traceback"}))


if __name__ == "__main__":
    main()
