"""Source-only discovery through the real MCP tool and shared named-query source owner."""

import anyio
from fastmcp import Client
from sqlalchemy import text

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.serve.source_search import SourceSearchRequest, search_source

from .test_pdf_native_consumer_journey import native_source_task


def test_source_search_requires_no_completed_knowledge_and_mcp_returns_exact_handles(
    semantic_db_engine,
    semantic_writer_engine,
    tmp_path,
):
    _, run, _, view_id, _ = native_source_task(semantic_db_engine, semantic_writer_engine, tmp_path)
    with semantic_writer_engine.connect() as conn:
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
            build_semantic_server(SemanticAgentSession(semantic_writer_engine, run))
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
