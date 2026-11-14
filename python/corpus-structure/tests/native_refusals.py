"""Native refusal diagnostics shared by tests; expected guard identities stay at call sites."""

from collections.abc import Generator
from contextlib import contextmanager

import psycopg
import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.invariant_failures import InvariantViolation


@contextmanager
def native_refusal(
    sqlstate: str,
    *,
    constraint: str | None = None,
    message: str | None = None,
    context: str | None = None,
) -> Generator[None]:
    """Require the exact native reason, including its diagnostic tuple on mismatch."""
    try:
        yield
    except Exception as error:
        native = error.__cause__ if isinstance(error, InvariantViolation) else error
        assert isinstance(native, DBAPIError), f"expected native DBAPIError, observed {error!r}"
        driver = native.orig
        assert isinstance(driver, psycopg.Error), f"expected psycopg.Error, observed {driver!r}"
        observed = (
            driver.sqlstate,
            driver.diag.constraint_name,
            driver.diag.message_primary,
            driver.diag.context,
        )
        assert driver.sqlstate == sqlstate, f"native refusal diagnostics: {observed!r}"
        if constraint is not None:
            assert driver.diag.constraint_name == constraint, (
                f"native refusal diagnostics: {observed!r}"
            )
        if message is not None:
            assert driver.diag.message_primary == message, (
                f"native refusal diagnostics: {observed!r}"
            )
        if context is not None:
            assert context in (driver.diag.context or ""), (
                f"native refusal diagnostics: {observed!r}"
            )
    else:
        pytest.fail("expected native refusal, but operation succeeded")
