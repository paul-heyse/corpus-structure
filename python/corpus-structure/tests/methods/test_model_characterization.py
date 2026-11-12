"""Baseline questions execute independently and unavailable providers stay explicit."""

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from semantic.test_model_characterization import builder, d1_reply, scope
from semantic.test_model_characterization import prepared as prepared

from corpus_structure.core.method import MethodContext, MethodSettings, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.model_characterization import (
    ModelCharacterizationConfig,
    ModelCharacterizationMethod,
)
from corpus_structure.semantic.interpretation_questions import declared_families
from corpus_structure.semantic.model_characterization import (
    CHARACTERIZATION_FAMILIES,
    question_manifest,
)


def inputs(prepared):
    selected = scope()
    draft = builder(selected)
    cfg = ModelCharacterizationConfig(
        characterization_base_document=draft.base,
        characterization_source_scope=draft.scope,
        question_manifest=question_manifest(prepared),
    )
    reader = SimpleNamespace(
        prepared=prepared,
        source_views=lambda: (selected.view.ref,),
        source_view=lambda identity: selected.view,
        characterization_layers=lambda pins: {},
    )
    run = SimpleNamespace(reader=reader)
    unit = UnitView(UnitRef(TaskUnitType.DOCUMENT, selected.view.ref.document_id), run)
    operation: dict[str, str] = {
        **{key: value for key, value in draft.operation.items() if isinstance(value, str)},
        "key": "text.model_characterization",
        "version": ModelCharacterizationMethod.version,
        "model": cfg.model,
        "grammar": cfg.grammar,
        "context": cfg.context,
    }
    ctx = MethodContext(
        run,
        reader,
        MethodSettings(data_dir=Path("."), model_cache=Path("/fixture-model-cache")),
        logging.getLogger(__name__),
        characterization_operation=lambda ref: operation,
    )
    return selected, draft, cfg, unit, ctx


def test_unavailable_profiles_publish_partial_family_outcomes_without_hidden_calls(
    prepared, monkeypatch
):
    from corpus_structure.methods import model_characterization

    selected, _draft, cfg, unit, ctx = inputs(prepared)

    def forbidden(*args, **kwargs):
        raise AssertionError("unavailable profile started native inference")

    monkeypatch.setattr(model_characterization, "pm2_client", forbidden)
    monkeypatch.setattr(model_characterization, "gliner_extract", forbidden)
    method = ModelCharacterizationMethod()
    assert tuple(method.select(unit.run, cfg)) == (unit.ref,)
    (result,) = method.run([unit], cfg, ctx)
    layer = result.characterization_layer
    assert layer is not None and layer.payload["outcome"] == "partial"
    assert {row["family"] for row in layer.payload["coverage"]} == set(CHARACTERIZATION_FAMILIES)
    assert all(row["outcome"] == "failed" for row in layer.payload["coverage"])
    assert result.cost is not None
    # The natural retained source view is the complete default examined context.
    scopes = method._scopes(unit.run.reader, cfg, builder(selected))
    assert len(scopes) == 1 and scopes[0].examined == (0, 7)


def test_all_source_first_families_run_when_no_candidate_exists(prepared):
    selected, output, _cfg, _unit, ctx = inputs(prepared)
    families = declared_families(prepared.registry_rows)

    class FixtureWorker:
        def __init__(self):
            self.startup = dict(provider="fixture-d1", calibration="fixture-calibration")
            self.keys = []

        def infer(self, request, *, check_active):
            replies = []
            for payload in request["batch"]:
                self.keys.extend(payload["questions"])
                questions: dict[str, Any] = {}
                for key, question in payload["questions"].items():
                    if question["type"] == "text":
                        questions[key] = dict(
                            type="text", found=0.1, span=None, text=None, path=None
                        )
                    else:
                        questions[key] = dict(
                            type="choice",
                            choices=["assertion"],
                            probabilities={
                                label: 0.8 if label == "assertion" else 0.02
                                for label in question["criteria"]
                            },
                        )
                wrapped = SimpleNamespace(payload=payload)
                replies.append(d1_reply(wrapped, questions))
            if False:
                yield ()
            return dict(batch=replies)

    from corpus_structure.core.method import drive_prepared_work

    worker = FixtureWorker()
    drive_prepared_work(
        ModelCharacterizationMethod()._d1_work(worker, ctx, output, [selected], families, {}),
        ctx.check_active,
    )
    assert {
        "modal_cue",
        "quantifier_cue",
        "negative_cue",
        "attribution_cue",
        "functions",
        "function_support",
    } <= set(worker.keys)
    assert not {"host", "referent"} & set(worker.keys)
    assert any(
        annotation.get("model_answer", {}).get("state") == "dependency_unresolved"
        for annotation in output.annotations
    )
    assert not output.proposals.get((selected.identity + "character_scope_v1", "relative_scope"))
    assert output.covered["character_host_choice_v1"][0][1] == "partial"
    assert output.covered["character_referent_choice_v1"][0][1] == "partial"


