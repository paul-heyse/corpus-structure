"""Independent native-diagnostic translation cases; no provider/enforcement claim."""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.store import (
    DatabaseCause,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
)


class NativeFailure(Exception):
    sqlstate = "23514"

    def __init__(self, detail):
        self.diag = SimpleNamespace(
            constraint_name="source_view_address",
            schema_name="kb",
            table_name="source_view",
            column_name="section_pointer",
            datatype_name="text",
            message_detail=detail,
        )
        super().__init__("message prose is not a discriminator")


def test_structured_native_facts_survive_driver_wrapper():
    envelope = dict(
        protocol="corpus-invariant-1",
        guard="execution_task",
        version="2",
        invariant="attempt_fence",
    )
    error = NativeFailure(json.dumps(envelope))
    wrapped = DBAPIError("not retained SQL", {}, error, connection_invalidated=False)
    result = classify_error(
        wrapped, phase=DatabasePhase.COMMITTING, effects=EffectKnowledge.UNCERTAIN
    )
    assert result.cause == DatabaseCause.CONSTRAINT
    assert result.constraint == "source_view_address"
    assert result.sqlstate == "23514"
    assert not result.invalidated
    assert result.phase == DatabasePhase.COMMITTING
    assert result.effects == EffectKnowledge.UNCERTAIN
    details = dict(result.details)
    assert details["schema_name"] == "kb"
    assert details["table_name"] == "source_view"
    assert details["column_name"] == "section_pointer"
    assert details["datatype_name"] == "text"
    assert json.loads(details["invariant_detail"]) == envelope


@pytest.mark.parametrize(
    "detail",
    [
        "Key (private_value)=(do not expose) already exists.",
        "{bad json",
        "null",
        "[]",
        '{"protocol":"other","guard":"x","version":"2","invariant":"x"}',
        '{"protocol":"corpus-invariant-1","guard":"x","version":2,"invariant":"x"}',
        '{"protocol":"corpus-invariant-1","guard":"","version":"2","invariant":"x"}',
        '{"protocol":"corpus-invariant-1","guard":"x","version":"2","invariant":"x","row":"private"}',
    ],
)
def test_unmapped_or_ordinary_detail_is_not_a_public_guard(detail):
    original = NativeFailure(detail)
    result = classify_error(original)
    assert "invariant_detail" not in dict(result.details)
    assert original.diag.message_detail == detail
    assert result.cause == DatabaseCause.CONSTRAINT


def test_unrelated_failure_keeps_its_unknown_category():
    result = classify_error(RuntimeError("attempt fence"))
    assert result.cause == DatabaseCause.UNKNOWN
    assert result.details == ()


def test_invalidated_connection_preserves_native_facts_without_changing_cause_priority():
    original = NativeFailure(None)
    wrapped = DBAPIError("unreported SQL", {}, original, connection_invalidated=True)
    result = classify_error(wrapped)
    assert result.cause == DatabaseCause.CONNECTION_UNUSABLE
    assert result.invalidated
    assert result.constraint == "source_view_address"
    assert dict(result.details)["table_name"] == "source_view"
