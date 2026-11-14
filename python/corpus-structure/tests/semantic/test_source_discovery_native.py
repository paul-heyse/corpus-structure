"""Actual selected-source producer publication, governed closure and native children."""

import json
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
from corpus_structure.semantic import SourceArtifact, SourceBundle
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    DiscoverySelection,
    OperationSelection,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_identity import (
    SemanticRequestKey,
    decode_semantic_value,
    semantic_value,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    native_operation_declarations,
    native_protocol_sources,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.original_documents import acquire_original_document_selection
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.source_admission import acquire_original_source_selection
from corpus_structure.semantic.source_discovery import (
    source_discovery_inputs,
    source_discovery_operation_sources,
)
from corpus_structure.semantic.source_profiles import (
    source_profile_inputs,
    source_profile_operation_sources,
)
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.native_record_fixtures import RecordSourceRecipe, claim_record_source
from semantic.original_source_fixture import completed_original_source_reference


@cache
def _source_recipe():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_profile_inputs(
        source_discovery_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    sources = combine_primary_sources(
        source_discovery_operation_sources(), source_profile_operation_sources()
    )
    native = native_protocol_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*native, *capture_port_generator_sources())),
        (native_operation_declarations(native),),
        sources,
    )
    recipe = KernelRecipe(
        "actual-source-discovery",
        "",
        None,
        "",
        source_stage="private-source",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )
    return recipe, sources


