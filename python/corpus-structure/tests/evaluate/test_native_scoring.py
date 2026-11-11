"""Native task scores challenge independently authored labels and retain missing scope."""

import json

import pytest
from pydantic import ValidationError
from spacy.tokens import Doc, Span
from spacy.vocab import Vocab

from corpus_structure.evaluate.native_scoring import NativeScoringReference, score_native


def reference(kind, **kwargs):
    return NativeScoringReference(
        kind=kind,
        text="All trials fail",
        words=("All", "trials", "fail"),
        spaces=(True, True, False),
        **kwargs,
    )


def prediction():
    return Doc(Vocab(), words=["All", "trials", "fail"], spaces=[True, True, False])


def test_wrong_boundary_lowers_native_token_score_without_inference():
    gold = reference("tokenization")
    good = score_native(prediction(), gold)
    wrong = Doc(Vocab(), words=["All", "trials fail"], spaces=[True, False])
    bad = score_native(wrong, gold)
    assert good["scores"]["token_f"] == 1.0
    assert bad["scores"]["token_f"] < good["scores"]["token_f"]
    assert bad["coverage"]["reference"]["eligible"] == 3
    json.dumps(bad, allow_nan=False)


def test_wrong_span_label_lowers_native_span_score():
    gold = reference(
        "spans", span_key="roles", spans=({"start": 4, "end": 10, "label": "subject"},)
    )
    good, wrong = prediction(), prediction()
    good.spans["roles"] = [Span(good, 1, 2, label="subject")]
    wrong.spans["roles"] = [Span(wrong, 1, 2, label="actor")]
    assert score_native(good, gold)["scores"]["roles_f"] == 1.0
    assert score_native(wrong, gold)["scores"]["roles_f"] == 0.0


def test_unalignable_and_uninspected_spans_stay_in_reference_coverage():
    gold = reference(
        "spans",
        span_key="roles",
        spans=(
            {"start": 0, "end": 3, "label": "quantifier"},
            {"start": 5, "end": 8, "label": "inside-token"},
            {"start": 11, "end": 15, "label": "unknown", "state": "uninspected"},
        ),
    )
    pred = prediction()
    pred.spans["roles"] = [Span(pred, 0, 1, label="quantifier"), Span(pred, 2, 3, label="unknown")]
    result = score_native(pred, gold)
    assert result["status"] == "partial"
    assert result["coverage"]["reference"] == dict(
        eligible=3, inspected=2, scored=1, unalignable=1, uninspected=1
    )
    assert result["coverage"]["prediction"]["withheld"] == 1
    assert result["scores"]["roles_f"] == 1.0


def test_missing_span_population_is_not_a_correct_empty_answer():
    gold = reference("spans", span_key="roles")
    result = score_native(prediction(), gold)
    assert result["status"] == "unavailable"
    pred = prediction()
    pred.spans["roles"] = []
    result = score_native(pred, gold)
    assert result["status"] == "examined_empty"
    assert result["scores"]["roles_f"] is None


def test_wrong_dependency_head_lowers_native_las():
    gold = reference("dependencies", heads=(1, 2, 2), deps=("det", "nsubj", "ROOT"))
    good = Doc(
        Vocab(),
        words=list(gold.words),
        spaces=list(gold.spaces),
        heads=[1, 2, 2],
        deps=["det", "nsubj", "ROOT"],
    )
    wrong = Doc(
        Vocab(),
        words=list(gold.words),
        spaces=list(gold.spaces),
        heads=[2, 2, 2],
        deps=["det", "nsubj", "ROOT"],
    )
    assert score_native(good, gold)["scores"]["dep_las"] == 1.0
    assert score_native(wrong, gold)["scores"]["dep_las"] < 1.0
    assert score_native(prediction(), gold)["reason"] == "prediction_dependencies_missing"


def test_dependency_missing_reference_is_not_fabricated_root_or_negative():
    gold = reference("dependencies", heads=(None, 2, 2), deps=(None, "nsubj", "ROOT"))
    pred = Doc(
        Vocab(),
        words=list(gold.words),
        spaces=list(gold.spaces),
        heads=[1, 2, 2],
        deps=["det", "nsubj", "ROOT"],
    )
    result = score_native(pred, gold)
    assert result["status"] == "partial"
    assert result["coverage"]["reference"]["uninspected"] == 1
    assert result["scores"]["dep_las"] == 1.0


def test_multilabel_unknown_gold_is_masked_and_threshold_is_declared():
    gold = reference(
        "categories",
        labels=("assertion", "example", "proof"),
        cats={"assertion": 1.0, "example": 0.0, "proof": None},
        multi_label=True,
        threshold=0.7,
    )
    pred = prediction()
    pred.cats = {"assertion": 0.8, "example": 0.6, "proof": 1.0}
    result = score_native(pred, gold)
    assert result["status"] == "partial"
    assert result["score_scope"]["labels"] == ["assertion", "example"]
    assert result["scores"]["cats_micro_f"] == 1.0
    assert result["coverage"]["reference"]["uninspected"] == 1
    pred.cats = {"assertion": 0.6, "example": 0.6, "proof": 1.0}
    assert score_native(pred, gold)["scores"]["cats_micro_f"] == 0.0


