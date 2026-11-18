"""The shared refusal matcher checks real driver diagnostics on the rollback connection."""

import pytest
from native_refusals import native_refusal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.invariant_failures import InvariantViolation


def test_native_refusal_accepts_exact_driver_diagnostics(infrastructure_rollback):
    with (
        native_refusal("22012", message="division by zero"),
        infrastructure_rollback.begin_nested(),
    ):
        infrastructure_rollback.execute(text("SELECT 1 / 0"))


@pytest.mark.parametrize(
    "expected",
    [
        {"sqlstate": "23514"},
        {"sqlstate": "22012", "message": "another reason"},
        {"sqlstate": "22012", "constraint": "another_constraint"},
        {"sqlstate": "22012", "context": "missing_guard"},
    ],
)
def test_native_refusal_rejects_different_driver_reason(infrastructure_rollback, expected):
    with (
        pytest.raises(AssertionError, match="native refusal diagnostics"),
        native_refusal(**expected),
        infrastructure_rollback.begin_nested(),
    ):
        infrastructure_rollback.execute(text("SELECT 1 / 0"))


def test_native_refusal_accepts_constraint_and_context(infrastructure_rollback):
    statement = """DO $$ BEGIN
      RAISE EXCEPTION 'authored guard' USING ERRCODE='23514', CONSTRAINT='authored_constraint';
    END $$"""
    with (
        native_refusal(
            "23514",
            constraint="authored_constraint",
            message="authored guard",
            context="inline_code_block",
        ),
        infrastructure_rollback.begin_nested(),
    ):
        infrastructure_rollback.execute(text(statement))


def test_native_refusal_unwraps_production_invariant_violation(infrastructure_rollback):
    # Construct only the wrapper: the diagnostic still comes from PostgreSQL.
    with native_refusal("22012", message="division by zero"):
        try:
            with infrastructure_rollback.begin_nested():
                infrastructure_rollback.execute(text("SELECT 1 / 0"))
        except DBAPIError as native:
            wrapper = InvariantViolation.__new__(InvariantViolation)
            Exception.__init__(wrapper, "controlled invariant wrapper")
            raise wrapper from native


def test_native_refusal_rejects_non_driver_exception():
    with pytest.raises(AssertionError, match="expected native DBAPIError"), native_refusal("22012"):
        raise ValueError("not a driver refusal")


def test_native_refusal_rejects_missing_exception():
    with pytest.raises(pytest.fail.Exception, match="operation succeeded"), native_refusal("22012"):
        pass