def test_changed_released_question_manifest_cannot_reuse_frozen_config(prepared):
    _selected, _output, cfg, unit, _ctx = inputs(prepared)
    method = ModelCharacterizationMethod()
    with pytest.raises(ValueError, match="question manifest"):
        method.select(unit.run, cfg.model_copy(update={"question_manifest": None}))
    assert cfg.question_manifest is not None
    altered = {**cfg.question_manifest, "character_scope_v1": "0" * 64}
    with pytest.raises(ValueError, match="question manifest"):
        method.select(unit.run, cfg.model_copy(update={"question_manifest": altered}))


def test_candidate_discovery_uses_active_selection_and_retains_validation_closure(
    prepared, monkeypatch
):
    from corpus_structure.methods import model_characterization

    _selected, _draft, cfg, unit, ctx = inputs(prepared)
    method = ModelCharacterizationMethod()
    (initial,) = method.run([unit], cfg, ctx)
    assert initial.characterization_layer is not None
    retained = initial.characterization_layer
    active, old = retained.reference(101), retained.reference(100)
    cfg = cfg.model_copy(update={"characterization_layers": (active.values(),)})
    monkeypatch.setattr(
        model_characterization,
        "_dependency_closure",
        lambda _reader, _pins: {active: retained, old: retained},
    )
    original = method._d1
    seen = []

    def capture(cfg, ctx, builder, scopes, families, dependencies, providers):
        seen.extend(dependencies)
        return original(cfg, ctx, builder, scopes, families, dependencies, providers)

    monkeypatch.setattr(method, "_d1", capture)
    (result,) = method.run([unit], cfg, ctx)
    assert seen == [active]
    assert result.characterization_layer is not None
    assert result.characterization_layer.payload["dependencies"] == [active.values(), old.values()]
    assert result.characterization_layer.payload["operation"]["required_layers"] == [
        active.values()
    ]


def test_current_d1_configuration_requires_cuda_without_cpu_fallback():
    from pydantic import ValidationError

    from corpus_structure.orchestrate.pm2_stage import InterpretationProfile

    assert ModelCharacterizationConfig().d1_device == "cuda"
    with pytest.raises(ValidationError, match="cuda"):
        ModelCharacterizationConfig.model_validate({"d1_device": "cpu"})
    startup = dict(provider="d1", device="cuda:0", dtype="torch.bfloat16")
    assert InterpretationProfile(provider="d1", startup=startup).device == "cuda"
    with pytest.raises(ValidationError, match="cuda"):
        InterpretationProfile.model_validate(dict(provider="d1", device="cpu", startup=startup))
    with pytest.raises(ValidationError, match="bfloat16"):
        InterpretationProfile(provider="d1", startup={**startup, "dtype": "torch.float32"})


def test_native_d1_cpu_refusal_precedes_model_or_asset_loading(tmp_path):
    from corpus_structure.methods.pm2_native import _load_d1, _load_profile

    with pytest.raises(ValueError, match="requires CUDA"):
        _load_d1(tmp_path / "no-assets", "cpu")
    profile = tmp_path / "profile.json"
    profile.write_text('{"provider":"d1","device":"cpu"}')
    with pytest.raises(ValueError, match="requires CUDA"):
        _load_profile(profile)