def test_exclusive_sparse_gold_and_missing_prediction_cannot_imply_negative_labels():
    sparse = reference("categories", labels=("yes", "no"), cats={"yes": 1.0}, multi_label=False)
    pred = prediction()
    pred.cats = {"yes": 0.9, "no": 0.1}
    assert (
        score_native(pred, sparse)["reason"]
        == "exclusive_reference_requires_complete_independent_onehot_labels"
    )
    full = reference(
        "categories",
        labels=("yes", "no"),
        cats={"yes": 1.0, "no": 0.0},
        multi_label=False,
        positive_label="yes",
    )
    assert score_native(pred, full)["scores"]["cats_score"] == 1.0
    pred.cats = {"yes": 0.9}
    result = score_native(pred, full)
    assert result["status"] == "unavailable"
    assert result["coverage"]["prediction"]["missing"] == ["no"]


def test_empty_native_diagnostic_and_unavailable_source_are_distinct():
    gold = NativeScoringReference(kind="tokenization", text="", words=(), spaces=())
    result = score_native(Doc(Vocab(), words=[], spaces=[]), gold)
    assert result["status"] == "examined_empty"
    assert result["scores"]["token_f"] is None
    assert score_native(None, gold)["reason"] == "prediction_missing"
    assert score_native(prediction(), gold)["reason"] == "prediction_source_text_differs"
    assert (
        score_native(prediction(), reference("tokenization", inspected=False))["status"]
        == "uninspected"
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"scheme": "UD"},
        {"heads": (0, 1, 2)},
        {"unexpected": True},
    ],
)
def test_native_contract_refuses_scheme_relabelling_and_unrelated_fields(kwargs):
    with pytest.raises(ValidationError):
        reference("tokenization", **kwargs)


def test_native_reference_requires_exact_source_segmentation_and_explicit_policy():
    with pytest.raises(ValidationError, match="exact text"):
        NativeScoringReference(
            kind="tokenization", text="xy", words=("x", "y"), spaces=(True, False)
        )
    with pytest.raises(ValidationError, match="threshold"):
        reference("categories", labels=("yes",), cats={"yes": 1}, multi_label=True)
    with pytest.raises(ValidationError, match="overlap"):
        reference(
            "spans",
            span_key="overlapping",
            spans=({"start": 0, "end": 10, "label": "a"}, {"start": 4, "end": 15, "label": "b"}),
        )


def test_sentence_boundary_scores_use_native_sentences_and_exact_independent_extents():
    gold = reference("spans", span_key="sents", labeled=False, spans=({"start": 0, "end": 15},))
    good = Doc(
        Vocab(), words=list(gold.words), spaces=list(gold.spaces), sent_starts=[True, False, False]
    )
    wrong = Doc(
        Vocab(), words=list(gold.words), spaces=list(gold.spaces), sent_starts=[True, True, False]
    )
    expected = score_native(good, gold)
    actual = score_native(wrong, gold)
    assert expected["scores"]["sents_f"] == 1.0 and expected["exact_match"] is True
    assert actual["scores"]["sents_f"] == 0.0 and actual["exact_match"] is False
    assert score_native(prediction(), gold)["reason"] == "prediction_span_population_missing"


def test_exact_span_comparison_conserves_duplicate_emissions_beyond_native_set_metrics():
    gold = reference(
        "spans", span_key="roles", spans=({"start": 4, "end": 10, "label": "subject"},)
    )
    pred = prediction()
    pred.spans["roles"] = [Span(pred, 1, 2, label="subject"), Span(pred, 1, 2, label="subject")]
    result = score_native(pred, gold)
    assert result["scores"]["roles_f"] == 1.0
    assert result["exact_match"] is False


def test_exact_native_decisions_do_not_turn_unknown_scope_into_a_pass():
    pred = prediction()
    pred.spans["roles"] = [Span(pred, 0, 1, label="determiner")]
    gold = reference(
        "spans", span_key="roles", spans=({"start": 1, "end": 2, "label": "unalignable"},)
    )
    result = score_native(pred, gold)
    assert result["status"] == "partial" and result["exact_match"] is None
    assert score_native(pred, reference("tokenization"))["exact_match"] is True
    merged = Doc(Vocab(), words=["All trials", "fail"], spaces=[True, False])
    assert score_native(merged, reference("tokenization"))["exact_match"] is False


@pytest.mark.parametrize("field", ["inspected", "labeled", "allow_overlap", "multi_label"])
def test_reference_policy_booleans_match_the_strict_protected_wire(field):
    fields: dict[str, object] = dict(
        labels=("yes",), cats={"yes": 1.0}, multi_label=True, threshold=0.7
    )
    fields[field] = "false"
    with pytest.raises(ValidationError, match="valid boolean"):
        reference("categories", **fields)
