"""Typed native source requests remain distinct from archived scalar coordinates."""
import pytest
from pydantic import ValidationError, TypeAdapter
from corpus_structure.serve.native_source import NativeSourceRequest
from corpus_structure.serve.source import SourceRequest


def test_native_request_pin_and_continuation_identity():
    value=NativeSourceRequest(run_id=1,task_id=2,product_key='native',content_digest='a'*64)
    assert value.model_copy(update={'limit':1,'cursor':'x'}).selection_digest()==value.selection_digest()
    assert value.model_copy(update={'pointer':'#/texts/1'}).selection_digest()!=value.selection_digest()
    assert value.model_copy(update={'membership':'descendants'}).selection_digest()!=value.selection_digest()
    with pytest.raises(ValidationError):
        NativeSourceRequest(run_id=1,task_id=2,product_key='native',content_digest='bad')


def test_tool_union_distinguishes_native_and_archived_coordinates():
    adapter=TypeAdapter(SourceRequest | NativeSourceRequest)
    native=adapter.validate_python(dict(version=2,run_id=1,task_id=2,product_key='native',content_digest='a'*64))
    assert isinstance(native,NativeSourceRequest)
    archive=adapter.validate_python(dict(run_id=1,rendition_id=2))
    assert isinstance(archive,SourceRequest)
    with pytest.raises(ValidationError):
        adapter.validate_python(dict(version=2,run_id=1,rendition_id=2,task_id=2,product_key='native',content_digest='a'*64))


def test_native_scope_selects_original_once_and_declares_subsection_expansion():
    from corpus_structure.orchestrate.slices import records, SliceError
    documents=[dict(key='pdf-document',mime='application/pdf',content_hash='a'*64,meta={})]
    corpus,scope=records(documents,{'qualification':[{'native_sections':['1.1: Sets']}]},
        slice=None,scope='qualification',corpus=None)
    assert corpus['documents']==['pdf-document']
    assert scope is not None
    assert scope['sections']==['1.1: Sets'] and scope['include_descendants'] is True
    with pytest.raises(SliceError,match='native_sections'):
        records(documents,{'old':['page.html']},slice=None,scope='old',corpus=None)


def test_mcp_registration_exposes_versioned_native_reads_and_explicit_render():
    import asyncio
    from fastmcp import Client
    from sqlalchemy import create_engine
    from corpus_structure.intervene.semantic_server import SemanticAgentSession,build_semantic_server
    engine=create_engine('sqlite://')
    async def check():
        async with Client(build_semantic_server(SemanticAgentSession(engine,1))) as client:
            tools={tool.name:tool for tool in await client.list_tools()}
            assert 'inspect_source' in tools and 'render_source_region' in tools
            request=tools['inspect_source'].input_schema['properties']['request']
            assert len(request['anyOf'])==2
            inspect_annotations=tools['inspect_source'].annotations
            render_annotations=tools['render_source_region'].annotations
            assert inspect_annotations is not None and render_annotations is not None
            assert inspect_annotations.read_only_hint is True
            assert render_annotations.read_only_hint is False
    try:
        asyncio.run(check())
    finally:
        engine.dispose()
