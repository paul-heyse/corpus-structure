"""Source-report fidelity and identity, independent from admitted fact meaning."""

import math
from pathlib import Path

import pytest
from pydantic import BaseModel

from corpus_structure.core.method import ObservationDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, TaskUnitType
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.observations import bind_result, observation_inputs, source_python, source_value


def prepared():
    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(observation_inputs(SourceBundle("core", (SourceArtifact("core", path.read_bytes()),))))


def test_source_value_preserves_scalar_types_empty_containers_and_field_order():
    raw = {"absent_is_not_null": None, "integer": 2**100, "boolean": False,
           "negative_zero": -0.0, "text": "2", "array": [[], {}, {"β": "😀"}]}
    value = source_value(raw)
    assert value["fields"][1]["value"] == {"kind": "integer", "integer": 2**100}
    assert value["fields"][2]["value"] == {"kind": "boolean", "boolean": False}
    assert value["fields"][3]["value"] == {"kind": "float", "hexadecimal": "-0x0.0p+0"}
    restored = source_python(value)
    assert restored == raw
    assert list(restored) == list(raw)
    assert math.copysign(1.0, restored["negative_zero"]) == -1.0
    assert source_python(source_value({})) == {}


def test_source_tree_rejects_nonfinite_numbers_nonstring_fields_and_duplicate_names():
    with pytest.raises(ValueError, match="nonfinite"):
        source_value(float("nan"))
    with pytest.raises(TypeError, match="keys"):
        source_value({1: "not a string key"})
    with pytest.raises(ValueError, match="repeated"):
        source_python({"kind": "object", "fields": [
            {"name": "x", "position": 0, "value": {"kind": "null"}},
            {"name": "x", "position": 1, "value": {"kind": "null"}},
        ]})


class Payload(BaseModel):
    text: str


def result():
    draft = ObservationDraft(kind=ObservationKind.MENTION, payload=Payload(text="μ"),
                             payload_class=Payload, payload_version="1", span=(4, 5))
    return UnitResult(ref=UnitRef(TaskUnitType.SEGMENT, 99, "page#unit1"),
                      outcome=ObservationOutcome.PRODUCED, observations=(draft, draft))


def bind(release, **changes):
    kwargs = dict(source="source:original-content", method="extract", operation_version="2",
                  configuration_hash="config:1", input_hash="input:1", result=result())
    return bind_result(release, **(kwargs | changes)).model_dump(mode="python")


def test_binding_retains_repeated_items_and_replays_stable_keys():
    release = prepared()
    bound = bind(release)
    assert bound == bind(release)
    rows = bound["observations"]
    assert [row["item_key"] for row in rows] == ["mention/0", "mention/1"]
    assert len({row["observation_key"] for row in rows}) == 2
    assert [source_python(row["payload"]) for row in rows] == [{"text": "μ"}, {"text": "μ"}]
    assert [(row["span_start"], row["span_end"]) for row in rows] == [(4, 5), (4, 5)]
    changed = bind(release, input_hash="input:changed")
    assert changed["observations"][0]["observation_key"] != rows[0]["observation_key"]
    assert "SourceObservationBatch" in {definition.name for definition in release.definitions}


def test_coverage_is_explicit_and_not_inferred_from_empty_assertion_output():
    release = prepared()
    unit = UnitResult(ref=UnitRef(TaskUnitType.RENDITION, 4, "page"), outcome=ObservationOutcome.EMPTY)
    bound = bind(release, result=unit, coverage=({"family": "math", "scope": "page#math1",
                                               "outcome": "partial", "reason": "ambiguous parse"},))
    assert bound["observations"] == ()
    assert bound["coverage"][0]["outcome"] == "partial"
    assert bound["outcome"] == "empty"
