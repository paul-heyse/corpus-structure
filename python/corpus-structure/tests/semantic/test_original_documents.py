"""Raw immutable document facts preserve byte identity without execution or path salt."""

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_support import (
    OriginalDocumentRef,
    OriginalSourceSelection,
)
from corpus_structure.semantic.data_operation_wire import validate_native_wire
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_protocol_authoring import native_protocol_sources
from corpus_structure.semantic.original_documents import OriginalDocumentAcquisition


def reference():
    return OriginalDocumentRef(
        kind="original-document",
        project_id="project:one",
        document_key="document:semantic",
        content_hash="a" * 64,
        mime="application/pdf",
    )


def test_raw_document_selection_has_explicit_whole_scope_and_distinct_reference_type():
    acquired = OriginalDocumentAcquisition("book", reference())
    selection = acquired.selection()
    assert selection.record() == {
        "reference": reference().model_dump(mode="json"),
        "selectors": [{"scope": "whole-document"}],
    }
    assert acquired.root.original_source == "document:semantic"
    assert json.loads(acquired.root.analyzed_scope) == {
        "document": "document:semantic",
        "scope": "whole-document",
    }
    with pytest.raises(ValidationError):
        OriginalDocumentRef.model_validate(
            {**reference().model_dump(), "original_path": "/host/book.pdf"}
        )
    with pytest.raises(ValueError, match="whole-document"):
        replace(selection, selectors=canonical_bytes([{"scope": "page"}]))
    with pytest.raises(ValueError):
        OriginalSourceSelection("book", canonical_bytes({}), selection.selectors)


def test_raw_admission_wire_refuses_body_recipe_and_view_references():
    request = {
        "demand_id": "demand:one",
        "selection_name": "book",
        **OriginalDocumentAcquisition("book", reference()).selection().record(),
    }
    captured = native_protocol_sources()
    validate_native_wire("admit_original_document_asset", "input", request, sources=captured)
    for extra in ({"body": {"document": "forged"}}, {"recipe": "converter:one"}):
        with pytest.raises(ValueError):
            validate_native_wire(
                "admit_original_document_asset", "input", {**request, **extra}, sources=captured
            )
    # This complete historical physical reference used to be admitted as an
    # original fact. Its real shape now refuses at the current boundary.
    from corpus_structure.semantic.data_operation_support import read_original_source_reference

    legacy = dict(
        project_id="project:one",
        run_id=1,
        cut_id=2,
        release_id="release",
        result_revision=0,
        source_view_id=3,
        native_task_id=4,
        native_product_key="native:key",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    with pytest.raises(ValidationError):
        read_original_source_reference(canonical_bytes(legacy))
    with pytest.raises(ValidationError):
        OriginalSourceSelection(
            "legacy", canonical_bytes(legacy), canonical_bytes([{"projection": "b" * 64}])
        )


@pytest.mark.parametrize("original_target", ["DdoOriginalDocument"], indirect=True)
def test_original_document_nominal_target_prepares_without_capture_capability(original_target):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    model = bound_data_operation_model(original_target[3])
    operation = model.operation("urn:original-fact-test:consume")
    assert operation.capabilities.preparation == "none"
    role = next(role for role in operation.roles if role.direction == "input")
    kind = next(kind for kind in model.kinds if kind.semantic_id == role.kind)
    assert kind.name == "DdoOriginalDocument"
