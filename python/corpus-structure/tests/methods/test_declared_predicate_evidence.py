"""Missing retained annotation is a denied inspection, never successful empty facts."""

import pytest

from corpus_structure.methods.predicate_contributions import declared_predicate_evidence
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_record_sources import (
    DeclaredNativeFrameSource,
    DeclaredRecordSource,
    DeclaredSourceSlice,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import NativeSourceContext, PreparedNativeSources


def declared_frame():
    from corpus_structure.semantic.source_products import native_projection_identity

    text = "Ada acts."
    items = [{"self_ref": "#/texts/0", "text": text, "label": "text"}]
    pieces = [
        {
            "kind": "native_text",
            "item_ref": "#/texts/0",
            "start": 0,
            "end": len(text),
            "source_field": "text",
        }
    ]
    projection = native_projection_identity(text, pieces, items, (), ())
    address = DeclaredRecordSource(
        "document",
        projection,
        "#/texts/0",
        "direct",
        SubjectContext("project", "subject", "document", b"null"),
        "source-product",
        None,
        "source-kind",
    )
    return DeclaredNativeFrameSource(
        canonical_bytes(
            {
                "source": {
                    "document": "document",
                    "projection": projection,
                    "section_pointer": "#/texts/0",
                    "membership": "direct",
                },
                "text": text,
                "items": items,
                "pieces": pieces,
            }
        ).decode(),
        canonical_bytes(address.pin()).decode(),
    )


def test_declared_predicate_missing_annotations_retains_noninspection_denominator():
    frame = declared_frame()
    preparation = PreparedNativeSources((frame,))
    context = NativeSourceContext(
        frame,
        (),
        (DeclaredSourceSlice(frame.source_key, 0, 9),),
        "exact declared read",
        "bound",
        "selected",
        version=2,
        preparation=preparation,
    )
    missing = declared_predicate_evidence(frame, context, (), dependency="actual-native-input")
    assert not missing.inspection_complete
    assert missing.contributions == missing.coordinate_texts == ()
    assert len(missing.operations) == 2
    assert {row["outcome"] for row in missing.operations} == {"not_run"}
    assert all(row["inspected_count"] == row["emitted_count"] == 0 for row in missing.operations)
    failed = declared_predicate_evidence(
        frame,
        context,
        (),
        dependency="actual-native-input",
        annotation_errors=("retained annotation unavailable",),
    )
    assert not failed.inspection_complete
    assert {row["outcome"] for row in failed.operations} == {"failed"}
    assert all(
        row["computation_dependencies"] == ("actual-native-input",) for row in failed.operations
    )
    with pytest.raises(ValueError, match="exact owned source context"):
        declared_predicate_evidence(declared_frame(), context, (), dependency="actual-native-input")
