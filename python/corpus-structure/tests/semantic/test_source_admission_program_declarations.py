"""Typed source providers retain captured scope, exact ACLs and install prerequisites."""

from dataclasses import replace

import pytest
from sqlalchemy import text

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.data_operation_source_native import (
    source_native_programs,
    source_native_sources,
)
from corpus_structure.semantic.data_operation_visual_read import _schema
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM, execute_native_sql
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.original_document_native import (
    ASSET_DIGEST_BASIS,
    source_original_native_programs,
)
from corpus_structure.semantic.source_admission_native import source_admission_native_programs
from corpus_structure.semantic.source_capture_native import source_capture_native_programs
from corpus_structure.semantic.visual_evidence import VisualEvidenceArtifact
from corpus_structure.semantic.visual_read_native import visual_read_native_programs


def test_source_leaf_producers_retain_structured_programs_and_exact_purpose_owners(monkeypatch):
    def refuse_render(self):
        raise AssertionError("source producer rendered before its native authoring boundary")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    model = get_metadata()
    capture = source_capture_native_programs(model)
    source = source_admission_native_programs(model, capture_programs=capture)
    original = source_original_native_programs(model, ASSET_DIGEST_BASIS)
    visual = visual_read_native_programs(model, _schema(VisualEvidenceArtifact))
    programs = (*source, *original, *visual)
    assert len(programs) == 15
    privileged = {
        item.identity.name: item.access.purposes for item in programs if item.access.purposes
    }
    assert privileged == {
        "ddo_pdf_capture_source": ("write",),
        "ddo_pdf_observation_source": ("write",),
        "register_original_document": ("write",),
        "require_source_admission": ("write", "read", "admit", "evaluate"),
    }
    for item in programs:
        assert item.source == "data-operation-source-admission:forward"
        assert item.owner == role_name("publisher")
        if not item.access.purposes:
            assert item.access == INTERNAL_PROGRAM
    positions = {item.identity.name: index for index, item in enumerate(source)}
    assert all(
        positions[item.identity.name] < positions["read_selected_pdf_source"] for item in capture
    )
    assert visual[-1].routine.security_definer is True
    assert visual[-1].routine.volatility == "volatile"


def test_source_capture_correspondence_refuses_independently_altered_statements():
    model = get_metadata()
    sources = source_native_sources(target_metadata=model)
    programs = source_native_programs(target_metadata=model, sources=sources)
    assert len(programs) == 15
    assert "ddo_impl_read_selected_visual_evidence" in {item.identity.name for item in programs}
    for changed in (
        "native/data-operation-source-capture.sql",
        "native/data-operation-source-admission.sql",
        "native/source-originals.sql",
        "native/data-operation-visual-read.sql",
    ):
        altered = tuple(
            replace(item, content=item.content + b"\nchanged") if item.name == changed else item
            for item in sources
        )
        with pytest.raises(ValueError, match="differ from captured"):
            source_native_programs(target_metadata=model, sources=altered)


def test_typed_visual_candidates_keep_independent_parent_first_paging(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    declaration = visual_read_native_programs(get_metadata(), _schema(VisualEvidenceArtifact))[0]
    execute_native_sql(connection, declaration.routine.render())
    import json

    mapped = {
        "rows": [
            {"kind": "picture", "occurrence_id": "p"},
            {
                "kind": "caption_candidate",
                "occurrence_id": "caption",
                "text": "Straße Shared Distribution",
                "associated_picture_occurrence_ids": ["p"],
            },
        ]
    }
    actual = connection.scalar(
        text("SELECT ops.ddo_visual_candidate_rows(CAST(:mapped AS jsonb),CAST(:query AS jsonb))"),
        {
            "mapped": json.dumps(mapped),
            "query": json.dumps({"after": 0, "limit": 1, "regions": []}),
        },
    )
    assert [item["occurrence_id"] for item in actual["items"]] == ["p"]
    assert actual["next_after"] == 1
