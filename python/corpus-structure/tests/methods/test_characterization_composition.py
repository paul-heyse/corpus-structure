"""Ordinary composition selects exact retained inputs and preserves weaker profiles."""

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from semantic.test_characterization import layer_payload

from corpus_structure.core.method import MethodContext, MethodSettings, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.characterization import ComposeViewConfig, ComposeViewMethod
from corpus_structure.orchestrate.phase0 import registry
from corpus_structure.semantic.characterization import validate_layer, _published_layer_manifest
from corpus_structure.semantic.product_reference import ProductReference


@pytest.fixture(scope="module")
def prepared():
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.characterization import characterization_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    return prepare_release(characterization_inputs(bundle))


def inputs(prepared):
    body = layer_payload(prepared)
    base = ProductReference(**body["base_document"])
    ref = SimpleNamespace(id=11, document_id=17, native_product=base)
    reader = SimpleNamespace(
        prepared=prepared, source_views=lambda: [ref], characterization_layers=lambda pins: {}
    )
    reader.characterization_manifests = lambda pins: {
        pin: _published_layer_manifest(pin, {
            key: value for key, value in report.payload.items()
            if key in {"format", "release_id", "base_document", "operation", "source_scope", "outcome", "dependencies", "coverage"}
        })
        for pin, report in reader.characterization_layers(pins).items()
    }
    run = SimpleNamespace(reader=reader)
    unit = UnitView(UnitRef(TaskUnitType.DOCUMENT, 17), run)
    return body, reader, run, unit


def context(unit):
    return MethodContext(
        unit.run,
        unit.run.reader,
        MethodSettings(data_dir=Path("."), model_cache=Path(".")),
        logging.getLogger(__name__),
    )


def test_source_only_is_real_registered_method_and_returns_terminal_view(prepared, tmp_path):
    body, _reader, run, unit = inputs(prepared)
    method = registry(tmp_path).method("text.compose_view")
    cfg = ComposeViewConfig(
        characterization_base_document=body["base_document"],
        characterization_source_scope=body["source_scope"],
    )
    assert list(method.select(run, cfg)) == [unit.ref]
    (result,) = method.run([unit], cfg, context(unit))
    assert result.characterization_view is not None
    assert result.characterization_view.payload["profile"] == "source_only"
    assert result.characterization_view is not None
    assert result.characterization_view.payload["layers"] == []
    assert result.characterization_view is not None
    assert result.characterization_view.payload["coverage"] == []


def test_selected_layer_closure_is_retained_and_all_determinants_change_input(prepared):
    body, reader, _run, unit = inputs(prepared)
    report = validate_layer(prepared, body)
    pin = report.reference(19)
    reader.characterization_layers = lambda pins: {pin: report}
    cfg = ComposeViewConfig(
        characterization_base_document=body["base_document"],
        characterization_source_scope=body["source_scope"],
        characterization_layers=(pin.values(),),
        characterization_profile="selected_layers",
    )
    method = ComposeViewMethod()
    (result,) = method.run([unit], cfg, context(unit))
    assert result.characterization_view is not None
    assert result.characterization_view.payload["coverage"] == report.payload["coverage"]
    assert result.characterization_view is not None
    assert result.characterization_view.payload["layers"] == [pin.values()]
    source_only = cfg.model_copy(
        update={"characterization_layers": (), "characterization_profile": "source_only"}
    )
    assert method.input_digest(unit, cfg).bytes != method.input_digest(unit, source_only).bytes


def test_unbound_config_and_wrong_document_refuse(prepared):
    body, _reader, run, unit = inputs(prepared)
    with pytest.raises(ValueError, match="explicit base"):
        ComposeViewMethod().select(run, ComposeViewConfig())
    cfg = ComposeViewConfig(
        characterization_base_document=body["base_document"],
        characterization_source_scope=body["source_scope"],
    )
    with pytest.raises(ValueError, match="task unit"):
        ComposeViewMethod().run(
            [UnitView(UnitRef(TaskUnitType.DOCUMENT, 99), run)], cfg, context(unit)
        )
    with pytest.raises(ValueError, match="source_only"):
        ComposeViewConfig(
            characterization_layers=(dict(task_id=1, product_key="layer", content_digest="a" * 64),)
        )


def test_composition_resolves_original_release_without_rewriting_retained_layer(prepared):
    from semantic.test_characterization_replay import construction_release_inputs

    from corpus_structure.semantic import prepare_release

    body, reader, _run, unit = inputs(prepared)
    report = validate_layer(prepared, body)
    pin = report.reference(19)
    newer = prepare_release(construction_release_inputs())
    reader.prepared = newer
    reader.characterization_layers = lambda pins: {pin: report}
    resolved = []

    def release(identity):
        resolved.append(identity)
        assert identity == prepared.release_id
        return prepared

    reader.characterization_release = release
    cfg = ComposeViewConfig(
        characterization_base_document=body["base_document"],
        characterization_source_scope=body["source_scope"],
        characterization_layers=(pin.values(),),
        characterization_profile="selected_layers",
    )
    (result,) = ComposeViewMethod().run([unit], cfg, context(unit))
    assert result.characterization_view is not None
    assert result.characterization_view.payload["release_id"] == newer.release_id
    assert result.characterization_view.payload["layers"] == [pin.values()]
    assert report.payload["release_id"] == prepared.release_id
    # Original-release authentication belongs to the protected manifest read, not a
    # fresh whole-layer reconstruction during composition.
    assert resolved == []


def test_dependency_retention_does_not_select_its_interpretations(prepared):
    from copy import deepcopy

    from corpus_structure.semantic.characterization import validate_view

    body, reader, _run, unit = inputs(prepared)
    old = validate_layer(prepared, body)
    old_pin = old.reference(19)
    newer_body = deepcopy(body)
    newer_body["dependencies"] = [old_pin.values()]
    newer_body["operation"]["input"] = "refreshed-rules"
    newer_body["coverage"][0]["reason"] = "newly selected analysis"
    new = validate_layer(prepared, newer_body, dependencies={old_pin: old})
    new_pin = new.reference(20)
    closure = {old_pin: old, new_pin: new}
    reader.characterization_layers = lambda pins: closure
    cfg = ComposeViewConfig(
        characterization_base_document=body["base_document"],
        characterization_source_scope=body["source_scope"],
        characterization_layers=(old_pin.values(), new_pin.values()),
        characterization_active_layers=(new_pin.values(),),
        characterization_profile="selected_layers",
    )
    (result,) = ComposeViewMethod().run([unit], cfg, context(unit))
    assert result.characterization_view is not None
    view = result.characterization_view.payload
    assert view["layers"] == [old_pin.values(), new_pin.values()]
    assert view["active_layers"] == [new_pin.values()]
    assert view["coverage"] == new.payload["coverage"]
    with pytest.raises(ValueError, match="coverage"):
        validate_view(prepared, {**view, "coverage": old.payload["coverage"]}, closure)
    with pytest.raises(ValueError, match="active layer"):
        validate_view(
            prepared, {**view, "active_layers": [new_pin.values(), new_pin.values()]}, closure
        )
    with pytest.raises(ValueError, match="dependency closure"):
        validate_view(prepared, {**view, "layers": [new_pin.values()]}, closure)
