"""Original facts enter through authentic published custody, never inference episodes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_admission import (
    admit_data_operation_release,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner, freeze_demand
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_preparation import prepare_data_operation_inputs
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from corpus_structure.semantic.source_admission import acquire_original_source_selection

from .native_record_fixtures import private_source as private_source
from .native_record_fixtures import private_source_options as private_source_options
from .original_source_fixture import completed_original_source_reference
from .test_data_operation_storage import _declaration


@pytest.fixture
def original_target(tmp_path):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    (tmp_path / "core.yaml").write_bytes(core.read_bytes())
    (tmp_path / "schema.yaml").write_text("""id: urn:original-fact-test
name: target
imports: [core]
prefixes: {t: 'urn:original-fact-test:'}
default_prefix: t
classes: {Marker: {}}
""")
    operation = _declaration()
    operation.update(id="urn:original-fact-test:consume", behavior="source-value-consumer-v1")
    operation["roles"][0].update(maximum=1, collection="scalar")
    operation["roles"].insert(
        0,
        {
            "name": "source",
            "kind": "DdoSelectedNativeSource",
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "required",
            "support": {
                "provenance": "value_substitution",
                "source": "same-original",
                "coverage": "selected-scope",
                "identity_requirements": [],
                "origins": ["original-source"],
            },
        },
    )
    (tmp_path / "operations.yaml").write_bytes(
        canonical_bytes(
            {
                "version": "data-operation-model-v1",
                "operations": [operation],
            }
        )
    )
    (tmp_path / "target.yaml").write_text("""version: data-operation-inputs-v1
