"""Actual registered MCP envelope bounds for current selected source tools.

The query adapter is controlled here; these cases establish transport, not native custody.
"""
import json
from contextlib import nullcontext
from hashlib import sha256

import anyio
import pytest
from fastmcp import Client
from mcp.types import CallToolResult, TextContent
from sqlalchemy import create_engine

from corpus_structure.intervene.semantic_server import build_retained_reader_server
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.visual_evidence import VisualEvidencePin, VisualEvidenceRead, VisualText
from corpus_structure.serve.native_source import NativeSourceRequest, NativeSourceResponse
from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference
from corpus_structure.serve.pdf_visual_evidence import VisualObservationManifest, VisualObservationEntry
from corpus_structure.serve.visual_evidence_packet import VisualEvidencePacket

PAYLOAD='Unicode α "quoted" \\ slash\n'*25
SOURCE=dict(project_id="project:A",demand_id="demand:A",read_id="read:A",use_id="use:source",product_id="product:source",derivation_id="episode:source")
EVIDENCE=VisualEvidencePin(use_id="use:visual",product_id="product:visual",derivation_id="episode:visual")
RAW=VisualEvidencePin(use_id="use:visual",product_id="product:raw",derivation_id="episode:raw")
CUT=dict(project_id="project:A",demand_id="demand:A",read_id="read:A",release_id="release:A",runtime_id="runtime:A",
         selection={"targets":["source.visual/map"]},trust_snapshot={},read_snapshot="1:2:",frontier_at="2026-11-15T00:00:00+00:00",scope={})


def _native_request(max_bytes=1024*1024,*,visual=False):
    if visual:
        return NativeSourceRequest(**SOURCE,max_bytes=max_bytes,view="visual_evidence",evidence=EVIDENCE,page_no=3)
    return NativeSourceRequest(**SOURCE,max_bytes=max_bytes)


def _wire(response):
    return CallToolResult(content=response.content,structured_content=response.structured_content,
                          is_error=response.is_error,meta=response.meta)


def _wire_size(response):
    return len(_wire(response).model_dump_json(by_alias=True,exclude_none=True).encode())


def _response(request,visual):
    candidate=VisualEvidenceRead(evidence=EVIDENCE,raw_evidence=RAW,
        producer={"id":"episode:visual","request_id":"request:visual","release_id":"release:A","recipe":"recipe:map","runtime_id":"runtime:A"},
        raw_producer={"id":"episode:raw","request_id":"request:raw","release_id":"release:raw","recipe":"recipe:recognize","runtime_id":"runtime:raw"},
        page_no=3,original_artifact_digest="c"*64,original_regions=[],submitted_region=None,
        observation_release_id="release:raw",observation={"provider_outcome":"partial"},mapping_availability="available",
        items=(VisualText(occurrence_id="o1",kind="mermaid",text=PAYLOAD),)) if visual else None
    return NativeSourceResponse(selection=request,cut=CUT,release_id="release:A",health={},
        rows=[{"text":"incumbent" if visual else PAYLOAD}],visual_evidence=candidate)


