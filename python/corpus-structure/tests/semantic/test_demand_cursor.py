"""Finite paging coordinates remain separate from captured contextual documents."""

import base64
from typing import Any

import pytest

from corpus_structure.semantic.continuation_codec import (
    DEMAND_MEMBER_CURSOR,
    DEMAND_ROW_CURSOR,
    decode_demand_cursor,
    encode_cursor,
)


def cursor() -> dict[str, Any]:
    return {
        "version": DEMAND_ROW_CURSOR,
        "implementation": "implementation:A",
        "selection": "selection:A",
        "cut": "cut:A",
        "read_id": "read:A",
        "position": 3,
        "seek": {"after": "obligation:A", "support_after": "support:A"},
    }


def test_demand_cursor_retains_native_and_presentation_positions():
    value = cursor()
    assert decode_demand_cursor(encode_cursor(value)) == value


@pytest.mark.parametrize(
    "field", ["request", "scope", "trust_snapshot", "limit", "max_bytes", "recheck_bodies"]
)
def test_demand_cursor_refuses_context_or_acquisition_policy(field):
    value = cursor()
    value[field] = {}
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(encode_cursor(value))


@pytest.mark.parametrize("position", [True, -1, 1.5, 2**63])
def test_demand_cursor_requires_integral_nonnegative_position(position):
    value = cursor()
    value["position"] = position
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(encode_cursor(value))


@pytest.mark.parametrize("seek", [{"after": {}}, {"scope": "A"}, {"support_after": ""}])
def test_demand_cursor_validates_native_seek_coordinates(seek):
    value = dict(cursor(), seek=seek)
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(encode_cursor(value))


def test_member_cursor_keeps_exact_key_and_first_page_read_pin():
    value = cursor()
    del value["seek"]
    value["version"] = DEMAND_MEMBER_CURSOR
    for position in (["obligation:A", "use:A", "result", 0, "product:A", ""], None):
        value["position"] = position
        assert decode_demand_cursor(encode_cursor(value)) == value
    value["position"] = ["obligation:A", "use:A", "result", True, "product:A", ""]
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(encode_cursor(value))


@pytest.mark.parametrize("document", [b'{"position":0,"position":1}', b'{"position":NaN}'])
def test_demand_cursor_rejects_ambiguous_or_nonfinite_json(document):
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(base64.urlsafe_b64encode(document).decode())


def test_governed_cursor_keeps_exact_named_generation():
    value = dict(cursor(), generation=2)
    assert decode_demand_cursor(encode_cursor(value)) == value
    value["generation"] = True
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(encode_cursor(value))


def test_all_cursor_decoders_bound_input_before_parsing():
    from corpus_structure.semantic.continuation_codec import decode_rich_cursor

    encoded = base64.urlsafe_b64encode(b'{"padding":"' + b"a" * 25000 + b'"}').decode()
    for decode in (decode_demand_cursor, decode_rich_cursor):
        with pytest.raises(ValueError, match="invalid"):
            decode(encoded)


@pytest.mark.parametrize("position", [True, -1, 1.5, 2**63, "35"])
def test_pinned_derived_cursor_requires_a_finite_integral_offset(position):
    from corpus_structure.semantic.continuation_codec import decode_pinned_cursor

    with pytest.raises(ValueError, match="ordinal"):
        decode_pinned_cursor(
            encode_cursor(
                dict(
                    version="derived-test",
                    selection="selection:A",
                    implementation="implementation:A",
                    cut="cut:A",
                    read_id="read:A",
                    position=position,
                )
            ),
            version="derived-test",
            selection="selection:A",
        )
