"""Serving code eligibility shared by bounded pages and their expendable cache."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

if TYPE_CHECKING:
    from .code_identity import CodeIdentity
    from .code_reuse import CompactReuseReport


class ServingImplementation(str):
    complete: bool
    verify: Callable[[], None] | None
    code: CodeIdentity
    compact_report: CompactReuseReport | None

    def __new__(cls, identity: str, code: CodeIdentity, verify: Callable[[], None] | None = None):
        # An incomplete observation is useful attribution for this one read.
        # Its nonce prevents a guessed repeat from acquiring continuation rights.
        token = identity if code.complete else sha256((identity + uuid4().hex).encode()).hexdigest()
        value = super().__new__(cls, token)
        value.complete = code.complete
        value.code = code
        value.compact_report = None
        value.verify = verify
        return value


_ACTIVE: ContextVar[ServingImplementation | None] = ContextVar("serving_code", default=None)


@contextmanager
def serving_code(implementation: ServingImplementation):
    from .code_reuse import record_code_reuse

    record_code_reuse(
        implementation.code,
        entry_point=implementation.code.entries[0]
        if implementation.code.entries
        else "selected read",
        tier="selected-result",
        outcome="unknown" if implementation.complete else "withheld",
    )
    token = _ACTIVE.set(implementation)
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def reusable_serving_code(implementation: str | None = None) -> bool:
    selected = _ACTIVE.get()
    if (
        selected is None
        or not selected.complete
        or (implementation is not None and implementation != selected)
    ):
        return False
    if selected.verify is not None:
        selected.verify()
    return True


def serving_report(record):
    selected = _ACTIVE.get()
    if selected is None or selected.complete:
        return record
    result = dict(record)
    for field in ("cursor", "continuation", "next_cursor", "resource_handle"):
        if field in result:
            result[field] = None
    from .code_reuse import compact_code_reuse

    if selected.compact_report is None:
        selected.compact_report = compact_code_reuse(selected.code)
    projection = selected.compact_report
    result["reuse"] = {**projection, "unknowns": [fact.copy() for fact in projection["unknowns"]]}
    return result


def record_serving_reuse(outcome: Literal["derived", "reused", "withheld", "unknown"]):
    from .code_reuse import record_code_reuse

    selected = _ACTIVE.get()
    if selected is not None:
        record_code_reuse(
            selected.code,
            entry_point=selected.code.entries[0] if selected.code.entries else "selected read",
            tier="selected-result",
            outcome=outcome,
        )
