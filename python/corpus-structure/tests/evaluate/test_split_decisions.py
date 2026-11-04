"""Frozen split preparation; independent reasons and population expectations."""

import json

import pytest

from corpus_structure.core.vocab import DocumentSplit
from corpus_structure.evaluate.split import Assignment, SplitConfig, SplitDocument, SplitError
from corpus_structure.evaluate.split_decisions import prepare_split_decision
from corpus_structure.semantic.refusals import SemanticOperationRefusal


@pytest.mark.parametrize("chapter", [True, 3, 1.5, ["one"], {"id": "one"}])
def test_nontext_chapter_refuses_without_cross_language_stringification(chapter):
    with pytest.raises(SemanticOperationRefusal, match="unsupported split chapter") as caught:
        prepare_split_decision("p", "r", [SplitDocument(1, "a", chapter)], SplitConfig(), {})
    assert caught.value.semantic_reason.expected == "string or null chapter metadata"


def test_effective_override_and_non_hash_reasons_are_retained():
    documents = [SplitDocument(1, "book/reserved", "one"), SplitDocument(2, "book/forced", "two")]
    policy = SplitConfig(
        seed=3, reserved={"reserved": "worked example"}, forced_dev={"forced": "development"}
    )
    decision = prepare_split_decision("p", "r", documents, policy, {}, seed=19)
    value = json.loads(decision.intent)
    assert value["seed"] == 19
    assert value["seed_origin"] == "override"
    assert value["policy"]["seed"] == 3
    assert value["assignments"] == [
        {"document_id": 1, "split": "reserved", "reason": "reserved: worked example", "seed": None},
        {"document_id": 2, "split": "dev", "reason": "forced_dev: development", "seed": None},
    ]
    assert prepare_split_decision("p", "r", documents[::-1], policy, {}, seed=19) == decision


def test_prior_basis_and_actual_population_change_identity_without_relabelling():
    docs = [SplitDocument(1, "a", "one"), SplitDocument(2, "a", "one")]
    previous = {1: Assignment(1, DocumentSplit.TEST, "persisted", None)}
    decision = prepare_split_decision("p", "r", docs, SplitConfig(), previous)
    value = json.loads(decision.intent)
    assert value["previous"] == [
        {"document_id": 1, "split": "test", "reason": "persisted", "seed": None}
    ]
    assert value["assignments"] == [
        {"document_id": 2, "split": "test", "reason": "persisted", "seed": None}
    ]
    smaller = prepare_split_decision("p", "r", docs[:1], SplitConfig(), previous)
    assert smaller.decision_id != decision.decision_id
    override = prepare_split_decision("p", "r", docs, SplitConfig(), previous, seed=0)
    assert override.decision_id != decision.decision_id


def test_basis_cannot_silently_drop_prior_rows_or_duplicate_documents():
    doc = SplitDocument(1, "a", None)
    with pytest.raises(SplitError, match="unique documents"):
        prepare_split_decision("p", "r", [doc, doc], SplitConfig(), {})
    with pytest.raises(SplitError, match="in-population"):
        prepare_split_decision(
            "p", "r", [doc], SplitConfig(), {2: Assignment(2, DocumentSplit.DEV, "persisted", None)}
        )
