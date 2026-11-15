"""Source-only current native/MCP journeys through real DDO publication custody."""

import base64
from hashlib import sha256
from importlib.resources import files

import anyio
import pytest
from fastmcp import Client
from sqlalchemy.exc import DBAPIError

from corpus_structure.intervene.server import build_server
from corpus_structure.semantic.demand_results import selected_read_snapshot
from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.source_search import SourceSearchRequest, search_source
from semantic.current_pdf_source_support import PROJECT
from semantic.current_pdf_source_support import current_pdf_source as current_pdf_source


def test_source_search_requires_only_source_demand_and_mcp_returns_exact_handles(current_pdf_source):
    case = current_pdf_source
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        pin, _catalog = case.publication(connection)
        found = search_source(connection, SourceSearchRequest(project_id=PROJECT, demand_id=case.demand_id,
            read_id=pin.read_id, sources=(pin,), text="Alice"))
        assert found.rows and all("Alice" in hit.excerpt for hit in found.rows)
        for hit in found.rows:
            assert hit.source == pin and hit.original_source == case.document_key
            assert hit.selection.derivation_id == pin.derivation_id
            assert hit.projection_digest and hit.source_digest
            assert inspect_native_source(connection, hit.selection).rows

    async def journey():
        # The read receipt was genuinely committed above; no run binding or relabelled ID.
        async with Client(build_server(project=PROJECT, demand=case.demand_id, read_engine=case.kernel.purpose("read"))) as client:
            response = await client.call_tool("find", {"request": dict(project_id=PROJECT,
                demand_id=case.demand_id, read_id=pin.read_id, sources=[pin.model_dump(mode="json")], text="Alice")})
            assert not response.is_error and response.structured_content is not None
            rows = json_loads(response.structured_content["exact_json"])["rows"]
            assert rows and rows[0]["selection"]["product_id"] == pin.product_id
            inspected = await client.call_tool("inspect_source", {"request": rows[0]["selection"]})
            assert not inspected.is_error and inspected.structured_content is not None
            assert inspected.structured_content["rows"]
    anyio.run(journey)


def test_artifact_pages_remain_bound_to_exact_selected_publication(current_pdf_source):
    case = current_pdf_source
    expected = files("corpus_structure").joinpath("model/semantic/docling-validation.schema.json").read_bytes()
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        pin, _ = case.publication(connection)
        request = NativeSourceRequest(**pin.model_dump(), view="artifact", artifact_digest=sha256(expected).hexdigest())
        actual, selected = bytearray(), request
        while True:
            reply = inspect_native_source(connection, selected)
            (chunk,) = reply.rows
            assert chunk["offset"] == len(actual) and chunk["total_bytes"] == len(expected)
            assert chunk["encoding"] == "base64" and isinstance(chunk["data"], str)
            actual.extend(base64.b64decode(chunk["data"]))
            if reply.next_cursor is None:
                break
            selected = request.model_copy(update={"cursor": reply.next_cursor})
        assert actual == expected
        for changed in ({"artifact_digest": "0" * 64}, {"derivation_id": "derivation:foreign"}, {"read_id": "read:foreign"}):
            with pytest.raises((ValueError, DBAPIError)), connection.begin_nested():
                inspect_native_source(connection, request.model_copy(update=changed))
