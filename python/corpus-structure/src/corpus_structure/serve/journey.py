"""Shared completed-result binding and parameter identity for retained read consumers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Connection

from corpus_structure.core.canonical import digest
from corpus_structure.semantic.query import ReadSession, bind_completed_result
from corpus_structure.semantic.refusals import (
    InvalidContinuation,
    SemanticRefusal,
    StaleSnapshot,
    WrongBinding,
)


class QueryRefused(SemanticRefusal):
    """A query that cannot name an authoritative completed result."""


class StaleToken(InvalidContinuation):
    pass


def bind_session(conn: Connection, run_id: int) -> ReadSession:
    try:
        return bind_completed_result(conn, run_id)
    except WrongBinding, StaleSnapshot, InvalidContinuation:
        raise
    except SemanticRefusal as error:
        raise QueryRefused(str(error)) from error


def params_digest(params: Mapping[str, Any]) -> str:
    from corpus_structure.core.canonical import decimal_of_float

    def normalized(value: Any) -> Any:
        if isinstance(value, float):
            return {"$float": decimal_of_float(value)}
        if isinstance(value, dict):
            return {k: normalized(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalized(v) for v in value]
        return value

    return digest(normalized(dict(params)))
