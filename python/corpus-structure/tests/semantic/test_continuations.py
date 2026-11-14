"""Independent continuation failure expectations, not producer-derived acceptance vectors."""

import base64
import json

import pytest

from corpus_structure.semantic.continuations import decode_continuation, validate_continuation
from corpus_structure.semantic.refusals import (
    InvalidContinuation,
    StaleSnapshot,
    WrongBinding,
    WrongRelease,
)


@pytest.mark.parametrize(
    "field,actual,reason,exception",
    [
        ("release", "other", "wrong_release", WrongRelease),
        ("realization", "other", "wrong_realization", WrongBinding),
        ("query", "other", "wrong_query", WrongBinding),
        ("params", "other", "wrong_parameters", WrongBinding),
        ("projection", "fact", "wrong_projection", WrongBinding),
        ("arithmetic", "float", "wrong_profile", WrongBinding),
        ("revision", 2, "stale_revision", StaleSnapshot),
        ("version", "2", "stale_version", StaleSnapshot),
    ],
)
def test_binding_failures_are_distinct_from_freshness(field, actual, reason, exception):
    expected = {
        "release": "r",
        "realization": "z",
        "query": "claims",
        "params": "p",
        "projection": "accepted",
        "arithmetic": "exact",
        "revision": 1,
        "version": "1",
    }
    with pytest.raises(exception) as caught:
        validate_continuation(None, {**expected, field: actual}, expected)
    assert caught.value.reason == reason
    validate_continuation(None, expected, expected)


@pytest.mark.parametrize("replacement", [True, "1", 1.0, None])
def test_named_token_revision_is_an_integer_not_coercible(replacement):
    body = {
        "token_version": 2,
        "query_contract": "q",
        "implementation": "i",
        "compatibility": "c",
        "run": 1,
        "query": "claims",
        "version": "1",
        "params": "p",
        "position": None,
        "release": "r",
        "realization": "z",
        "revision": replacement,
        "projection": "accepted",
        "arithmetic": "exact",
    }
    token = base64.urlsafe_b64encode(json.dumps(body).encode()).decode()
    with pytest.raises(InvalidContinuation) as caught:
        decode_continuation(token, kind="named")
    assert caught.value.reason == "invalid_token"


def test_real_released_continuation_contract_is_consumed():
    from semantic.proposals_support import prepared

    release = prepared(composed=True)
    validate_continuation(release, {"release": "r"}, {"release": "r"})
    assert ("validate_continuation", "reason", "reason") in release._result_adapters
    with pytest.raises(WrongRelease):
        validate_continuation(release, {"release": "other"}, {"release": "r"})
