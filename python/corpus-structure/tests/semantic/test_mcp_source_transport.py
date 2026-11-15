"""Full registered MCP delivery bounds, independent of source query work admission."""

import json
from contextlib import nullcontext

import anyio
import pytest
from fastmcp import Client
from mcp.types import CallToolResult, TextContent
from sqlalchemy import create_engine

from corpus_structure.intervene.semantic_server import (
    RetainedReaderBinding,
    build_retained_reader_server,
)
from corpus_structure.serve.native_source import NativeSourceRequest, NativeSourceResponse
from corpus_structure.semantic.visual_evidence import VisualEvidencePin, VisualEvidenceRead, VisualText
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


@pytest.mark.parametrize(
    "name,visual", [("find", False), ("inspect_source", False), ("inspect_source", True)]
)
def test_registered_source_tools_bound_whole_wire_and_preserve_payload(monkeypatch, name, visual):
    engine = create_engine("sqlite://")
    produced = []
    monkeypatch.setattr(
        "corpus_structure.semantic.query.read_snapshot", lambda selected: nullcontext(None)
    )

    def inspect(conn, request):
        candidate = None
        if visual:
            assert request.evidence is not None and request.evidence.run_id == 5
            assert request.view == "visual_evidence" and request.page_no == 3
            candidate = VisualEvidenceRead(
                page_no=3,
                original_artifact_digest="c" * 64,
                original_regions=[],
                submitted_region=None,
                observation_release_id="observation-release",
                observation={"outcome": "partial"},
                mapping_availability="available",
                items=(VisualText(occurrence_id="o1", kind="mermaid", text=PAYLOAD),),
            )
        result = NativeSourceResponse(
            selection=request,
            release_id="fixture-release",
            health={},
            rows=[{"text": "incumbent" if visual else PAYLOAD}],
            visual_evidence=candidate,
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
        if visual:
            return NativeSourceRequest(
                run_id=1,
                task_id=2,
                product_key="native",
                content_digest="a" * 64,
                max_bytes=budget,
                view="visual_evidence",
                evidence=VisualEvidencePin(
                    run_id=5, task_id=6, product_key="mapped", content_digest="b" * 64
                ),
                page_no=3,
            )
        return _native_request(max_bytes=budget)

    async def journey():
        async with Client(build_retained_reader_server(RetainedReaderBinding(engine, 1))) as client:
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
        async with Client(build_retained_reader_server(RetainedReaderBinding(engine, 1))) as client:
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
