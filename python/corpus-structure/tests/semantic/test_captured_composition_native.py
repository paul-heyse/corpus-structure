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
        captured_document_view_operation_sources if captured else full_document_view_operation_sources
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
        == ("text.compose_view/captured-full-native" if captured else "text.compose_view/full-native")
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
    from types import SimpleNamespace

    from corpus_structure.methods import full_document_composition
    from corpus_structure.methods.captured_document_composition import ComposeCapturedDocumentFamily

    first = SimpleNamespace(value={"source": {"section_pointer": "a"}})
    second = SimpleNamespace(value={"source": {"section_pointer": "b"}})
    early = SimpleNamespace(content=b'{"source":{"section_pointer":"a"}}', semantic_id="a")
    late = SimpleNamespace(content=b'{"source":{"section_pointer":"a"}}', semantic_id="z")
    last = SimpleNamespace(content=b'{"source":{"section_pointer":"b"}}', semantic_id="b")
    observed = []

    def execute(receiver, sources, products, active, profile):
        observed.append((sources, products, active, profile))

    monkeypatch.setattr(full_document_composition, "execute_view_profile", execute)
    owner = (
        ComposeCapturedDocumentFamily
        if captured
        else full_document_composition.ComposeFullDocumentOperation
    )
    owner.run(object.__new__(owner), (second, first), (last, late, early), (), (), (), (), (), ())
    assert observed == [((first, second), (early, late, last), (early, late, last), "full_characterization")]


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
        assert len(inputs) == 8 and {role.collection for role in inputs} == {"set"}
        selections = _default_profile_selections(kernel.model, (target,), {})
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
        # Capture and discover within this demand's admitted producer scope.
        # Stop after the two source sweeps so the analytical families remain pending.
        with controlled_pdf_converter(section_content(rows)):
            result = execute_data_demand(
                kernel.purpose("write"),
                demand,
                source_root=ROOT / "python/corpus-structure/src",
                admission_engine=kernel.purpose("admit"),
                project_id=PROJECT,
                database_capacity=6,
                max_rounds=2,
            )
        assert result.receipt_count == 2
        with kernel.purpose("write").begin() as connection:
            snapshot = DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(demand)
        obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
        (discovered,) = [
            use
            for use in snapshot["uses"]
            if obligations[use["obligation_id"]]["operation_id"] == producer
        ]
        assert discovered["fate"] == "fulfilled"
        (product,) = discovered["products"]
        derivation = discovered["derivation_id"]
        assert derivation is not None
        with kernel.purpose("write").begin() as connection:
            DemandPlanner(kernel.model, DataOperationStorage(connection)).expand_discovery(
                snapshot,
                population="selected-source-views",
                product=product["product_id"],
                derivation=derivation,
            )
        with kernel.purpose("write").begin() as connection:
            snapshot = DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(demand)
        (population,) = [
            row for row in snapshot["populations"] if row["name"] == "selected-source-views"
        ]
        assert len(population["members"]) == 2
        with kernel.purpose("write").begin() as connection:
            tuple(
                DemandPlanner(kernel.model, DataOperationStorage(connection)).bound_requests(
                    snapshot, authorization=b"{}"
                )
            )
        with kernel.purpose("write").begin() as connection:
            current = DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(demand)
        obligations = {row["obligation_id"]: row for row in current["obligations"]}
        (composition,) = [
            use
            for use in current["uses"]
            if obligations[use["obligation_id"]]["operation_id"] == target
        ]
        assert composition["fate"] == "not-applicable"
        reasons = cast(WireReasonSelection, composition["selection"]).get("reasons")
        assert reasons and {row["code"] for row in reasons} == {"binding-covers"}
