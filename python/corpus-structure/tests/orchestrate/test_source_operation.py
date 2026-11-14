"""Ordinary choices preserve source meaning while compiled declarations own execution."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from corpus_structure.orchestrate.source_request import (
    NamedScope,
    SourceRunRequest,
    WholeDocument,
    method_settings,
    source_selection,
)
from corpus_structure.semantic.data_operation_service import (
    DemandOperationSelection,
    DemandRoot,
    NativeDemandRequest,
)


def request(**changes):
    return SourceRunRequest(
        **{"project_id": "project", "release_id": "release", "runtime_id": "runtime", **changes}
    )


@pytest.mark.parametrize(
    "selection",
    [
        source_selection(),
        source_selection(scope="one"),
        source_selection(slice="one"),
        WholeDocument(),
    ],
)
def test_typed_source_intent_roundtrips_exact_source_choices(selection):
    value = request(
        selection=selection, workflow="capture", documents=("book",), membership="direct"
    )
    assert SourceRunRequest.model_validate_json(value.model_dump_json()) == value
    assert value.runtime_id == "runtime" and value.documents == ("book",)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"slice": "one", "scope": "two"},
        {"slice": "one", "whole_document": True},
        {"scope": "one", "whole_document": True},
        {"corpus": "old-dom"},
    ],
)
def test_source_selector_preflight_is_shared_and_pure(kwargs):
    with pytest.raises(ValueError):
        source_selection(**kwargs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("graph", {}),
        ("registry_for", "owner"),
        ("fresh", ["text.formal_evidence"]),
        ("realization_id", "legacy-run-input"),
        ("workflow", "m1-candidate"),
        ("membership", "newest"),
        ("runtime_id", ""),
        ("domain", "../statistics"),
    ],
)
def test_native_source_request_refuses_retired_authority_and_invalid_choices(field, value):
    with pytest.raises(ValidationError):
        request(**{field: value})


def test_nested_source_selection_refuses_implementation_dependencies():
    payload = request(selection=NamedScope("one")).model_dump(mode="json")
    payload["selection"]["graph"] = {}
    with pytest.raises(ValidationError):
        SourceRunRequest.model_validate(payload)


def test_shared_settings_factory_preserves_complete_settings_and_physical_policy(tmp_path):
    from corpus_structure.settings import Settings

    configured = Settings()
    selected = method_settings(configured, {"workers": 1})
    assert selected.execution_policy.workers == 1
    assert (
        selected.execution_policy.max_owned_bytes
        == configured.characterization_execution.max_owned_bytes
    )
    assert selected.nemotron_endpoint == configured.nemotron.endpoint
    assert selected.nemotron_worker == configured.nemotron.worker
    assert selected.model_cache == configured.paths.model_cache
    with pytest.raises(ValueError, match="object"):
        method_settings(configured, [])


def test_explicit_operation_choices_and_source_context_are_frozen_independently():
    from semantic.data_operation_declaration_support import model, operation

    from corpus_structure.semantic.data_operation_service import freeze_native_demand

    compiled = model(
        operation("op:unused"),
        operation("op:base"),
        operation("op:result", potential_dependencies=["op:base"]),
    )
    root = DemandRoot(
        subject="source-view", original_source="book", analyzed_scope={"start": 3, "end": 8}
    )
    value = NativeDemandRequest(
        project_id="p",
        release_id="r",
        runtime_id="t",
        roots=(root,),
        targets=("op:result",),
        execution_profile="selected-provider",
        selections=(
            DemandOperationSelection(operation="op:result", selected_dependencies=("op:base",)),
        ),
    )
    prepared = SimpleNamespace()
    from unittest.mock import patch

    from corpus_structure.semantic import data_operation_service

    with patch.object(data_operation_service, "bound_data_operation_model", return_value=compiled):
        frozen = freeze_native_demand(prepared, value)
    assert frozen.record["roots"] == [
        {
            "subject": "source-view",
            "original_source": "book",
            "analyzed_scope": {"start": 3, "end": 8},
        }
    ]
    assert {entry["operation"] for entry in frozen.record["operations"]} == {"op:base", "op:result"}
    assert frozen.record["execution_profile"] == "selected-provider"
