"""Restricted fitter transport and captured grade-shape controls."""

from copy import deepcopy
import json
import math

import pytest
from jsonschema import Draft7Validator, ValidationError

from corpus_structure.evaluate.declared_record_policy import DdoRecordGrade
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.record_policy_native import (
    read_record_feature_fit_frame, record_policy_grade_schema,
)
from evaluate.test_declared_record_policy import grade_frame


def selection():
    return CutSelection(json_bytes(dict(
        project_id="project:one", demand_id="demand:one", release_id="release:one",
        runtime_id="runtime:one", read_id="read:one", read_snapshot="1:2:",
        frontier_at="2026-11-15T00:00:00+00:00", selection={}, scope={}, trust_snapshot={},
    )))


def test_captured_grade_schema_preserves_closed_fields_and_exact_three_pass_tuple():
    schema = json.loads(record_policy_grade_schema())
    grade = DdoRecordGrade.from_frame(grade_frame()).model_dump(mode="json")
    validator = Draft7Validator(schema)
    validator.validate(grade)
    for change in ("extra", "missing-custody", "two-passes", "four-passes", "unknown-partition"):
        value = deepcopy(grade)
        if change == "extra": value["labels"] = []
        elif change == "missing-custody": del value["frame_canonical_json"]
        elif change == "two-passes": value["frame"]["reference_passes"].pop()
        elif change == "four-passes": value["frame"]["reference_passes"].append(value["frame"]["reference_passes"][0])
        else: value["frame"]["partition"] = "ordinary"
        with pytest.raises(ValidationError):
            validator.validate(value)


def test_fit_transport_preserves_actual_cut_bytes_and_rejects_substituted_selection(monkeypatch):
    cut = selection()
    grade = DdoRecordGrade.from_frame(grade_frame()).model_dump(mode="json")
    result = dict(cut=cut.record, product_id="product:grade", derivation_id="derivation:grade",
                  receipt_id="receipt:grade", frame=grade)
    requests = []

    def read(storage, request):
        requests.append(request)
        return result

    monkeypatch.setattr(DataOperationStorage, "read_record_feature_fit_frame", read)
    args = dict(project_id="project:one", demand_id="demand:one", read_id="read:one",
                use_id="use:grade", product_id="product:grade", derivation_id="derivation:grade",
                expected_cut=cut.identity, frame_digest=grade["frame_digest"], cut=cut)
    assert read_record_feature_fit_frame(object(), **args) == result
    assert requests[0]["cut_canonical_json"].encode() == cut.content
    with pytest.raises(ValueError, match="exact retained cut bytes"):
        read_record_feature_fit_frame(object(), **{**args, "expected_cut": "cut-selection:" + "0" * 64})
    assert len(requests) == 1
    result["cut"] = {**cut.record, "runtime_id": "runtime:other"}
    with pytest.raises(ValueError, match="another retained cut"):
        read_record_feature_fit_frame(object(), **args)
    result["cut"] = cut.record
    result["product_id"] = "product:other"
    with pytest.raises(ValueError, match="another protected grade"):
        read_record_feature_fit_frame(object(), **args)


def test_fit_transport_restores_signed_zero_from_authenticated_canonical_frame(monkeypatch):
    cut = selection()
    frame = grade_frame()
    event = frame.events[0]
    features = event.features.model_copy(update={"values": (-0.0,)})
    frame = frame.model_copy(update={"events": (event.model_copy(update={"features": features}),)})
    grade = DdoRecordGrade.from_frame(frame).model_dump(mode="json")
    projected = deepcopy(grade)
    projected["frame"]["events"][0]["features"]["values"][0] = 0.0
    monkeypatch.setattr(DataOperationStorage, "read_record_feature_fit_frame", lambda *args: dict(
        cut=cut.record, product_id="product:grade", derivation_id="derivation:grade",
        receipt_id="receipt:grade", frame=projected,
    ))
    restored = read_record_feature_fit_frame(object(), project_id="project:one", demand_id="demand:one",
        read_id="read:one", use_id="use:grade", product_id="product:grade", derivation_id="derivation:grade",
        expected_cut=cut.identity, frame_digest=grade["frame_digest"], cut=cut)
    assert math.copysign(1.0, restored["frame"]["frame"]["events"][0]["features"]["values"][0]) == -1.0
    assert restored["frame"]["frame_canonical_json"] == grade["frame_canonical_json"]
