"""Completion-local reuse preserves independent rule and observed-input meaning."""

from copy import deepcopy
from dataclasses import replace

import pytest

from corpus_structure.semantic import established_validity
from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.data_operation_json import scope_identity
from corpus_structure.semantic.data_operation_model import (
    DataRuleRead,
    EffectiveDataRule,
    EffectiveKind,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.established_validity import (
    RuleAttestationPreparation,
    RuleObservedInput,
)


def rule(**changes):
    return replace(
        EffectiveDataRule(
            id="rule-a",
            kind="kind",
            kind_contract="kind-contract",
            collection=None,
            scope="product",
            form="attested",
            parameters=b'{"input_reads":{"source":["selector"]}}',
            reads=(DataRuleRead("source", "value", ()),),
            checker="producer",
            checker_operation="operation",
            checker_callable="producer:check",
            checker_determinant="checker-determinant",
            fingerprint="fingerprint-a",
        ),
        **changes,
    )


def preparation(kind=None):
    return RuleAttestationPreparation(
        kind or EffectiveKind("kind", "Kind", "class", b"{}"),
        "operation",
        {
            "role": "output",
            "position": 0,
            "multiplicity": 1,
            "product": {
                "kind_contract": "kind-contract",
                "body": semantic_value({"value": 3}),
                "members": [],
            },
        },
        SubjectContext("project", "subject", "source", b"{}", subject_definition="subject"),
    )


def test_rules_share_projection_but_keep_fingerprints_and_exact_inputs(monkeypatch):
    decoded = []
    decode = established_validity.decode_semantic_value

    def capture_decode(value):
        decoded.append(value)
        return decode(value)

    monkeypatch.setattr(established_validity, "decode_semantic_value", capture_decode)
    prepared = preparation()
    unchanged_output = deepcopy(prepared.output)
    selected = {"source": (RuleObservedInput({"selector": "a", "other": 1}, 2),)}
    first = prepared.attest(rule(), selected_inputs=selected)
    second = prepared.attest(
        rule(id="rule-b", fingerprint="fingerprint-b"), selected_inputs=selected
    )
    source_premise = canonical_identity(
        "rule-premise",
        scope_identity(["product", [None, {"value": semantic_value(3)}], None, [None, None]]),
    ).key
    expected = canonical_identity(
        "rule-observed-premise",
        scope_identity([source_premise, [["source", [[2, [semantic_value("a")]]]]]]),
    ).key
    assert first.premise == second.premise == expected
    assert first.rule_id == "rule-a" and second.rule_id == "rule-b"
    assert first.rule_fingerprint == "fingerprint-a"
    assert second.rule_fingerprint == "fingerprint-b"
    assert len(decoded) == 1
    assert len(prepared.source_premises) == len(prepared.input_premises) == 1
    assert prepared.output == unchanged_output
    changed = {"source": (RuleObservedInput({"selector": "b"}, 2),)}
    assert prepared.attest(rule(), selected_inputs=changed).premise != expected
    repeated = {"source": (RuleObservedInput({"selector": "a"}, 1),)}
    assert prepared.attest(rule(), selected_inputs=repeated).premise != expected
    with pytest.raises(ValueError, match="every declared observed input role"):
        prepared.attest(rule())
    with pytest.raises(ValueError, match="declared checker"):
        prepared.attest(rule(checker_operation="other"), selected_inputs=selected)


def test_partition_groups_are_shared_with_independent_expected_commitment(monkeypatch):
    calls = []
    group_digests = established_validity.partition_group_digests

    def capture_groups(items, groups):
        calls.append(groups)
        return group_digests(items, groups)

    monkeypatch.setattr(established_validity, "partition_group_digests", capture_groups)
    prepared = preparation(
        EffectiveKind(
            "kind",
            "Kind",
            "class",
            b'{"collections":{"tokens":{"field_groups":{"geometry":["start","end"]}}}}',
        )
    )
    packet = {
        "collection": "tokens",
        "partition_key": "block",
        "ordinal": 0,
        "placement": {"start": 10, "end": 20},
        "partition_digest": "partition-digest",
        "body": semantic_value([{"start": 0, "end": 2, "label": "x"}]),
    }
    checker = rule(
        collection="tokens",
        scope="partition",
        parameters=b"{}",
        reads=(DataRuleRead("source", "start", ("geometry",)), DataRuleRead("source", "label", ())),
    )
    first = prepared.attest(checker, partition=packet)
    second = prepared.attest(replace(checker, id="rule-b", fingerprint="b"), partition=packet)
    geometry = canonical_identity("partition-group", [{"start": 0, "end": 2}]).key
    expected = canonical_identity(
        "rule-premise",
        scope_identity(
            [
                "partition",
                [
                    [
                        None,
                        None,
                        None,
                        None,
                        None,
                        {"geometry": geometry},
                        {"label": [semantic_value("x")]},
                    ]
                ],
                None,
                [None, None],
            ]
        ),
    ).key
    assert first.premise == second.premise == expected
    assert first.partition_key == second.partition_key == "block"
    assert calls == [{"geometry": ["start", "end"]}]
    assert len(prepared.decoded_values) == 1
    assert len(prepared.partition_fields) == 1
    with pytest.raises(ValueError, match="exact whole-output scope"):
        prepared.attest(checker, partition={**packet, "collection": "sentences"})
