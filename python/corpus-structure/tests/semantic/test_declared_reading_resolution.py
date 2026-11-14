"""Independent reading-score expectations; controlled ingress is not native admission."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.reading_resolution_products import (
    RECIPE,
    reading_resolution_inputs,
    reading_resolution_operation_sources,
    resolve_reading_values,
    resolved_reading_events,
)
from corpus_structure.semantic.record_policy import (
    FEATURES,
    FeatureInstance,
    FitDiagnostics,
    LinearParameters,
    PolicyApplicability,
    RecordAlgorithm,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def prepared_ingress():
    fields = SimpleNamespace(ancestors=("SemanticRecordFields",), properties=(SimpleNamespace(name="family", equals_string="table"), SimpleNamespace(name="value")))
    return SimpleNamespace(release_id="controlled-release", index=SimpleNamespace(definitions={"ControlledFields": fields}), validate_json=lambda name, content: SimpleNamespace(model_dump=lambda **kwargs: json.loads(content)))


def candidate_report():
    body = {"candidate_type": "record", "contract": "ControlledFields", "standing": "candidate", "family": "table", "record_id": "same-occurrence", "interpretation_id": "original-reading", "policy_version": "actual-source-policy", "computation_dependencies": ["native-group:one"], "fields": [{"role": "value", "state": "present", "evidence_status": "available", "kind": "literal"}], "anchors": [{"precision": "exact"}]}
    return {"standing": "private_uncalibrated_candidates", "inspection_outcome": "produced", "source_pin": {"source": "actual-retained-source"}, "members": ({"member_id": "original-member", "kind_contract": "actual-record-kind", "context": {"subject": "original-occurrence"}, "body": body},), "diagnostics_json": json.dumps({"model_observations": [{"raw_confidence": 0.25}], "reports": [{"diagnostics": [{"group_dependency": "native-group:one", "code": "actual", "group": 0}, {"group_dependency": "native-group:one", "code": "actual", "group": 1}]}]})}


def feature():
    algorithm = RecordAlgorithm(features=(FEATURES[0],))
    return FeatureInstance(algorithm=algorithm, applicability=PolicyApplicability(release_id="controlled-release", family="table", subset="controlled-subset", assumptions="independent fixed feature fixture"), parameters=LinearParameters(feature_signature=algorithm.feature_signature, names=("present_fraction",), coefficients=(3.0,), center=(0.5,), scale=(2.0,), intercept=-0.25), fit=FitDiagnostics(partition="feature_fit", frame_digest="a" * 64, reference_digest="b" * 64, coverage_digest="c" * 64, provenance="controlled previously fitted fixture", negative_count=2, positive_count=2, declared_origin_group_count=2, conditioning_assumptions="fixed finite fixture", converged=True, iterations=1, standing="fitted", reason="actual explicit parameters"))


def policy(instances=()):
    return {"version": "reading-feature-policy-1", "recipe": RECIPE, "subset": "controlled-subset", "feature_instances": source_value([value.model_dump(mode="json") for value in instances])}


def test_reading_producer_has_closed_factory_and_source_witness():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = reading_resolution_inputs(SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)))
    model = compile_data_operations(bundle, python_sources=reading_resolution_operation_sources())
    operation = model.operation("resolve.m1_readings/declared")
    assert operation.capabilities.prepared_factory is not None
    assert len(operation.output_witnesses) == 1
    assert all(value.complete for value in model.implementation_slices)


def test_reading_scoring_retains_real_center_scale_parameters_and_raw_observations():
    upstream = candidate_report()
    product = resolve_reading_values(prepared_ingress(), upstream, policy((feature(),)))
    (event,) = resolved_reading_events(product)
    assert event["outcome"] == "completed"
    assert event["final_event_score"] == pytest.approx(-0.25 + (1.0 - 0.5) / 2.0 * 3.0)
    assert event["feature_instance_digest"] == feature().digest
    assert len(event["feature_diagnostics"]) == 1
    detail = json.loads(product["diagnostics_json"])
    assert detail["producer_diagnostics"]["model_observations"] == [{"raw_confidence": 0.25}]
    assert upstream["members"][0]["body"]["interpretation_id"] == "original-reading"
    assert product["members"][0]["body"]["record_id"] == "same-occurrence"
    assert product["members"][0]["body"]["interpretation_id"] != "original-reading"


@pytest.mark.parametrize("mismatch", ["release_id", "family", "subset"])
def test_reading_policy_never_applies_outside_exact_applicability(mismatch):
    instance = feature()
    values = instance.applicability.model_dump(mode="json")
    values[mismatch] = "definition" if mismatch == "family" else "other"
    instance = instance.model_copy(update={"applicability": PolicyApplicability(**values)})
    product = resolve_reading_values(prepared_ingress(), candidate_report(), policy((instance,)))
    (event,) = resolved_reading_events(product)
    assert event["outcome"] == "not_run"
    assert event["final_event_score"] is None
    assert event["feature_instance_digest"] is None


def test_reading_resolution_keeps_unavailable_policy_honest_and_refuses_duplicate_instances():
    product = resolve_reading_values(prepared_ingress(), candidate_report(), policy())
    (event,) = resolved_reading_events(product)
    assert event["outcome"] == "not_run" and event["final_event_score"] is None
    with pytest.raises(ValueError, match="repeats a fitted instance"):
        resolve_reading_values(prepared_ingress(), candidate_report(), policy((feature(), feature())))
