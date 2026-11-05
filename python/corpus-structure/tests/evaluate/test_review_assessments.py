"""Bounded capture preserves exact author bytes and settles failed cursors."""

import base64
from hashlib import sha256
from unittest.mock import MagicMock

import pytest

from corpus_structure.evaluate.review_assessments import (
    AssessmentReviewSelection,
    assessment_review_capture,
    iter_assessment_review_rows,
)
from corpus_structure.evaluate.semantic import ReferenceError


class Result:
    closed = False

    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def scalars(self):
        return iter(self.rows)


class Connection(MagicMock):
    def __init__(self, rows):
        super().__init__()
        self.result = Result(rows)

    def execute(self, statement, parameters, **options):
        self.parameters = parameters
        return self.result


def authored(value=b'{ "cases": [] }\n'):
    return {"kind": "pass", "value": {
        "authored_base64": base64.b64encode(value).decode(),
        "content_digest": sha256(value).hexdigest(),
    }}


def test_exact_author_bytes_and_explicit_receipt():
    conn = Connection([authored()])
    rows = list(iter_assessment_review_rows(
        conn, project_id="original", set_id=7, exposure_receipt_id=13,
    ))
    assert base64.b64decode(rows[0]["value"]["authored_base64"]) == b'{ "cases": [] }\n'
    assert conn.parameters == {"project": "original", "set_id": 7, "receipt": 13}
    assert conn.result.closed


def test_changed_author_bytes_fail_and_close():
    row = authored()
    row["value"]["content_digest"] = "0" * 64
    conn = Connection([row])
    with pytest.raises(ReferenceError, match="immutable digest"):
        list(iter_assessment_review_rows(conn, project_id="p", set_id=1))
    assert conn.result.closed


def test_postgresql_wrapped_base64_preserves_original_bytes():
    value = b"long source reference " * 100
    row = authored(value)
    row["value"]["authored_base64"] = base64.encodebytes(value).decode()
    conn = Connection([row])
    assert len(list(iter_assessment_review_rows(conn, project_id="p", set_id=1))) == 1


@pytest.mark.parametrize("bounds", [{"max_rows": 1}, {"max_bytes": 1}])
def test_declared_bound_refuses_partial_capture_and_closes(bounds):
    conn = Connection([authored(), authored()])
    with pytest.raises(ReferenceError, match="bounds"):
        list(iter_assessment_review_rows(conn, project_id="p", set_id=1, **bounds))
    assert conn.result.closed


def test_callback_preserves_set_scope_and_does_not_create_principal():
    callback = assessment_review_capture((AssessmentReviewSelection("p", 7, 13),))
    conn = Connection([{"kind": "set", "value": {"judgments_exposed": False}}])
    rows = list(callback(conn)["assessment_history"])
    assert rows[0]["set_id"] == 7
    assert conn.parameters["receipt"] == 13
    with pytest.raises(ValueError, match="repeats"):
        assessment_review_capture((AssessmentReviewSelection("p", 7), AssessmentReviewSelection("p", 7)))
