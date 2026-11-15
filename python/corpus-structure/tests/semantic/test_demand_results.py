"""Independent selected membership, group pagination and actual MCP read contracts."""
from decimal import Decimal

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import create_engine

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_results import CutSelection, DemandResult
from corpus_structure.serve.demand_journey import DemandQueryRequest, _decode, serve_demand_query


def _page(*, trust=None, member_id=None, empty=False):
    body = dict(members=[dict(member_id="first", kind_contract="kind:first", context=dict(subject="one", original_source="source:A", analyzed_scope={"scale": Decimal("1.20")}), body={"amount": Decimal("12.340")}), dict(member_id="second", kind_contract="kind:second", context=dict(subject="two", original_source="source:A", analyzed_scope={}), body={"target": "first", "direction": "outgoing"})])
    return dict(demand_id="demand:A", project_id="project:A", release_id="release:A", runtime_id="runtime:A", selection={"targets": ["op:A"]}, trust_snapshot={} if trust is None else trust, read_id="read:A", read_snapshot="1:2:", frontier_at="2026-11-14T00:00:00+00:00", scope={}, view="products", state="active", populations=[], original_source_admissions=[], continuation=None,
                obligations=[dict(obligation_id="obligation:A", fate="waiting" if empty else "fulfilled")],
                uses=[] if empty else [dict(use_id="use:A", obligation_id="obligation:A", fate="fulfilled", historical_fate="fulfilled", derivation_id="episode:original", products=[dict(role="result", position=0, multiplicity=2, product_id="product:A", member_id=member_id, kind_contract="kind:container", subject="root", original_source="source:A", analyzed_scope={}, body_state="present", body=semantic_value(body))])])


def test_members_retain_actual_context_episode_direction_and_multiplicity():
    page = DemandResult(json_bytes(_page()))
    members = page.members()
    assert [(row["product_id"], row["member_id"]) for row in members] == [("product:A", None), ("product:A", "first"), ("product:A", "second")]
    assert {row["derivation_id"] for row in members} == {"episode:original"}
    assert {row["multiplicity"] for row in members} == {2}
    assert members[1]["body"]["amount"] == Decimal("12.340")
    assert members[1]["analyzed_scope"] == {"scale": Decimal("1.20")}
    assert members[2]["body"] == {"target": "first", "direction": "outgoing"}
    selected = DemandResult(json_bytes(_page(member_id="second"))).members()
    assert [row["member_id"] for row in selected] == ["second"]
    with pytest.raises(ValueError, match="absent"):
        DemandResult(json_bytes(_page(member_id="foreign"))).members()


def test_cut_distinguishes_native_boundary_context_and_current_trust():
    original = CutSelection.from_native(_page())
    assert original.identity == CutSelection.from_native(_page()).identity
    assert original.identity != CutSelection.from_native(_page(trust={"source:A": 1})).identity
    changed = _page()
    changed["scope"] = {"subject": "one"}
    assert original.identity != CutSelection.from_native(changed).identity


def test_current_member_cursor_preserves_whole_group_and_refuses_wrong_target(monkeypatch):
    def read(connection, demand_id, *, project_id, continuation, **kwargs):
        assert demand_id == "demand:A" and project_id == "project:A"
        request = dict(continuation or {"demand_id": demand_id}, limit=1, max_bytes=1048576, view="products")
        return DemandResult(json_bytes(_page()), json_bytes(request))
    monkeypatch.setattr("corpus_structure.serve.demand_journey.read_demand_result", read)
    request = DemandQueryRequest(demand_id="demand:A", project_id="project:A", limit=1)
    first = serve_demand_query(None, request)
    assert [row["member_id"] for row in first["items"]] == [None]
    assert "selection" not in _decode(first["continuation"])["request"]
    second = serve_demand_query(None, request.model_copy(update={"cursor": first["continuation"]}))
    assert [row["member_id"] for row in second["items"]] == ["first"]
    third = serve_demand_query(None, request.model_copy(update={"cursor": second["continuation"]}))
    assert [row["member_id"] for row in third["items"]] == ["second"]
    assert third["continuation"] is None
    with pytest.raises(ValueError, match="selection"):
        serve_demand_query(None, request.model_copy(update={"cursor": first["continuation"], "kind_contract": "foreign"}))
    resource = DemandQueryRequest.model_validate(_decode(second["resource_handle"]))
    assert serve_demand_query(None, resource)["items"] == second["items"]


def test_waiting_and_completed_empty_operations_do_not_claim_absence(monkeypatch):
    native = _page(empty=True)
    monkeypatch.setattr("corpus_structure.serve.demand_journey.read_demand_result", lambda *a, **k: DemandResult(json_bytes(native)))
    request = DemandQueryRequest(demand_id="demand:A", project_id="project:A", view="operations")
    result = serve_demand_query(None, request)
    assert result["items"] == [{"obligation": {"obligation_id": "obligation:A", "fate": "waiting"}, "uses": []}]
    result = serve_demand_query(None, request.model_copy(update={"view": "members"}))
    assert result["items"] == [] and result["knowledge"] == "unknown"


def test_actual_main_mcp_read_and_resource_use_same_owner_and_exact_json(monkeypatch):
    from corpus_structure.intervene.server import build_server
    from corpus_structure.serve.demand_journey import _cursor
    engine = create_engine("sqlite://")
    request = DemandQueryRequest(demand_id="demand:A", project_id="project:A", max_bytes=8192)
    calls = []
    def selected(connection, acquired):
        calls.append(acquired)
        return dict(cut_id="cut:A", items=[{"amount": Decimal("10000000000.00000000001")}], resource_handle=_cursor(acquired.model_dump(mode="python")))
    monkeypatch.setattr("corpus_structure.intervene.demand_read_tools.serve_demand_query", selected)
    async def journey():
        async with Client(build_server(session=object(), read_engine=engine, project="project:A", demand="demand:A")) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert tools["read_result"].annotations.read_only_hint is True
            result = await client.call_tool("read_result", {"request": request.model_dump(mode="json")})
            exact = json_loads(result.structured_content["exact_json"])
            assert exact["items"][0]["amount"] == Decimal("10000000000.00000000001")
            resource = await client.read_resource(result.structured_content["resource"])
            assert resource and len(calls) == 2
            denied = await client.call_tool("read_result", {"request": request.model_copy(update={"project_id": "foreign"}).model_dump(mode="json")}, raise_on_error=False)
            assert denied.is_error and len(calls) == 2
    try:
        anyio.run(journey)
    finally:
        engine.dispose()
