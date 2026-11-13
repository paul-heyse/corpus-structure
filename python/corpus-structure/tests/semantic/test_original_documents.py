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
from corpus_structure.semantic.original_documents import OriginalDocumentAcquisition

from .test_data_operation_original_native import original_target as original_target
from .test_data_operation_wire import captured


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
    validate_native_wire("admit_original_document_asset", "input", request, sources=captured())
    for extra in ({"body": {"document": "forged"}}, {"recipe": "converter:one"}):
        with pytest.raises(ValueError):
            validate_native_wire(
                "admit_original_document_asset", "input", {**request, **extra}, sources=captured()
            )
    with pytest.raises(ValueError):
        validate_native_wire("admit_original_source_view", "input", request, sources=captured())


@pytest.mark.parametrize("original_target", ["DdoOriginalDocument"], indirect=True)
def test_original_document_nominal_target_prepares_with_actual_pdf_capability(original_target):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    model = bound_data_operation_model(original_target[3])
    operation = model.operation("urn:original-fact-test:consume")
    assert operation.capabilities.preparation == "pdf-native"
    role = next(role for role in operation.roles if role.direction == "input")
    kind = next(kind for kind in model.kinds if kind.semantic_id == role.kind)
    assert kind.name == "DdoOriginalDocument"
