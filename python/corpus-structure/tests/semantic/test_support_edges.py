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


def test_changed_population_member_reuses_unchanged_child_results(
    semantic_bare_engine, fresh_target_epoch, tmp_path, monkeypatch
):
    from dataclasses import replace
    from typing import cast as type_cast

    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.data_operation_demands import DemandPlanner
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.data_operation_binding_support import discover
    from semantic.data_operation_kernel_support import POPULATION, admit_kernel, prepare_kernel
    from semantic.population_completion_support import complete_ready

    engine = semantic_bare_engine
    _, _, _, _, _, location = install_target_root(engine, fresh_target_epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    assert POPULATION.declaration_content is not None
    declaration = json.loads(POPULATION.declaration_content)
    for operation in declaration["operations"]:
        operation["validity_family"] = ["none"]
    child = next(
        operation for operation in declaration["operations"] if operation["id"] == "urn:child"
    )
    child["dependencies"] = ["urn:discover"]
    child["roles"].insert(
        0,
        dict(
            name="item",
            kind="Sample",
            direction="input",
            minimum=1,
            maximum=1,
            collection="scalar",
            presence="required",
            support=dict(
                provenance="value_substitution",
                source="same-original",
                coverage=dict(role="item", description="selected-scope"),
                identity_requirements=[],
            ),
        ),
    )
    child["binding"] = dict(operator="scan", roles=["item"])
    contexts = tuple(
        dict(subject="item:" + name, original_source="source:test", analyzed_scope={"page": 1})
        for name in ("a", "b", "c")
    )

    def prepare(name, project):
        recipe = replace(
            POPULATION, project_id=project, declaration_content=canonical_bytes(declaration)
        )
        preparation = prepare_kernel(recipe, directory=tmp_path / name)
        with engine.begin() as connection:
            return admit_kernel(connection, recipe, preparation=preparation)

    def children(kernel, demand):
        with engine.begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            snapshot = planner.resume(demand["demand_id"])
            producer = next(
                use
                for use in snapshot["uses"]
                if use["products"]
                and any(
                    row["obligation_id"] == use["obligation_id"]
                    and row["operation_id"] == "urn:discover"
                    for row in snapshot["obligations"]
                )
            )
        with engine.begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            planner.expand_discovery(
                snapshot,
                population="all-items",
                product=producer["products"][0]["product_id"],
                derivation=type_cast(str, producer["derivation_id"]),
            )
            snapshot = planner.resume(demand["demand_id"])
        with engine.begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            ready = planner.ready(snapshot, authorization=b"{}")
        return tuple(row for row in ready if row.operation == "urn:child")

    old = prepare("original-members", "ddo-test")
    first, _, old_population = discover(
        old,
        values=(5, 15, 25),
        member_contexts=contexts,
        member_ids=("a", "b", "c"),
        child_input_role="item",
    )
    original_children = children(old, first)
    assert {row.subject for row in original_children} == {"item:a", "item:b", "item:c"}
    original = {
        row.subject: complete_ready(old, row, value=value)
        for row, value in zip(
            sorted(original_children, key=lambda row: row.subject), (5, 15, 25), strict=True
        )
    }
    next(operation for operation in declaration["operations"] if operation["id"] == "urn:discover")[
        "behavior"
    ] = "changed-discovery-members-v2"
    current = prepare("changed-members", None)
    assert current.identities["urn:child", "recipe"] == old.identities["urn:child", "recipe"]
    second, _, current_population = discover(
        current,
        values=(5, 16, 25),
        member_contexts=contexts,
        member_ids=("a", "b", "c"),
        child_input_role="item",
    )
    replacement = children(current, second)
    original_requests = {row.subject: json.loads(row.request) for row in original_children}
    for row in replacement:
        if row.subject != "item:b":
            assert json.loads(row.request) == original_requests[row.subject]
    assert [row.subject for row in replacement] == ["item:b"]
    changed = complete_ready(current, replacement[0], value=16)
    with engine.begin() as connection:
        snapshot = DemandPlanner(current.model, DataOperationStorage(connection)).resume(
            second["demand_id"]
        )
        child_obligations = {
            row["obligation_id"]: row["subject"]
            for row in snapshot["obligations"]
            if row["operation_id"] == "urn:child"
        }
        used = {
            child_obligations[row["obligation_id"]]: row["derivation_id"]
            for row in snapshot["uses"]
            if row["obligation_id"] in child_obligations and row["fate"] == "fulfilled"
        }
    assert used == {
        "item:a": original["item:a"]["derivation_id"],
        "item:b": changed["derivation_id"],
        "item:c": original["item:c"]["derivation_id"],
    }
    assert changed["derivation_id"] != original["item:b"]["derivation_id"]
    with engine.begin() as connection:
        planner = DemandPlanner(current.model, DataOperationStorage(connection))
        ready = planner.ready(snapshot, authorization=b"{}")
    aggregate = [row for row in ready if row.operation == "urn:consumer"]
    assert len(aggregate) == 1
    assert [
        member.member for role in aggregate[0].binding_result.roles for member in role.members
    ] == ["b"]
    aggregate_receipt = complete_ready(current, aggregate[0], value=16)
    with engine.connect() as connection:
        observed = connection.scalar(
            text(
                "SELECT data.ddo_json(product.canonical_body) "
                "FROM kb.data_product product JOIN ops.data_derivation_output output "
                "ON output.product_id=product.id WHERE output.derivation_id=:episode "
                "AND output.role='result' AND output.member_id IS NULL"
            ),
            {"episode": aggregate_receipt["derivation_id"]},
        )
    assert observed == 16
    _assert_selected_substitution_scope(
        engine, second, original["item:a"]["derivation_id"], old_population, current_population
    )


def _assert_selected_substitution_scope(
    engine, demand, old_child, old_population, current_population
):
    from typing import cast as type_cast

    from sqlalchemy import literal, select

    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.data_operation_projections import _support_walk
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.metadata import get_metadata

    with engine.begin() as connection:
        snapshot = DataOperationStorage(connection).read_demand_result(
            {"demand_id": demand["demand_id"]}
        )
    obligation = next(
        row
        for row in snapshot["obligations"]
        if row["operation_id"] == "urn:child" and row["subject"] == "item:a"
    )
    chosen = next(
        row
        for row in snapshot["uses"]
        if row["obligation_id"] == obligation["obligation_id"] and row["fate"] == "fulfilled"
    )
    assert chosen["derivation_id"] == old_child
    old_evidence, current_evidence = old_population["evidence"], current_population["evidence"]
    expected = {
        ("use", chosen["use_id"]),
        ("episode", old_child),
        ("use", old_evidence["admission_use_id"]),
        ("episode", old_evidence["derivation_id"]),
        ("use", current_evidence["admission_use_id"]),
        ("episode", current_evidence["derivation_id"]),
        ("population", current_population["population_id"]),
    }
    seed = select(literal("use").label("kind"), literal(chosen["use_id"]).label("id")).cte(
        "selected_scope_seed"
    )
    scope = _support_walk(get_metadata(), seed, name="selected_scope_nodes")
    with engine.begin() as connection:
        assert set(connection.execute(select(scope))) == expected
        with connection.begin_nested() as current_revocation:
            DataOperationStorage(connection).revoke_data_support(
                type_cast(
                    WireRevokeDataSupportRequest,
                    dict(
                        project_id="ddo-test",
                        original_source="source:test",
                        selector_kind="derivation",
                        selector=current_evidence["derivation_id"],
                        reason="withdraw current support while producing support still stands",
                    ),
                )
            )
            assert connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"), {"episode": old_child}
            ) is True
            assert connection.scalar(
                text("SELECT ops.ddo_node_valid('use',:use)"), {"use": chosen["use_id"]}
            ) is False
            current_revocation.rollback()
        DataOperationStorage(connection).revoke_data_support(
            type_cast(
                WireRevokeDataSupportRequest,
                dict(
                    project_id="ddo-test",
                    original_source="source:test",
                    selector_kind="derivation",
                    selector=old_evidence["derivation_id"],
                    reason="withdraw historical producer after authentic member substitution",
                ),
            )
        )
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"), {"episode": old_child}
            )
            is False
        )
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('use',:use)"), {"use": chosen["use_id"]}
            )
            is True
        )
        assert set(connection.execute(select(scope))) == expected


