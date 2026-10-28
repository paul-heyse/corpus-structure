"""Canonical JSON, digests and keys (D1 §10.1; foundations §3.2).

`canonical_json` is the one serialization behind keys, rendition content digests and configuration
hashes: UTF-8 without insignificant whitespace; every string, object keys included, NFC-normalized;
object keys sorted by code point (Python's order over NFC strings, not RFC 8785's UTF-16 order).
A pre-walk refuses, with the path of the offending part, anything outside JSON's integers,
strings, booleans, null, arrays and string-keyed objects: floats and `Decimal`s (a decimal travels
as its canonical string, D1 §6.2), dates, bytes, sets, non-string keys, strings that are not valid
UTF-8 (a lone surrogate), and two keys of one object that are equal after NFC (refused, never
merged).

Floats never reach a hash. Loaders that meet them convert explicitly: `decimal_of_float` gives the
canonical decimal of a float's shortest round-trip form, and `canonical_decimal` turns a decimal
literal into the D1 §6.2 canonical string.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from decimal import Decimal
from typing import Any

KEY_HEX_DIGITS = 32

# The D1 §6.2 canonical decimal: no exponent, no trailing zeros after the point, no point without
# digits after it, no leading `+`, exactly one zero before the point below one, and no `-0`.
CANONICAL_DECIMAL = r"0|-?(?:[1-9][0-9]*(?:\.[0-9]*[1-9])?|0\.[0-9]*[1-9])"
_CANONICAL_DECIMAL = re.compile(CANONICAL_DECIMAL)
_DECIMAL_LITERAL = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class CanonicalJsonError(ValueError):
    """A value outside canonical JSON, with the path (`$`, `$.a[2]`) of the offending part."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason


def _string(value: str, path: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise CanonicalJsonError(path, "string is not valid UTF-8 (lone surrogate)") from None
    return unicodedata.normalize("NFC", value)


def _normalize(value: Any, path: str) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)  # an IntEnum or other subclass becomes a plain integer
    if isinstance(value, str):
        return _string(value, path)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalJsonError(path, f"object key {key!r} is not a string")
            nfc = _string(key, f"{path}.{key!r}")
            if nfc in out:
                raise CanonicalJsonError(path, f"two object keys equal {nfc!r} after NFC")
            out[nfc] = _normalize(item, f"{path}.{nfc}")
        return out
    if isinstance(value, list | tuple):
        return [_normalize(item, f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, float):
        reason = "float (convert with decimal_of_float in the loader)"
    elif isinstance(value, Decimal):
        reason = "Decimal (a decimal travels as its canonical string)"
    else:
        reason = f"{type(value).__name__} is not a JSON value"
    raise CanonicalJsonError(path, reason)


def canonical_json(value: Any) -> bytes:
    """The canonical JSON bytes of `value` (D1 §10.1); refuses non-canonical input."""
    normalized = _normalize(value, "$")
    text = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return text.encode("utf-8")


def digest(value: Any) -> str:
    """The full SHA-256 hex digest of `value`'s canonical JSON."""
    return hashlib.sha256(canonical_json(value)).hexdigest()


def make_key(prefix: str, parts: Any) -> str:
    """`prefix:` plus the first 32 hex digits of the SHA-256 of the parts' canonical JSON."""
    if not re.fullmatch(r"[a-z]+", prefix):
        raise ValueError(f"key prefix must be lowercase letters: {prefix!r}")
    return f"{prefix}:{digest(parts)[:KEY_HEX_DIGITS]}"


def is_canonical_decimal(text: str) -> bool:
    return _CANONICAL_DECIMAL.fullmatch(text) is not None


def canonical_decimal(literal: str) -> str:
    """The D1 §6.2 canonical string of a decimal literal (`1e-3` -> `0.001`, `300.0` -> `300`)."""
    if not isinstance(literal, str) or not _DECIMAL_LITERAL.fullmatch(literal):
        raise ValueError(f"not a decimal literal: {literal!r}")
    text = format(Decimal(literal), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("-0", ""):
        return "0"
    return text


def decimal_of_float(value: float) -> str:
    """The canonical decimal of a float's shortest round-trip form (`repr`); refuses NaN, ±inf."""
    if not isinstance(value, float):
        raise TypeError(f"expected a float, got {type(value).__name__}")
    if not math.isfinite(value):
        raise ValueError(f"not a finite float: {value!r}")
    return canonical_decimal(repr(value))
