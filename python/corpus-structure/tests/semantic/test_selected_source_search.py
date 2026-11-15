"""Exact current search scope, native ranking and continuation refusals."""

import base64
from decimal import Decimal

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


@pytest.mark.parametrize("surface", ["main", "retained"])
def test_current_find_mcp_preserves_selected_handles_unicode_and_fractional_cut(monkeypatch, surface):
    from contextlib import nullcontext

    import anyio
    from fastmcp import Client
    from sqlalchemy import create_engine

    from corpus_structure.intervene.semantic_server import build_retained_reader_server
    from corpus_structure.serve.native_source import NativeSourceRequest
    from corpus_structure.serve.source_search import SourceSearchHit, SourceSearchResponse

    pin, cut, publication = selection()
    cut["scope"] = {"fraction": Decimal("0.123456789012345678901")}
    payload = 'Unicode α "quoted" \\ slash\n' * 40
    monkeypatch.setattr(
        "corpus_structure.semantic.demand_results.selected_read_snapshot",
        lambda selected: nullcontext(None),
    )

    def search(connection, selected):
        assert selected.sources == (pin,)
        assert (selected.project_id, selected.demand_id, selected.read_id) == (
            pin.project_id, pin.demand_id, pin.read_id,
        )
        return SourceSearchResponse(
            cut=cut, population_complete=True, rows=[SourceSearchHit(
                source=pin, original_source="original.pdf", source_digest=publication.source_digest,
                projection_digest="b" * 64,
                selection=NativeSourceRequest(**pin.model_dump(), section_pointer="#/groups/8", membership="descendants"),
                excerpt=payload, score=0.5,
            )],
        )

    monkeypatch.setattr("corpus_structure.serve.source_search.search_source", search)
    engine = create_engine("sqlite://")

    from corpus_structure.intervene.server import build_server
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.demand_results import CutSelection
    server = build_server(project="p", demand=pin.demand_id, read_engine=engine) if surface == "main" else build_retained_reader_server(project="p", read_engine=engine)
    async def journey():
        async with Client(server) as client:
            result = await client.call_tool("find", {"request": request().model_dump(mode="json")})
            assert not result.is_error
            assert result.structured_content is not None
            assert result.structured_content["format"] == "selected-source-search-exact-json-v1"
            exact = json_loads(result.structured_content["exact_json"])
            assert exact["cut"]["scope"]["fraction"] == Decimal("0.123456789012345678901")
            assert exact["rows"][0]["score"] == Decimal("0.5")
            from corpus_structure.semantic.data_operation_json import json_bytes
            assert result.structured_content["cut_id"] == CutSelection(json_bytes(cut)).identity
            row = exact["rows"][0]
            assert row["excerpt"] == payload
            assert row["source"] == pin.model_dump()
            assert row["selection"]["product_id"] == pin.product_id
            assert exact["cut"] == cut
            refused = await client.call_tool("find", {"request": request(max_bytes=1024).model_dump(mode="json")}, raise_on_error=False)
            assert refused.is_error

    try:
        anyio.run(journey)
    finally:
        engine.dispose()
