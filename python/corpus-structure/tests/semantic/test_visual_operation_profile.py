"""Current visual declarations compose genuine capture, external result and mapping."""

import builtins
import importlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.core.work import drive_prepared_work
from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.orchestrate.data_operations import _PythonWork
from corpus_structure.semantic import data_operation_prepared_products, visual_requests
from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_ports import PythonRoleValue, python_port_identity
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.file_custody import FileCustodyError
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_requests import (
    pdf_region_inputs,
    pdf_region_operation_sources,
)
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from corpus_structure.semantic.visual_requests import (
    visual_external_declaration,
    visual_operation_sources,
)
from semantic.test_pdf_visual_requests import selected_image


def _prepared_visual_profile(tmp_path):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = pdf_region_inputs(
        pdf_capture_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    recipe = PdfRecipe("0" * 40, "1" * 40, recipe_id="docling-standard-pdf-stream-v1")
    assets = PreparedPdfAssets(tmp_path, b"{}", ())
    sources = combine_primary_sources(
        pdf_region_operation_sources(
            pdf_capture_operation_sources(recipe, assets, directory=tmp_path / "owned")
        ),
        visual_operation_sources(),
    )
    from corpus_structure.semantic.composed import data_operation_dependencies

    declaration = visual_external_declaration()
    dependencies = data_operation_dependencies(
        ResolvedDependencies(), declarations=(declaration,), python_sources=sources
    )
    prepared = prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2"))
    model = compile_data_operations(
        schema=bundle,
        python_sources=sources,
        declarations=(declaration,),
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    return bundle, prepared, model, sources


def test_visual_profile_uses_external_native_receipt_and_mechanical_mapping(tmp_path):
    _, prepared, model, _ = _prepared_visual_profile(tmp_path)
    assert prepared.validate_python("DdoVisualSelection", {"page_no": 1}).model_dump(
        mode="python", exclude_unset=True
    ) == {"page_no": 1}
    for invalid in (
        {"page_no": 1, "pointer": "#/texts/0"},
        {"page_no": 1, "region_index": 0},
        {"page_no": 1, "rotation": 90},
    ):
        with pytest.raises(ValueError):
            prepared.validate_python("DdoVisualSelection", invalid)
    recognize = model.operation("source.visual/recognize")
    assert recognize.external is not None
    assert recognize.effects[0].fulfillment == "native-publication-receipt"
    assert recognize.dependencies == ("source.visual_input/render",)
    assert recognize.output_witnesses
    comparisons = recognize.output_witnesses[0].comparisons
    assert {value.output_field for value in comparisons} >= {
        "/image/content_digest",
        "/image/document",
        "/image/transform_json",
        "/image/selection",
    }
    mapping = model.operation("source.visual/map")
    assert mapping.dependencies == ("source.visual/recognize",) and not mapping.effects
    assert model.operation("source.visual_input/render").dependencies == ("source.pdf/capture",)


def test_mapping_brackets_work_and_refuses_changed_asset_on_function_local_import(
    tmp_path, monkeypatch
):
    from corpus_structure.ingest.chandra_mapping_operation import ChandraMappingOperation

    module = "controlled_late_visual_asset"
    asset_path = tmp_path / (module + ".py")
    asset_path.write_bytes(b"mapping_state = 'original'\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    original_profile = visual_requests.visual_mapping_profile()
    profile = json.loads(original_profile.content)
    profile["files"].append((str(asset_path), asset_path.read_bytes().hex()))
    artifact = SourceArtifact(original_profile.name, canonical_bytes(profile))
    monkeypatch.setattr(visual_requests, "visual_mapping_profile", lambda: artifact)
    bundle, prepared, model, sources = _prepared_visual_profile(tmp_path)
    operation = model.operation(visual_requests.VISUAL_MAP)
    base = python_port_identity(
        model,
        sources,
        operation.semantic_id,
        schema=bundle,
        prepared=prepared,
        declarations=(visual_external_declaration(),),
    )
    implementation = next(
        item for item in model.implementation_slices if item.root == operation.implementation_root
    )
    identity = PreparedCapabilityIdentity(
        **asdict(base),
        runtime="runtime:visual-correspondence-control",
        assets=canonical_bytes(
            tuple(asdict(item) for item in (*operation.assets, *implementation.boundaries))
        ),
    )
    authorized = []
    port = ChandraMappingOperation.acquire_port(
        prepared,
        model,
        operation.semantic_id,
        identity=identity,
        authorize=authorized.append,
        custody=sources.boundary_contracts,
        sources=sources,
    )
    assert authorized == [identity]

    def forbid_reacquisition(*args, **kwargs):
        pytest.fail("mapping repeated full correspondence during a computation")

    monkeypatch.setattr(
        data_operation_prepared_products, "verify_prepared_product", forbid_reacquisition
    )
    incoming = next(role for role in operation.roles if role.direction == "input")
    kind = next(
        item.key
        for item in model.identities
        if (item.owner, item.domain) == (incoming.kind, "kind")
    )
    raw = "no structured visual content"
    observation = dict(
        image=selected_image(),
        raw_response=raw,
        response_digest=sha256(raw.encode()).hexdigest(),
        finish_reason="end_of_sequence",
        runtime_identity_json="{}",
        provider_outcome="succeeded",
        diagnostic="",
    )

    def run_mapping():
        with ThreadPoolExecutor(max_workers=1) as pool:
            plan = port.plan_python(
                (PythonRoleValue(incoming.name, kind, observation),),
                binding=SimpleNamespace(
                    sufficient=True,
                    operation=operation.semantic_id,
                    parameters=canonical_bytes(semantic_value({})),
                ),
                execution_owner=SimpleNamespace(
                    submit_python=lambda compute: _PythonWork(pool.submit(compute), lambda: None)
                ),
            )
            return drive_prepared_work(plan, lambda: None)

    completion = run_mapping()
    assert completion.outputs[0].value()["source_fidelity"] == "unassessed"
    assert authorized == [identity] * 3

    real_import = builtins.__import__

    def import_changed_asset(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pdf_visual_mapping" and level == 1 and fromlist == ("map_visual_result",):
            assert module not in sys.modules
            asset_path.write_bytes(b"mapping_state = 'changed during work'\n")
            assert importlib.import_module(module).mapping_state == "changed during work"
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_changed_asset)
    try:
        with pytest.raises(FileCustodyError, match="acquired file changed"):
            run_mapping()
    finally:
        sys.modules.pop(module, None)
