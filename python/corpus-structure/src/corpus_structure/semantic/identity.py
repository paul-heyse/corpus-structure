"""Scoped occurrence and fact identities, independent of the installed key scheme."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    """Canonical semantic values; input bytes are never normalized with this function."""

    def exact(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            if not obj.is_finite():
                raise ValueError("non-finite decimal")
            text = format(obj, "f") if obj else "0"
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            return {"decimal": text}
        raise TypeError(f"unsupported semantic value: {type(obj).__name__}")

    return json.dumps(
        value,
        default=exact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _meaning(value: Any) -> Any:
    if value is None:
        return ["null"]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("naive datetime has no semantic instant")
        return ["datetime", value.astimezone(UTC).isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, bool):
        return ["boolean", value]
    if isinstance(value, str):
        return ["string", value]
    if isinstance(value, int):
        return ["integer", str(value)]
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite decimal")
        text = format(value, "f") if value else "0"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return ["decimal", text]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float")
        return ["float", value.hex()]
    if isinstance(value, (list, tuple)):
        return ["sequence", [_meaning(x) for x in value]]
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return ["mapping", [[k, _meaning(v)] for k, v in sorted(value.items())]]
    raise TypeError(f"unsupported semantic value {type(value).__name__}")


def occurrence_key(release_id: str, realization: str, source: str, item: str) -> str:
    """Two occurrences differ by source/item; a retry uses the same complete tuple."""
    if not all((release_id, realization, source, item)):
        raise ValueError("occurrence identity requires release, realization, source and item")
    return "occ:" + sha256(canonical_bytes([release_id, realization, source, item])).hexdigest()


def fact_key(
    release_id: str,
    realization: str,
    subject: str,
    predicate: str,
    object_: Any,
    qualification: dict[str, Any],
) -> str:
    """Qualification is meaning-bearing; evidence/confidence are separate support data."""
    if not all((release_id, realization, subject, predicate)):
        raise ValueError("fact identity requires scoped subject and predicate")
    if {"evidence", "confidence", "supports"}.intersection(qualification):
        raise ValueError("support/assessment fields are not semantic qualification")
    return (
        "fact:"
        + sha256(
            canonical_bytes(
                [
                    release_id,
                    realization,
                    subject,
                    predicate,
                    _meaning(object_),
                    _meaning(qualification),
                ]
            )
        ).hexdigest()
    )


def alternative_group_key(release_id: str, realization: str, fact_ids: tuple[str, ...]) -> str:
    """An unordered alternative set collapses duplicate occurrences of one fact."""
    members = sorted(set(fact_ids))
    if (
        not release_id
        or not realization
        or len(members) < 2
        or any(not member for member in members)
    ):
        raise ValueError("alternative group requires a scoped set of at least two distinct facts")
    return "alternative:" + sha256(canonical_bytes([release_id, realization, members])).hexdigest()
