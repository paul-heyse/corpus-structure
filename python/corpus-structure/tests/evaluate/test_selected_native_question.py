"""Independent whole-block question bounds; no provider/native acquisition evidence."""

from copy import deepcopy

import pytest
from pydantic import ValidationError
from semantic.test_selected_references import reference_body

from corpus_structure.evaluate.native_scoring import SelectedNativeScoringQuestion
from corpus_structure.evaluate.selected_references import _reference_invariants
from corpus_structure.semantic.observations import source_value


def question():
    return dict(
        projection="a" * 64,
        start=7,
        end=16,
        reference=dict(
            kind="tokenization",
            text="Ada acts.",
            words=["Ada", "acts", "."],
            spaces=[True, False, False],
        ),
    )


def test_whole_block_native_question_requires_exact_extent_and_native_scheme():
    value = question()
    actual = SelectedNativeScoringQuestion.model_validate(value)
    assert (actual.start, actual.end, actual.reference.text) == (7, 16, "Ada acts.")
    for mutation in ({"end": 15}, {"start": True}, {"projection": ""}):
        with pytest.raises(ValidationError):
            SelectedNativeScoringQuestion.model_validate({**value, **mutation})
    wrong = deepcopy(value)
    wrong["reference"]["scheme"] = "universal-dependencies"
    with pytest.raises(ValidationError):
        SelectedNativeScoringQuestion.model_validate(wrong)


def test_native_question_is_checked_when_freezing_independent_reference():
    body = reference_body()
    body["cases"][0].update(matcher="spacy_native", expected=source_value(question()))
    _reference_invariants(body)
    body["cases"][0]["expected"] = source_value({**question(), "end": 12})
    with pytest.raises(ValidationError, match="whole-block"):
        _reference_invariants(body)
