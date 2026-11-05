"""Retained-product resolution; controlled extraction is never a native provider pass."""

import json
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
        parse_detail=json.loads(canonical_bytes(product.parse_detail)),
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


def test_forward_resolver_keeps_full_typed_population_and_avoids_raw_re_adaptation(monkeypatch):
    from corpus_structure.methods import contribution_adapter
    from corpus_structure.semantic.contributions import contribution_identity
    from corpus_structure.semantic.observations import bind_result, source_value

    unit, ctx, upstream, worker = retained_fixture(monkeypatch)
    source = ctx.reader.source_view(unit.ref.unit_id)
    batch = contribution_adapter.replay_retained_contributions(ctx.reader, source, upstream)
    base = next(row for row in batch.contributions if row["kind"] == "proposal")
    extra = []
    for name in ("entity.fixture", "source_rule.fixture", "math.syntax"):
        row = dict(
            base,
            semantic_type=name,
            item_key=name,
            value=source_value(
                {"category": name, "nested": [{"tokens": ["Mean"], "coordinates": [0, 4]}]}
            ),
        )
        row["contribution_id"] = contribution_identity(row)
        extra.append(row)
    operations = tuple(
        dict(op, emitted_count=op["emitted_count"] + len(extra))
        if op["operation_key"] == base["operation_key"]
        else op
        for op in batch.operations
    )
    typed = (*batch.contributions, *extra)
    upstream.update(
        contributions=typed,
        contribution_operations=operations,
        contribution_coordinate_texts=batch.coordinate_texts,
    )
    for field in ("contributions", "contribution_operations", "contribution_coordinate_texts"):
        upstream[field] = json.loads(canonical_bytes(upstream[field]))
    monkeypatch.setattr(
        contribution_adapter,
        "restore_report",
        lambda *_: pytest.fail("sealed typed products must not be re-adapted"),
    )
    before = len(worker.calls)
    method = M1Readings()
    (result,) = method.run((unit,), M1ReadingConfig(), ctx)
    assert len(worker.calls) == before
    actual = {row["contribution_id"]: row for row in result.contributions or ()}
    assert all(
        canonical_bytes(actual[row["contribution_id"]]) == canonical_bytes(row) for row in typed
    )
    assert result.contribution_operations is not None
    assert all(
        any(
            canonical_bytes(op) == canonical_bytes(restored)
            for restored in result.contribution_operations
        )
        for op in operations
    )
    local = next(op for op in result.contribution_operations if "local_interpretation" in op)
    assert local["local_interpretation"]["outcome"] == "not_run"
    terminal = bind_result(
        ctx.reader.prepared,
        source=unit.ref.unit_key,
        method=method.name,
        operation_version=method.version,
        configuration_hash="fixture",
        input_hash="fixture",
        invocation_key="fixture",
        result=result,
    )
    assert len(terminal.model_dump()["contributions"]) >= len(typed)


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
    assert event["outcome"] == "completed" and event["feature_instance_digest"] == instance.digest
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


def test_resolver_decodes_archived_source_product_json_before_completion(monkeypatch):
    import json

    unit, ctx, upstream, worker = retained_fixture(monkeypatch)
    wire = json.loads(canonical_bytes(upstream))
    ctx.reader.source_result = lambda *_: wire
    before = len(worker.calls)
    (result,) = M1Readings().run((unit,), M1ReadingConfig(), ctx)
    assert result.records
    row = result.records[0]
    validated = ctx.reader.prepared.validate_python("SourceRecord", row)
    assert upstream["records"] is not None
    assert validated.record_id == upstream["records"][0]["record_id"]
    assert len(worker.calls) == before


def test_replay_projects_retained_raw_without_model_and_before_record_filter(monkeypatch):
    from copy import deepcopy

    unit, ctx, upstream, worker = retained_fixture(monkeypatch)
    before = deepcopy(upstream)
    calls = len(worker.calls)
    # Removing stronger record products cannot remove the returned local parts.
    upstream["records"] = ()
    frozen = deepcopy(upstream)
    (result,) = M1Readings().run((unit,), M1ReadingConfig(), ctx)
    assert len(worker.calls) == calls and upstream == frozen
    assert result.records == ()
    assert result.contributions and result.contribution_operations
    assert any(row["semantic_type"] == "definition.term" for row in result.contributions)
    assert all(row["standing"] == "retained_private" for row in result.contributions)
    assert result.contribution_coordinate_texts
    assert before["parse_detail"] == upstream["parse_detail"]


def test_replay_missing_retained_profile_routes_only_missing_report(monkeypatch):
    unit, ctx, upstream, worker = retained_fixture(monkeypatch)
    upstream["parse_detail"]["effective_profiles"] = {}
    calls = len(worker.calls)
    (result,) = M1Readings().run((unit,), M1ReadingConfig(), ctx)
    assert len(worker.calls) == calls
    assert result.contribution_operations
    assert all(row["outcome"] == "unsupported" for row in result.contribution_operations)
    assert any("effective profile" in row["reason"] for row in result.contribution_operations)
    assert result.contributions == ()


