"""Released policy shape and byte custody, without evaluator authority claims."""

from copy import deepcopy
from functools import cache
from typing import Any

import pytest

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.record_policy import RecordAcceptanceInstance
from corpus_structure.semantic.record_policy_products import (
    record_policy_inputs,
    validate_record_policy_binding,
)

from .test_record_contracts import release_inputs
from .test_record_policy import calibrated, fitted


@cache
def prepared():
    bundle, profile, _ = release_inputs()
    return prepare_release(record_policy_inputs(bundle), profile=profile)


def binding() -> dict[str, Any]:
    p = prepared()
    feature = fitted()
    feature = feature.model_copy(
        update={
            "applicability": feature.applicability.model_copy(update={"release_id": p.release_id})
        }
    )
    instance = RecordAcceptanceInstance(
        feature=feature,
        calibration=calibrated(feature),
        threshold=0.97,
        threshold_procedure="fixed-before-assessment",
        conditioning_assumptions="finite frozen frame",
    )
    return dict(
        instance=instance.model_dump(mode="json"),
        instance_digest=instance.digest,
        instance_canonical_json=canonical_bytes(instance.model_dump(mode="json")).decode(),
        evaluation_id=1,
        evaluation_digest="d" * 64,
    )


def test_policy_binding_requires_released_shape_and_exact_canonical_parameters():
    value = binding()
    result = validate_record_policy_binding(prepared(), value)
    assert result.threshold == 0.97
    assert result.digest == value["instance_digest"]
    assert "RecordPolicyBinding" in prepared().index.definitions


@pytest.mark.parametrize("mutation", ["digest", "bytes", "body", "extra", "release", "algorithm"])
def test_policy_binding_refuses_parameter_and_byte_drift(mutation):
    value = deepcopy(binding())
    if mutation == "digest":
        value["instance_digest"] = "0" * 64
    elif mutation == "bytes":
        value["instance_canonical_json"] += " "
    elif mutation == "body":
        value["instance"]["threshold"] = 0.5
    elif mutation == "extra":
        value["labels"] = []
    elif mutation == "release":
        value["instance"]["feature"]["applicability"]["release_id"] = "release:other"
    else:
        value["instance"]["feature"]["algorithm"]["solver"] = "liblinear"
    with pytest.raises(ValueError):
        validate_record_policy_binding(prepared(), value)
