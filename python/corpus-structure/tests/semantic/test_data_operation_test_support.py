"""Behavioral controls for shared DDO preparation and wire-checked routing."""

from dataclasses import replace
from typing import cast as typing_cast

import pytest
from scenario_recipes import scenario_builder

from corpus_structure.semantic._data_operation_wire import (
    WireInspectDataCompletionRequest,
)
from semantic.data_operation_binding_support import WireCheckedStorage
from semantic.data_operation_kernel_support import (
    CLAIM_SOURCE,
    EXECUTION,
    ORIGINAL_DOCUMENT,
    ORIGINAL_PDF,
    POPULATION,
    STORAGE,
    build_kernel,
    prepare_kernel,
)


@pytest.mark.parametrize(
    ("recipe", "operation"),
    [
        (STORAGE, "urn:ddo-test:source"),
        (POPULATION, "urn:discover"),
        (EXECUTION, "urn:ddo-execution:answer"),
        (CLAIM_SOURCE, "urn:corpus:operation:claim-source-item"),
        (ORIGINAL_DOCUMENT, "urn:original-fact-test:consume"),
        (ORIGINAL_PDF, "urn:original-fact-test:consume"),
    ],
    ids=lambda value: getattr(value, "name", value),
)
def test_recipe_prepares_its_captured_model_and_reuses_equal_value(recipe, operation):
    prepared = prepare_kernel(recipe)
    assert prepared.model.operation(operation).semantic_id == operation
    assert prepare_kernel(replace(recipe)) is prepared
    assert scenario_builder(recipe) is build_kernel


@pytest.mark.parametrize(
    ("payload", "reply", "recorded"),
    [
        (
            {"intent_id": "intent:one", "demand_id": "demand:one", "generation": True},
            {"state": "known-uncommitted", "intent_retained": False},
            False,
        ),
        (
            {"intent_id": "intent:one", "demand_id": "demand:one"},
            {"state": "committed", "intent_retained": True},
            True,
        ),
    ],
    ids=["invalid-input", "invalid-result"],
)
def test_wire_checked_double_refuses_malformed_input_and_reply(payload, reply, recorded):
    storage = WireCheckedStorage({"inspect_data_completion": reply})
    with pytest.raises(ValueError):
        storage.inspect_data_completion(typing_cast(WireInspectDataCompletionRequest, payload))
    assert bool(storage.calls) is recorded


def test_wire_checked_double_refuses_unconfigured_operation():
    storage = WireCheckedStorage({})
    with pytest.raises(ValueError, match="unknown configured native"):
        storage.inspect_data_completion(
            typing_cast(
                WireInspectDataCompletionRequest,
                {"intent_id": "intent:one", "demand_id": "demand:one"},
            )
        )
    assert storage.calls == []


