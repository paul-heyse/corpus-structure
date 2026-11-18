"""Private N29 successor and actual settlement under declared validity."""

import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from time import monotonic, sleep
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.schema.data_steps import DataStepRequest, prepare_data_steps
from corpus_structure.semantic._data_operation_wire import (
    WirePublishDataDerivationRequest,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.data_operation_admission import inspect_data_operation_release
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    native_source_digest,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.migrations import ALEMBIC_DIR, upgrade
from corpus_structure.semantic.native_authoring import (
    authored_admission_sql,
    load_native_state,
    verify_rendered_candidate,
)
from corpus_structure.semantic.native_objects import native_owner
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.target_installation import (
    capture_target_installation,
    prepare_target_successor,
)
from native_test_support import principal_engine
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel
from semantic.test_target_installation_native import register_target_revision

N29 = "semantic_ddo_pe_n29"


def _seed_old_definitions(connection):
    with native_owner(connection, "corpus_sem_publisher"):
        connection.exec_driver_sql(
            "INSERT INTO sem.release(release_id,content_digest,profile,prepared_bytes,manifest_bytes) "
            "VALUES ('release:n29-validity-control','digest','control','{}','{}')"
        )
        connection.exec_driver_sql(
            "INSERT INTO sem.data_operation_definition("
            "release_id,operation_id,subject_definition,recipe,profile,implementation_revision,"
            "input_roles,output_roles,support_contract,binding_expression,definition_identity,"
            "eligibility_identity,quantified,validity_family,dependencies) "
            "SELECT 'release:n29-validity-control',name,'subject',name,'derivation','control',"
            "'[]','[]','{}','{}',name,name,false,family,'[]' "
            "FROM (VALUES ('claimed','record-grade'),('ordinary',NULL)) AS old(name,family)"
        )


@pytest.fixture
def declared_validity_target(semantic_database_at, tmp_path, monkeypatch):
    from corpus_structure.semantic import migrations

    metadata = get_metadata()
    deployment = capture_target_installation(metadata)
    captured_digest = native_source_digest(deployment.authoring_inputs.native_sources)
    predecessor = load_native_state(ALEMBIC_DIR / "versions" / (N29 + "_native.json"))
    retired = frozenset(
        item.identity for item in predecessor if item.identity.name == "ddo_classify_validity"
    )
    assert len(retired) == 1
    steps = prepare_data_steps(
        (DataStepRequest(name="ddo_declared_validity"),), target=metadata, predecessor=N29
    )
    with semantic_database_at(N29) as engine:
        with engine.begin() as connection:
            _seed_old_definitions(connection)
            candidate, authoring = prepare_target_successor(
                connection,
                deployment,
                predecessor=predecessor,
                retire=retired,
                owned_authoring=True,
                predecessor_revision=N29,
                data_steps=steps,
            )
            assert candidate.upgrade_ops is not None
            rendered = _native_candidate_python(candidate.upgrade_ops)
            verify_rendered_candidate(
                connection,
                rendered,
                authoring,
                candidate.privilege_policies,
                authored_admission_sql(authoring),
            )
        location = tmp_path / "candidate-revisions"
        shutil.copytree(ALEMBIC_DIR, location, ignore=shutil.ignore_patterns("__pycache__"))
        revision = register_target_revision(
            location, "udm_a_control", rendered, authoring, candidate, predecessor=N29
        )
        with engine.begin() as connection:
            upgrade(
                connection, revision.revision, script_location=location, expected_predecessor=N29
            )
            assert (
                connection.scalar(
                    text("SELECT sem.data_operation_native_descriptor()->>'source_digest'")
                )
                == captured_digest
            )
        monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
        yield engine


def test_n29_conversion_and_conservative_settlement(
    declared_validity_target, native_settings, tmp_path
):
    engine = declared_validity_target
    with engine.begin() as connection:
        staged = connection.execute(
            text(
                "SELECT operation_id,validity_families,validity_conservative "
                "FROM sem.data_operation_definition WHERE release_id='release:n29-validity-control' "
                "ORDER BY operation_id"
            )
        ).all()
        assert staged == [("claimed", ["record-grade"], False), ("ordinary", [], False)]
        connection.exec_driver_sql(
            "CREATE TEMP TABLE validity_array_control "
            "(LIKE sem.data_operation_definition INCLUDING CONSTRAINTS)"
        )
        for bad in ("ARRAY['unknown']", "ARRAY[NULL::text]"):
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.exec_driver_sql(
                    "CREATE TEMP TABLE validity_array_input AS TABLE validity_array_control WITH NO DATA"
                )
                connection.exec_driver_sql(
                    "INSERT INTO validity_array_input SELECT * FROM sem.data_operation_definition "
                    "WHERE operation_id='ordinary'"
                )
                connection.exec_driver_sql(
                    "UPDATE validity_array_input SET validity_families=" + bad
                )
                connection.exec_driver_sql(
                    "INSERT INTO validity_array_control TABLE validity_array_input"
                )

    declaration = json.loads(STORAGE.declaration_content or b"{}")
    for operation in declaration["operations"]:
        if operation["id"] == "urn:ddo-test:source":
            operation.pop("validity_family", None)
        else:
            operation["validity_family"] = ["none"]
    recipe = replace(STORAGE, declaration_content=canonical_bytes(declaration))
    preparation = prepare_kernel(recipe, directory=tmp_path / "validity-basis")
    with engine.begin() as connection:
        assert preparation.prepared.native_kernel_digest == connection.scalar(
            text("SELECT sem.data_operation_native_descriptor()->>'source_digest'")
        )
        kernel = admit_kernel(connection, recipe, preparation=preparation)
        connection.exec_driver_sql(
            "INSERT INTO ops.data_trust_scope(scope,project_id,epoch) "
            "VALUES ('unrelated-previous','ddo-test',4),('unrelated-other-project','another',9)"
        )

    def leased(subject, original_source):
        _, _, _, attached = attach(kernel, subject=subject, original_source=original_source)
        return claim(kernel, attached, seconds=120)

    proof = leased("conservative:previous", "source:previous")
    episode = publish(kernel, proof, retain(kernel, proof))["derivation_id"]
    revocable = leased("conservative:revocable", "source:revocable")
    revoked = publish(kernel, revocable, retain(kernel, revocable))["derivation_id"]
    first = leased("conservative:first", "source:first")
    second = leased("conservative:second", "source:second")

    def settle(fence):
        with engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
            intent = retain(kernel, fence, connection=connection)
        with engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
            result = DataOperationStorage(connection).publish_data_derivation(
                cast(WirePublishDataDerivationRequest, {**fence, "intent_id": intent["intent_id"]})
            )
        return intent, result

    def observe_block():
        with engine.connect() as connection:
            return connection.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND wait_event_type='Lock' AND query LIKE '%ops.retain_data_completion_intent%'"
                )
            )

    # The revocation holds the trust row while both settlements acquire their new seals.
    with ThreadPoolExecutor(max_workers=2) as workers:
        with engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
            valid = text("SELECT ops.ddo_conservative_dependencies_valid(:episode)")
            assert connection.scalar(valid, {"episode": episode}) is True
            connection.exec_driver_sql(
                "INSERT INTO ops.data_trust_scope(scope,project_id,epoch) "
                "VALUES ('unrelated-late','ddo-test',0)"
            )
            assert connection.scalar(valid, {"episode": episode}) is True
            revocation = DataOperationStorage(connection).revoke_data_support(
                cast(
                    WireRevokeDataSupportRequest,
                    {
                        "project_id": "ddo-test",
                        "original_source": "source:revocable",
                        "selector_kind": "derivation",
                        "selector": revoked,
                        "reason": "private completion scope control",
                    },
                )
            )
            assert connection.scalar(valid, {"episode": episode}) is False
            futures = [workers.submit(settle, fence) for fence in (first, second)]
            started = monotonic()
            while observe_block() < 2 and monotonic() - started < 2:
                sleep(0.02)
            assert observe_block() == 2
        completed = [item.result(timeout=15) for item in futures]

    published = [result for _, result in completed]
    assert len({item["derivation_id"] for item in published}) == 2
    assert all(item["trust_snapshot"]["unrelated-previous"] == 4 for item in published)
    assert all("unrelated-other-project" not in item["trust_snapshot"] for item in published)
    assert all(
        item["trust_snapshot"][revocation["scope"]] == revocation["epoch"] for item in published
    )
    assert publish(kernel, first, completed[0][0])["replayed"] is True

    reader = principal_engine(native_settings, "read", engine.url.database)
    try:
        with reader.begin() as connection:
            archived = open_release(connection, kernel.prepared.release_id)
            _, result = inspect_data_operation_release(connection, archived, validity_only=True)
            assert result["conservative_operations"] == ["urn:ddo-test:source"]
    finally:
        reader.dispose()
