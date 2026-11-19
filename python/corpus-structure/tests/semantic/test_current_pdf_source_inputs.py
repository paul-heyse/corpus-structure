"""Current source journey preparation; native custody remains a separate obligation."""

import pytest

from semantic.current_pdf_source_support import PdfSourceScenario, source_content
from semantic.data_operation_kernel_support import prepare_worker_kernel


def test_pdf_preparation_reuses_only_a_live_binding_and_retains_evicted_resources(
    tmp_path, monkeypatch
):
    from collections import OrderedDict
    from dataclasses import replace

    from native_scenario_seeds import recipe_id
    from semantic import data_operation_kernel_support as support

    recipe = PdfSourceScenario(source_content())
    first_directory = tmp_path / "independent-binding-first"
    second_directory = tmp_path / "independent-binding-second"
    for directory in (first_directory, second_directory):
        directory.mkdir()
    first = support.WorkerKernelBinding(first_directory)
    second = support.WorkerKernelBinding(second_directory)
    monkeypatch.setattr(support, "_preparations", OrderedDict())
    monkeypatch.setattr(support, "_PREPARATION_LIMIT", 2)

    def custody(preparation):
        return next(
            asset.content
            for asset in preparation.dependencies.artifacts
            if asset.name == "runtime-transport/pdf-capture/execution-custody"
        )

    try:
        assert recipe_id(recipe) == recipe_id(PdfSourceScenario(source_content()))
        retained = prepare_worker_kernel(recipe, first)
        assert prepare_worker_kernel(recipe, first) is retained
        another = prepare_worker_kernel(recipe, second)
        assert another is not retained
        for prepared, selected, foreign in (
            (retained, first_directory, second_directory),
            (another, second_directory, first_directory),
        ):
            assert prepared.directory.is_relative_to(selected)
            assert selected.name.encode() in custody(prepared)
            assert foreign.name.encode() not in custody(prepared)

        prepare_worker_kernel(replace(recipe, sections=("#/groups/0",)), second)
        rebuilt = prepare_worker_kernel(recipe, first)
        assert rebuilt is not retained and rebuilt.directory != retained.directory
        assert retained.directory.is_dir()
        first.close()
        with pytest.raises(RuntimeError, match="kernel preparation binding is closed"):
            prepare_worker_kernel(recipe, first)
        assert retained.directory.is_dir()
        direct_path = tmp_path / "per-consumer"
        direct_recipe = recipe.bind(direct_path)
        assert support.prepare_kernel(direct_recipe, directory=direct_path) is not (
            support.prepare_kernel(direct_recipe, directory=direct_path)
        )
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize("math_context", [False, True])
def test_current_pdf_fixture_prepares_real_native_owners_without_legacy_seed(
    worker_kernel_binding, math_context
):
    recipe = PdfSourceScenario(source_content(), math_context=math_context)
    prepared = prepare_worker_kernel(recipe, worker_kernel_binding)
    assert prepare_worker_kernel(recipe, worker_kernel_binding) is prepared
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
        from corpus_structure.semantic.math_context import prepare_interpretation_context

        interpreted = prepare_interpretation_context(
            macros={}, kind="formula", context_profile=context
        )
        assert interpreted.model_id == context.model_id


def test_current_section_fixture_serializes_real_empty_and_formula_sections(tmp_path):
    """Exercise the converter boundary used by native consumers before capture."""
    import json
    from types import SimpleNamespace

    import pyarrow as pa

    from corpus_structure.ingest.pdf import PdfRecipe
    from semantic.current_pdf_source_support import section_content

    recipe = PdfRecipe(
        "0" * 40,
        "1" * 40,
        device="cpu",
        ocr_device="cpu",
        recipe_id="docling-standard-pdf-stream-v1",
    )
    from dataclasses import asdict

    from pdf_controlled_support import controlled_pdf_stream

    from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource, PdfStreamRequest
    from corpus_structure.semantic.pdf_certification import prepare_pdf_producer_contract
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

    original = tmp_path / "original.pdf"
    original.write_bytes(b"%PDF-1.7\ncontrolled converter content")
    with OwnedPdfSource.acquire(original, tmp_path / "owned") as source:
        request = PdfStreamRequest(
            source,
            tmp_path / "spool",
            tmp_path / "records",
            "current-test-build",
            "current-test-release",
            **asdict(prepare_pdf_producer_contract(trusted_pdf_context(), kind="native")),
        )
        reply = controlled_pdf_stream(
            SimpleNamespace(recipe=recipe, assets=None),
            request,
            section_content((("formula", "f(x)=x", "f(x)=x", "succeeded"), ("text", "", "", None))),
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