def test_historical_replay_consumes_exact_external_schema_without_reextracting(monkeypatch):
    unit, ctx, upstream, worker = retained_fixture(monkeypatch)
    packs = upstream["parse_detail"].pop("schema_packs")
    upstream["parse_detail"].pop("context_manifests")
    calls = len(worker.calls)
    (result,) = M1Readings().run((unit,), M1ReadingConfig(retained_schema_packs=packs), ctx)
    assert len(worker.calls) == calls and result.contributions
    assert result.contribution_operations is not None
    recovery = [row for row in result.contribution_operations if "local_interpretation" not in row]
    assert all(row["outcome"] in {"succeeded", "empty"} for row in recovery)
    local = [row for row in result.contribution_operations if "local_interpretation" in row]
    assert len(local) == 1 and local[0]["outcome"] == "not_run"
    assert local[0]["local_interpretation"]["probability_standing"] == "not_computed"
    assert result.coverage[0].outcome == "complete"


def test_explicit_historical_port_rebinds_new_alias_and_keeps_original_result(monkeypatch):
    from copy import deepcopy
    from dataclasses import replace
    from hashlib import sha256

    from corpus_structure.core.method import RetainedSourceResult
    from corpus_structure.semantic.source_views import PreparedSourceView

    unit, ctx, upstream, worker = retained_fixture(monkeypatch)
    old = ctx.reader.source_view(unit.ref.unit_id)
    current = PreparedSourceView(
        replace(old.ref, id=70, key="successor:source:70"),
        old.text,
        old.pieces,
        old.items,
        old.ancestors,
        old.health,
    )
    config = registry(ROOT / "domains/statistics").overlay("extract.m1_candidates", "default")
    retained = RetainedSourceResult(
        selected_task_id=37,
        task_id=37,
        run_id=14,
        release_id="archived-release",
        body_digest=sha256(canonical_bytes(upstream)).hexdigest(),
        prepared=ctx.reader.prepared,
        configuration=config.model_dump(mode="python"),
        result=upstream,
        source_views=(old,),
        source_bindings=(
            dict(
                original_source_view_id=old.ref.id,
                current_source_view_id=current.ref.id,
                original_source=old.ref.key,
                current_source=current.ref.key,
                physical_digest="a" * 64,
            ),
        ),
    )
    ctx.reader.source_view = lambda identity: current
    ctx.reader.source_result = lambda *_: pytest.fail("historical replay used current upstream")
    ctx.reader.retained_source_result = lambda source, task, method: retained
    ctx.reader.source_views = lambda: (current.ref,)
    unit.ref = UnitRef(TaskUnitType.SOURCE_VIEW, current.ref.id, current.ref.key)
    cfg = M1ReadingConfig(retained_source_tasks=(37,))
    assert cfg.source_dependencies == "retained_source_result"
    frozen, calls = deepcopy(upstream), len(worker.calls)
    method = M1Readings()
    assert method.select(SimpleNamespace(reader=ctx.reader), cfg) == (unit.ref,)
    original_digest = method.input_digest(unit, cfg)
    (result,) = method.run((unit,), cfg, ctx)
    assert len(worker.calls) == calls and upstream == frozen
    assert result.records == () and result.contributions
    assert all(row["pin"]["source"] == current.ref.key for row in result.contributions)
    assert all(row["pin"]["source_view_id"] == current.ref.id for row in result.contributions)
    assert any(
        "predecessor-contribution:" in dependency
        for row in result.contributions
        for dependency in row["computation_dependencies"]
    )
    assert result.parse_detail is not None
    retained_input = result.parse_detail["retained_input"]
    assert isinstance(retained_input, dict)
    original_pin = retained_input["original_source_pin"]
    assert isinstance(original_pin, dict)
    assert original_pin["source_view_id"] == old.ref.id
    assert result.contribution_operations is not None
    assert all(
        op["retained_task_id"] == 37 and op["retained_result_digest"] == retained.body_digest
        for op in result.contribution_operations
    )
    changed = replace(retained, body_digest="b" * 64)
    ctx.reader.retained_source_result = lambda *_: changed
    assert method.input_digest(unit, cfg) != original_digest


def test_historical_mode_has_no_implicit_or_ambiguous_fallback(monkeypatch):
    unit, ctx, _upstream, worker = retained_fixture(monkeypatch)
    cfg = M1ReadingConfig(retained_source_tasks=(37,))
    calls = len(worker.calls)
    ctx.reader.retained_source_result = lambda *_: (_ for _ in ()).throw(
        ValueError("physical source changed")
    )
    with pytest.raises(ValueError, match="physical source changed"):
        M1Readings().run((unit,), cfg, ctx)
    assert len(worker.calls) == calls
    with pytest.raises(ValueError, match="explicit retained"):
        M1ReadingConfig(source_dependencies="retained_source_result")
