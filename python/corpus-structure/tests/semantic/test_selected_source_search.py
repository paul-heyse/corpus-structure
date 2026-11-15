"""Exact current search scope, native ranking and continuation refusals."""

import base64

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.serve.source_search import SourceSearchRequest, _position, _rank_sections
from semantic.selected_source_contract_support import selection


def request(**changes):
    pin, _, _ = selection()
    fields = dict(
        project_id=pin.project_id, demand_id=pin.demand_id, read_id=pin.read_id,
        sources=[pin.model_dump()], text="running",
    )
    fields.update(changes)
    return SourceSearchRequest.model_validate(fields)


def test_search_refuses_mixed_native_cuts_and_duplicate_source_populations():
    pin, _, _ = selection()
    for sources in (
        [pin.model_dump(), pin.model_dump()],
        [{**pin.model_dump(), "read_id": "read:another"}],
    ):
        with pytest.raises(ValidationError):
            request(sources=sources)


def test_search_refuses_old_run_scope_and_nonintegral_work_bounds():
    with pytest.raises(ValidationError):
        SourceSearchRequest.model_validate(dict(run_id=1, text="running"))
    for value in (True, "12", 1.5):
        with pytest.raises(ValidationError):
            request(max_rows=value)


@pytest.mark.parametrize("score,key", [("nan", "key"), ("0x1p+0", None), ("-0x1p+0", "key")])
def test_search_refuses_invalid_cursor_position(score, key):
    cursor = base64.urlsafe_b64encode(canonical_bytes(dict(
        version=1, selection="expected", score=score, key=key,
    ))).decode()
    with pytest.raises(InvalidContinuation):
        _position(request(cursor=cursor), "expected")


def test_search_continuation_carries_exact_score_and_population_identity():
    score = 0.123456789
    cursor = base64.urlsafe_b64encode(canonical_bytes(dict(
        version=1, selection="expected", score=score.hex(), key="source:one",
    ))).decode()
    assert _position(request(cursor=cursor), "expected") == (score, "source:one")
    with pytest.raises(InvalidContinuation):
        _position(request(cursor=cursor), "changed-source-population")


@pytest.mark.db
def test_native_search_retains_english_stemming_rank_and_total_tie_order(semantic_bare_engine):
    with semantic_bare_engine.connect() as connection:
        first = _rank_sections(
            connection, [("z", "The runner was running."), ("a", "The runner was running."), ("other", "A cat sleeps.")],
            "run", position=None, limit=1,
        )
        assert len(first) == 1 and first[0]["key"] == "a"
        assert "running" in first[0]["excerpt"] and first[0]["score"] > 0
        remaining = _rank_sections(
            connection, [("z", "The runner was running."), ("a", "The runner was running."), ("other", "A cat sleeps.")],
            "run", position=(first[0]["score"], first[0]["key"]), limit=2,
        )
        assert [row["key"] for row in remaining] == ["z"]
