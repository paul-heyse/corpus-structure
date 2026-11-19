"""Serving code eligibility shared by bounded pages and their expendable cache."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict
from hashlib import sha256
from uuid import uuid4

from .code_identity import CodeIdentity


class ServingImplementation(str):
    complete: bool
    diagnostics: tuple[dict, ...]

    def __new__(cls, identity: str, code: CodeIdentity):
        # An incomplete observation is useful attribution for this one read.
        # Its nonce prevents a guessed repeat from acquiring continuation rights.
        token = identity if code.complete else sha256((identity + uuid4().hex).encode()).hexdigest()
        value = super().__new__(cls, token)
        value.complete = code.complete
        value.diagnostics = tuple(asdict(item) for item in code.unknowns)
        return value


_ACTIVE: ContextVar[ServingImplementation | None] = ContextVar("serving_code", default=None)


@contextmanager
def serving_code(implementation: ServingImplementation):
    token = _ACTIVE.set(implementation)
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def reusable_serving_code() -> bool:
    selected = _ACTIVE.get()
    return selected is None or selected.complete


def serving_report(record):
    selected = _ACTIVE.get()
    if selected is None or selected.complete:
        return record
    result = dict(record)
    for field in ("cursor", "continuation", "next_cursor", "resource_handle"):
        if field in result:
            result[field] = None
    result["reuse"] = {
        "eligible": False,
        "reason": "incomplete_code_identity",
        "unknowns": selected.diagnostics[:1],
        "omitted": max(0, len(selected.diagnostics) - 1),
    }
    return result
