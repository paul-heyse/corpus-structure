"""Captured document fan-in over independently published native source members."""

import json
from dataclasses import replace
from hashlib import sha256
from typing import cast

import pytest

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection, pm2_selection
from corpus_structure.semantic._data_operation_wire import WireReasonSelection
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    OperationSelection,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_service import (
    DemandOperationSelection,
    execute_data_demand,
)
from corpus_structure.semantic.data_operation_source_discovery import source_discovery_relations
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.original_documents import acquire_original_document_selection
from corpus_structure.semantic.primary_operations import primary_operation_inputs
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.current_pdf_source_support import (
    PROJECT,
    ROOT,
    admit_current_target,
    current_pdf_recipe,
    section_content,
)
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, split_captured_operations


@pytest.mark.parametrize("captured", (False, True))
def test_composition_closes_its_coordinate_ordering_dependency(captured):
    from corpus_structure.semantic.characterization_ports import (
        captured_document_view_operation_sources,
        full_document_view_operation_sources,
    )
    from corpus_structure.semantic.python_operation_sources import ClosedPythonSources

    source_factory = (
        captured_document_view_operation_sources
        if captured
        else full_document_view_operation_sources
    )
    sources = source_factory(include_dependencies=False)
    assert any(
        source.module == "corpus_structure.semantic.enriched_document_products"
        for source in sources.sources
    )
    (composition,) = (
        operation
        for operation in ClosedPythonSources(sources).operations()
        if json.loads(operation.metadata).get("id")
        == (
            "text.compose_view/captured-full-native"
            if captured
            else "text.compose_view/full-native"
        )
    )
    assert composition.implementation.complete, composition.implementation.unknowns
    assert all(
        role["collection"] == "set"
        for role in json.loads(composition.metadata)["roles"]
        if role["direction"] == "input"
    )
    assert any(
        boundary.reference
        == "corpus_structure.semantic.enriched_document_products.ordered_composition_inputs"
        and boundary.contract == "characterization/view-assets"
        for boundary in composition.implementation.boundaries
    )


@pytest.mark.parametrize("captured", (False, True))
def test_composition_presents_sets_by_source_coordinate(captured, monkeypatch):
    from corpus_structure.methods import full_document_composition
    from corpus_structure.methods.captured_document_composition import ComposeCapturedDocumentFamily
    from corpus_structure.semantic.enriched_document_products import RetainedCharacterizationProduct
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.native_source_view import thaw_native
    from corpus_structure.semantic.source_products import FrozenNativeSource
    from semantic.formal_products_support import publication_context, released_profile, selected

    profile = released_profile()
    original = selected(profile, "Literal composition ordering control.")

    def region(section):
        body = thaw_native(original.value)
        body["source"]["section_pointer"] = section
        return FrozenNativeSource.acquire(profile.prepared, body)

    first, second = region("#/groups/a"), region("#/groups/b")

    def manifest(source, outcome):
        return RetainedCharacterizationProduct.acquire(
            profile.prepared,
            profile.model,
            profile.prepared.index.definitions["DdoFormalManifest"].iri,
            canonical_bytes(dict(
                record_type="manifest", source=source.value["source"],
                selectors=source.value["selectors"], coverage=[], outcome=outcome,
            )),
            subject_context=publication_context(source),
        )

    left, right = manifest(first, "complete"), manifest(first, "partial")
    assert left.semantic_id != right.semantic_id
    early, late = (left, right) if left.semantic_id < right.semantic_id else (right, left)
    last = manifest(second, "complete")
    observed = []

    def execute(receiver, sources, products, active, profile):
        observed.append((sources, products, active, profile))

    monkeypatch.setattr(full_document_composition, "execute_view_profile", execute)
    owner = (
        ComposeCapturedDocumentFamily
        if captured
        else full_document_composition.ComposeFullDocumentOperation
    )
    object.__new__(owner).run((second, first), (last, late, early), (), (), (), (), (), ())
    assert observed == [
        ((first, second), (early, late, last), (early, late, last), "full_characterization")
    ]