@pytest.mark.parametrize("name,visual",[("inspect_source",False),("inspect_source",True),("visual_evidence_packet",True)])
def test_registered_current_source_tools_bound_whole_wire_and_preserve_payload(monkeypatch,name,visual):
    engine=create_engine("sqlite://")
    monkeypatch.setattr("corpus_structure.semantic.demand_results.selected_read_snapshot",lambda selected:nullcontext(None))
    produced=[]
    def inspect(conn,request):
        assert request.project_id==SOURCE["project_id"] and request.read_id==SOURCE["read_id"]
        if visual: assert request.evidence==EVIDENCE
        result=_response(request,visual)
        produced.append(result.model_dump(mode="json"))
        return result
    def packet(conn,request):
        source=inspect(conn,request)
        result=VisualEvidencePacket(digest=sha256(canonical_bytes(source.model_dump(mode="json"))).hexdigest(),source=source)
        produced[-1]=result.model_dump(mode="json")
        return result
    monkeypatch.setattr("corpus_structure.serve.native_source.inspect_native_source",inspect)
    monkeypatch.setattr("corpus_structure.serve.visual_evidence_packet.visual_evidence_packet",packet)
    async def journey():
        async with Client(build_retained_reader_server(project="project:A",read_engine=engine)) as client:
            tools={tool.name:tool for tool in await client.list_tools()}
            annotation=tools[name].annotations
            assert annotation is not None and annotation.read_only_hint is True
            def arguments(budget): return {"request":_native_request(budget,visual=visual).model_dump(mode="json")}
            refused=await client.call_tool(name,arguments(2048),raise_on_error=False)
            assert refused.is_error and "oversized_item" in str(refused.content)
            assert PAYLOAD not in str(refused.content)
            delivered=await client.call_tool(name,arguments(8192))
            assert not delivered.is_error and delivered.structured_content==produced[-1]
            assert len(delivered.content)==1 and isinstance(delivered.content[0],TextContent)
            assert json.loads(delivered.content[0].text)==produced[-1]
            encoded=_wire_size(delivered)
            assert 2048<encoded<=8192
            assert delivered.meta is not None
            assert delivered.meta["io.modelcontextprotocol/serverInfo"]["name"]=="corpus-structure"
            exact=await client.call_tool(name,arguments(encoded))
            assert not exact.is_error and _wire_size(exact)==encoded
            tight=await client.call_tool(name,arguments(encoded-1),raise_on_error=False)
            assert tight.is_error and "oversized_item" in str(tight.content)
    try: anyio.run(journey)
    finally: engine.dispose()


def test_manifest_uses_same_current_source_reference_and_preserves_raw_producer(monkeypatch):
    engine=create_engine("sqlite://")
    monkeypatch.setattr("corpus_structure.semantic.demand_results.selected_read_snapshot",lambda selected:nullcontext(None))
    seen=[]
    def manifest(conn,source,**options):
        seen.append((source,options))
        return VisualObservationManifest(source=source,cut=CUT,continuation=None,
            observations=(VisualObservationEntry(page_no=3,rotation=0,raw=RAW,mapped=EVIDENCE,
                producer={"id":"episode:visual"},raw_producer={"id":"episode:raw"},execution_outcome="partial",mapping_availability="available"),))
    monkeypatch.setattr("corpus_structure.serve.pdf_visual_evidence.visual_observation_manifest",manifest)
    async def journey():
        async with Client(build_retained_reader_server(project="project:A",read_engine=engine)) as client:
            result=await client.call_tool("list_visual_observations",{"source":SOURCE,"page_no":3,"limit":10})
            assert result.structured_content is not None
            assert result.structured_content["cut"]==CUT
            assert result.structured_content["observations"][0]["raw"]==RAW.model_dump()
            assert result.structured_content["observations"][0]["raw_producer"]=={"id":"episode:raw"}
    try: anyio.run(journey)
    finally: engine.dispose()
    assert seen[0][0]==SelectedPdfSourceReference(**SOURCE) and seen[0][1]["page_no"]==3


def test_current_tools_refuse_another_project_before_acquisition(monkeypatch):
    project = "project:other"
    engine=create_engine("sqlite://")
    opened=[]
    monkeypatch.setattr("corpus_structure.semantic.demand_results.selected_read_snapshot",lambda selected:opened.append(True) or nullcontext(None))
    async def journey():
        server=build_retained_reader_server(project=project,read_engine=engine)
        async with Client(server) as client:
            result=await client.call_tool("inspect_source",{"request":_native_request().model_dump(mode="json")},raise_on_error=False)
            assert result.is_error and "another server project" in str(result.content)
    try: anyio.run(journey)
    finally: engine.dispose()
    assert not opened


def test_tiny_source_transport_budget_is_control_error(monkeypatch):
    engine=create_engine("sqlite://")
    monkeypatch.setattr("corpus_structure.semantic.demand_results.selected_read_snapshot",lambda selected:nullcontext(None))
    monkeypatch.setattr("corpus_structure.serve.native_source.inspect_native_source",lambda conn,request:NativeSourceResponse(selection=request,cut=CUT,release_id="fixture",health={},rows=[]))
    async def journey():
        async with Client(build_retained_reader_server(project="project:A",read_engine=engine)) as client:
            result=await client.call_tool("inspect_source",{"request":_native_request(1).model_dump(mode="json")},raise_on_error=False)
            assert result.is_error and "oversized_item" in str(result.content)
            assert _wire_size(result)>1
    try: anyio.run(journey)
    finally: engine.dispose()
