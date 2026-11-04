"""Full registered MCP delivery bounds, independent of source query work admission."""

import json
from contextlib import nullcontext

import anyio
import pytest
from fastmcp import Client
from mcp.types import CallToolResult, TextContent
from sqlalchemy import create_engine, select

from corpus_structure.intervene import semantic_server, service
from corpus_structure.intervene.semantic_server import (
    SemanticAgentSession,
    SemanticProjectSession,
    build_semantic_server,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import ProposalIssue
from corpus_structure.semantic.query import ReadLimit
from corpus_structure.serve.native_source import NativeSourceRequest, NativeSourceResponse
from corpus_structure.serve.source_search import (
    SourceSearchHit,
    SourceSearchRequest,
    SourceSearchResponse,
)

PAYLOAD = 'Unicode \u03b1 "quoted" \\ slash\n' * 25


def _native_request(max_bytes: int = 1024 * 1024):
    return NativeSourceRequest(
        run_id=1, task_id=2, product_key="native", content_digest="a" * 64, max_bytes=max_bytes
    )


def _wire_size(response):
    return len(_wire(response).model_dump_json(by_alias=True, exclude_none=True).encode("utf-8"))


def _wire(response):
    return CallToolResult(
        content=response.content,
        structured_content=response.structured_content,
        is_error=response.is_error,
        meta=response.meta,
    )


@pytest.mark.parametrize("name", ["find", "inspect_source"])
def test_registered_source_tools_bound_whole_wire_and_preserve_payload(monkeypatch, name):
    engine = create_engine("sqlite://")
    produced = []
    monkeypatch.setattr(
        "corpus_structure.semantic.query.read_snapshot", lambda selected: nullcontext(None)
    )

    def inspect(conn, request):
        result = NativeSourceResponse(
            selection=request, release_id="fixture-release", health={}, rows=[{"text": PAYLOAD}]
        )
        assert len(result.model_dump_json().encode()) < request.max_bytes
        produced.append(result.model_dump(mode="json"))
        return result

    def search(conn, request):
        result = SourceSearchResponse(
            run_id=request.run_id,
            rows=[
                SourceSearchHit(
                    source_view_id=3,
                    projection_digest="b" * 64,
                    source_uri="fixture.pdf",
                    selection=_native_request(),
                    excerpt=PAYLOAD,
                    score=1.0,
                )
            ],
        )
        assert len(result.model_dump_json().encode()) < request.max_bytes
        produced.append(result.model_dump(mode="json"))
        return result

    monkeypatch.setattr("corpus_structure.serve.native_source.inspect_native_source", inspect)
    monkeypatch.setattr("corpus_structure.serve.source_search.search_source", search)

    def request(budget):
        if name == "find":
            return SourceSearchRequest(run_id=1, text="Unicode", max_bytes=budget)
        return _native_request(max_bytes=budget)

    async def journey():
        async with Client(build_semantic_server(SemanticAgentSession(engine, 1))) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            schema = tools[name].output_schema
            assert schema is not None and schema["type"] == "object"
            assert "rows" in schema["properties"]
            annotations = tools[name].annotations
            assert annotations is not None and annotations.read_only_hint is True
            refused = await client.call_tool(
                name, {"request": request(2048).model_dump(mode="json")}, raise_on_error=False
            )
            assert refused.is_error and "oversized_item" in str(refused.content)
            assert PAYLOAD not in str(refused.content)
            delivered = await client.call_tool(
                name, {"request": request(8192).model_dump(mode="json")}
            )
            assert not delivered.is_error
            assert delivered.structured_content == produced[-1]
            assert len(delivered.content) == 1 and isinstance(delivered.content[0], TextContent)
            assert json.loads(delivered.content[0].text) == produced[-1]
            encoded = _wire_size(delivered)
            assert 2048 < encoded <= 8192
            assert delivered.meta is not None
            assert (
                delivered.meta["io.modelcontextprotocol/serverInfo"]["name"] == "corpus-structure"
            )
            # Use the actual SDK-emitted envelope as the boundary. This catches
            # post-dispatch serverInfo/resultType bytes missing from admission.
            exact = await client.call_tool(
                name, {"request": request(encoded).model_dump(mode="json")}
            )
            assert not exact.is_error
            assert _wire_size(exact) == encoded
            tight = await client.call_tool(
                name,
                {"request": request(encoded - 1).model_dump(mode="json")},
                raise_on_error=False,
            )
            assert tight.is_error and "oversized_item" in str(tight.content)

    try:
        anyio.run(journey)
    finally:
        engine.dispose()


def test_registered_queue_bounds_full_ack_metadata(monkeypatch):
    engine = create_engine("sqlite://")
    ack = service.QueueNext(
        tasks=[
            service.LeasedTask(
                task_id=2,
                run_id=1,
                unit_key=PAYLOAD,
                parts=1,
                chars=1,
                previous_issues=(ProposalIssue(path="claims[0]", code="fixture", detail=PAYLOAD),),
            )
        ]
    )
    monkeypatch.setattr(SemanticProjectSession, "next", lambda *args: ack)
    monkeypatch.setattr(semantic_server, "QUEUE_ACK_MAX_BYTES", 2048)
    assert len(ack.model_dump_json().encode()) < 2048

    server = build_semantic_server(SemanticProjectSession(engine, "fixture"))

    async def journey():
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            schema = tools["queue_next"].output_schema
            assert schema is not None and schema["properties"]["tasks"]["type"] == "array"
            refused = await client.call_tool("queue_next", {}, raise_on_error=False)
            assert refused.is_error and "oversized_item" in str(refused.content)
            monkeypatch.setattr(semantic_server, "QUEUE_ACK_MAX_BYTES", 8192)
            delivered = await client.call_tool("queue_next", {})
            assert delivered.structured_content == ack.model_dump(mode="json")
            assert isinstance(delivered.content[0], TextContent)
            assert json.loads(delivered.content[0].text) == ack.model_dump(mode="json")
            encoded = _wire_size(delivered)
            assert encoded <= 8192
            monkeypatch.setattr(semantic_server, "QUEUE_ACK_MAX_BYTES", encoded)
            exact = await client.call_tool("queue_next", {})
            assert not exact.is_error
            assert _wire_size(exact) == encoded
            monkeypatch.setattr(semantic_server, "QUEUE_ACK_MAX_BYTES", encoded - 1)
            tight = await client.call_tool("queue_next", {}, raise_on_error=False)
            assert tight.is_error and "oversized_item" in str(tight.content)

    try:
        anyio.run(journey)
    finally:
        engine.dispose()


def test_tiny_source_transport_budget_is_control_error(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(
        "corpus_structure.semantic.query.read_snapshot", lambda selected: nullcontext(None)
    )
    monkeypatch.setattr(
        "corpus_structure.serve.native_source.inspect_native_source",
        lambda conn, request: NativeSourceResponse(
            selection=request, release_id="fixture", health={}, rows=[]
        ),
    )

    async def journey():
        async with Client(build_semantic_server(SemanticAgentSession(engine, 1))) as client:
            result = await client.call_tool(
                "inspect_source",
                {"request": _native_request(max_bytes=1).model_dump(mode="json")},
                raise_on_error=False,
            )
            assert result.is_error and "oversized_item" in str(result.content)
            # Error-control envelopes are not successful payloads promised to fit one byte.
            assert len(_wire(result).model_dump_json().encode()) > 1

    try:
        anyio.run(journey)
    finally:
        engine.dispose()


def test_native_queue_ack_refusal_rolls_back_claim_cache_and_events(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    from .agent_scenarios import build_resubmission_case

    _, run, task, _ = build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "ack.pdf"
    )
    session = SemanticAgentSession(semantic_writer_engine, run)
    events = []
    monkeypatch.setattr(
        semantic_server, "_invocation_event", lambda *args, **kwargs: events.append(args)
    )
    monkeypatch.setattr(semantic_server, "QUEUE_ACK_MAX_BYTES", 64)

    def task_state():
        with semantic_writer_engine.connect() as conn:
            return dict(
                conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
                .mappings()
                .one()
            )

    before = task_state()
    with pytest.raises(ReadLimit, match="complete MCP response"):
        session.next("extract", 1)
    assert task_state() == before
    assert session.sessions == {} and events == []

    async def journey():
        async with Client(build_semantic_server(session)) as client:
            refused = await client.call_tool("queue_next", {}, raise_on_error=False)
            assert refused.is_error and "oversized_item" in str(refused.content)
            assert task_state() == before
            assert session.sessions == {} and events == []
            monkeypatch.setattr(semantic_server, "QUEUE_ACK_MAX_BYTES", 8 * 1024 * 1024)
            delivered = await client.call_tool("queue_next", {})
            assert not delivered.is_error
            assert delivered.structured_content is not None
            assert [row["task_id"] for row in delivered.structured_content["tasks"]] == [task]
            assert set(session.sessions) == {task} and len(events) == 1

    anyio.run(journey)
    assert task_state()["attempt"] == before["attempt"] + 1


def test_registered_read_unit_checks_exact_wire_and_preserves_fragments(monkeypatch):
    from types import SimpleNamespace

    engine = create_engine("sqlite://")
    packet = SimpleNamespace(
        hash="c" * 64,
        parts=lambda: (SimpleNamespace(name="unit"),),
        part_pages=lambda part: (PAYLOAD,),
    )
    active = SimpleNamespace(prepared=None, packet=packet, read=lambda name, part: PAYLOAD)
    monkeypatch.setattr(SemanticAgentSession, "active", lambda self, task_id: active)
    monkeypatch.setattr(
        semantic_server, "located_failure_context", lambda *args, **kw: nullcontext()
    )
    monkeypatch.setattr(semantic_server, "READ_UNIT_MAX_BYTES", 8192)

    async def journey():
        async with Client(build_semantic_server(SemanticAgentSession(engine, 1))) as client:
            delivered = await client.call_tool("read_unit", {"task_id": 2})
            assert delivered.structured_content == dict(
                task_id=2, part=1, parts=1, hash="c" * 64, text=PAYLOAD
            )
            assert len(delivered.content) == 1 and isinstance(delivered.content[0], TextContent)
            assert delivered.content[0].text == PAYLOAD
            encoded = _wire_size(delivered)
            monkeypatch.setattr(semantic_server, "READ_UNIT_MAX_BYTES", encoded)
            exact = await client.call_tool("read_unit", {"task_id": 2})
            assert not exact.is_error and _wire_size(exact) == encoded
            monkeypatch.setattr(semantic_server, "READ_UNIT_MAX_BYTES", encoded - 1)
            refused = await client.call_tool("read_unit", {"task_id": 2}, raise_on_error=False)
            assert refused.is_error and "oversized_item" in str(refused.content)
            assert PAYLOAD not in str(refused.content)

    try:
        anyio.run(journey)
    finally:
        engine.dispose()


@pytest.mark.parametrize("large_optional_result", [False, True])
def test_registered_render_exact_wire_and_retained_reference_refusals(
    monkeypatch, large_optional_result
):
    from types import SimpleNamespace

    from mcp.types import ImageContent

    from corpus_structure.semantic.native_requests import NativeRequestResult

    engine = create_engine("sqlite://")
    artifact = b"\x89PNG\r\n\x1a\n" + b"x" * 2048
    digest = "d" * 64
    result = NativeRequestResult(
        run_id=1,
        task_id=2,
        cut_id=3,
        status="done",
        source_view_id=4,
        product_digest="e" * 64,
        artifact_digest=digest,
        result={"detail": "x" * 2500} if large_optional_result else {},
    )
    body_reads = []

    def execute(statement):
        if "octet_length" in str(statement):
            return SimpleNamespace(scalar_one=lambda: len(artifact))
        body_reads.append(str(statement))
        return SimpleNamespace(scalar_one=lambda: artifact)

    monkeypatch.setattr(
        "corpus_structure.semantic.query.read_snapshot",
        lambda selected: nullcontext(SimpleNamespace(execute=execute)),
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.native_requests.request_source_view", lambda *args, **kw: result
    )

    def arguments(budget):
        return dict(run_id=1, source_view_id=4, pointer="#/texts/0", max_bytes=budget)

    async def journey():
        async with Client(build_semantic_server(SemanticAgentSession(engine, 1))) as client:
            delivered = await client.call_tool("render_source_region", arguments(8192))
            assert not delivered.is_error and delivered.structured_content is not None
            assert delivered.structured_content["inline_image"]["disposition"] == "included"
            assert isinstance(delivered.content[0], ImageContent)
            encoded = _wire_size(delivered)
            assert 1024 < encoded < 8192
            # max_bytes is itself response metadata. Both budgets have four digits,
            # so changing its value does not change the response's encoded length.
            assert 1000 <= encoded <= 9999
            body_reads.clear()
            exact = await client.call_tool("render_source_region", arguments(encoded))
            assert not exact.is_error and _wire_size(exact) == encoded
            assert len(body_reads) == 1
            body_reads.clear()
            refused = await client.call_tool(
                "render_source_region", arguments(encoded - 1), raise_on_error=False
            )
            assert refused.is_error and body_reads == []
            assert refused.structured_content is not None
            assert refused.structured_content["artifact_digest"] == digest
            assert refused.structured_content["inline_image"]["disposition"] == "refused"
            assert _wire_size(refused) <= encoded - 1
            body_reads.clear()
            compact = await client.call_tool(
                "render_source_region", arguments(1024), raise_on_error=False
            )
            assert compact.is_error and body_reads == []
            assert compact.structured_content is not None
            assert compact.structured_content["artifact_digest"] == digest
            assert compact.structured_content["source_view_id"] == 4
            assert compact.structured_content["inline_image"]["disposition"] == "refused"
            assert _wire_size(compact) <= 1024
            if large_optional_result:
                assert "result" not in compact.structured_content
            else:
                assert compact.structured_content["result"] == {}

    try:
        anyio.run(journey)
    finally:
        engine.dispose()
