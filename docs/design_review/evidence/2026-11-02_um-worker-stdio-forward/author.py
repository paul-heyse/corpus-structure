"""Rehearse the native PDF diagnostic-stream provenance successor on owned resources."""

from __future__ import annotations

import argparse
import json
import os
import sys
from hashlib import sha256
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
PREDECESSOR = "semantic_um_closure_20261102"
REVISION = "semantic_um_stdio_20261102"


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
                        transitions = candidate.upgrade_ops.ops
                        observed = [
                            {
                                "type": type(item).__name__,
                                "identity": item.identity.qualified if isinstance(item, NativeTransitionOp) else None,
                                "payload": item.payload() if isinstance(item, NativeTransitionOp) else repr(item),
                            }
                            for item in transitions
                        ]
                        (output / "candidate.json").write_bytes(canonical_bytes(observed))
                        assert len(transitions) == 2, [(item["type"], item["identity"]) for item in observed]
                        assert all(isinstance(item, NativeTransitionOp) for item in transitions)
                        identities = {item.identity.qualified for item in transitions}
                        assert identities == {
                            "data.execution_contract_descriptor()",
                            "ops.freeze_pdf_build(text,bigint,bigint,text,text)",
                        }, identities
                        for item in transitions:
                            assert item.before is not None and item.after is not None
                            assert not item.recreate
                            assert item.before.identity == item.after.identity
                            assert item.before.role_bindings == item.after.role_bindings
                            assert item.before.catalog_version == item.after.catalog_version
                            assert item.before.binding_version == item.after.binding_version
                            assert {
                                key: value for key, value in item.before.catalog.items()
                                if key != "body"
                            } == {
                                key: value for key, value in item.after.catalog.items()
                                if key != "body"
                            }, item.identity.qualified
                        transition = next(
                            item for item in transitions
                            if item.identity.qualified == "data.execution_contract_descriptor()"
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
                        assert changed == {"model_id", "inputs", "functions"}, changed
                        freeze_name = "ops.freeze_pdf_build(text,bigint,bigint,text,text)"
                        old_functions = {item["signature"]: item for item in before["functions"]}
                        new_functions = {item["signature"]: item for item in after["functions"]}
                        assert {
                            name for name in old_functions.keys() | new_functions.keys()
                            if old_functions.get(name) != new_functions.get(name)
                        } == {freeze_name}
                        guard = next(item for item in transitions if item.identity.qualified == freeze_name)
                        old_guard, new_guard = old_functions[freeze_name], new_functions[freeze_name]
                        assert {
                            key: value for key, value in old_guard.items() if key != "body_sha256"
                        } == {
                            key: value for key, value in new_guard.items()
                            if key in old_guard and key != "body_sha256"
                        }
                        extra_catalog_fields = {
                            "argument_defaults": guard.after.catalog["defaults"],
                            "argument_definition": guard.after.catalog["arguments"],
                            "result_definition": guard.after.catalog["result"],
                            "catalog_acl": guard.after.catalog["acl"],
                            "cost": guard.after.catalog["cost"],
                            "rows": guard.after.catalog["rows"],
                            "support": guard.after.catalog["support"],
                        }
                        assert set(new_guard) - set(old_guard) == set(extra_catalog_fields)
                        assert {key: new_guard[key] for key in extra_catalog_fields} == extra_catalog_fields
                        assert sha256(guard.before.catalog["body"].encode()).hexdigest() == old_functions[freeze_name]["body_sha256"]
                        assert sha256(guard.after.catalog["body"].encode()).hexdigest() == new_functions[freeze_name]["body_sha256"]
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
                            "execution/implementation/pdf/worker.py",
                            "execution/implementation/pdf/stream-orchestration.py",
                            "execution/implementation/pdf/publication-native.py",
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
                        for item in transitions:
                            operations.invoke(item)
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
                            "operations": [item.payload() for item in transitions],
                            "desired": [item.payload() for item in authoring.desired],
                        }
                        (output / "native.json").write_bytes(canonical_bytes(state))
                        (output / "admission.sql").write_text(admission)
                        report = {
                            "outcome": "passed",
                            "revision": expected,
                            "native_operations": len(transitions),
                            "transition_identities": sorted(identities),
                            "body_hashes": {
                                item.identity.qualified: {
                                    "before": sha256(item.before.catalog["body"].encode()).hexdigest(),
                                    "after": sha256(item.after.catalog["body"].encode()).hexdigest(),
                                }
                                for item in transitions
                            },
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
