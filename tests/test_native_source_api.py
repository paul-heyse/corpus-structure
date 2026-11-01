"""Typed native source requests remain distinct from archived scalar coordinates."""

import pytest
from pydantic import ValidationError

from corpus_structure.serve.native_source import NativeSourceRequest


def test_native_request_pin_and_continuation_identity():
    value = NativeSourceRequest(run_id=1, task_id=2, product_key="native", content_digest="a" * 64)
    assert (
        value.model_copy(update={"limit": 1, "cursor": "x"}).selection_digest()
        == value.selection_digest()
    )
    assert (
        value.model_copy(update={"pointer": "#/texts/1"}).selection_digest()
        != value.selection_digest()
    )
    assert (
        value.model_copy(update={"membership": "descendants"}).selection_digest()
        != value.selection_digest()
    )
    with pytest.raises(ValidationError):
        NativeSourceRequest(run_id=1, task_id=2, product_key="native", content_digest="bad")


def test_current_request_refuses_archived_coordinates_and_old_contract_versions():
    current = dict(
        version=3, run_id=1, task_id=2, product_key="integrated", content_digest="a" * 64
    )
    assert NativeSourceRequest.model_validate(current).version == 3
    for invalid in (
        dict(run_id=1, rendition_id=2),
        dict(current, version=2),
        dict(current, rendition_id=2),
    ):
        with pytest.raises(ValidationError):
            NativeSourceRequest.model_validate(invalid)


def test_native_scope_selects_original_once_and_declares_subsection_expansion():
    from corpus_structure.orchestrate.slices import SliceError, records

    documents = [dict(key="pdf-document", mime="application/pdf", content_hash="a" * 64, meta={})]
    corpus, scope = records(
        documents,
        {"qualification": [{"native_sections": ["1.1: Sets"]}]},
        slice=None,
        scope="qualification",
        corpus=None,
    )
    assert corpus["documents"] == ["pdf-document"]
    assert scope is not None
    assert scope["sections"] == ["1.1: Sets"] and scope["include_descendants"] is True
    with pytest.raises(SliceError, match="native_sections"):
        records(documents, {"old": ["page.html"]}, slice=None, scope="old", corpus=None)


def test_mcp_registration_exposes_versioned_native_reads_and_explicit_render():
    import asyncio

    from fastmcp import Client
    from sqlalchemy import create_engine

    from corpus_structure.intervene.semantic_server import (
        SemanticAgentSession,
        build_semantic_server,
    )

    engine = create_engine("sqlite://")

    async def check():
        async with Client(build_semantic_server(SemanticAgentSession(engine, 1))) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert "inspect_source" in tools and "render_source_region" in tools
            request = tools["inspect_source"].input_schema["properties"]["request"]
            assert "anyOf" not in request
            inspect_annotations = tools["inspect_source"].annotations
            render_annotations = tools["render_source_region"].annotations
            assert inspect_annotations is not None and render_annotations is not None
            assert inspect_annotations.read_only_hint is True
            assert render_annotations.read_only_hint is False

    try:
        asyncio.run(check())
    finally:
        engine.dispose()
