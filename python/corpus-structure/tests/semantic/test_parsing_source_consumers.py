"""Restricted native source reads through the shared service, CLI and MCP protocol.

MCP uses the actual in-process client transport. External host attachment is a separate
acceptance journey. Engine injection routes registered CLI commands to owned test databases.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256

import anyio
import pyarrow.parquet as pq
import pytest
from fastmcp import Client

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.semantic.operations import OperationConflict
from corpus_structure.semantic.parsing_products import (
    ProductReference, prepare_parsing_product, read_layered_product, store_parsing_product,
)
from corpus_structure.semantic.parsing_queries import trace_layered_origins
from corpus_structure.semantic.parsing_requests import request_parsing
from corpus_structure.serve.source import SourceRequest, inspect_source

from .test_operations import setup
from .test_parsing_products import _native_build, product_values
from .test_parsing_requests import source_build


@dataclass(frozen=True)
class SelectedProducts:
    source_run: int
    request_run: int
    rendition: int
    root: ProductReference
    text: ProductReference
    math: ProductReference


@pytest.fixture
def selected_products(semantic_db_engine, semantic_writer_engine, tmp_path):
    _, source_run, root, text, rendition = source_build(
        semantic_db_engine, semantic_writer_engine, tmp_path,
        canonical=r"\Archived", macros={r"\Archived": r"\mathbb{R}"},
    )
    result = request_parsing(semantic_writer_engine, root=root, text_product=text,
        demand="symbolic", math_index=0, code_commit="source-consumer-test")
    assert result.status == "source_ready", result.diagnostic
    return SelectedProducts(source_run, result.run_id, rendition, root, text,
                            next(p for p in result.products if p.product_key == "math"))


def test_native_shared_trace_reaches_artifacts_and_original_bytes_with_bounded_fanout(
    selected_products, semantic_reader_engine
):
    selected = selected_products
    with semantic_reader_engine.begin() as conn:
        retained_text = read_layered_product(conn, selected.text)
        assert retained_text is not None
        text = retained_text.values()
        expanded = next(r for r in text["representations"] if r["representation_id"] == "expanded:0")
        artifact_bytes = {sha256(r["text_content"].encode()).hexdigest() for r in text["representations"]
                          if r["kind"] == "artifact"}
        artifact = inspect_source(conn, SourceRequest(run_id=selected.source_run, rendition_id=selected.rendition,
            producing_task_id=selected.text.task_id, product_key="text", view="trace",
            representation_id="expanded:0", start=0, end=expanded["extent_length"]))
        artifact_rows = artifact.model_dump(mode="json")["rows"]
        assert artifact.outcome == "complete" and artifact_rows
        assert all(row["kind"] == "artifact" for row in artifact_rows)
        assert all(row["extent"]["artifact_digest"] in artifact_bytes for row in artifact_rows)
        assert all(row["extent"]["unit"] == "codepoint" for row in artifact_rows)
        assert all(row["path"][0]["operation"] == "expand" for row in artifact_rows)
        limited = trace_layered_origins(conn, reference=selected.text, representation_id="expanded:0",
                                        start=0, end=expanded["extent_length"], limit=2)
        assert limited["outcome"] == "limit"
        assert limited["examined_mappings"] <= 2 and len(limited["contributions"]) <= 2
        original = inspect_source(conn, SourceRequest(run_id=selected.request_run, rendition_id=selected.rendition,
            producing_task_id=selected.math.task_id, product_key="math", view="trace",
            representation_id="parse_input", start=0, end=9))
        assert original.outcome == "complete" and original.product_digest == selected.math.content_digest
        original_rows = original.model_dump(mode="json")["rows"]
        assert original_rows
        for row in original_rows:
            assert row["kind"] == "original"
            assert row["extent"]["unit"] == "byte"
            assert row["extent"]["target_task_id"] == selected.root.task_id
            assert (row["extent"]["start_offset"], row["extent"]["end_offset"]) == (3, 12)
            assert [step["operation"] for step in row["path"]] == ["copy", "copy", "normalize", "decode"]
        with pytest.raises(OperationConflict, match="exact origin"):
            inspect_source(conn, SourceRequest(run_id=selected.request_run, rendition_id=selected.rendition,
                producing_task_id=selected.math.task_id, product_key="math", view="trace",
                representation_id="parse_input", start=0, end=9, require_exact=True))


def test_native_original_representation_uses_byte_coordinates_for_multibyte_text(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    prepared = setup(semantic_db_engine, observations=True, composed=True)
    raw = b"a\xc3\xa9 "
    product = prepare_parsing_product(product_values(raw), raw)
    with semantic_writer_engine.begin() as conn:
        run, task, attempt, rendition = _native_build(conn, prepared, raw, tmp_path)
        store_parsing_product(conn, task_id=task, attempt=attempt, holder="fixture", product=product)
    with semantic_reader_engine.begin() as conn:
        answer = inspect_source(conn, SourceRequest(run_id=run, rendition_id=rendition,
            producing_task_id=task, product_key="source", view="components", representation_id="raw",
            start=1, end=4))
        assert answer.outcome == "complete"
        assert [(r["unit"], r["start_offset"], r["end_offset"]) for r in answer.rows] == [("byte", 0, 3), ("byte", 3, 4)]
        traced = inspect_source(conn, SourceRequest(run_id=run, rendition_id=rendition,
            producing_task_id=task, product_key="source", view="trace", representation_id="raw",
            start=1, end=4, require_exact=True))
        assert traced.outcome == "complete" and len(traced.rows) == 1
        extent = traced.model_dump(mode="json")["rows"][0]["extent"]
        assert (extent["unit"], extent["start_offset"], extent["end_offset"]) == ("byte", 1, 4)
        assert raw[extent["start_offset"]:extent["end_offset"]] == b"\xc3\xa9 "


def test_registered_source_cli_inspect_trace_and_parquet_export_preserve_pins(
    selected_products, semantic_reader_engine, cli, monkeypatch, tmp_path
):
    from corpus_structure.semantic import runtime
    selected = selected_products
    purposes = []
    @contextmanager
    def native_reader(settings, *args, purpose, **kwargs):
        purposes.append(purpose)
        assert purpose == "read"
        yield semantic_reader_engine
    monkeypatch.setattr(runtime, "open_runtime_engine", native_reader)
    pin = (str(selected.request_run), str(selected.rendition))
    options = ("--product", "math", "--representation", "parse_input",
               "--producing-task", str(selected.math.task_id))
    inspected = cli("source", "inspect", *pin, *options, "--start", "0", "--end", "9", "--json")
    assert inspected.exit_code == 0, (inspected.output, inspected.exception)
    value = json.loads(inspected.stdout)
    assert value["product_digest"] == selected.math.content_digest
    assert [(r["category"], r["start_offset"], r["end_offset"]) for r in value["rows"]] == [("control_word", 0, 9)]
    traced = cli("source", "trace", *pin, "0", "9", *options, "--json")
    assert traced.exit_code == 0, (traced.output, traced.exception)
    trace = json.loads(traced.stdout)
    assert trace["outcome"] == "complete" and trace["product_digest"] == selected.math.content_digest
    assert all(r["kind"] == "original" and r["extent"]["unit"] == "byte" for r in trace["rows"])
    bounded = cli("source", "trace", *pin, "0", "9", *options, "--limit", "1", "--json")
    assert bounded.exit_code == 0 and json.loads(bounded.stdout)["outcome"] == "limit"
    exact = cli("source", "trace", *pin, "0", "9", *options, "--exact", "--json")
    assert exact.exit_code == 1 and json.loads(exact.stdout)["error"]["code"] == "OperationConflict"
    target = tmp_path / "source-components.parquet"
    exported = cli("source", "export", *pin, str(target), *options, "--format", "parquet")
    assert exported.exit_code == 0, (exported.output, exported.exception)
    data = pq.read_table(target)
    schema_metadata = data.schema.metadata
    assert schema_metadata is not None
    metadata = json.loads(schema_metadata[b"source_selection"])
    assert metadata["product_digest"] == selected.math.content_digest
    assert metadata["rows"][0]["reference"] == selected.math.values()
    assert metadata["rows"][0]["root"] == selected.root.values()
    rows = data.to_pylist()
    assert [(r["task_id"], r["product_key"], r["unit"], r["start_offset"], r["end_offset"])
            for r in rows] == [(selected.math.task_id, "math", "codepoint", 0, 9)]
    before = target.read_bytes()
    replay = cli("source", "export", *pin, str(target), *options, "--format", "parquet")
    assert replay.exit_code != 0 and target.read_bytes() == before
    jsonl = tmp_path / "source-components.jsonl"
    streamed = cli("source", "export", *pin, str(jsonl), *options)
    assert streamed.exit_code == 0, (streamed.output, streamed.exception)
    lines = [json.loads(line) for line in jsonl.read_text().splitlines()]
    assert len(lines) == 1
    assert lines[0]["selection"]["product_digest"] == selected.math.content_digest
    assert lines[0]["component"]["product_key"] == "math"
    missing = cli("source", "inspect", *pin, "--product", "math", "--producing-task",
                  str(selected.math.task_id + 1000000), "--json")
    assert missing.exit_code == 0 and json.loads(missing.stdout)["outcome"] == "unavailable"
    assert purposes and set(purposes) == {"read"}


def test_actual_mcp_protocol_reads_shared_service_without_stronger_work(
    selected_products, semantic_reader_engine, monkeypatch
):
    selected = selected_products
    def forbidden(*args, **kwargs):
        raise AssertionError("inspection requested mathematical work")
    monkeypatch.setattr("corpus_structure.methods.math.grammar.parser_for", forbidden)
    server = build_semantic_server(SemanticAgentSession(semantic_reader_engine, selected.request_run))
    async def journey():
        async with Client(server) as client:
            tools = await client.list_tools()
            source = next(tool for tool in tools if tool.name == "inspect_source")
            assert source.output_schema is not None
            request = SourceRequest(run_id=selected.request_run, rendition_id=selected.rendition,
                producing_task_id=selected.math.task_id, product_key="math", view="components",
                representation_id="parse_input", start=0, end=9)
            result = await client.call_tool("inspect_source", {"request": request.model_dump(mode="json")})
            value = result.structured_content
            assert value is not None
            assert value["product_digest"] == selected.math.content_digest
            assert [(r["category"], r["start_offset"], r["end_offset"]) for r in value["rows"]] == [("control_word", 0, 9)]
            trace_request = request.model_copy(update={"view": "trace"})
            traced = await client.call_tool("inspect_source", {"request": trace_request.model_dump(mode="json")})
            traced_value = traced.structured_content
            assert traced_value is not None
            assert traced_value["outcome"] == "complete"
            assert all(row["extent"]["unit"] == "byte" for row in traced_value["rows"])
            exact = await client.call_tool("inspect_source", {"request": trace_request.model_copy(update={"require_exact": True}).model_dump(mode="json")}, raise_on_error=False)
            assert exact.is_error and "exact origin" in str(exact.content)
            wrong_run = await client.call_tool("inspect_source", {"request": request.model_copy(update={"run_id": selected.source_run}).model_dump(mode="json")}, raise_on_error=False)
            assert wrong_run.is_error and "different semantic run" in str(wrong_run.content)
    anyio.run(journey)


def test_native_bounded_reads_do_not_transfer_manifests_or_representation_text(
    selected_products, semantic_reader_engine
):
    from sqlalchemy import event

    selected = selected_products
    observed = []
    forbidden = {"payload", "text_content", "text_content_utf8_base64", "content"}
    def observe(conn, cursor, statement, parameters, context, executemany):
        if not any(name in statement for name in (
            "ops.parsing_product", "ops.parsing_layer_product", "kb.parsing_", "kb.source_artifact"
        )) or cursor.description is None:
            return
        names = {column.name for column in cursor.description}
        assert not names & forbidden, f"unbounded body columns transferred: {names & forbidden}"
        observed.append((statement, names))
    event.listen(semantic_reader_engine, "after_cursor_execute", observe)
    try:
        with semantic_reader_engine.begin() as conn:
            base = dict(run_id=selected.request_run, rendition_id=selected.rendition,
                        producing_task_id=selected.math.task_id, product_key="math")
            components = inspect_source(conn, SourceRequest(**base, view="components",
                representation_id="parse_input", start=0, end=9, limit=2))
            assert len(components.rows) == 1
            endpoints = inspect_source(conn, SourceRequest(**base, view="relationships",
                relationship_id="source-reading", limit=2))
            assert [row["role"] for row in endpoints.rows] == ["target", "source"]
            original = inspect_source(conn, SourceRequest(**base, view="trace",
                representation_id="parse_input", start=0, end=9, limit=20))
            assert original.outcome == "complete" and original.rows
            artifact = inspect_source(conn, SourceRequest(run_id=selected.source_run,
                rendition_id=selected.rendition, producing_task_id=selected.text.task_id,
                product_key="text", view="trace", representation_id="expanded:0", start=0, end=10, limit=20))
            assert artifact.outcome == "complete" and artifact.rows
            headers = inspect_source(conn, SourceRequest(run_id=selected.request_run,
                rendition_id=selected.rendition, view="products", limit=10))
            assert {row["kind"] for row in headers.rows} == {"source", "text", "interpretation"}
        assert observed
        assert any("sha256" in statement for statement, _ in observed)
    finally:
        event.remove(semantic_reader_engine, "after_cursor_execute", observe)


def test_native_header_corruption_with_matching_payload_pin_is_refused(
    selected_products, semantic_db_engine, semantic_reader_engine
):
    from sqlalchemy import update
    from corpus_structure.semantic.metadata import table

    selected = selected_products
    relation = table("ops.parsing_layer_product")
    # Only this owned clone is corrupted, under its actual owner. Its immutable body and
    # reference digest remain unchanged; a header-only reader must still detect disagreement.
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.exec_driver_sql("ALTER TABLE ops.parsing_layer_product DISABLE TRIGGER USER")
        conn.execute(update(relation).where(relation.c.task_id == selected.math.task_id,
            relation.c.product_key == "math").values(coverage="partial"))
        conn.exec_driver_sql("ALTER TABLE ops.parsing_layer_product ENABLE TRIGGER USER")
    with semantic_reader_engine.begin() as conn:
        with pytest.raises(ValueError, match="registry|identity|manifest"):
            inspect_source(conn, SourceRequest(run_id=selected.request_run, rendition_id=selected.rendition,
                producing_task_id=selected.math.task_id, product_key="math", view="components",
                representation_id="parse_input", start=0, end=9, limit=2))
