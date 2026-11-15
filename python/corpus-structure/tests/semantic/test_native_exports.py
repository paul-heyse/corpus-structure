"""Whole native exports use actual selected DDO publication custody."""

import json

import pytest

from corpus_structure.serve.native_source import NativeSourceRequest, export_native_source
from semantic.current_pdf_source_support import current_pdf_source as current_pdf_source


def test_complete_docling_json_export_preserves_native_shape(current_pdf_source, tmp_path):
    """The converter is controlled; selection, publication and native readers are real."""
    from docling_core.types.doc import DoclingDocument

    source = current_pdf_source
    with source.kernel.purpose("read").begin() as connection:
        reference, _ = source.publication(connection)
        request = NativeSourceRequest(**reference.model_dump())
        output = tmp_path / "native.docling.json"
        export_native_source(connection, request, output, format="docling-json")
        restored = DoclingDocument.model_validate_json(output.read_bytes())
        assert restored.name == "Independent current source"
        assert [item.text for item in restored.texts] == [
            "1 Selected source",
            "Alice was running.",
        ]
        assert len(restored.pages) == 1
        assert json.loads(output.read_bytes())["texts"][1]["orig"] == "Alice was running."
        assert not output.with_name(output.name + ".partial").exists()
        with pytest.raises(FileExistsError):
            export_native_source(connection, request, output, format="docling-json")
        partial = tmp_path / "partial-selection.json"
        with pytest.raises(ValueError, match="partial source selector"):
            export_native_source(
                connection,
                request.model_copy(update={"section_pointer": "#/body"}),
                partial,
                format="docling-json",
            )
        assert not partial.exists()
