"""Captured document fan-in over independently published native source members."""

from dataclasses import replace
from hashlib import sha256

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection, pm2_selection
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    OperationSelection,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_service import execute_data_demand
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
)
from semantic.current_pdf_source_support import (
    published_pdf_source_factory as published_pdf_source_factory,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, split_captured_operations


def captured_recipe(directory):
    directory.mkdir(parents=True, exist_ok=True)
    asset = directory / "controlled-spacy-model.bin"
    asset.write_bytes(b"controlled composition preparation, no provider execution")
    recipe = current_pdf_recipe(directory)
    captured = recipe.captured_inputs
    assert captured is not None
    _, _, sources = split_captured_operations(captured)
    core = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
    sentence_configuration = SentenceConfig(exclude=("ner",))
    inputs = primary_operation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)),
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
    published_pdf_source_factory,
    tmp_path,
):
    from corpus_structure.orchestrate.source_operation import _default_profile_selections

    target = "text.compose_view/captured-full-native"
    producer = "source.pdf_views/discovery"
    with published_pdf_source_factory(
        (
            ("text", "First region.", "First region.", None),
            ("text", "Second region.", "Second region.", None),
        )
    ) as source:
        kernel = admit_current_target(
            source, captured_recipe(tmp_path / "recipe"), tmp_path / "consumer"
        )
        inputs = [
            role for role in kernel.model.operation(target).roles if role.direction == "input"
        ]
        assert len(inputs) == 8 and {role.collection for role in inputs} == {"set"}
        selections = _default_profile_selections(kernel.model, (target,), {})
        selections[producer] = selections[producer].model_copy(
            update={"parameters": {"sections": list(source.sections), "membership": "descendants"}}
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
                    )
                    for name, row in selections.items()
                ),
                discovery=relations,
                original_sources=(original.selection(),),
                inference="captured-two-region-binding",
                execution_profile=kernel.recipe.execution_profile,
            )
            demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
                frozen, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
            )["demand_id"]
        # One sweep reuses the already published capture/discovery. No regional
        # provider executes before its source population has been expanded.
        execute_data_demand(
            kernel.purpose("write"),
            demand,
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
            project_id=PROJECT,
            database_capacity=6,
            max_rounds=1,
        )
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
                    snapshot, authorization=b"{}", retained=True
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
        assert composition["fate"] == "awaiting-inputs"
        selection = composition["selection"]
        assert "reasons" in selection
        reasons = selection["reasons"]
        assert reasons and {row["code"] for row in reasons} == {"binding-covers"}
