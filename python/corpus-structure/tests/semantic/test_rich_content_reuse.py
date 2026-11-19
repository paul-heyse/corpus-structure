"""An authorized current rich entity page can reuse its immutable whole admission."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.cache_store import CacheStore
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.rich_queries import RichQueryRefused
from corpus_structure.semantic.selected_query_cache import SELECTED_QUERY_CACHE, disk_row_cache
from corpus_structure.serve import rich_queries
from corpus_structure.serve.rich_knowledge import (
    SelectedRichKnowledge,
    SelectedRichReference,
    _frontier_content_witness,
)
from semantic.selected_query_cache_support import complete_serving_code as complete_serving_code
from semantic.test_rich_queries import query_source as query_source
from semantic.test_rich_queries import statistics as statistics
from semantic.test_rich_query_delivery import CUT


def test_frontier_witness_keeps_scope_and_native_width_without_receipt_identity():
    before: dict[str, Any] = {
        "view": "frontier",
        "read_id": "read:1111",
        "read_snapshot": "2:8:",
        "frontier_at": "2026-11-19T01:00:00.11223+00:00",
        "release_id": "release:first",
        "runtime_id": "runtime:first",
        "trust_snapshot": {"scope": 1},
        "uses": [{"use_id": "use:1", "products": [{"product_id": "product:1"}]}],
    }
    before["continuation"] = {
        name: before[name] for name in ("read_id", "read_snapshot", "frontier_at")
    }
    second = deepcopy(before)
    second["read_id"] = second["continuation"]["read_id"] = "read:2222"
    second["read_snapshot"] = second["continuation"]["read_snapshot"] = "3:9:"

    first = _frontier_content_witness(json_bytes(before))
    assert first is not None and _frontier_content_witness(json_bytes(second)) == first
    for name, value in (
        ("release_id", "release:updated"),
        ("runtime_id", "runtime:updated"),
        ("trust_snapshot", {"scope": 2}),
        ("uses", [{"use_id": "use:2", "products": [{"product_id": "product:1"}]}]),
    ):
        assert _frontier_content_witness(json_bytes(second | {name: value})) != first
    second["read_snapshot"] = second["continuation"]["read_snapshot"] = "30:90:"
    assert _frontier_content_witness(json_bytes(second)) != first


@pytest.mark.usefixtures("complete_serving_code")
def test_entity_reuses_disk_rows_after_fresh_cut_check(
    statistics, monkeypatch, tmp_path, record_property
):
    graph, index = statistics
    reference = graph.root_input.reference
    acquisitions, derived = [], []
    authorized = True

    def acquire(connection, demand_id, **options):
        assert options["content_witness"] and demand_id == CUT["demand_id"]
        if not authorized:
            raise RichQueryRefused("selected body disclosure refused")
        read_id = f"read:{len(acquisitions):04d}"
        cut = CutSelection(json_bytes(CUT | {"read_id": read_id}))
        acquisitions.append(cut.identity)
        witness = _frontier_content_witness(json_bytes(cut.record | {"view": "frontier"}))
        return SelectedRichReference(cut, b"{}", reference, graph.context, content_witness=witness)

    def derive(connection, demand_id, *, cut, **options):
        derived.append(cut.identity)
        return SelectedRichKnowledge(cut, b"{}", reference, graph.context, index.state)

    monkeypatch.setattr(rich_queries, "read_selected_rich_reference", acquire)
    monkeypatch.setattr(rich_queries, "read_selected_rich_knowledge", derive)
    store = CacheStore(tmp_path / "cache", program_store_bytes=0, page_store_bytes=8 * 1024**2)
    request = rich_queries.RichQueryRequest.model_validate(
        dict(
            demand_id=CUT["demand_id"],
            project_id=CUT["project_id"],
            product_id=reference.product_id,
            query={"name": "entity"},
            limit=1,
        )
    )
    with disk_row_cache(store):
        first = rich_queries.serve_rich_query(None, request)
        page = next(tier for tier in store.snapshot().tiers if tier.tier == "pages")
        assert page.entries == 1
        record_property("controlled_entity_page_bytes", page.bytes)
        SELECTED_QUERY_CACHE.clear()
        repeat = rich_queries.serve_rich_query(None, request)
        assert first["cut"]["read_id"] != repeat["cut"]["read_id"]
        assert first["rows"] == repeat["rows"] and len(first["rows"]) == 1
        assert first["cursor"] and repeat["cursor"] != first["cursor"]
        assert acquisitions == [first["cut_id"], repeat["cut_id"]]
        assert derived == [first["cut_id"]]
        authorized = False
        with pytest.raises(RichQueryRefused, match="disclosure refused"):
            rich_queries.serve_rich_query(None, request)
        assert next(tier for tier in store.snapshot().tiers if tier.tier == "pages").hits == 1
