"""Shared read-continuation identity validation; cursor codecs remain query-owned."""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from .refusals import InvalidContinuation, StaleSnapshot, WrongBinding, WrongRelease
from .types import PreparedRelease


class _PrimitiveToken(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    release: str
    realization: str
    revision: int
    query: str
    after: str


class _NamedToken(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    run: int
    query: str
    version: str
    params: str
    position: JsonValue
    release: str
    realization: str
    revision: int
    projection: str
    arithmetic: str
    token_version: Literal[2]
    query_contract: str
    implementation: str
    compatibility: str


def decode_continuation(token: str, *, kind: Literal["primitive", "named"]) -> dict[str, Any]:
    try:
        data = base64.b64decode(token.encode("ascii"), altchars=b"-_", validate=True)
        header = json.loads(data) if kind == "named" else None
        if isinstance(header, dict) and (
            type(header.get("token_version")) is not int or header.get("token_version") != 2
        ):
            from .query_compatibility import QueryCompatibilityError

            raise QueryCompatibilityError(
                "unsupported named-query continuation reader; start a new supported query",
                reason="unsupported_query_token",
            )
        model = _PrimitiveToken if kind == "primitive" else _NamedToken
        return model.model_validate_json(data, strict=True).model_dump()
    except (UnicodeError, binascii.Error, json.JSONDecodeError, ValidationError) as error:
        raise InvalidContinuation("invalid continuation token") from error


def _record_reason(prepared: PreparedRelease | None, reason: str) -> None:
    if prepared is None:
        return
    if prepared.execution_model_id is None:
        raise ValueError("continuation requires a composed execution binding")
    rows = [row for row in prepared.registry_rows if row.kind == "execution_model"]
    if len(rows) != 1 or rows[0].name != prepared.execution_model_id:
        raise ValueError("continuation requires its exact execution binding")
    from .contracts import bound_execution_model
    from .operation_results import validate_result_dimension

    bound_execution_model(prepared).require_operation("validate_continuation")
    validate_result_dimension(prepared, "validate_continuation", "reason", reason, field="reason")


def validate_continuation(
    prepared: PreparedRelease | None,
    actual: Mapping[str, object],
    expected: Mapping[str, object],
) -> None:
    """Compare explicit requested identities separately from live-state freshness.

    A new transaction capture id is deliberately absent: revision equality is the promised
    continuation guarantee, not continued access to an old physical transaction snapshot.
    """
    reasons = {
        "release": "wrong_release",
        "realization": "wrong_realization",
        "run": "wrong_realization",
        "query": "wrong_query",
        "params": "wrong_parameters",
        "projection": "wrong_projection",
        "arithmetic": "wrong_profile",
        "revision": "stale_revision",
        "version": "stale_version",
    }
    for field, value in expected.items():
        if field not in reasons:
            raise ValueError(f"unsupported continuation identity field {field}")
        if actual.get(field) == value:
            continue
        reason = reasons[field]
        _record_reason(prepared, reason)
        message = (
            "continuation query parameters/projection/order/profile differ"
            if field == "query"
            else f"continuation {field} differs from the requested binding"
        )
        if reason == "wrong_release":
            raise WrongRelease(message)
        if reason.startswith("stale_"):
            raise StaleSnapshot(message, reason=reason)
        raise WrongBinding(message, reason=reason)
    _record_reason(prepared, "continued")
