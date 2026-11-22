"""Current native validity on a freshly installed target."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from time import monotonic, sleep
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from corpus_structure.semantic._data_operation_wire import (
    WirePublishDataDerivationRequest,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.data_operation_admission import inspect_data_operation_release
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.migrations import upgrade
from corpus_structure.semantic.releases import open_release
from native_test_support import principal_engine
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel


def test_current_root_native_validity_and_conservative_settlement(
    semantic_bare_engine, native_settings, tmp_path
):
    engine = semantic_bare_engine
    with engine.begin() as connection:
        upgrade(connection)
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
                    "INSERT INTO validity_array_control("
                    "release_id,operation_id,subject_definition,recipe,profile,"
                    "implementation_revision,input_roles,output_roles,support_contract,"
                    "binding_expression,definition_identity,eligibility_identity,"
                    "quantified,validity_families,validity_conservative,dependencies,"
                    "parameter_definitions) "
                    "VALUES ('release:control','control','subject','recipe','derivation',"
                    "'control','[]','[]','{}','{}','definition','eligibility',false,"
                    + bad
                    + ",false,'[]','{}')"
                )
    _conservative_settlement(engine, native_settings, tmp_path, project="ddo-test")


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
