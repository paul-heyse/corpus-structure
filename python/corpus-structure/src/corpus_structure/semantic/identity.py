"""Scoped occurrence and fact identities, independent of the installed key scheme."""

from __future__ import annotations

import json
from decimal import Decimal
from hashlib import sha256
from typing import Any

from .value_codec import decimal_text, value_meaning

# Compatibility name for existing semantic consumers; there is one implementation.
_meaning = value_meaning


def canonical_bytes(value: Any) -> bytes:
    """Canonical semantic values; input bytes are never normalized with this function."""

    def exact(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return {"decimal": decimal_text(obj)}
        raise TypeError(f"unsupported semantic value: {type(obj).__name__}")

    return json.dumps(
        value,
        default=exact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


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
