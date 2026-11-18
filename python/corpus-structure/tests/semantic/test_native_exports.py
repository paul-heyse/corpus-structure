"""Whole native exports use actual selected DDO publication custody."""

import json

import pytest

from corpus_structure.serve.native_source import NativeSourceRequest, export_native_source
from semantic.current_pdf_source_support import published_pdf_source as published_pdf_source


def test_complete_docling_json_export_preserves_native_shape(published_pdf_source, tmp_path):
    """The converter is controlled; selection, publication and native readers are real."""
    from docling_core.types.doc import DoclingDocument

    source = published_pdf_source
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


def test_published_capture_clones_share_one_conversion_and_refuse_new_work(
    scenario_seeds, monkeypatch, tmp_path
):
    from dataclasses import replace

    from pdf_controlled_support import _ControlledPdfProducer

    from native_scenario_seeds import recipe_id
    from semantic.current_pdf_source_support import (
        PdfSourceScenario,
        section_content,
        selected_current_sources,
    )

    scenario = PdfSourceScenario(
        section_content((("text", "Independent retained source", "", None),)),
        ("#/groups/0",),
    )
    calls = []
    convert = _ControlledPdfProducer.convert

    def observed(self, *args, **kwargs):
        calls.append(self.content)
        return convert(self, *args, **kwargs)

    monkeypatch.setattr(_ControlledPdfProducer, "convert", observed)
    with (
        scenario_seeds.commit_clone(scenario) as first,
        scenario_seeds.commit_clone(scenario) as second,
    ):
        assert first.database_oid != second.database_oid
        assert first.origin == second.origin
        sources = [clone.stage.acquired(clone, published_only=True) for clone in (first, second)]
        assert sources[0].document_key == sources[1].document_key
        assert {row["body"]["text"].strip() for row, _ in selected_current_sources(sources[0])} == {
            "Independent retained source"
        }
        for source in sources:
            with source.kernel.purpose("read").begin() as connection:
                selection, _ = source.publication(connection)
                assert selection is not None
            with (
                source.kernel.purpose("write").begin() as connection,
                pytest.raises(ValueError, match="published capture cannot register a new demand"),
            ):
                source.register(connection, "source.pdf/capture")
    assert calls == [scenario.content]
    with (
        pytest.raises(ValueError, match="scenario needs a writable binding"),
        scenario_seeds.commit_clone(scenario.bind(tmp_path / "writable-only")),
    ):
        pytest.fail("a bound PDF recipe was sealed")
    changed = replace(
        scenario, content=section_content((("text", "Different retained source", "", None),))
    )
    assert recipe_id(changed) != recipe_id(scenario)
    with scenario_seeds.commit_clone(changed) as clone:
        assert clone.origin != first.origin
        changed_source = clone.stage.acquired(clone, published_only=True)
        assert {
            row["body"]["text"].strip() for row, _ in selected_current_sources(changed_source)
        } == {"Different retained source"}
    assert calls == [scenario.content, changed.content]
