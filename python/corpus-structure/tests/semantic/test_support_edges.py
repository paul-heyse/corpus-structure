"""Independent profile and malformed-reference controls for native support."""

import json
import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from corpus_structure.semantic.support_edges import declared_support_edges, reference_node
from semantic.test_target_installation_native import (
    fresh_target_epoch as fresh_target_epoch,
)
from semantic.test_target_installation_native import (
    install_target_root,
)


def test_profiles_preserve_historical_and_selected_support_distinctions():
    edges = declared_support_edges()
    profiles = {
        profile: {entry.name for entry in edges if profile in entry.profiles}
        for profile in ("validity", "scope", "public", "lineage")
    }
    assert profiles["lineage"] == {"historical-support"}
    assert profiles["scope"] == {
        "episode-support",
        "episode-original",
        "use-episode",
        "use-selected-support",
        "use-population",
        "population-use",
        "population-parent",
    }
    assert profiles["public"] == profiles["scope"] | {"public-authority-report"}
    assert profiles["validity"] == profiles["scope"] | {
        "terminal",
        "episode-producer",
        "use-choice",
        "use-producer",
    }


@pytest.mark.parametrize(
    "reference, expected",
    [
        ({"kind": "original-source", "admission_id": "original"}, ("original", "original")),
        ({"kind": "authored", "admission_id": "authored"}, ("original", "authored")),
        ({"admission_use_id": "use", "derivation_id": "historical"}, ("use", "use")),
        ({"derivation_id": "episode"}, ("episode", "episode")),
    ],
)
def test_reference_node_preserves_declared_kind_and_identity(reference, expected):
    assert reference_node(reference) == expected


@pytest.mark.parametrize(
    "reference", [{}, {"kind": "authored"}, {"admission_use_id": ""}, {"derivation_id": None}, []]
)
def test_unknown_support_reference_refuses(reference):
    with pytest.raises(ValueError, match="unrecognized native support reference"):
        reference_node(reference)


