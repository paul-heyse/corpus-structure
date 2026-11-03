"""Whole native exports retain Docling structure and refuse partial selection or stale pins."""

import json

import pytest

from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.serve.native_source import NativeSourceRequest, export_native_source

from .test_pdf_native_consumer_journey import native_build_resubmission_case


def test_complete_docling_json_export_preserves_native_shape(
    semantic_db_engine,
    semantic_writer_engine,
    tmp_path,
):
    from docling_core.types.doc import DocItemLabel, DoclingDocument, GroupLabel

    _, run, _, view_id, _ = native_build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path
    )
    with semantic_writer_engine.connect() as conn:
        view = load_source_view(conn, view_id)
        pin = view.ref.native_product
        request = NativeSourceRequest(
            run_id=run,
            task_id=pin.task_id,
            product_key=pin.product_key,
            content_digest=pin.content_digest,
        )
        # Independent expected native structure; no retired aggregate storage is consulted.
        expected = DoclingDocument(name="Independent source")
        section = expected.add_group(label=GroupLabel.SECTION, name="People")
        expected.add_text(
            label=DocItemLabel.TEXT, text="Alice is here.", orig="Alice is here.", parent=section
        )
        output = tmp_path / "native.docling.json"
        export_native_source(conn, request, output, format="docling-json")
        assert json.loads(output.read_bytes()) == expected.export_to_dict()
        restored = DoclingDocument.model_validate_json(output.read_bytes())
        assert restored.groups[0].name == "People"
        assert restored.texts[0].text == "Alice is here."
        assert not output.with_name(output.name + ".partial").exists()
        with pytest.raises(FileExistsError):
            export_native_source(conn, request, output, format="docling-json")
        partial = tmp_path / "partial-selection.json"
        with pytest.raises(ValueError, match="partial source selector"):
            export_native_source(
                conn,
                request.model_copy(update={"section_pointer": view.ref.section_pointer}),
                partial,
                format="docling-json",
            )
        assert not partial.exists()
        stale = tmp_path / "wrong-pin.json"
        with pytest.raises(ValueError, match="requires a current published record"):
            export_native_source(
                conn,
                request.model_copy(update={"content_digest": "f" * 64}),
                stale,
                format="docling-json",
            )
        assert not stale.exists()