@pytest.mark.parametrize(
    "ddo_original_source",
    [OriginalSeedRecipe(RecordSourceRecipe(), _source_recipe()[0])],
    indirect=True,
    ids=["actual-source-discovery"],
)
@pytest.mark.parametrize(
    "complete,views",
    [(True, False), (False, False), (True, True)],
    ids=["closed-empty", "partial-empty", "closed-two-scopes"],
)
def test_actual_source_discovery_closure_and_scoped_child_publication(
    ddo_original_source, complete, views
):
    case = ddo_original_source
    retained = claim_record_source(case.source, writer=case.writer, clone=case.clone)
    reference, selectors = completed_original_source_reference(retained)
    kernel = case.kernel
    prepared, model = kernel.prepared, kernel.model
    with case.admin.begin() as connection:
        first = acquire_original_source_selection(
            connection, prepared, reference, selectors, name="first"
        )
        original = acquire_original_document_selection(
            connection,
            project_id=retained.project_id,
            document_key=first.source.value["source"]["document"],
        )
        acquisitions = []
        length = len(first.source.value["text"])
        if views:
            assert length >= 2
            projection = reference.projection_digest
            acquisitions = [
                acquire_original_source_selection(
                    connection,
                    prepared,
                    reference,
                    [{"projection": projection, "start": start, "end": end}],
                    name="view:" + str(index),
                )
                for index, (start, end) in enumerate(((0, length // 2), (length // 2, length)))
            ]
            assert acquisitions[0].root.subject == acquisitions[1].root.subject
            assert acquisitions[0].root.analyzed_scope != acquisitions[1].root.analyzed_scope
        intent = freeze_demand(
            model,
            roots=(original.root,),
            targets=("source.selected_views/discovery",),
            selections=(
                OperationSelection(
                    "source.selected_views/discovery",
                    parameters=canonical_bytes({"complete": complete}),
                ),
            ),
            discovery=(
                DiscoverySelection(
                    "source.selected_views/discovery",
                    "result",
                    "profile.segments/source-native",
                    "selected-source-views",
                    target_role="source",
                ),
            ),
            inference="source-discovery-control",
            execution_profile=_source_recipe()[0].execution_profile,
            original_sources=(
                original.selection(),
                *(acquired.selection() for acquired in acquisitions),
            ),
        )
        planner = DemandPlanner(model, DataOperationStorage(connection))
        invalid = intent.record
        invalid["discovery"][0]["target_role"] = "not-an-input"
        with pytest.raises(DBAPIError, match="discovery target role"), connection.begin_nested():
            planner.register(
                replace(intent, content=canonical_bytes(invalid)),
                project=retained.project_id,
                release=prepared.release_id,
                runtime=kernel.runtime,
            )
        demand = planner.register(
            intent, project=retained.project_id, release=prepared.release_id, runtime=kernel.runtime
        )["demand_id"]
    executor = NativeDemandExecutor(
        kernel.purpose("write"),
        prepared,
        kernel.preparation.runtime,
        _source_recipe()[1],
        schema=kernel.preparation.bundle,
        admission_engine=kernel.purpose("admit"),
    )
    executor.run(demand)
    assert executor.budget.used_bytes == 0
    with case.admin.begin() as connection:
        storage = DataOperationStorage(connection)
        snapshot = storage.invoke("read_demand_result", {"demand_id": demand, "view": "products"})
        obligations = [
            row
            for row in snapshot["obligations"]
            if row["operation_id"] == "profile.segments/source-native"
        ]
        assert len(obligations) == (2 if views else 0)
        population = (
            connection.execute(
                text(
                    "SELECT id,complete,members,evidence FROM ops.data_population WHERE demand_id=:demand"
                ),
                {"demand": demand},
            )
            .mappings()
            .one()
        )
        assert population["complete"] is complete
        assert len(population["members"]) == (2 if views else 0)
        if views:
            assert {row["subject"] for row in population["members"]} == {
                acquisitions[0].root.subject
            }
            assert {canonical_bytes(row["analyzed_scope"]) for row in population["members"]} == {
                acquired.root.analyzed_scope for acquired in acquisitions
            }
            child_uses = [
                use
                for use in snapshot["uses"]
                if use["obligation_id"] in {row["obligation_id"] for row in obligations}
            ]
            assert len(child_uses) == 2 and all(use["fate"] == "fulfilled" for use in child_uses), [
                (use["fate"], use["selection"].get("reasons")) for use in child_uses
            ]
            bodies = [
                decode_semantic_value(product["body"])
                for use in child_uses
                for product in use["products"]
            ]
            assert sorted(body["chars"] for body in bodies) == sorted(
                end - start for start, end in ((0, length // 2), (length // 2, length))
            )
            for use in child_uses:
                selected_input = connection.execute(
                    text(
                        "SELECT product_id,member_id FROM ops.data_derivation_input WHERE derivation_id=:episode"
                    ),
                    {"episode": use["derivation_id"]},
                ).one()
                assert selected_input.product_id == population["evidence"]["product_id"]
                assert selected_input.member_id in {
                    member["member_id"] for member in population["members"]
                }
            _refuse_same_context_original(connection, storage, snapshot, child_uses[0], population)
    assert executor.run(demand).receipt_count == 0


def _refuse_same_context_original(connection, storage, snapshot, use, population):
    request = (
        connection.execute(
            text("SELECT * FROM ops.data_request WHERE id=:request"), {"request": use["request_id"]}
        )
        .mappings()
        .one()
    )
    original = (
        connection.execute(
            text(
                "SELECT * FROM ops.data_binding_rows(:demand,:operation,CAST(:trust AS jsonb),:read,:subject,:source,CAST(:scope AS jsonb)) WHERE member IS NULL"
            ),
            {
                "demand": snapshot["demand_id"],
                "operation": request["operation_id"],
                "trust": json.dumps(snapshot["trust_snapshot"]),
                "read": snapshot["read_id"],
                "subject": request["subject"],
                "source": request["original_source"],
                "scope": json.dumps(request["analyzed_scope"]),
            },
        )
        .mappings()
        .one()
    )
    assert original["product"] != population["evidence"]["product_id"]
    assert (
        original["subject"] == request["subject"]
        and original["analyzed_scope"] == request["analyzed_scope"]
    )
    binding = json.loads(json.dumps(request["binding"]))
    binding.pop("execution_profile", None)
    binding["read_id"] = snapshot["read_id"]
    inputs = decode_semantic_value(binding["request_inputs"])
    present = inputs["source"]["value"]
    inputs["source"]["value"] = replace(
        present, value=[{**present.value[0], "product": original["product"], "member": None}]
    )
    binding["request_inputs"] = semantic_value(inputs)
    binding["inputs"] = [
        {
            "role": "source",
            "position": original["position"],
            "multiplicity": original["multiplicity"],
            "product_id": original["product"],
            "member_id": None,
        }
    ]
    binding["support"] = [item for item in binding["support"] if item["role"] != "source"] + [
        {**reference, "role": "source", "position": original["position"]}
        for reference in original["support_references"]
    ]
    key = SemanticRequestKey(
        request["recipe"],
        request["subject"],
        inputs,
        decode_semantic_value(binding["parameters"]),
        binding["inference"],
        subject_context=SubjectContext(
            request["project_id"],
            request["subject"],
            request["original_source"],
            canonical_bytes(request["analyzed_scope"]),
        ),
    )
    with (
        pytest.raises(
            DBAPIError,
            match="discovery input differs from exact selected parent/member/context support",
        ),
        connection.begin_nested(),
    ):
        storage.invoke(
            "attach_data_request",
            {
                "obligation_id": use["obligation_id"],
                "request_meaning": json.loads(key.identity.canonical_input),
                "request_key": key.identity.key,
                "binding": binding,
                "replicate": request["replicate"],
            },
        )
