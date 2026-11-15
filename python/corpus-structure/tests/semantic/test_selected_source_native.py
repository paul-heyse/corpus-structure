"""Selected current source custody survives detached offline formula preparation."""

import pytest

from corpus_structure.semantic.math_context import prepare_interpretation_context
from corpus_structure.serve.selected_source import (
    AdditionalContextRequired,
    SelectedSourceExportRequest,
    SelectedSourceReader,
    SelectedSourceSelection,
    _captured_analysis_profile,
    export_selected_source,
)
from semantic.companion_export_native_support import read_settings as read_settings
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)


def test_native_selection_context_and_offline_preparation(
    current_pdf_source_factory,
    native_settings,
    tmp_path,
):
    with current_pdf_source_factory(
        (
            ("formula", "x=1", "original A", "succeeded"),
            ("formula", "x=2", "original B", "succeeded"),
        ),
        math_context=True,
    ) as source:
        with source.kernel.purpose("read").begin() as connection:
            pin, _ = source.publication(connection)
        request = SelectedSourceExportRequest(
            pin=pin,
            selection=SelectedSourceSelection(root="#/groups/0"),
            destination=tmp_path / "export",
        )
        profile = _captured_analysis_profile(
            source.kernel.prepared, source.kernel.preparation.dependencies
        )
        assert profile is not None
        context = prepare_interpretation_context(macros={}, kind="formula", context_profile=profile)
        receipt = export_selected_source(
            request, read_settings(native_settings, source.kernel.engine)
        )
        assert receipt.format == "selected-source-v2" and receipt.pin == pin
        # All source readers, transactions and drivers have settled before offline preparation.
        with SelectedSourceReader(request.destination, expected_pin=pin) as reader:
            prepared = reader.prepare_formula_inputs(context)
            assert [item.source.item_pointer for item in prepared.formulas] == ["#/texts/0"]
            assert [item.source.original_text for item in prepared.formulas] == ["original A"]
            assert list(reader._index.execute("SELECT pointer FROM records ORDER BY ordinal")) == [
                ("#/groups/0",),
                ("#/texts/0",),
            ]
            with pytest.raises(AdditionalContextRequired) as error:
                reader.prepare_formula_inputs(context, required_outside_values=["#/texts/1"])
            assert any(row["target"]["pointer"] == "#/texts/1" for row in error.value.references)