def test_actual_package_kernel_inputs_preserve_read_only_source_custody(monkeypatch):
    from pathlib import Path

    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_storage import (
        native_operation_declarations,
        native_protocol_sources,
    )
    from corpus_structure.semantic.source_discovery import (
        source_discovery_inputs,
        source_discovery_operation_sources,
    )
    from corpus_structure.semantic.types import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
    )
    from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_discovery_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    sources = source_discovery_operation_sources()
    native = native_protocol_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies(native),
        (native_operation_declarations(native),),
        sources,
    )
    inputs = CapturedKernelInputs(bundle, dependencies, PreparationProfile(version="semantic-2"))
    recipe = KernelRecipe("actual-package-source-discovery", "", None, "", captured_inputs=inputs)
    original_write = Path.write_bytes
    captured_paths = {Path(source.filename) for source in sources.sources}

    def owned_write(path, content):
        assert path not in captured_paths, (
            "package source must never be materialized by a test fixture"
        )
        return original_write(path, content)

    monkeypatch.setattr(Path, "write_bytes", owned_write)
    actual = prepare_kernel(recipe)
    assert (
        actual.model.operation("source.selected_views/discovery").semantic_id
        == "source.selected_views/discovery"
    )
    assert actual.bundle == bundle and actual.dependencies == dependencies
    # A separately captured consumer has selected-view discovery, not PDF
    # recapture. Its request must explicitly pin the other demand's source members.
    from contextlib import nullcontext
    from types import SimpleNamespace

    from corpus_structure.semantic import original_documents
    from corpus_structure.semantic.data_operation_service import freeze_native_demand
    from corpus_structure.semantic.data_operation_support import OriginalDocumentRef
    from semantic import current_pdf_source_support as current_sources

    original = original_documents.OriginalDocumentAcquisition(
        "original",
        OriginalDocumentRef(
            kind="original-document",
            project_id=current_sources.PROJECT,
            document_key="document:controlled-consumer",
            content_hash="a" * 64,
            mime="application/pdf",
        ),
    )
    rows = tuple(
        dict(
            product_id="product:retained-native",
            member_id=member,
            subject="source:" + member,
            subject_definition="original-source-view",
            original_source=original.reference.document_key,
            analyzed_scope={"section": section, "membership": "descendants"},
        )
        for member, section in (("first", "#/groups/0"), ("second", "#/groups/1"))
    )
    from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry
    from corpus_structure.semantic.demand_results import CutSelection
    from semantic.demand_result_support import demand_result_page

    page = demand_result_page()
    page.update(project_id=current_sources.PROJECT)
    cut = CutSelection.from_native(page)
    rows = tuple(
        dict(
            row,
            _selected_entry=SelectedSourceSetEntry.from_selected_header(
                dict(
                    row,
                    use_id="unadmitted:source-use",
                    derivation_id="unadmitted:source-episode",
                    output_member_id=None,
                    role="result",
                    position=0,
                    multiplicity=1,
                ),
                cut,
            ),
        )
        for row in rows
    )
    monkeypatch.setattr(
        current_sources, "selected_current_sources", lambda source: tuple((row, {}) for row in rows)
    )
    monkeypatch.setattr(
        original_documents, "acquire_original_document_selection", lambda *args, **kwargs: original
    )
    kernel = SimpleNamespace(
        model=actual.model,
        prepared=actual.prepared,
        runtime="runtime:controlled-consumer",
        recipe=SimpleNamespace(execution_profile="source-native"),
        purpose=lambda role: SimpleNamespace(begin=lambda: nullcontext(None)),
    )
    source = SimpleNamespace(document_key=original.reference.document_key)
    request = current_sources.current_consumer_request(
        source, kernel, ("source.selected_views/discovery",), discover=True
    )
    assert request.targets == ("source.selected_views/discovery",)
    assert [(value.operation, value.parameters) for value in request.selections] == [
        ("source.selected_views/discovery", {"complete": True})
    ]
    assert set(request.source_sets) == {"selected-source-views"}
    (scope,) = request.source_sets.values()
    assert isinstance(scope, dict)
    entries = scope["entries"]
    acquisition = scope["acquisition"]
    assert isinstance(acquisition, dict)
    assert acquisition["kind"] == "selected-support-v1"
    reads = acquisition["reads"]
    assert isinstance(reads, list) and len(reads) == 1
    assert isinstance(entries, list)
    references, scopes, originals = [], [], []
    for entry in entries:
        assert isinstance(entry, dict)
        references.append(entry["reference"])
        scopes.append(entry["analyzed_scope"])
        originals.append(entry["original_source"])
    assert references == [
        {"product_id": "product:retained-native", "member_id": "first"},
        {"product_id": "product:retained-native", "member_id": "second"},
    ]
    assert scopes == [row["analyzed_scope"] for row in rows]
    assert originals == [original.reference.document_key] * len(entries)
    freeze_native_demand(actual.prepared, request)
    with pytest.raises(ValueError, match="lacks its explicit frozen source set"):
        freeze_native_demand(actual.prepared, request.model_copy(update={"source_sets": {}}))
    modified = replace(
        sources.sources[0], content=sources.sources[0].content + b"\n# changed custody\n"
    )
    invalid_sources = replace(sources, sources=(modified, *sources.sources[1:]))
    invalid = replace(
        inputs,
        dependencies=data_operation_dependencies(
            ResolvedDependencies(native),
            (native_operation_declarations(native),),
            invalid_sources,
        ),
    )
    with pytest.raises(ValueError, match="read-only file"):
        prepare_kernel(replace(recipe, name="changed-package-source", captured_inputs=invalid))
