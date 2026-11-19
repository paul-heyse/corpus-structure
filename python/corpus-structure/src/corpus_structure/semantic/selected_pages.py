"""Semantic continuation encoding and exact response-envelope pagination."""

import base64

from .data_operation_json import json_bytes, json_loads, wire_json_loads
from .refusals import InvalidContinuation

_SEPARATOR = len(json_bytes([0, 0])) - 2 * len(json_bytes(0)) - 2


def encode_cursor(value):
    encoded = base64.urlsafe_b64encode(json_bytes(value)).decode()
    if len(encoded) > 32768:
        raise ValueError("selected cursor exceeds the supported encoded bound")
    return encoded


def decode_cursor(value):
    try:
        return wire_json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError) as error:
        raise ValueError("invalid selected-result cursor") from error


def decode_rich_cursor(value: str) -> dict:
    try:
        parsed = json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError) as error:
        raise InvalidContinuation(
            "invalid rich query cursor", reason="invalid_continuation"
        ) from error
    if not isinstance(parsed, dict):
        raise InvalidContinuation("invalid rich query cursor", reason="invalid_continuation")
    return parsed


def byte_bounded_page(rows, *, offset, limit, max_bytes, report, row_fields=None):
    """Account for the envelope once and each appended row once, then check exactly.

    report(end, values, more) supplies fresh cut/provenance and the ordinal cursor.
    Multiple output arrays can share one indivisible pagination unit (dossiers).
    """
    from .serving_code import serving_report

    original_report = report

    def report(end, values, more):
        return serving_report(original_report(end, values, more))

    fields = {"items": lambda value: (value,)} if row_fields is None else row_fields
    dynamic_names = {
        "cursor",
        "continuation",
        "next_cursor",
        "page_complete",
        "knowledge",
        "unknowns",
        *fields,
    }
    initial = report(offset, [], True)
    static = {key: value for key, value in initial.items() if key not in dynamic_names}
    static_width = len(json_bytes(static))
    values, widths, counts = [], dict.fromkeys(fields, 0), dict.fromkeys(fields, 0)
    more = False
    for row in rows:
        if len(values) == limit:
            more = True
            break
        additions = {name: tuple(extract(row)) for name, extract in fields.items()}
        next_widths = {
            name: widths[name] + sum(len(json_bytes(value)) for value in additions[name])
            for name in fields
        }
        next_counts = {name: counts[name] + len(additions[name]) for name in fields}
        values.append(row)
        candidate = report(offset + len(values), values, True)
        dynamic = {key: value for key, value in candidate.items() if key in dynamic_names}
        dynamic.update({name: [] for name in fields})
        row_width = sum(
            next_widths[name] + _SEPARATOR * max(0, next_counts[name] - 1) for name in fields
        )
        width = (
            static_width
            + len(json_bytes(dynamic))
            - 2
            + (_SEPARATOR if static and dynamic else 0)
            + row_width
        )
        if width > max_bytes:
            values.pop()
            if not values:
                raise ValueError("one complete selected answer and its envelope exceed max_bytes")
            more = True
            break
        widths, counts = next_widths, next_counts
    result = report(offset + len(values), values, more)
    while len(json_bytes(result)) > max_bytes:
        if not values:
            raise ValueError("complete selected answer envelope exceeds max_bytes")
        values.pop()
        if not values:
            raise ValueError("one complete selected answer and its envelope exceed max_bytes")
        result = report(offset + len(values), values, True)
    return result
