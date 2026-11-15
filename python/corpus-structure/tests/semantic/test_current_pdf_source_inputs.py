"""Current source journey preparation; native custody remains a separate obligation."""

import pytest

from semantic.current_pdf_source_support import current_pdf_recipe
from semantic.data_operation_kernel_support import prepare_kernel


@pytest.mark.parametrize("math_context", [False, True])
def test_current_pdf_fixture_prepares_real_native_owners_without_legacy_seed(
    tmp_path, math_context
):
    recipe = current_pdf_recipe(tmp_path, math_context=math_context)
    assert recipe.project_id is None
    prepared = prepare_kernel(recipe)
    operations = {operation.semantic_id for operation in prepared.model.operations}
    assert {
        "data.initialize_source_project",
        "source.pdf/capture",
        "source.pdf_views/discovery",
    } <= operations
    incomplete = [
        (item.root, item.unknowns)
        for item in prepared.model.implementation_slices
        if not item.complete
    ]
    assert not incomplete
    from corpus_structure.serve.selected_source import _captured_analysis_profile

    context = _captured_analysis_profile(prepared.prepared, prepared.dependencies)
    assert (context is not None) is math_context
    if context is not None:
        from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

        interpreted = prepare_interpretation_context(
            prepared.prepared, macros={}, kind="formula", context_profile=context
        )
        assert interpreted.model_id == context.model_id


def test_current_section_fixture_serializes_real_empty_and_formula_sections(tmp_path):
    """Exercise the converter boundary used by native consumers before capture."""
    import json
    from types import SimpleNamespace

    import pyarrow as pa

    from corpus_structure.ingest.pdf import PdfRecipe
    from semantic.current_pdf_source_support import _section_stream

    recipe = PdfRecipe(
        "0" * 40,
        "1" * 40,
        device="cpu",
        ocr_device="cpu",
        recipe_id="docling-standard-pdf-stream-v1",
    )
    reply = _section_stream(
        (("formula", "f(x)=x", "f(x)=x", "succeeded"), ("text", "", "", None)),
        SimpleNamespace(recipe=recipe),
        SimpleNamespace(digest="a" * 64),
        spool_root=tmp_path / "spool",
        record_root=tmp_path / "records",
        build_id="current-test-build",
        release_id="current-test-release",
        on_replay=lambda replay: None,
        check_active=lambda: None,
    )
    assert reply.conversion_status == "success" and reply.errors == ()
    rows = {}
    for replay in reply.record_replays:
        with pa.memory_map(str(replay.path), "r") as mapped:
            rows.setdefault(replay.family, []).extend(
                pa.ipc.open_file(mapped).read_all().to_pylist()
            )
    addresses = {
        row["native_address"] for row in rows["native"] if row["native_address"] is not None
    }
    assert {"#/groups/0", "#/groups/1", "#/texts/0"} <= addresses
    assert "#/texts/1" not in addresses  # The second section is genuinely empty.
    completion = b"".join(
        row["body"]
        for row in sorted(rows["artifact_part"], key=lambda row: row["ordinal"])
        if row["stream_id"] == "native/completion"
    )
    records = [json.loads(line) for line in completion.splitlines()]
    assert [row for row in records if row["kind"] == "formula"] == [
        dict(kind="formula", item_ref="#/texts/0", outcome="succeeded", error=None)
    ]
