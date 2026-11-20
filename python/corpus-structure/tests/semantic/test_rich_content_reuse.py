"""An authorized current rich entity page can reuse its immutable whole admission."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.cache_store import CacheStore
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.demand_wire import decode_wire_demand_result
from corpus_structure.semantic.refusal_types import RichQueryRefused
from corpus_structure.semantic.rich_query_projection import (
    RichQueryInput,
    frontier_content_witness,
    prepare_rich_frontier,
)
from corpus_structure.semantic.selected_query_cache import SELECTED_QUERY_CACHE, disk_row_cache
from corpus_structure.semantic.value_codec import decimal_digit_limit
from corpus_structure.serve import rich_queries
from corpus_structure.serve.rich_knowledge import (
    SelectedRichKnowledge,
    SelectedRichReference,
)
from semantic.selected_query_cache_support import complete_serving_code as complete_serving_code
from semantic.test_rich_queries import query_source as query_source
from semantic.test_rich_queries import statistics as statistics
from semantic.test_rich_query_delivery import CUT


def witnessed_frontier(content):
    native = decode_wire_demand_result(content)
    return frontier_content_witness(prepare_rich_frontier(json_bytes(native)))


def frontier_record(cut=None):
    selection = dict(
        version="data-demand-public-selection-v1",
        intent_digest="selected-intent",
        model="selected-model",
        discovery=[],
        root_operations=[],
        roots=[],
        targets=["rich.admit"],
    )
    return dict(
        CUT if cut is None else cut,
        selection=selection,
        intent=selection,
        view="frontier",
        root=[],
        obligations=[],
        uses=[],
        populations=[],
        continuation=None,
    )


def test_frontier_witness_keeps_scope_and_native_width_without_receipt_identity():
    before: dict[str, Any] = frontier_record()
    before.update(
        read_id="read:1111",
        read_snapshot="2:8:",
        frontier_at="2026-11-19T01:00:00.11223+00:00",
        trust_snapshot={"scope": 1},
        scope={"product_ids": ["product:1"]},
    )
    before["continuation"] = dict(
        after="obligation:1",
        demand_id=before["demand_id"],
        limit=1,
        max_bytes=1048576,
        selection=before["selection"],
        trust_snapshot=before["trust_snapshot"],
        view="frontier",
        **{name: before[name] for name in ("read_id", "read_snapshot", "frontier_at")},
    )
    second = deepcopy(before)
    second["read_id"] = second["continuation"]["read_id"] = "read:2222"
    second["read_snapshot"] = second["continuation"]["read_snapshot"] = "3:9:"

    first = witnessed_frontier(json_bytes(before))
    assert first is not None and witnessed_frontier(json_bytes(second)) == first
    for name, value in (
        ("release_id", "release:updated"),
        ("runtime_id", "runtime:updated"),
        ("trust_snapshot", {"scope": 2}),
        ("scope", {"product_ids": ["product:2"]}),
    ):
        assert witnessed_frontier(json_bytes(second | {name: value})) != first
    second["read_snapshot"] = second["continuation"]["read_snapshot"] = "30:90:"
    assert witnessed_frontier(json_bytes(second)) != first
    assert before["continuation"]["read_id"] == "read:1111"
    admitted = decode_wire_demand_result(json_bytes(before))
    captured = prepare_rich_frontier(json_bytes(admitted))
    admitted["trust_snapshot"]["changed-after-acquisition"] = 1
    assert frontier_content_witness(captured) == first
    second["continuation"]["read_id"] = "another-read"
    assert witnessed_frontier(json_bytes(second)) is None
    assert witnessed_frontier(json_bytes(before | {"view": "products"})) is None


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
        witness = witnessed_frontier(json_bytes(frontier_record(cut.record)))
        return SelectedRichReference(cut, b"{}", reference, graph.context, content_witness=witness)

    def derive(connection, demand_id, *, cut, **options):
        derived.append(cut.identity)
        return SelectedRichKnowledge(
            cut,
            b"{}",
            reference,
            graph.context,
            RichQueryInput(
                index.state.prepared,
                index.state.model,
                graph.context,
                json_bytes(graph.root_input.reference.model_dump(mode="python")),
                json_bytes(semantic_value(index.state.graph.model_dump(mode="python"))),
                decimal_fixed_point_digits=decimal_digit_limit(),
            ),
        )

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


@pytest.mark.parametrize(
    "record",
    (
        {"kind": "computation", "derivation_id": "derivation:1", "admission_use_id": "use:1"},
        {"kind": "original-source", "admission_id": "admission:1", "source_reference": "source:1"},
        {"kind": "authored", "admission_id": "admission:1", "source_reference": "source:1"},
    ),
)
def test_rich_support_normalization_needs_only_its_exact_reference_fields(monkeypatch, record):
    from corpus_structure.semantic import value_codec
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichSelectedMember,
        rich_reference_key,
        rich_support_records,
    )

    def forbid_model():
        raise AssertionError("reference normalization must not acquire a numeric model")

    monkeypatch.setattr(value_codec, "decimal_digit_limit", forbid_model)
    reference = DdoRichSelectedMember.model_validate(
        dict(
            product_id="product:1",
            member_id=None,
            kind_contract="kind:1",
            support_references=[record, record],
        )
    )
    assert rich_support_records(reference.support_references) == [record]
    assert rich_reference_key(reference) == canonical_bytes(["product:1", None, "kind:1", [record]])
