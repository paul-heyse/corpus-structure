"""Current selected query12, native boundary scope and actual MCP resource consumers."""

from typing import Any

import anyio
import pytest
from fastmcp import Client
from methods.contextual_query_support import POINTER, TEXT, primary, source
from sqlalchemy import create_engine

from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.demand_results import DemandResult
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.serve.demand_context import DemandContextRequest, inspect_demand_context
from semantic.demand_result_support import demand_result_page


def fixture() -> tuple[DemandContextRequest, list[dict[str, Any]]]:
    frame = source()
    inventories, reference = primary(
        frame,
        dict(
            local_id="frame",
            kind="predicate",
            family="construction.source_readings",
            vocabulary="source-linguistic-rules-1",
            literals=["A supervisor approves the request."],
            children=[
                dict(role="predicate", target="predicate"),
                dict(role="direct_object", target="object"),
            ],
        ),
        [
            dict(local_id="predicate", literals=["approves"], status="interpreted"),
            dict(local_id="object", literals=["the request"], status="interpreted"),
        ],
    )
    inventory = inventories[reference.product].payload
    packets = []
    for name, tag in (("terms", "term"), ("occurrences", "occurrence")):
        packets.extend(
            dict(
                member_id=row["local_id"],
                kind_contract="kind:" + tag,
                context=dict(subject="primary", original_source="document:A", analyzed_scope={}),
                body=dict(row, record_type=tag),
            )
            for row in inventory[name]
        )
    body = dict(
        source=frame.value["source"],
        selectors=frame.value["selectors"],
        members=packets,
        dependencies=[],
        coverage=[],
    )
    start = TEXT.index("request")
    anchor = dict(
        pin=record_source_pin(frame),
        space="native",
        pointer=POINTER,
        precision="exact",
        start=start,
        end=start + 7,
        source_piece="request",
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    focal = dict(occurrence_id=occurrence_identity((anchor,)), anchors=[anchor])
    rows = [
        dict(
            key="source-parent",
            relation="kb.data_product",
            record=dict(id="product:source", canonical_body=semantic_value(dict(members=[]))),
        ),
        dict(
            key="source-member",
            relation="kb.data_product_member",
            record=dict(
                product_id="product:source",
                member_id="member:source",
                kind_contract="kind:source",
                subject="source:A",
                subject_definition="original-source-view",
                original_source="document:A",
                analyzed_scope=decode_semantic_value(
                    json_loads(frame.pin.values()["analyzed_scope_meaning"])
                ),
                body=semantic_value(frame.value),
            ),
        ),
        dict(
            key="primary",
            relation="kb.data_product",
            record=dict(id="product:primary", canonical_body=semantic_value(body)),
        ),
        dict(
            key="focal",
            relation="kb.data_product",
            record=dict(id="product:focal", canonical_body=semantic_value(focal)),
        ),
    ]
    request = DemandContextRequest(
        demand_id="demand:A",
        project_id="project:A",
        source_product_id="product:source",
        source_member_id="member:source",
        primary_product_id="product:primary",
        primary_member_id="frame",
        focal_product_id="product:focal",
        recipe="located-frame-2",
    )
    return request, rows


def install(monkeypatch, rows, *, trust=None):
    calls = []

    def read(connection, demand_id, *, project_id, scope, **kwargs):
        calls.append((demand_id, project_id, scope, kwargs))
        native = demand_result_page(trust=trust)
        native["scope"] = scope
        return DemandResult(json_bytes(native))

    monkeypatch.setattr("corpus_structure.semantic.demand_results.read_demand_result", read)
    monkeypatch.setattr(
        "corpus_structure.semantic.demand_results.stream_selected_support",
        lambda conn, page, **kwargs: iter(rows),
    )
    return calls


def test_current_query_context_uses_exact_selected_products_and_source(monkeypatch):
    request, rows = fixture()
    calls = install(monkeypatch, rows)
    result = inspect_demand_context(None, request)
    assert result["availability"] == "available"
    assert result["rendered"] == "Predicate: approves\nArgument direct_object: the request"
    assert result["primary"] == {"product_id": "product:primary", "member_id": "frame"}
    assert result["source"]["source_product"] == "product:source"
    assert calls[0][2] == {"product_ids": ["product:focal", "product:primary", "product:source"]}
    assert result["inference"] == "not_run"
    changed = request.model_copy(update={"read_id": "read:A", "expected_cut": result["cut_id"]})
    install(monkeypatch, rows, trust={"source:A": 1})
    with pytest.raises(ValueError, match="trust assessment"):
        inspect_demand_context(None, changed)


def test_current_query_context_missing_focal_is_unavailable_not_absent(monkeypatch):
    request, rows = fixture()
    install(monkeypatch, rows[:-1])
    result = inspect_demand_context(None, request)
    assert result["availability"] == "unavailable"
    assert "absent" not in result.values()


def test_actual_query12_tool_and_resource_preserve_pinned_semantic_refs(monkeypatch):
    from corpus_structure.intervene.server import build_server
    from corpus_structure.semantic.data_operation_external import ExternalDataSession

    request, rows = fixture()
    calls = install(monkeypatch, rows)
    engine = create_engine("sqlite://")

    async def journey():
        async with Client(
            build_server(
                session=ExternalDataSession(engine, "project:A", demand_id="demand:A"),
                read_engine=engine,
                project="project:A",
                demand="demand:A",
            )
        ) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert {
                "inspect_characterization",
                "inspect_definition",
                "inspect_query_context",
            } <= tools.keys()
            result = await client.call_tool(
                "inspect_query_context", {"request": request.model_dump(mode="json")}
            )
            assert result.structured_content is not None
            report = result.structured_content["result"]
            assert report["context"]["evidence"] == {
                "product_id": "product:primary",
                "member_id": "frame",
            }
            resource = await client.read_resource(result.structured_content["resource"])
            assert hasattr(resource[0], "text")
            replayed = json_loads(resource[0].text)["result"]
            assert replayed["context"] == report["context"]
            assert calls[-1][3]["continuation"]["read_id"] == "read:A"

    try:
        anyio.run(journey)
    finally:
        engine.dispose()