def captured_recipe(directory):
    directory.mkdir(parents=True, exist_ok=True)
    asset = directory / "controlled-spacy-model.bin"
    asset.write_bytes(b"controlled composition preparation, no provider execution")
    recipe = current_pdf_recipe(directory)
    captured = recipe.captured_inputs
    assert captured is not None
    remaining, _, sources = split_captured_operations(captured)
    capture_custody = next(
        artifact
        for artifact in remaining.artifacts
        if artifact.name == "runtime-transport/pdf-capture/execution-custody"
    )
    core = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
    sentence_configuration = SentenceConfig(exclude=("ner",))
    inputs = primary_operation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)),
        dependencies=replace(remaining, artifacts=(capture_custody,)),
        capture_sources=sources,
        sentence_configuration=sentence_configuration,
        sentence_selection=NativeSelection(
            NativeProfile(
                "spacy",
                {"controlled": "preparation"},
                {"files": {asset.name: sha256(asset.read_bytes()).hexdigest()}},
                sentence_configuration.model_dump(mode="json"),
                "float32",
                "cupy",
                4,
                1,
            ),
            directory,
        ),
        hanlp_selection=pm2_selection("hanlp", directory, {"controlled": "preparation"}, {}),
        visual=True,
    )
    return replace(
        recipe,
        name="captured-two-region-fan-in",
        captured_inputs=CapturedKernelInputs(inputs.bundle, inputs.dependencies, inputs.profile),
    )