def _cross_release_population(engine, location, tmp_path, monkeypatch, *, project_id="ddo-test"):
    from dataclasses import replace
    from typing import cast

    from corpus_structure.semantic import migrations
    from corpus_structure.semantic._data_operation_wire import (
        WireAttachDataRequestsRequest,
        WireCloseDataPopulationRequest,
        WireRegisterDataDemandRequest,
    )
    from corpus_structure.semantic.data_operation_identity import SemanticRequestKey
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.data_operation_values import semantic_value
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
    _assert_population_traversal(engine, current, demand, population)
    _changed_discovery_recipe_refuses_old_population(
        engine, current, evidence, project_id, tmp_path
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


def _assert_population_traversal(engine, current, demand, parent):
    from types import SimpleNamespace
    from typing import cast as type_cast

    import yaml
    from sqlalchemy import Text, cast, false, literal, literal_column, select, true, union_all
    from sqlalchemy.dialects.postgresql import JSONB

    from corpus_structure.semantic._data_operation_wire import WireSelectDataPopulationRequest
    from corpus_structure.semantic.data_operation_projections import _scope_projection
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.support_edges import support_edge_queries

    with engine.begin() as connection:
        storage = DataOperationStorage(connection)
        snapshot = storage.read_demand_result({"demand_id": demand["demand_id"]})
        consumer = next(
            row for row in snapshot["obligations"] if row["operation_id"] == "urn:consumer"
        )
    with engine.begin() as connection:
        selected = DataOperationStorage(connection).select_data_population(
            type_cast(
                WireSelectDataPopulationRequest,
                dict(
                    obligation_id=consumer["obligation_id"],
                    population_name="selected-items",
                    parent_population_id=parent["population_id"],
                    read_id=snapshot["read_id"],
                ),
            )
        )
    metadata = get_metadata()
    root = selected["population_id"]
    producer_use = parent["evidence"]["admission_use_id"]
    episode = parent["evidence"]["derivation_id"]
    expected = {
        ("population", root),
        ("population", parent["population_id"]),
        ("use", producer_use),
        ("episode", episode),
    }

    def walk(model, profile):
        closure = select(literal("population").label("kind"), literal(root).label("id")).cte(
            "fixture_nodes", recursive=True
        )
        edges = union_all(
            *(
                query.correlate(closure)
                for query in support_edge_queries(
                    model,
                    closure.c.kind,
                    closure.c.id,
                    profile,
                    authority=lambda identity: false(),
                    boundary=literal_column("NULL::ops.data_demand_read"),
                    product_ids=cast(literal("[]"), JSONB()),
                )
            )
        ).lateral("fixture_edges")
        return closure.union(
            select(edges.c.child_kind, edges.c.child_id)
            .select_from(closure.join(edges, true()))
            .where(edges.c.child_id.is_not(None))
        )

    with engine.connect() as connection:
        for profile in ("scope", "public"):
            assert set(connection.execute(select(walk(metadata, profile)))) == expected
        validity = connection.execute(
            text(
                "SELECT kind,id,valid FROM ops.ddo_valid_closure('{}'::text[], '{}'::text[], "
                "NULL::ops.data_demand_read, ARRAY[:population]::text[])"
            ),
            {"population": root},
        ).all()
        assert {(kind, identity) for kind, identity, _ in validity} == expected | {
            ("producer", episode)
        }
        assert all(valid for _, _, valid in validity)
        nodes = walk(metadata, "scope")
        scopes = _scope_projection(
            metadata,
            nodes,
            literal(snapshot["project_id"]),
            select(cast(literal(None), Text()).label("source")).where(false()),
            domain_dependencies=False,
        )
        expected_scope = connection.scalar(
            text("SELECT ops.ddo_scope(:project,'source:test')"),
            {"project": snapshot["project_id"]},
        )
        assert set(connection.scalars(scopes)) == {expected_scope}

        sources = dict(metadata.info["physical_sources"])
        document = yaml.safe_load(sources["operation-vocabularies.yaml"])
        document["enums"]["SupportEdgeKind"]["permissible_values"]["population-parent"][
            "annotations"
        ]["cs:edge"]["value"]["profiles"].remove("scope")
        sources["operation-vocabularies.yaml"] = yaml.safe_dump(document).encode()
        candidate = SimpleNamespace(
            tables=metadata.tables, info={**metadata.info, "physical_sources": sources}
        )
        assert set(connection.execute(select(walk(candidate, "scope")))) == expected - {
            ("population", parent["population_id"])
        }
        assert set(connection.execute(select(walk(candidate, "public")))) == expected


def _changed_discovery_recipe_refuses_old_population(
    engine, current, evidence, project_id, tmp_path
):
    from dataclasses import replace
    from typing import cast

    from corpus_structure.semantic._data_operation_wire import (
        WireCloseDataPopulationRequest,
        WireRegisterDataDemandRequest,
    )
    from corpus_structure.semantic.data_operation_demands import (
        DemandPlanner,
        DiscoverySelection,
        RootSubject,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.data_operation_kernel_support import POPULATION, admit_kernel, prepare_kernel

    assert POPULATION.declaration_content is not None
    declaration = json.loads(POPULATION.declaration_content)
    producer = next(row for row in declaration["operations"] if row["id"] == "urn:discover")
    producer["behavior"] = "changed-native-discovery-v2"
    recipe = replace(POPULATION, project_id=None, declaration_content=canonical_bytes(declaration))
    preparation = prepare_kernel(recipe, directory=tmp_path / "changed-discovery-recipe")
    with engine.begin() as connection:
        changed = admit_kernel(connection, recipe, preparation=preparation)
    assert (
        changed.identities["urn:discover", "recipe"] != current.identities["urn:discover", "recipe"]
    )
    selection = freeze_demand(
        changed.model,
        roots=(RootSubject("doc", "source:test", canonical_bytes({"page": 1})),),
        targets=("urn:consumer",),
        inference="inference:test",
        execution_profile="execution:test",
        discovery=(DiscoverySelection("urn:discover", "result", "urn:child", "all-items"),),
    ).record
    with engine.begin() as connection:
        storage = DataOperationStorage(connection)
        registered = storage.register_data_demand(
            cast(
                WireRegisterDataDemandRequest,
                dict(
                    project_id=project_id,
                    release_id=changed.prepared.release_id,
                    runtime_id=changed.runtime,
                    root=selection["roots"],
                    selection=selection,
                    strength="value",
                ),
            )
        )
    with engine.begin() as connection:
        planner = DemandPlanner(changed.model, DataOperationStorage(connection))
        snapshot = planner.resume(registered["demand_id"])
    with engine.begin() as connection:
        planner = DemandPlanner(changed.model, DataOperationStorage(connection))
        ready = planner.ready(snapshot, authorization=b"{}")
        assert len(ready) == 1 and ready[0].operation == "urn:discover"
        assert json.loads(ready[0].native)["action"] == "compute"
    with (
        engine.begin() as connection,
        pytest.raises(DBAPIError, match="population lacks admitted declared discovery output"),
    ):
        DataOperationStorage(connection).close_data_population(
            cast(
                WireCloseDataPopulationRequest,
                dict(
                    demand_id=registered["demand_id"],
                    name="all-items",
                    product_id=evidence["product_id"],
                    derivation_id=evidence["derivation_id"],
                    member_role="result",
                ),
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
    os.environ.get("CORPUS_UDM_TRANSITION_OBSERVATION") != "130661481",
    reason="explicit owned-stage observation is not selected",
)
def test_owned_stage_transition_discovery_and_impact(tmp_path, monkeypatch):
    from uuid import uuid4

    from corpus_structure.schema.model_deployment import deployment_settings
    from corpus_structure.semantic.migrations import current_revision, head_revision
    from corpus_structure.semantic.native_protocol_authoring import native_source_digest
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import acquired_target
    from corpus_structure.settings import Settings

    assert os.environ["CORPUS_UDM_TRANSITION_OBSERVATION"] == "130661481"
    _, settings = deployment_settings(Settings(), "deployment")
    with open_runtime_engine(
        settings, "udm-transition-stage-observation", purpose="maintenance"
    ) as engine:
        with engine.connect() as connection:
            target = acquired_target(connection, purpose="maintenance")
            assert target.database_oid == 130661481
            assert target.port == 5434
            assert current_revision(connection) == head_revision()
            installed = connection.scalar(
                text("SELECT sem.data_operation_native_descriptor()->>'source_digest'")
            )
            assert installed == native_source_digest(), (
                "stage and observation source require the same captured kernel"
            )
        project = "udm-transition-stage-observation-" + uuid4().hex
        _cross_release_population(engine, None, tmp_path, monkeypatch, project_id=project)
