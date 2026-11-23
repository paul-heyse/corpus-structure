"""Exact bounded continuation encoding without selected-read acquisition."""

import base64
from hashlib import sha256

from pydantic import BaseModel

from .data_operation_json import finite_json_loads, json_bytes, native_json_loads
from .refusal_types import InvalidContinuation

_MAX_ENCODED = 32768

DEMAND_MEMBER_CURSOR = "demand-member-cursor-v1"
DEMAND_ROW_CURSOR = "demand-row-cursor-v1"
DEMAND_SEEK_FIELDS = ("after", "support_after", "obligation_id")


def _decode_object(value, *, load=native_json_loads):
    if type(value) is not str or len(value) > _MAX_ENCODED:
        raise ValueError("selected cursor exceeds the supported encoded bound")
    parsed = load(base64.b64decode(value, altchars=b"-_", validate=True))
    if not isinstance(parsed, dict):
        raise ValueError("selected continuation requires an object")
    return parsed


def cursor_ordinal(value) -> int:
    """Validate a derived position before branching or acquiring a cut."""
    if type(value) is not int or not 0 <= value < 2**63:
        raise ValueError("invalid selected continuation ordinal")
    return value


def selection_digest(selection) -> str:
    """Bind a cursor to the caller's exact selection without embedding it."""
    return sha256(json_bytes(selection)).hexdigest()


def _selected_cursor(value, *, version, selection, fields):
    cursor = decode_rich_cursor(value)
    _require_selected_cursor(cursor, version=version, selection=selection, fields=fields)
    return cursor


def _require_selected_cursor(cursor, *, version, selection, fields):
    if (
        set(cursor) != {"version", "selection", "implementation", "position", *fields}
        or cursor["version"] != version
        or cursor["selection"] != selection
        or type(cursor["implementation"]) is not str
        or not cursor["implementation"]
    ):
        raise InvalidContinuation(
            "selected continuation differs from requested selection", reason="invalid_continuation"
        )


def _require_ordinal(position):
    try:
        cursor_ordinal(position)
    except ValueError as error:
        raise InvalidContinuation(str(error), reason="invalid_continuation") from error


def decode_selection_cursor(value, *, version, selection, implementation):
    """Open a derived cursor whose selection already contains all explicit read pins."""
    cursor = _selected_cursor(value, version=version, selection=selection, fields=())
    require_cursor_implementation(cursor, implementation)
    _require_ordinal(cursor["position"])
    return cursor


def decode_pinned_cursor(value, *, version, selection, keyset=False, extra_fields=()):
    """Open a compact selected continuation and validate its finite coordinates."""
    cursor = _selected_cursor(
        value, version=version, selection=selection, fields=("cut", "read_id", *extra_fields)
    )
    _require_native_pin(cursor)
    position = cursor["position"]
    if keyset == "native-output":
        _require_native_output_position(position)
    elif keyset:
        if type(position) is not str or not position:
            raise InvalidContinuation(
                "invalid selected keyset position", reason="invalid_continuation"
            )
    else:
        _require_ordinal(position)
    return cursor


def _require_native_pin(cursor):
    if any(type(cursor[key]) is not str or not cursor[key] for key in ("cut", "read_id")):
        raise InvalidContinuation("invalid selected native read pin", reason="invalid_continuation")


def _require_native_output_position(position):
    # Native output order is obligation, use, role, position, product and
    # member. A whole product has an empty member coordinate.
    if (
        type(position) is not list
        or len(position) != 6
        or any(type(position[i]) is not str or not position[i] for i in (0, 1, 2, 4))
        or type(position[5]) is not str
    ):
        raise InvalidContinuation(
            "invalid selected native output key", reason="invalid_continuation"
        )
    _require_ordinal(position[3])


def bind_cursor_request(request, cursor):
    """Reopen the cursor's exact authorized read, including its implementation."""
    if request.read_id is not None and (
        request.read_id != cursor["read_id"] or request.expected_cut != cursor["cut"]
    ):
        raise InvalidContinuation(
            "selected continuation differs from requested native read",
            reason="invalid_continuation",
        )
    if request.implementation is not None and request.implementation != cursor["implementation"]:
        raise InvalidContinuation(
            "selected continuation differs from requested implementation",
            reason="invalid_continuation",
        )
    return request.model_copy(
        update=dict(
            read_id=cursor["read_id"],
            expected_cut=cursor["cut"],
            implementation=cursor["implementation"],
        )
    )


def require_cursor_cut(cursor, cut):
    if cursor["cut"] != cut.identity or (
        "read_id" in cursor and cursor["read_id"] != cut.record["read_id"]
    ):
        raise InvalidContinuation(
            "cursor belongs to another cut/trust assessment", reason="invalid_continuation"
        )


def require_cursor_implementation(cursor, implementation):
    if cursor["implementation"] != implementation:
        raise InvalidContinuation(
            "selected continuation differs from installed implementation",
            reason="invalid_continuation",
        )


def pinned_cursor_basis(version, selection, cut, implementation, **fields):
    return dict(
        version=version,
        selection=selection,
        cut=cut.identity,
        read_id=cut.record["read_id"],
        implementation=implementation,
        **fields,
    )


def encode_cursor(value):
    wire = json_bytes(value)
    if type(wire) is not bytes:
        raise TypeError("selected cursor must be encoded as native bytes")
    encoded = base64.urlsafe_b64encode(wire).decode()
    if len(encoded) > _MAX_ENCODED:
        raise ValueError("selected cursor exceeds the supported encoded bound")
    return encoded


def decode_resource_handle[Request: BaseModel](value: str, request: type[Request]) -> Request:
    """Decode a bounded selected resource handle through its actual request model."""
    try:
        parsed = _decode_object(value)
    except (ValueError, TypeError) as error:
        raise ValueError("invalid selected resource handle") from error
    return request.model_validate(parsed)


def decode_demand_cursor(value):
    """Read exact native positions without accepting an embedded request or scope."""
    try:
        cursor = _decode_object(value, load=finite_json_loads)
        version, selection = cursor.get("version"), cursor.get("selection")
        if version not in (DEMAND_MEMBER_CURSOR, DEMAND_ROW_CURSOR):
            raise ValueError("unsupported demand cursor version")
        if type(selection) is not str or not selection:
            raise ValueError("invalid demand cursor selection")
        fields = ["cut", "read_id"]
        if "generation" in cursor:
            fields.append("generation")
            if cursor_ordinal(cursor["generation"]) == 0:
                raise ValueError("invalid governed cursor generation")
        if version == DEMAND_ROW_CURSOR:
            fields.append("seek")
        _require_selected_cursor(cursor, version=version, selection=selection, fields=fields)
        _require_native_pin(cursor)
        if version == DEMAND_MEMBER_CURSOR:
            # A first-page resource still carries its exact pin, with no seek key.
            if cursor["position"] is not None:
                _require_native_output_position(cursor["position"])
        else:
            cursor_ordinal(cursor["position"])
            seek = cursor["seek"]
            if (
                type(seek) is not dict
                or not seek.keys() <= set(DEMAND_SEEK_FIELDS)
                or any(type(position) is not str or not position for position in seek.values())
            ):
                raise ValueError("invalid demand cursor seek coordinates")
        return cursor
    except (ValueError, TypeError) as error:
        raise ValueError("invalid selected-result cursor") from error


def decode_rich_cursor(value: str) -> dict:
    try:
        return _decode_object(value)
    except (ValueError, TypeError) as error:
        raise InvalidContinuation(
            "invalid rich query cursor", reason="invalid_continuation"
        ) from error
