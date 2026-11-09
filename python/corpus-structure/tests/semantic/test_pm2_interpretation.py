"""Interpretation keeps released meanings, native choices and source evidence distinct."""

import json

import pytest

from corpus_structure.methods.pm2_interpretation_products import (
    interpretation_products,
    render_candidate_options,
)
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


def test_released_specialized_reads_do_not_change_implicit_selection():
    family = _family(
        {
            "family": "literal_completion_v1",
            "questions": [
                {"key": "literal", "kind": "text", "instructions": "Read the exact text."},
                {
                    "key": "deadline",
                    "kind": "date",
                    "instructions": "Read the deadline only.",
                    "explicit_only": True,
                },
            ],
        }
    )
    assert [question.key for question in family.select_questions(())] == ["literal"]
    assert [question.key for question in family.select_questions(("deadline",))] == ["deadline"]
    assert "explicit_only" not in family.questions[0].model_dump(mode="json")
    with pytest.raises(ValueError, match="unavailable"):
        family.select_questions(("missing",))


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


def test_revised_alias_carries_located_alternative_but_never_replaces_its_identity():
    family = _family(
        {
            "family": "local_referent_choice_v1",
            "candidate_types": ["mention"],
            "questions": [
                {
                    "key": "referent",
                    "kind": "choice",
                    "candidate_options": True,
                    "instructions": "Which preceding alternative denotes the same actor?",
                    "options": [
                        {
                            "key": "option_1",
                            "criterion": "No matching option.",
                            "disposition": "no_match",
                        },
                        {
                            "key": "unclear",
                            "criterion": "Ambiguous.",
                            "disposition": "insufficient_evidence",
                        },
                    ],
                }
            ],
        }
    )
    key = "candidate_" + "3" * 64
    candidate = {"key": key, "semantic_type": "mention"}
    located_text = {"actor": ["The reviewer"]}
    rendered, aliases = render_candidate_options(
        family, [{**candidate, "located_text": located_text}]
    )
    assert rendered == [
        {"key": "option_2", "semantic_type": "mention", "located_text": located_text}
    ]
    question = family.questions[0]
    request = {
        "state": {"candidates": rendered},
        "questions": {question.key: question.native(rendered)},
        "interpretation": {
            "version": "2",
            "declaration_digest": family.digest,
            "candidates": [candidate],
            "option_aliases": aliases,
        },
    }
    answer = {
        "type": "choice",
        "choice": "option_2",
        "probabilities": {"option_1": 0.1, "unclear": 0.1, "option_2": 0.8},
    }
    reply = {"native": {"answers": {question.key: answer}}}
    (result,) = interpretation_products(family, request, reply, {})
    assert result.value["selected_keys"] == (key,)
    assert result.value["native_answer"] == answer
    assert result.value["candidates"] == [candidate]
    request["interpretation"]["option_aliases"] = {"option_2": "unoffered"}
    with pytest.raises(ValueError, match="retained candidate population"):
        interpretation_products(family, request, reply, {})
