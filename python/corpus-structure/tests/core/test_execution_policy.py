"""Physical policy validation applies equally to direct and settings/JSON callers."""

from dataclasses import FrozenInstanceError, asdict

import pytest
from pydantic import TypeAdapter, ValidationError

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

_POLICY = TypeAdapter(CharacterizationExecutionPolicy)


def test_selected_defaults_and_frozen_roundtrip():
    policy = CharacterizationExecutionPolicy()
    assert asdict(policy) == dict(
        workers=2,
        max_submissions=2,
        max_regions=2,
        max_active_stage_runs=2,
        max_claims=4,
        provider_threads=4,
        provider_interop_threads=1,
        cpu_native_threads=1,
        max_provider_jobs=2,
        max_owned_bytes=2 * 1024**3,
        max_packet_bytes=256 * 1024**2,
        max_reply_bytes=64 * 1024**2,
        max_native_request_bytes=8 * 1024**2,
        max_native_reply_bytes=8 * 1024**2,
    )
    assert _POLICY.validate_json(_POLICY.dump_json(policy)) == policy
    field = "workers"
    with pytest.raises(FrozenInstanceError):
        setattr(policy, field, 3)


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, "2", None, float("inf")])
def test_every_bound_is_a_strict_positive_integer(value):
    for field in asdict(CharacterizationExecutionPolicy()):
        with pytest.raises(ValueError):
            CharacterizationExecutionPolicy(**{field: value})
        with pytest.raises(ValidationError):
            _POLICY.validate_python({field: value})


def test_unknown_fields_and_impossible_transfer_reservations_refuse():
    with pytest.raises(ValidationError, match="unexpected_keyword_argument"):
        _POLICY.validate_python({"worker": 2})
    with pytest.raises(ValueError, match="CPU transfer"):
        CharacterizationExecutionPolicy(max_owned_bytes=1)
    with pytest.raises(ValueError, match="native transfer"):
        CharacterizationExecutionPolicy(max_owned_bytes=10, max_packet_bytes=1, max_reply_bytes=1)
