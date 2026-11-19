"""Private N29 successor and actual settlement under declared validity."""

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from time import monotonic, sleep
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

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
    from alembic.script import ScriptDirectory

    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.migrations import alembic_config

    metadata = get_metadata()
    deployment = capture_target_installation(metadata)
    captured_digest = native_source_digest(deployment.authoring_inputs.native_sources)
    predecessor = load_native_state(ALEMBIC_DIR / "versions" / (N29 + "_native.json"))
    names = {"ddo_classify_validity", "ddo_rich_producing_request", "record_sql_admission"}
    retired = frozenset(item.identity for item in predecessor if item.identity.name in names)
    assert {item.name for item in retired} == names
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
        directory = ScriptDirectory.from_config(alembic_config(script_location=location))
        ancestors = {
            revision.revision for revision in directory.walk_revisions(base="base", head=N29)
        }
        for revision in directory.walk_revisions():
            if revision.revision not in ancestors:
                Path(revision.path).unlink()
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
        decimal = text("SELECT data.decimal_canonical(:value)")
        for value, expected in (
            ("9" * 10000, "9" * 10000),
            ("1e16383", "1" + "0" * 16383),
            ("1e-16383", "0." + "0" * 16382 + "1"),
            ("-000.0012300e+2", "-0.123"),
            ("-0.00e9999999999999999999999", "0"),
            ("12." + "0" * 20000, "12"),
        ):
            assert connection.scalar(decimal, {"value": value}) == expected
        for value in ("1e16384", "1e-16384", "9" * 16385, "1e9999999999999999999999"):
            with (
                pytest.raises(DBAPIError, match="canonical fixed-point digit limit") as refusal,
                connection.begin_nested(),
            ):
                connection.scalar(decimal, {"value": value})
            assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
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

    _conservative_settlement(engine, native_settings, tmp_path, project="ddo-test")


@pytest.mark.skipif(
    os.environ.get("CORPUS_UDM_TRANSITION_OBSERVATION") != "130661481",
    reason="requires an explicit observation of the owned transition stage",
)
def test_deployed_transition_conservative_settlement(native_settings, tmp_path):
    from corpus_structure.semantic.migrations import current_revision
    from corpus_structure.semantic.storage_target import acquired_target

    deployment = native_settings.deployment
    assert deployment is not None
    maintenance = deployment.maintenance_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(
        maintenance, connect_args={"application_name": "udm-transition-stage-observation"}
    )
    try:
        with engine.connect() as connection:
            target = acquired_target(connection, purpose="maintenance")
            assert (target.database_oid, target.database, target.port) == (
                130661481,
                "corpus_structure_ddo_stage",
                5434,
            )
            assert current_revision(connection) == "semantic_ddo_pe_n32"
        project = "udm-transition-conservative-" + uuid4().hex[:12]
        _conservative_settlement(engine, native_settings, tmp_path, project=project)
    finally:
        engine.dispose()