def test_installed_support_classifier_and_terminal_edges(
    semantic_bare_engine, fresh_target_epoch, tmp_path, monkeypatch
):
    engine = semantic_bare_engine
    _, _, _, _, _, location = install_target_root(engine, fresh_target_epoch, tmp_path)
    with engine.begin() as connection:
        for reference, expected in (
            (
                {"kind": "original-source", "admission_id": "admission"},
                {"kind": "original", "id": "admission"},
            ),
            (
                {"admission_use_id": "current", "derivation_id": "historical"},
                {"kind": "use", "id": "current"},
            ),
            ({"derivation_id": "historical"}, {"kind": "episode", "id": "historical"}),
        ):
            assert (
                connection.scalar(
                    text("SELECT ops.ddo_support_reference_node(CAST(:reference AS jsonb))"),
                    {"reference": json.dumps(reference)},
                )
                == expected
            )
        for reference in ({}, {"kind": "authored"}, {"admission_use_id": ""}, []):
            with (
                pytest.raises(IntegrityError, match="unrecognized native support reference"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text("SELECT ops.ddo_support_reference_node(CAST(:reference AS jsonb))"),
                    {"reference": json.dumps(reference)},
                )
        assert connection.execute(
            text("SELECT * FROM ops.ddo_validity_edges('original','control')")
        ).all() == [(0, None, None)]
    _cross_release_population(engine, location, tmp_path, monkeypatch)


def _cross_release_population(engine, location, tmp_path, monkeypatch, *, project_id="ddo-test"):
    from dataclasses import replace
    from typing import cast

    from corpus_structure.semantic import migrations
    from corpus_structure.semantic._data_operation_wire import (
        WireAttachDataRequestsRequest,
        WireCloseDataPopulationRequest,
        WireRegisterDataDemandRequest,
    )
    from corpus_structure.semantic.data_operation_identity import SemanticRequestKey, semantic_value
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.data_operation_binding_support import discover
    from semantic.data_operation_kernel_support import POPULATION, admit_kernel, prepare_kernel

    if location is not None:
        monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    old_recipe = replace(POPULATION, project_id=project_id)
    old_preparation = prepare_kernel(old_recipe, directory=tmp_path / "old")
    with engine.begin() as connection:
        old = admit_kernel(connection, old_recipe, preparation=old_preparation)
    _, _, parent = discover(old, project_id=project_id)
    new_recipe = replace(
        POPULATION, project_id=None, schema_text=POPULATION.schema_text + "  Unrelated: {}\n"
    )
    preparation = prepare_kernel(new_recipe, directory=tmp_path / "new")
    with engine.begin() as connection:
        current = admit_kernel(connection, new_recipe, preparation=preparation)
    assert current.prepared.release_id != old.prepared.release_id
    assert current.identities["urn:discover", "recipe"] == old.identities["urn:discover", "recipe"]
    from corpus_structure.semantic.data_operation_demands import (
        DiscoverySelection,
        RootSubject,
        freeze_demand,
    )

    selection = freeze_demand(
        current.model,
        roots=(RootSubject("doc", "source:test", canonical_bytes({"page": 1})),),
        targets=("urn:consumer",),
        inference="inference:test",
        execution_profile="execution:test",
        discovery=(DiscoverySelection("urn:discover", "result", "urn:child", "all-items"),),
    ).record
    with engine.begin() as connection:
        storage = DataOperationStorage(connection)
        demand = storage.register_data_demand(
            cast(
                WireRegisterDataDemandRequest,
                {
                    "project_id": project_id,
                    "release_id": current.prepared.release_id,
                    "runtime_id": current.runtime,
                    "root": selection["roots"],
                    "selection": selection,
                    "strength": "value",
                },
            )
        )
        snapshot = storage.read_demand_result({"demand_id": demand["demand_id"]})
    producer = next(row for row in snapshot["obligations"] if row["operation_id"] == "urn:discover")
    request = SemanticRequestKey(
        current.identities["urn:discover", "recipe"],
        "doc",
        {},
        {"parameters": {}, "replicate": None},
        "inference:test",
        subject_context=SubjectContext(
            project_id,
            "doc",
            "source:test",
            canonical_bytes({"page": 1}),
            subject_definition=current.model.operation("urn:discover").subject,
        ),
    )
    with engine.begin() as connection:
        result = DataOperationStorage(connection).attach_data_requests(
            cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": snapshot["read_id"],
                    "items": [
                        {
                            "obligation_id": producer["obligation_id"],
                            "request_meaning": json.loads(request.identity.canonical_input),
                            "request_key": request.identity.key,
                            "replicate": None,
                            "binding": {
                                "inputs": [],
                                "support": [],
                                "parameters": semantic_value(request.parameters),
                                "request_inputs": semantic_value({}),
                                "inference": "inference:test",
                                "populations": [],
                                "read_id": snapshot["read_id"],
                            },
                        }
                    ],
                },
            )
        )["items"][0]
        assert result["state"] == "fulfilled", result
    evidence = parent["evidence"]
    for foreign_source, foreign_scope in (
        ("source:foreign", {"page": 1}),
        ("source:test", {"page": 2}),
    ):
        foreign_selection = freeze_demand(
            current.model,
            roots=(RootSubject("doc", foreign_source, canonical_bytes(foreign_scope)),),
            targets=("urn:consumer",),
            inference="inference:test",
            execution_profile="execution:test",
            discovery=(DiscoverySelection("urn:discover", "result", "urn:child", "all-items"),),
        ).record
        with engine.begin() as connection:
            foreign = DataOperationStorage(connection).register_data_demand(
                cast(
                    WireRegisterDataDemandRequest,
                    {
                        "project_id": project_id,
                        "release_id": current.prepared.release_id,
                        "runtime_id": current.runtime,
                        "root": foreign_selection["roots"],
                        "selection": foreign_selection,
                        "strength": "value",
                    },
                )
            )
        with (
            engine.begin() as connection,
            pytest.raises(DBAPIError, match="population lacks admitted declared discovery output"),
        ):
            DataOperationStorage(connection).close_data_population(
                cast(
                    WireCloseDataPopulationRequest,
                    {
                        "demand_id": foreign["demand_id"],
                        "name": "all-items",
                        "product_id": evidence["product_id"],
                        "derivation_id": evidence["derivation_id"],
                        "member_role": "result",
                    },
                )
            )
    with engine.begin() as connection:
        with pytest.raises(DBAPIError), connection.begin_nested():
            DataOperationStorage(connection).close_data_population(
                cast(
                    WireCloseDataPopulationRequest,
                    {
                        "demand_id": demand["demand_id"],
                        "name": "all-items",
                        "product_id": evidence["product_id"],
                        "derivation_id": evidence["derivation_id"],
                        "member_role": "foreign-role",
                    },
                )
            )
        population = DataOperationStorage(connection).close_data_population(
            cast(
                WireCloseDataPopulationRequest,
                {
                    "demand_id": demand["demand_id"],
                    "name": "all-items",
                    "product_id": evidence["product_id"],
                    "derivation_id": evidence["derivation_id"],
                    "member_role": "result",
                },
            )
        )
        assert len(population["members"]) == 3
        assert population["evidence"]["derivation_id"] == evidence["derivation_id"]
        assert population["evidence"]["admission_use_id"] != evidence["admission_use_id"]
        assert (
            connection.scalar(
                text("SELECT release_id FROM ops.data_derivation WHERE id=:id"),
                {"id": evidence["derivation_id"]},
            )
            == old.prepared.release_id
        )
    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.demand_results import read_demand_result, stream_selected_support

    with engine.begin() as connection:
        revoked = DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": project_id,
                    "original_source": "source:test",
                    "selector_kind": "derivation",
                    "selector": evidence["derivation_id"],
                    "reason": "independent discovery control",
                },
            )
        )
    with engine.begin() as connection:
        page = read_demand_result(connection, demand["demand_id"], project_id=project_id)
        explained = [
            row["record"]
            for row in stream_selected_support(connection, page)
            if row["relation"] == "ops.data_support_explanation"
        ]
        assert any(
            row["revocation_id"] == revoked["revocation_id"]
            and row["root_derivation_id"] == evidence["derivation_id"]
            and row["node_id"] == evidence["derivation_id"]
            and row["valid"] is False
            for row in explained
        )
    with engine.begin() as connection, pytest.raises(DBAPIError):
        DataOperationStorage(connection).close_data_population(
            cast(
                WireCloseDataPopulationRequest,
                {
                    "demand_id": demand["demand_id"],
                    "name": "all-items",
                    "product_id": evidence["product_id"],
                    "derivation_id": evidence["derivation_id"],
                    "member_role": "result",
                },
            )
        )


