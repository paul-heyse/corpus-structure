"""Interpretation keeps released meanings, native choices and source evidence distinct."""

import json

import pytest

from corpus_structure.methods.pm2_interpretation_products import interpretation_products
from corpus_structure.semantic.interpretation_questions import (
    QUESTION_INPUT,
    compile_question_families,
    declared_families,
)
from corpus_structure.semantic.types import SourceArtifact


def _family(definition):
    rows = compile_question_families(
        (SourceArtifact(QUESTION_INPUT, json.dumps([definition]).encode()),)
    )
    return declared_families(rows)[definition["family"]]


def test_released_vocabulary_changes_without_changing_the_interpretation_adapter():
    for label, criterion in (
        ("illustration", "An example of a theorem or its proof."),
        ("checkpoint", "A documented gate before an operator may proceed."),
    ):
        family = _family(
            {
                "family": "passage_function_v1",
                "questions": [
                    {
                        "key": "purpose",
                        "kind": "choice",
                        "instructions": "Evaluate each purpose independently.",
                        "multiple": True,
                        "minimum_probability": 0.7,
                        "options": [
                            {"key": label, "criterion": criterion},
                            {"key": "warning", "criterion": "States a consequence of a failure."},
                        ],
                    }
                ],
            }
        )
        questions = {q.key: q.native([]) for q in family.questions}
        assert list(questions["purpose"]["criteria"]) == [label, "warning"]
        (result,) = interpretation_products(
            family,
            {
                "questions": questions,
                "interpretation": {"declaration_digest": family.digest, "candidates": []},
            },
            {
                "native": {
                    "answers": {
                        "purpose": {
                            "type": "choice",
                            "choices": ["warning", label],
                            "probabilities": {label: 0.91, "warning": 0.55},
                        }
                    }
                }
            },
            {},
        )
        assert result.members == ()
        assert result.value["observed_keys"] == (label, "warning")
        assert result.value["selected_keys"] == (label,)
        assert result.value["alternative_states"]["warning"] == "policy_withheld"
        with pytest.raises(ValueError, match="different released question"):
            interpretation_products(
                family, {"questions": questions}, {"native": {"answers": {}}}, {}
            )


@pytest.mark.parametrize("state", ["no_match", "insufficient_evidence", "missing_candidate"])
def test_candidate_decisions_keep_explicit_unresolved_outcomes_distinct(state):
    family = _family(
        {
            "family": "qualification_scope_v1",
            "candidate_types": ["frame"],
            "questions": [
                {
                    "key": "host",
                    "kind": "choice",
                    "instructions": "Choose the host if supported.",
                    "candidate_options": True,
                    "options": [
                        {
                            "key": "none",
                            "criterion": "No supplied host.",
                            "disposition": "no_match",
                        },
                        {
                            "key": "unknown",
                            "criterion": "Unclear.",
                            "disposition": "insufficient_evidence",
                        },
                        {
                            "key": "missing",
                            "criterion": "Omitted host.",
                            "disposition": "missing_candidate",
                        },
                    ],
                }
            ],
        }
    )
    choices = dict(no_match="none", insufficient_evidence="unknown", missing_candidate="missing")
    candidates = [{"key": "c1", "semantic_type": "frame"}]
    questions = {"host": family.questions[0].native(candidates)}
    chosen = choices[state]
    (result,) = interpretation_products(
        family,
        {
            "questions": questions,
            "interpretation": {"declaration_digest": family.digest, "candidates": candidates},
        },
        {
            "native": {
                "answers": {
                    "host": {
                        "type": "choice",
                        "choice": chosen,
                        "confidence": 1,
                        "probabilities": {
                            key: int(key == chosen) for key in questions["host"]["criteria"]
                        },
                    }
                }
            }
        },
        {},
    )
    assert result.value["state"] == state
    assert result.value["selected_keys"] == ()
    assert result.value["candidates"] == candidates


def test_binary_relation_keeps_both_criteria_and_native_observation():
    family = _family(
        {
            "family": "relation_interpretation_v1",
            "questions": [
                {
                    "key": "reported_reason",
                    "kind": "noul",
                    "instructions": "Does this source give a reason for the reported event?",
                    "positive": "The source states a reason.",
                    "negative": "No reason is stated.",
                }
            ],
        }
    )
    question = family.questions[0]
    (result,) = interpretation_products(
        family,
        {
            "questions": {question.key: question.native([])},
            "interpretation": {"declaration_digest": family.digest, "candidates": []},
        },
        {"native": {"answers": {question.key: {"type": "noul", "noul": 0.12}}}},
        {},
    )
    assert result.value["state"] == "observed_negative"
    assert result.value["selected_keys"] == ()
    assert result.value["binary_observation"] == {
        "direction": "negative",
        "positive_probability": 0.12,
        "positive_criterion": "The source states a reason.",
        "negative_criterion": "No reason is stated.",
    }
