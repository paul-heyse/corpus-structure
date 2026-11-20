"""Authoring invocation reuse, preserving independent source/reference checks."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from evaluate.declared_record_grading_support import current, cut, references
from evaluate.declared_record_policy_support import source

from corpus_structure.evaluate import declared_record_policy as policy
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusal_types import SemanticRefusal


@pytest.fixture
def authoring(monkeypatch):
    from corpus_structure.semantic import (
        data_operation_admission,
        demand_results,
        native_definition_projection,
        releases,
    )
    from corpus_structure.serve import interpretation_authoring

    prepared, model = current()
    independent, _, _ = references("table")
    acquired, coordinates, comparisons, published, transactions = [], [], [], [], []
    pin = source(1)
    row = dict(
        kind_contract=pin.kind_contract,
        subject=pin.subject,
        subject_definition=pin.subject_definition,
        original_source=pin.original_source,
        analyzed_scope=None,
    )
    body = dict(
        source=dict(
            document=pin.document,
            projection=pin.projection_digest,
            section_pointer=pin.section_pointer,
            membership=pin.membership,
        )
    )

    @contextmanager
    def selected_index(connection, demand_id, **kwargs):
        acquired.append((connection, demand_id, kwargs))
        yield None, object()

    @contextmanager
    def transaction():
        connection = object()
        transactions.append(connection)
        yield connection

    monkeypatch.setattr(demand_results, "selected_record_index", selected_index)
    monkeypatch.setattr(policy, "_selected_body", lambda *_args: (row, body))
    monkeypatch.setattr(
        policy,
        "_check_source_coordinates",
        lambda *args, source_cache=None: coordinates.append(args),
    )
    monkeypatch.setattr(releases, "open_release", lambda *_args: prepared)
    monkeypatch.setattr(data_operation_admission, "bound_data_operation_model", lambda _: model)
    from corpus_structure.evaluate import record_alignment

    monkeypatch.setattr(
        record_alignment, "align_records", lambda *args, **kwargs: comparisons.append(args)
    )
    monkeypatch.setattr(
        native_definition_projection,
        "read_native_definition_projection",
        lambda _: {
            "kinds": [
                dict(
                    kind=policy.PROTECTED_NAMESPACE + "DdoRecordReferencePopulation" + kind,
                    kind_contract="contract:" + kind,
                    universe="evaluator",
                )
                for kind in ("A", "B", "C")
            ]
        },
    )
    monkeypatch.setattr(
        interpretation_authoring,
        "author_interpretations",
        lambda *args, **kwargs: published.append(kwargs["request"]),
    )

    def request(values=independent):
        return SimpleNamespace(
            targets=("record_policy.grade",),
            project_id="project:one",
            original_sources={
                str(i): SimpleNamespace(
                    reference=dict(
                        kind="authored-fact",
                        kind_contract="contract:" + reference.pass_kind,
                        meaning_body=semantic_value(
                            dict(
                                pass_kind=reference.pass_kind,
                                references=[reference.model_dump(mode="json")],
                            )
                        ),
                    )
                )
                for i, reference in enumerate(values)
            },
        )

    return SimpleNamespace(
        engine=SimpleNamespace(begin=transaction),
        prepared=prepared,
        request=request,
        references=independent,
        acquired=acquired,
        coordinates=coordinates,
        comparisons=comparisons,
        published=published,
        transactions=transactions,
        row=row,
    )


def test_authoring_authenticates_same_cut_once_per_transaction_and_checks_every_reference(
    authoring,
):
    for _ in range(2):
        policy.author_record_policy_inputs(
            authoring.engine, authoring.prepared, request=authoring.request()
        )
    assert len(authoring.acquired) == 2
    assert len(authoring.transactions) == 2
    assert authoring.acquired[0][0] is not authoring.acquired[1][0]
    assert len(authoring.coordinates) == 12  # Each question and each reference's anchors.
    assert len(authoring.comparisons) == 6
    assert len(authoring.published) == 2


def test_authoring_acquires_different_cuts_separately_in_one_transaction(authoring):
    first, second, third = authoring.references
    other_cut = CutSelection(canonical_bytes(dict(cut().record, read_id="read:other")))
    second = second.model_copy(
        update={
            "question": second.question.model_copy(
                update={
                    "source_cut_id": other_cut.identity,
                    "source_cut_canonical_json": other_cut.content.decode(),
                }
            )
        }
    )
    policy.author_record_policy_inputs(
        authoring.engine, authoring.prepared, request=authoring.request((first, second, third))
    )
    assert len(authoring.acquired) == 2
    assert authoring.acquired[0][0] is authoring.acquired[1][0]
    assert {item[2]["expected_cut"] for item in authoring.acquired} == {
        cut().identity,
        other_cut.identity,
    }
    assert len(authoring.comparisons) == 3


def test_authoring_still_refuses_foreign_peer_source_before_publication(authoring):
    authoring.row["original_source"] = "foreign:original"
    with pytest.raises(SemanticRefusal, match="selected native identity/context"):
        policy.author_record_policy_inputs(
            authoring.engine, authoring.prepared, request=authoring.request()
        )
    assert len(authoring.acquired) == 1
    assert authoring.comparisons == authoring.published == []


def test_authoring_still_authenticates_each_related_peer_reference(authoring):
    from corpus_structure.semantic.data_operation_json import wire_json_loads

    first, second, third = authoring.references
    frame = wire_json_loads(first.question.frame_canonical_json)
    frame["related_pins"] = [source(2).model_dump(mode="json", exclude_none=True)]
    first = first.model_copy(
        update={
            "question": first.question.model_copy(
                update={
                    "frame_canonical_json": canonical_bytes(frame).decode(),
                }
            )
        }
    )
    with pytest.raises(SemanticRefusal, match="selected native identity/context"):
        policy.author_record_policy_inputs(
            authoring.engine, authoring.prepared, request=authoring.request((first, second, third))
        )
    assert len(authoring.acquired) == 1
    assert authoring.comparisons == authoring.published == []