def test_two_native_source_members_do_not_invent_composition_sequence_positions(
    current_pdf_source_factory,
    tmp_path,
):
    from pdf_controlled_support import controlled_pdf_converter

    from corpus_structure.orchestrate.source_operation import _default_profile_selections
    from corpus_structure.semantic.data_operation_bindings import inspect_binding_scopes
    from corpus_structure.semantic.data_operation_service import read_data_demand
    from corpus_structure.semantic.data_operation_values import decode_semantic_value

    target = "text.compose_view/captured-full-native"
    producer = "source.pdf_views/discovery"
    rows = (
        ("text", "First region.", "First region.", None),
        ("text", "Second region.", "Second region.", None),
    )
    with current_pdf_source_factory(rows) as source:
        kernel = admit_current_target(
            source, captured_recipe(tmp_path / "recipe"), tmp_path / "consumer"
        )
        inputs = [
            role for role in kernel.model.operation(target).roles if role.direction == "input"
        ]
        family_roles = {
            "annotations", "canonical", "hanlp", "formal", "constructions",
            "declaration_syntax", "contextual",
        }
        assert {role.name for role in inputs} == {"sources", *family_roles}
        assert {role.collection for role in inputs} == {"set"}
        expression = next(
            row.expression for row in kernel.model.bindings
            if row.semantic_id == kernel.model.operation(target).binding
        )
        assert inspect_binding_scopes(expression, tuple(role.name for role in inputs), {}).populations == {
            role: "selected-source-views" for role in {"sources", *family_roles}
        }
        # Select one pure CPU child to receive the genuine source population.
        # Stop before it executes. The shared source denominator closes while
        # the selected family manifestations do not cover its two contexts.
        # Preparation-only native profiles are never provider evidence.
        selections = _default_profile_selections(
            kernel.model, (target,), {
                target: DemandOperationSelection(
                    operation=target,
                    selected_dependencies=("text.formal_evidence/source-native",),
                ),
            },
        )
        selections[producer] = DemandOperationSelection(
            operation=producer,
            parameters={"sections": list(source.sections), "membership": "direct"},
        )
        graph = kernel.model.projection_graph(
            "selected-dependencies",
            selected_dependencies=tuple(
                (name, row.selected_dependencies) for name, row in selections.items()
            ),
        )
        required = {target, producer, *graph.closure((target,))}
        relations = tuple(
            relation
            for operation in sorted(required)
            for relation in source_discovery_relations(kernel.model, producer, "result", operation)
        )
        # Execute genuine native capture/discovery in this same demand. PDF
        # capture is attempt-only when lowering custody is incomplete, so a
        # publication from another demand cannot stand in for this execution.
        with kernel.purpose("write").begin() as connection:
            original = acquire_original_document_selection(
                connection, project_id=PROJECT, document_key=source.document_key
            )
            frozen = freeze_demand(
                kernel.model,
                roots=(original.root,),
                targets=(producer, target),
                selections=tuple(
                    OperationSelection(
                        name,
                        parameters=json_bytes(row.parameters),
                        choices=json_bytes(row.choices),
                        selected_dependencies=row.selected_dependencies,
                        replicate=row.replicate,
                    )
                    for name, row in selections.items()
                ),
                discovery=relations,
                original_sources=(original.selection(),),
                inference="current-source-journey",
                execution_profile=kernel.recipe.execution_profile,
            )
            demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
                frozen, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
            )["demand_id"]
        with controlled_pdf_converter(section_content(rows)):
            for _ in range(3):
                execute_data_demand(
                    kernel.purpose("write"),
                    demand,
                    source_root=ROOT / "python/corpus-structure/src",
                    admission_engine=kernel.purpose("admit"),
                    project_id=PROJECT,
                    database_capacity=6,
                    max_rounds=1,
                )
                with kernel.purpose("write").begin() as connection:
                    snapshot = DemandPlanner(
                        kernel.model, DataOperationStorage(connection)
                    ).resume(demand)
                if any(
                    row["operation_id"] == producer and row["fate"] == "fulfilled"
                    for row in snapshot["obligations"]
                ):
                    break
            else:
                pytest.fail("native source-view publication did not settle")
        # Receipt writes use the acquired read in a fresh native transaction.
        with kernel.purpose("write").begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            assert planner.settle_pending_discovery(snapshot)
        with kernel.purpose("write").begin() as connection:
            snapshot = DemandPlanner(
                kernel.model, DataOperationStorage(connection)
            ).resume(demand)
        with kernel.purpose("write").begin() as connection:
            source_page = read_data_demand(connection, demand, view="products", limit=1000)
        source_operations = {
            row["obligation_id"]: row["operation_id"] for row in source_page["obligations"]
        }
        assert {
            source_operations[use["obligation_id"]] for use in source_page["uses"]
            if use["fate"] == "fulfilled"
        } == {"source.pdf/capture", producer}
        (published,) = [
            product
            for use in source_page["uses"]
            if source_operations[use["obligation_id"]] == producer
            for product in use["products"]
            if product["member_id"] is None and product["role"] == "result"
        ]
        published_members = decode_semantic_value(published["body"])["members"]
        assert {
            (packet["body"]["source"]["section_pointer"], packet["body"]["text"])
            for packet in published_members
        } == {("#/groups/0", "First region."), ("#/groups/1", "Second region.")}
        expected_members = {
            packet["member_id"]: packet["context"] for packet in published_members
        }

        (population,) = [
            row for row in snapshot["populations"] if row["name"] == "selected-source-views"
        ]
        assert population["complete"] is True
        assert len(population["members"]) == 2
        assert {
            member["member_id"]: {
                name: member[name] for name in (
                    "subject", "subject_definition", "original_source", "analyzed_scope"
                )
            }
            for member in population["members"]
        } == expected_members
        with kernel.purpose("write").begin() as connection:
            tuple(DemandPlanner(kernel.model, DataOperationStorage(connection)).bound_requests(
                snapshot, authorization=b"{}"
            ))
        with kernel.purpose("write").begin() as connection:
            snapshot = DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(demand)
        obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
        (composition,) = [
            use
            for use in snapshot["uses"]
            if obligations[use["obligation_id"]]["operation_id"] == target
        ]
        # This is a source-only selection against a closed shared denominator,
        # not an assertion that all analytical producer families have settled.
        assert composition["fate"] == "not-applicable", composition
        reasons = cast(WireReasonSelection, composition["selection"]).get("reasons")
        assert reasons and len(reasons) == len(family_roles)
        assert {row["code"] for row in reasons} == {"binding-covers"}
        assert all(row["location"].startswith(target + "/binding/") for row in reasons)