def test_candidate_edge_profile_changes_only_its_declared_traversal():
    from types import SimpleNamespace

    import yaml
    from sqlalchemy import literal

    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.support_edges import support_edge_queries

    base = get_metadata()
    sources = dict(base.info["physical_sources"])
    content = yaml.safe_load(sources["operation-vocabularies.yaml"])
    edge = content["enums"]["SupportEdgeKind"]["permissible_values"]["population-parent"][
        "annotations"
    ]["cs:edge"]["value"]
    edge["profiles"].remove("scope")
    sources["operation-vocabularies.yaml"] = yaml.safe_dump(content).encode()
    candidate = SimpleNamespace(tables=base.tables, info={**base.info, "physical_sources": sources})
    assert len(support_edge_queries(candidate, literal("population"), literal("p"), "scope")) == 6
    assert len(support_edge_queries(base, literal("population"), literal("p"), "scope")) == 7
    assert len(
        support_edge_queries(candidate, literal("population"), literal("p"), "validity")
    ) == len(support_edge_queries(base, literal("population"), literal("p"), "validity"))
    del edge["target"]
    sources["operation-vocabularies.yaml"] = yaml.safe_dump(content).encode()
    with pytest.raises(
        ValueError, match="support edge lacks its declared traversal: population-parent"
    ):
        support_edge_queries(candidate, literal("population"), literal("p"), "scope")


def test_native_witnesses_attribute_direct_and_selected_upstream_once():
    from types import SimpleNamespace

    from corpus_structure.semantic.change_impact import _native_revocation_causes

    rows = [
        dict(
            root_use_id="current",
            root_derivation_id="producer",
            node_kind=kind,
            node_id="producer",
            valid=False,
            revocation_id="revoked-producer",
            selector_kind="derivation",
            selector="producer",
            support_path=["use:current", kind + ":producer"],
        )
        for kind in ("episode", "producer")
    ]
    rows.append(
        dict(
            root_use_id="current",
            root_derivation_id="producer",
            node_kind="producer",
            node_id="replacement",
            valid=False,
            revocation_id="revoked-support",
            selector_kind="derivation",
            selector="replacement",
            support_path=["use:current", "producer:replacement"],
        )
    )
    rows.append(dict(rows[0], root_use_id="another", revocation_id="unselected"))
    index = SimpleNamespace(
        rows=lambda relation: rows if relation == "ops.data_support_explanation" else ()
    )
    causes = _native_revocation_causes(index, {"producer"}, ("current",))
    assert {(cause.kind, cause.selector, cause.reference) for cause in causes} == {
        ("direct", "producer", "revoked-producer"),
        ("upstream", "replacement", "revoked-support"),
    }
    assert len(causes) == 2
    assert all(cause.support_path[0] == "use:current" for cause in causes)


@pytest.mark.skipif(
    not os.environ.get("CORPUS_UDM_B_STAGE_OBSERVATION"),
    reason="explicit owned-stage observation is not selected",
)
def test_owned_stage_n31_discovery_and_impact(tmp_path, monkeypatch):
    from uuid import uuid4

    from corpus_structure.schema.model_deployment import deployment_settings
    from corpus_structure.semantic.data_operation_storage import native_source_digest
    from corpus_structure.semantic.migrations import current_revision
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import acquired_target
    from corpus_structure.settings import Settings

    assert os.environ["CORPUS_UDM_B_STAGE_OBSERVATION"] == "130661481"
    _, settings = deployment_settings(Settings(), "deployment")
    with open_runtime_engine(settings, "udm-b-stage-observation", purpose="maintenance") as engine:
        with engine.connect() as connection:
            target = acquired_target(connection, purpose="maintenance")
            assert target.database_oid == 130661481
            assert target.port == 5434
            assert current_revision(connection) == "semantic_ddo_pe_n31"
            installed = connection.scalar(
                text("SELECT sem.data_operation_native_descriptor()->>'source_digest'")
            )
            assert installed == native_source_digest(), (
                "stage and observation source require the same captured kernel"
            )
        project = "udm-b-stage-observation-" + uuid4().hex
        _cross_release_population(engine, None, tmp_path, monkeypatch, project_id=project)
