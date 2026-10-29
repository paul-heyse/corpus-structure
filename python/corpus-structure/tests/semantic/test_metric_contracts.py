"""Declared metric meaning, scope and lossless source values."""

from pathlib import Path

import pytest

from corpus_structure.core.method import MeasurementDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import MeasurementScope, ObservationOutcome, TaskUnitType
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.metrics import metric_definitions, observation_dependencies
from corpus_structure.semantic.observations import bind_result, observation_inputs, source_python
from corpus_structure.semantic.types import PreparationError, ResolvedDependencies


def release(content=None):
    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = observation_inputs(SourceBundle("core", (SourceArtifact("core", path.read_bytes()),)))
    return prepare_release(bundle, observation_dependencies(ResolvedDependencies(), content))


def measured(prepared, name="segment.chars", scope=MeasurementScope.SEGMENT, value=0.0):
    result = UnitResult(
        ref=UnitRef(TaskUnitType.SEGMENT, 4, "unit:4"),
        outcome=ObservationOutcome.EMPTY,
        measurements=(
            MeasurementDraft(
                metric=name, scope_type=scope, scope_id=4, scope_key="unit:4", value=value
            ),
        ),
    )
    return bind_result(
        prepared,
        source="source:1",
        method="profile.segments",
        operation_version="1",
        configuration_hash="config:1",
        input_hash="input:1",
        invocation_key="invoke:1",
        result=result,
    )


def test_packaged_metrics_are_explicit_and_source_value_is_preserved():
    prepared = release()
    assert set(metric_definitions(prepared)) == {
        "segment.chars",
        "segment.math_share",
        "segment.inline_math",
        "segment.display_math",
    }
    report = measured(prepared, value=-0.0).model_dump(mode="python")
    metric = report["measurements"][0]
    assert metric["scope_type"] == "segment"
    assert metric["scope_id"] == 4
    assert metric["value"]["hexadecimal"] == "-0x0.0p+0"
    assert source_python(metric["value"]) == -0.0
    assert report["method"] == "profile.segments"
    assert report["operation_version"] == "1"


def test_unresolved_metric_and_wrong_subject_refuse():
    prepared = release()
    with pytest.raises(ValueError, match="unresolved metric"):
        measured(prepared, name="unregistered.count")
    with pytest.raises(ValueError, match="subject differs"):
        measured(prepared, scope=MeasurementScope.RUN)


@pytest.mark.parametrize(
    "data",
    [
        b"metrics: [{id: x}]",
        b"metrics: {x: 1}",
        b"metrics: [{id: x, value_type: guessed, subject_kind: segment, detail_schema: "
        b"SourceObject, description: invalid}]",
    ],
)
def test_invalid_metric_declarations_fail_preparation(data):
    with pytest.raises(PreparationError) as error:
        release(data)
    assert error.value.diagnostics[0].code == "metric_definitions"
