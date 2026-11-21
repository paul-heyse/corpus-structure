"""Finite paging coordinates remain separate from captured contextual documents."""

import base64
from copy import deepcopy

import pytest

from corpus_structure.semantic.continuation_codec import decode_demand_cursor, encode_cursor


def cursor():
    return {
        "version": "demand-query-v2",
        "implementation": "implementation:A",
        "selection": "selection:A",
        "cut": "cut:A",
        "ordinal": 3,
        "request": {
            "demand_id": "demand:A",
            "view": "products",
            "scope": {"subject": "subject:A", "original_source": None},
        },
    }


def test_demand_cursor_retains_exact_paging_request():
    value = cursor()
    assert decode_demand_cursor(encode_cursor(value)) == value
    checked = decode_demand_cursor(encode_cursor(value))
    checked["request"]["scope"]["subject"] = "changed"
    assert value["request"]["scope"]["subject"] == "subject:A"


@pytest.mark.parametrize("field", ["selection", "trust_snapshot", "limit", "max_bytes", "recheck_bodies"])
def test_demand_cursor_refuses_context_or_acquisition_policy(field):
    value = cursor()
    value["request"][field] = {} if field in {"selection", "trust_snapshot"} else 1
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(encode_cursor(value))


@pytest.mark.parametrize("ordinal", [True, -1, 1.5])
def test_demand_cursor_requires_integral_nonnegative_position(ordinal):
    value = cursor()
    value["ordinal"] = ordinal
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(encode_cursor(value))


def test_demand_cursor_validates_embedded_native_request():
    value = deepcopy(cursor())
    value["request"]["scope"]["analyzed_scope"] = {"scale": 1.2}
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(encode_cursor(value))


@pytest.mark.parametrize("document", [b'{"ordinal":0,"ordinal":1}', b'{"ordinal":NaN}'])
def test_demand_cursor_rejects_ambiguous_or_nonfinite_json(document):
    with pytest.raises(ValueError, match="invalid selected-result cursor"):
        decode_demand_cursor(base64.urlsafe_b64encode(document).decode())