root: target
schemas: [{name: target, path: schema.yaml}, {name: core, path: core.yaml}]
declarations: [{name: operations, path: operations.yaml}]
source_bindings: true
""")
    return prepare_data_operation_inputs(tmp_path, "target.yaml")


def test_original_fact_target_has_explicit_value_based_origin_policy(original_target):
    model = bound_data_operation_model(original_target[3])
    operation = next(
        op for op in model.operations if op.semantic_id == "urn:original-fact-test:consume"
    )
    role = next(role for role in operation.roles if role.direction == "input")
    assert role.support is not None
    assert role.support.origins == ("original-source",)
    assert role.support.identity_requirements == ()


def test_authentic_original_fact_admission_publication_and_revocation(
    private_source, original_target, semantic_db_engine
):
    reference, selectors = completed_original_source_reference(private_source)
    bundle, dependencies, profile, prepared = original_target
    model = bound_data_operation_model(prepared)
    runtime = prepare_data_operation_runtime(
        prepared, dependencies.artifacts, execution_profile="execution:original-fact", observed={}
    )
    with semantic_db_engine.begin() as connection:
        persist_release(connection, bundle, dependencies, profile, prepared)
        admit_data_operation_release(connection, prepared)
        persist_runtime_binding(connection, prepared, runtime)
        acquired = acquire_original_source_selection(connection, prepared, reference, selectors)
        intent = freeze_demand(
            model,
            roots=(acquired.root,),
            targets=("urn:original-fact-test:consume",),
            inference="inference:original-value",
            execution_profile="execution:original-fact",
            original_sources=(acquired.selection(),),
        )
        storage = DataOperationStorage(connection)
        demand = DemandPlanner(model, storage).register(
            intent,
            project=private_source.project_id,
            release=prepared.release_id,
            runtime=runtime.runtime_id,
        )
        snapshot = storage.invoke("read_demand_result", demand)
        admissions = snapshot["original_source_admissions"]
        assert len(admissions) == 1
        admission = admissions[0]
        assert admission["original_source"] == acquired.root.original_source
        assert admission["evidence"]["document_content_hash"] == acquired.original_content_hash
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
        assert connection.scalar(text("SELECT count(*) FROM ops.data_request")) == 0
        # Repeated authenticated admission neither invents an episode nor a new value.
        repeated = storage.invoke(
            "admit_original_source_view",
            {
                "demand_id": demand["demand_id"],
                "selection_name": acquired.name,
                **acquired.selection().record(),
            },
        )
        assert repeated["admission_id"] == admission["admission_id"]
        assert repeated["product_id"] == admission["product_id"]
        selected = DemandPlanner(model, storage).ready(snapshot, authorization=b"{}")
        assert len(selected) == 1
        ready = selected[0]
        binding = json.loads(ready.binding)
        assert binding["support"] == [
            {
                "kind": "original-source",
                "admission_id": admission["admission_id"],
                "source_reference": admission["source_reference"],
                "role": "source",
                "position": 0,
            }
        ]
        assert "support_derivation_id" not in binding["inputs"][0]
        assert ready.resolved.roles[0].members[0].support_episodes == ()
        # An identical subject/source with a different selector scope cannot see this fact.
        wrong_scope = connection.execute(
            text(
                "SELECT count(*) FROM ops.data_binding_rows(:demand,:operation,"
                "CAST(:trust AS jsonb),:read,:subject,:source,CAST(:scope AS jsonb))"
            ),
            {
                "demand": demand["demand_id"],
                "operation": ready.operation,
                "trust": json.dumps(snapshot["trust_snapshot"]),
                "read": snapshot["read_id"],
                "subject": acquired.root.subject,
                "source": acquired.root.original_source,
                "scope": json.dumps({"source": acquired.source.value["source"], "selectors": []}),
            },
        ).scalar_one()
        assert wrong_scope == 0
        native = json.loads(ready.native)
        claimed = storage.invoke(
            "claim_data_request",
            {
                "request_id": native["request_id"],
                "holder": "original-test",
                "lease_seconds": 30,
            },
        )
        fence = {
            key: claimed[key]
            for key in ("request_id", "generation", "task_id", "attempt", "holder")
        }
        output_kind = next(
            role.kind
            for op in model.operations
            if op.semantic_id == ready.operation
            for role in op.roles
            if role.direction == "output"
        )
        kind = next(
            item.key
            for item in model.identities
            if item.owner == output_kind and item.domain == "kind"
        )
        retained = storage.invoke(
            "retain_data_completion_intent",
            {
                **fence,
                "runtime_id": runtime.runtime_id,
                "completion": {
                    "outcome": "success",
                    "inputs": binding["inputs"],
                    "support": binding["support"],
                    "implementation_revision": "source-value-consumer-v1",
                    "outputs": [
                        {
                            "role": "result",
                            "position": 0,
                            "multiplicity": 1,
                            "product": {
                                "kind_contract": kind,
                                "body": semantic_value(7),
                                "members": [],
                            },
                        }
                    ],
                },
            },
        )
        published = storage.invoke(
            "publish_data_derivation",
            {
                **fence,
                "intent_id": retained["intent_id"],
            },
        )
        assert published["derivation_id"]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation_support")) == 0
        assert (
            connection.scalar(text("SELECT count(*) FROM ops.data_derivation_original_support"))
            == 1
        )
        storage.invoke(
            "revoke_data_support",
            {
                "project_id": private_source.project_id,
                "original_source": acquired.root.original_source,
                "selector_kind": "original-admission",
                "selector": admission["admission_id"],
                "reason": "original source trust withdrawn",
            },
        )
        current = storage.invoke("read_demand_result", demand)
        assert current["original_source_admissions"] == []
        assert current["uses"][0]["fate"] == "unavailable"
        # Committed content and truthful lineage remain historically readable.
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.original_source_admission")) == 1
        with connection.begin_nested() as savepoint:
            with pytest.raises(DBAPIError, match="revoked"):
                storage.invoke(
                    "admit_original_source_view",
                    {
                        "demand_id": demand["demand_id"],
                        "selection_name": acquired.name,
                        **acquired.selection().record(),
                    },
                )
            savepoint.rollback()
