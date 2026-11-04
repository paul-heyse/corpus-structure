"""Evaluator candidate correctness preserves private standing and exact full readings."""
from copy import deepcopy

import pytest

from corpus_structure.evaluate.record_policy import _diagnostics, whole_reading_correct

from .test_record_alignment import finish, frame, prepared, reading, role


def test_candidate_correctness_does_not_require_or_grant_public_acceptance():
    reference, contexts = reading("table")
    candidate = deepcopy(reference)
    candidate["standing"] = "candidate"
    before = deepcopy(candidate)
    assert whole_reading_correct(
        prepared(), candidate, (reference,), frame(reference), coordinate_texts=contexts
    )
    assert candidate == before
    assert candidate["standing"] == "candidate"


def test_complete_wrong_reading_and_nonpresent_meaning_are_negative_labels():
    reference, contexts = reading("table")
    candidate = deepcopy(reference)
    candidate["standing"] = "candidate"
    note = role(candidate, "note")
    note.clear()
    note.update(role="note", kind="literal", state="unstated", meaning_changing=True,
                evidence_status="unavailable", evidence_sets=(), reason="not observed")
    finish(candidate)
    assert not whole_reading_correct(
        prepared(), candidate, (reference,), frame(reference), coordinate_texts=contexts
    )


def test_stale_source_binding_refuses_instead_of_becoming_a_negative_label():
    reference, contexts = reading("table")
    candidate = deepcopy(reference)
    candidate["standing"] = "candidate"
    candidate["policy_version"] = "another-policy"
    finish(candidate)
    with pytest.raises(ValueError, match="policy"):
        whole_reading_correct(
            prepared(), candidate, (reference,), frame(reference), coordinate_texts=contexts
        )


def test_diagnostics_follow_exact_native_group_dependencies_not_array_positions():
    owned = {"group_dependency": "native-group:owned", "role": "note", "code": "unlocated"}
    other = {"group_dependency": "native-group:other", "role": "note", "code": "unlocated"}
    unbound = {"role": "note", "code": "unlocated"}
    detail = {"reports": [{"diagnostics": [other, unbound]}, {"diagnostics": [owned]}]}
    assert _diagnostics({"computation_dependencies": ["native-group:owned"]}, detail) == [owned]
    assert _diagnostics({"computation_dependencies": []}, detail) == []
