"""Source-only discovery through the real MCP tool and shared named-query source owner."""

import anyio
from fastmcp import Client
from sqlalchemy import text

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.serve.source_search import SourceSearchRequest, search_source
from semantic.agent_scenarios import native_build_resubmission_case


def test_source_search_requires_no_completed_knowledge_and_mcp_returns_exact_handles(
    commit_db_engine,
    commit_writer_engine,
    tmp_path,
):
    _, run, _, view_id, _ = native_build_resubmission_case(
        commit_db_engine, commit_writer_engine, tmp_path
    )
    with commit_writer_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.completed_result WHERE run_id=:run"), {"run": run}
            )
            == 0
        )
        found = search_source(conn, SourceSearchRequest(run_id=run, text="Alice"))
        (hit,) = found.rows
        assert hit.source_view_id == view_id
        assert hit.selection.run_id == run
        assert "Alice" in hit.excerpt
        assert hit.selection.content_digest and hit.projection_digest

    async def journey():
        async with Client(
            build_semantic_server(SemanticAgentSession(commit_writer_engine, run))
        ) as client:
            found = await client.call_tool("find", {"request": {"run_id": run, "text": "Alice"}})
            assert not found.is_error
            assert found.structured_content is not None
            rows = found.structured_content["rows"]
            assert rows[0]["source_view_id"] == view_id
            inspected = await client.call_tool("inspect_source", {"request": rows[0]["selection"]})
            assert not inspected.is_error
            assert inspected.structured_content is not None
            assert inspected.structured_content["rows"]

    anyio.run(journey)


def test_artifact_pages_are_bound_to_the_exact_selected_product(
    commit_db_engine,
    commit_writer_engine,
    tmp_path,
):
    import base64
    from hashlib import sha256
    from importlib.resources import files

    import pytest

    from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source

    _, run, _, view_id, _ = native_build_resubmission_case(
        commit_db_engine, commit_writer_engine, tmp_path
    )
    expected = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    with commit_writer_engine.connect() as conn:
        (hit,) = search_source(conn, SourceSearchRequest(run_id=run, text="Alice")).rows
        assert hit.source_view_id == view_id
        request = NativeSourceRequest(
            run_id=run,
            task_id=hit.selection.task_id,
            product_key=hit.selection.product_key,
            content_digest=hit.selection.content_digest,
            view="artifact",
            artifact_digest=sha256(expected).hexdigest(),
        )
        result = bytearray()
        selected = request
        while True:
            response = inspect_native_source(conn, selected)
            (chunk,) = response.rows
            assert chunk["offset"] == len(result)
            assert chunk["total_bytes"] == len(expected)
            assert chunk["encoding"] == "base64"
            encoded = chunk["data"]
            assert isinstance(encoded, str)
            block = base64.b64decode(encoded)
            assert len(block) <= 65536
            result.extend(block)
            if response.next_cursor is None:
                break
            selected = request.model_copy(update={"cursor": response.next_cursor})
        assert result == expected
        for changed in ({"artifact_digest": "0" * 64}, {"content_digest": "f" * 64}):
            with pytest.raises(ValueError):
                inspect_native_source(conn, request.model_copy(update=changed))
