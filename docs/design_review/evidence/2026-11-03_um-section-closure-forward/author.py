"""Rehearse the selected section closure source successor on owned native resources."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.migrations import current_revision, upgrade
from corpus_structure.semantic.native_candidate import (
    candidate_admission_sql,
    prepare_series_candidate,
    series_native_definitions,
)
from corpus_structure.semantic.native_objects import admit_native
from corpus_structure.semantic.source_view_native import _admission_descriptor
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]
PREDECESSOR = "semantic_um_selector_20261103"
REVISION = "semantic_um_section_20261103"


def run(mode: str, output: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from native_test_support import PgAdmin, semantic_principals, server_url

    output.mkdir(parents=True, exist_ok=False)
    settings = Settings()
    server = PgAdmin(
        server_url(settings), settings.database.template, settings=settings
    )
    server.check()
    server.check_roles(semantic_principals())
    token = f"{os.getpid()}_{uuid4().hex[:12]}"
    with server.semantic_template("cs_sem_head_" + token) as template:
        with server.database(
            "cs_sem_test_" + token, template.name, policy=template.policy
        ) as engine:
            with engine.connect() as conn:
                transaction = conn.begin()
                try:
                    expected = PREDECESSOR if mode == "author" else REVISION
                    assert current_revision(conn) == expected
                    candidate, authoring = prepare_series_candidate(
                        conn, owned_authoring=True
                    )
                    assert candidate.upgrade_ops is not None
                    if mode == "replay":
                        assert candidate.upgrade_ops.is_empty()
                        upgrade(conn)
                        assert current_revision(conn) == REVISION
                        admit_native(conn, authoring.desired)
                        report = {
                            "outcome": "passed",
                            "revision": expected,
                            "operations": 0,
                        }
                    else:
                        observed = [
                            {
                                "type": type(item).__name__,
                                "identity": item.identity.qualified if isinstance(item, NativeTransitionOp) else None,
                                "payload": item.payload() if isinstance(item, NativeTransitionOp) else repr(item),
                            }
                            for item in candidate.upgrade_ops.ops
                        ]
                        (output / "candidate.json").write_bytes(canonical_bytes(observed))
                        assert len(candidate.upgrade_ops.ops) == 1, [(item["type"], item["identity"]) for item in observed]
                        transition = candidate.upgrade_ops.ops[0]
                        assert isinstance(transition, NativeTransitionOp)
                        assert (
                            transition.identity.qualified
                            == "data.execution_contract_descriptor()"
                        )
                        assert (
                            transition.before is not None
                            and transition.after is not None
                        )
                        before = _admission_descriptor(
                            ";\n".join(transition.before.statements)
                        )
                        after = _admission_descriptor(
                            ";\n".join(transition.after.statements)
                        )
                        changed = {
                            key
                            for key in before.keys() | after.keys()
                            if before.get(key) != after.get(key)
                        }
                        assert changed == {"model_id", "inputs"}
                        previous = {
                            item["name"]: item["sha256"] for item in before["inputs"]
                        }
                        current = {
                            item["name"]: item["sha256"] for item in after["inputs"]
                        }
                        changed_inputs = {
                            name
                            for name in previous.keys() | current.keys()
                            if previous.get(name) != current.get(name)
                        }
                        assert changed_inputs == {
                            "execution/implementation/pdf/section-views.py",
                        }, changed_inputs
                        assert {
                            key: value
                            for key, value in transition.before.catalog.items()
                            if key != "body"
                        } == {
                            key: value
                            for key, value in transition.after.catalog.items()
                            if key != "body"
                        }
                        operations = Operations(MigrationContext.configure(conn))
                        operations.invoke(transition)
                        admit_native(conn, authoring.desired)
                        empty, _ = prepare_series_candidate(
                            conn, predecessor=authoring.desired, owned_authoring=True
                        )
                        assert (
                            empty.upgrade_ops is not None
                            and empty.upgrade_ops.is_empty()
                        )
                        admission = candidate_admission_sql(
                            conn,
                            series_native_definitions(conn),
                            authoring.desired,
                            retire=authoring.retire,
                            predecessor=authoring.predecessor,
                        )
                        state = {
                            "version": 1,
                            "predecessor": PREDECESSOR,
                            "operations": [transition.payload()],
                            "desired": [item.payload() for item in authoring.desired],
                        }
                        (output / "native.json").write_bytes(canonical_bytes(state))
                        (output / "admission.sql").write_text(admission)
                        report = {
                            "outcome": "passed",
                            "revision": expected,
                            "native_operations": 1,
                            "ordinary_operations": 0,
                            "descriptor_changed": sorted(changed),
                            "changed_inputs": sorted(changed_inputs),
                            "prior_model_id": before["model_id"],
                            "current_model_id": after["model_id"],
                        }
                finally:
                    transaction.rollback()
                assert current_revision(conn) == expected
                admit_native(
                    conn,
                    authoring.predecessor if mode == "author" else authoring.desired,
                )
    (output / "result.json").write_bytes(canonical_bytes(report))
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("author", "replay"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.mode, args.output)
