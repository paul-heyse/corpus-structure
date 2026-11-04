"""Retained-product resolution; controlled extraction is never a native provider pass."""

from types import SimpleNamespace

import pytest

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import ObservationOutcome, Stage, TaskUnitType
from corpus_structure.methods.m1_readings import EVENT_PROCEDURE, M1ReadingConfig, M1Readings
from corpus_structure.methods.m1_source import M1Candidates, M1Config
from corpus_structure.orchestrate.m1 import registry, source_graph
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_policy import PolicyApplicability
from methods.test_m1_producer import ROOT, ControlledDecoder, owned_reader, view


def retained_fixture(monkeypatch, *, mode="definition"):
    source = view()
    reader = owned_reader(source)
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))
    ctx = SimpleNamespace(reader=reader, check_active=lambda: None)
    producer = M1Candidates()
    worker = ControlledDecoder(mode)
    monkeypatch.setattr(producer, "_resident", lambda _: worker)
    cfg = registry(ROOT / "domains/statistics").overlay(producer.name, "default")
    (product,) = producer.run((unit,), cfg, ctx)
    assert product.parse_detail is not None
    upstream = dict(
        method=producer.name,
        input_hash="retained-input",
        configuration_hash="retained-config",
        parse_detail=product.parse_detail,
        records=product.records,
        outcome=product.outcome.value,
    )
    reader.source_result = lambda *_: upstream
    unit.run = SimpleNamespace(reader=reader)
    return unit, ctx, upstream, worker


def test_readings_profile_is_explicit_and_retains_the_historical_profiles():
    methods = registry(ROOT / "domains/statistics")
    for name, inspection in (("default", False), ("described", False), ("readings", True)):
        cfg = methods.overlay("extract.m1_candidates", name)
        assert isinstance(cfg, M1Config) and cfg.source_inspection is inspection
    assert source_graph("readings").stages[-1][0] == Stage.ASSEMBLE
    assert source_graph("readings").stages[-1][1][0].config == "resolve.m1_readings/default"
    assert len(source_graph("default").stages) == len(source_graph("described").stages) == 2


def test_resolver_reuses_retained_candidates_and_seals_explicit_not_run_scores(monkeypatch):
    unit, ctx, upstream, worker = retained_fixture(monkeypatch)
    method, cfg = M1Readings(), M1ReadingConfig()
    before = len(worker.calls)
    (result,) = method.run((unit,), cfg, ctx)
    assert len(worker.calls) == before
    assert result.outcome is ObservationOutcome.PRODUCED
    assert result.records is not None and upstream["records"] is not None
    assert result.records[0]["record_id"] == upstream["records"][0]["record_id"]
    assert result.records[0]["interpretation_id"] != upstream["records"][0]["interpretation_id"]
    assert result.records[0]["standing"] == "candidate"
    assert result.parse_detail is not None
    events = result.parse_detail["record_policy_events"]
    assert isinstance(events, list)
    (event,) = events
    assert isinstance(event, dict)
    assert event["outcome"] == "not_run" and event["final_event_score"] is None
    assert event["event_procedure"] == EVENT_PROCEDURE
    assert result.parse_detail["seal"]
    (replay,) = method.run((unit,), cfg, ctx)
    assert replay == result and len(worker.calls) == before
    original_digest = method.input_digest(unit, cfg)
    upstream["configuration_hash"] = "changed-upstream-config"
    assert method.input_digest(unit, cfg) != original_digest
    assert len(worker.calls) == before


@pytest.mark.parametrize(
    "mode,outcome", [("empty", ObservationOutcome.EMPTY), ("failed", ObservationOutcome.FAILED)]
)
def test_resolver_preserves_upstream_empty_and_failure(monkeypatch, mode, outcome):
    unit, ctx, _upstream, _worker = retained_fixture(monkeypatch, mode=mode)
    (result,) = M1Readings().run((unit,), M1ReadingConfig(), ctx)
    assert result.outcome is outcome
    if mode == "failed":
        assert result.records is None and result.error
    else:
        assert result.records == ()


def test_resolver_refuses_changed_source_and_never_reruns_producer(monkeypatch):
    unit, ctx, upstream, _worker = retained_fixture(monkeypatch)
    upstream["parse_detail"]["source_pin"]["projection_digest"] = "e" * 64
    with pytest.raises(ValueError, match="source binding"):
        M1Readings().run((unit,), M1ReadingConfig(), ctx)
    ctx.reader.source_result = lambda *_: None
    with pytest.raises(ValueError, match="no source result"):
        M1Readings().run((unit,), M1ReadingConfig(), ctx)


def test_finite_feature_instance_scores_final_reading_without_repeating_extraction(monkeypatch):
    """Use the actual test-population fit, without a source-quality/admission claim."""
    import json
    from hashlib import sha256

    from semantic.test_record_policy import fitted

    unit, ctx, _upstream, worker = retained_fixture(monkeypatch)
    instance = fitted().model_copy(
        update={
            "applicability": PolicyApplicability(
                release_id=ctx.reader.prepared.release_id,
                family="definition",
                subset="statistics-m1-source-readings-2",
                assumptions="controlled method integration fixture",
            )
        }
    )
    cfg = M1ReadingConfig.model_validate_json(
        json.dumps({"feature_instances": [instance.model_dump(mode="json")]})
    )
    before = len(worker.calls)
    (result,) = M1Readings().run((unit,), cfg, ctx)
    assert len(worker.calls) == before and result.records is not None
    assert result.parse_detail is not None
    events = result.parse_detail["record_policy_events"]
    assert isinstance(events, list)
    (event,) = events
    assert isinstance(event, dict)
    assert event["outcome"] == "scored" and event["feature_instance_digest"] == instance.digest
    row = result.records[0]
    present_fraction = sum(f["state"] == "present" for f in row["fields"]) / len(row["fields"])
    expected = instance.parameters.intercept + instance.parameters.coefficients[0] * (
        (present_fraction - instance.parameters.center[0]) / instance.parameters.scale[0]
    )
    assert event["final_event_score"] == pytest.approx(expected)
    canonical = event["feature_input_canonical_json"]
    assert isinstance(canonical, str)
    assert json.loads(canonical) == [json.loads(canonical_bytes(row)), event["diagnostics"]]
    assert sha256(canonical.encode()).hexdigest() == event["feature_input_digest"]
    assert "record-feature-instance:" + instance.digest in row["computation_dependencies"]
    assert row["standing"] == "candidate"