def _conservative_settlement(engine, native_settings, tmp_path, *, project):
    declaration = json.loads(STORAGE.declaration_content or b"{}")
    for operation in declaration["operations"]:
        if operation["id"] == "urn:ddo-test:source":
            operation.pop("validity_family", None)
        else:
            operation["validity_family"] = ["none"]
    ordinary = next(
        dict(operation)
        for operation in declaration["operations"]
        if operation["id"] == "urn:ddo-test:source"
    )
    ordinary.update(id="urn:ddo-test:ordinary-source", validity_family=["none"])
    declaration["operations"].append(ordinary)
    recipe = replace(STORAGE, declaration_content=canonical_bytes(declaration), project_id=project)
    preparation = prepare_kernel(recipe, directory=tmp_path / "validity-basis")
    with engine.begin() as connection:
        assert preparation.prepared.native_kernel_digest == connection.scalar(
            text("SELECT sem.data_operation_native_descriptor()->>'source_digest'")
        )
        kernel = admit_kernel(connection, recipe, preparation=preparation)
        connection.execute(
            text(
                "INSERT INTO ops.data_trust_scope(scope,project_id,epoch) "
                "VALUES (:previous,:project,4),(:other,:other_project,9)"
            ),
            {
                "previous": f"{project}:previous",
                "project": project,
                "other": f"{project}:other",
                "other_project": f"{project}:other-project",
            },
        )

    def leased(subject, original_source, operation="urn:ddo-test:source"):
        _, _, _, attached = attach(
            kernel,
            subject=subject,
            original_source=original_source,
            project_id=project,
            operation=operation,
        )
        return claim(kernel, attached, seconds=120)

    ordinary_fence = leased("ordinary:previous", "source:ordinary", "urn:ddo-test:ordinary-source")
    ordinary_receipt = publish(kernel, ordinary_fence, retain(kernel, ordinary_fence))
    assert f"{project}:previous" not in ordinary_receipt["trust_snapshot"]

    proof = leased("conservative:previous", "source:previous")
    episode = publish(kernel, proof, retain(kernel, proof))["derivation_id"]
    other_project = f"{project}:other-project"
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO data.project(project_id) VALUES (:project)"),
            {"project": other_project},
        )
    _, _, _, foreign_attached = attach(
        kernel, subject="foreign:source", original_source="source:foreign", project_id=other_project
    )
    foreign_fence = claim(kernel, foreign_attached)
    foreign_receipt = publish(kernel, foreign_fence, retain(kernel, foreign_fence))
    with engine.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                dict(
                    project_id=other_project,
                    original_source="source:foreign",
                    selector_kind="derivation",
                    selector=foreign_receipt["derivation_id"],
                    reason="independent foreign project revocation",
                ),
            )
        )
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT ops.ddo_conservative_dependencies_valid(:episode)"),
                {"episode": episode},
            )
            is True
        )
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
            connection.execute(
                text(
                    "INSERT INTO ops.data_trust_scope(scope,project_id,epoch) "
                    "VALUES (:late,:project,0)"
                ),
                {"late": f"{project}:late", "project": project},
            )
            assert connection.scalar(valid, {"episode": episode}) is True
            revocation = DataOperationStorage(connection).revoke_data_support(
                cast(
                    WireRevokeDataSupportRequest,
                    {
                        "project_id": project,
                        "original_source": "source:revocable",
                        "selector_kind": "derivation",
                        "selector": revoked,
                        "reason": "conservative completion scope observation",
                    },
                )
            )
            assert connection.scalar(valid, {"episode": episode}) is False
            assert (
                connection.scalar(
                    text("SELECT ops.ddo_node_valid('episode',:episode)"),
                    {"episode": ordinary_receipt["derivation_id"]},
                )
                is True
            )
            futures = [workers.submit(settle, fence) for fence in (first, second)]
            started = monotonic()
            while observe_block() < 2 and monotonic() - started < 2:
                sleep(0.02)
            assert observe_block() == 2
        completed = [item.result(timeout=15) for item in futures]

    published = [result for _, result in completed]
    assert len({item["derivation_id"] for item in published}) == 2
    assert all(item["trust_snapshot"][f"{project}:previous"] == 4 for item in published)
    assert all(f"{project}:other" not in item["trust_snapshot"] for item in published)
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
        declaration["operations"][
            next(
                index
                for index, operation in enumerate(declaration["operations"])
                if operation["id"] == "urn:ddo-test:source"
            )
        ]["validity_family"] = ["none"]
        changed_recipe = replace(
            recipe, declaration_content=canonical_bytes(declaration), project_id=None
        )
        changed_preparation = prepare_kernel(changed_recipe, directory=tmp_path / "explicit-none")
        assert changed_preparation.prepared.release_id != kernel.prepared.release_id
        assert (
            changed_preparation.prepared.native_kernel_digest
            == kernel.prepared.native_kernel_digest
        )
        with engine.begin() as connection:
            changed = admit_kernel(connection, changed_recipe, preparation=changed_preparation)
        _, _, _, attached = attach(
            changed, subject="new:none", original_source="source:none", project_id=project
        )
        fence = claim(changed, attached)
        receipt = publish(changed, fence, retain(changed, fence))
        assert f"{project}:previous" not in receipt["trust_snapshot"]
        with engine.begin() as connection:
            DataOperationStorage(connection).revoke_data_support(
                cast(
                    WireRevokeDataSupportRequest,
                    dict(
                        project_id=project,
                        original_source="source:revocable",
                        selector_kind="derivation",
                        selector=revoked,
                        reason="none claim retains declared support scope only",
                    ),
                )
            )
            assert (
                connection.scalar(
                    text("SELECT ops.ddo_node_valid('episode',:episode)"),
                    {"episode": receipt["derivation_id"]},
                )
                is True
            )
    finally:
        reader.dispose()
