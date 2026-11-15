"""Selected current visual candidates, beside their independently selected PDF source."""
from __future__ import annotations

from base64 import b64encode
from typing import TYPE_CHECKING, Any, Literal, cast
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from corpus_structure.semantic.visual_evidence import VisualEvidencePin, VisualEvidenceRead, VisualSourceRegion
from corpus_structure.semantic.data_operation_visual_read import VisualHeaderReply, VisualRowsReply, VisualArtifactReply, VisualReadReply
from .selected_pdf import SelectedPdfSource, SelectedPdfSourceReference, acquire_selected_pdf_source

if TYPE_CHECKING:
    from sqlalchemy import Connection
    from corpus_structure.core.db.lifetime import BorrowerCancellation
    from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
    from corpus_structure.semantic.types import PreparedRelease
    from .native_source import NativeSourceRequest, NativeSourceResponse


def _read(conn, source, evidence, mode, budget, **selectors):
    from pydantic import TypeAdapter
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.data_operation_wire import validate_native_wire
    from corpus_structure.semantic._data_operation_wire import WireReadSelectedVisualEvidenceRequest
    from corpus_structure.semantic.data_operation_json import json_bytes
    if budget.max_bytes<=budget.bytes:
        from corpus_structure.semantic.query import ReadLimit
        raise ReadLimit("visual byte budget exhausted",reason="work_limit")
    payload = dict(source=source.reference.model_dump(mode="json"), evidence=evidence.model_dump(mode="json"),
                   mode=mode, after=0, limit=100, max_bytes=budget.max_bytes-budget.bytes,
                   regions=[])
    payload.update(selectors)
    payload = {key:value for key,value in payload.items() if value is not None}
    request = cast(WireReadSelectedVisualEvidenceRequest, validate_native_wire("read_selected_visual_evidence","input",payload))
    reply = DataOperationStorage(conn).read_selected_visual_evidence(request)
    budget.value(reply)
    _charge_rows(budget, 1)
    checked=TypeAdapter(VisualReadReply).validate_json(json_bytes(reply))
    if isinstance(checked,VisualRowsReply):
        from corpus_structure.semantic.visual_evidence import VisualTable
        _charge_rows(budget,sum(1+(len(row.cells) if isinstance(row,VisualTable) else 0) for row in checked.items))
    return checked


class VisualObservationEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    page_no: int = Field(gt=0)
    pointer: str | None = None
    region_index: int | None = None
    rotation: int
    raw: VisualEvidencePin
    mapped: VisualEvidencePin | None = None
    producer: dict[str, JsonValue]
    raw_producer: dict[str, JsonValue]
    execution_outcome: str
    mapping_availability: Literal["not_selected", "unavailable", "available"]


class VisualObservationManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: SelectedPdfSourceReference
    cut: dict[str, JsonValue]
    observations: tuple[VisualObservationEntry,...]
    continuation: dict[str, JsonValue] | None


def visual_observation_manifest(conn, source: SelectedPdfSourceReference, *, page_no=None,
                                continuation=None, limit=100, max_bytes=1024*1024):
    """Discover selected metadata only; each header reacquires the same cut proof."""
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.demand_results import read_demand_result
    from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
    selected = acquire_selected_pdf_source(conn, source)
    model = bound_data_operation_model(selected.prepared)
    kinds = {item.key for item in model.identities if item.domain=="kind" and item.owner in {
        "https://corpus-structure.dev/semantic/data-operation-visual/DdoVisualMapping",
        "https://corpus-structure.dev/semantic/data-operation-visual/DdoChandraObservation"}}
    request = dict(continuation or {key:value for key,value in selected.cut.record.items()
                                  if key not in {"project_id","release_id","runtime_id"}})
    request["view"]="frontier"
    page = read_demand_result(conn, source.demand_id, project_id=source.project_id,
                             continuation=request,cut=selected.cut,view="frontier",limit=limit,max_bytes=max_bytes)
    budget=PublishedReadBudget(max_rows=10000,max_bytes=max_bytes)
    entries=[]
    for use in page.record["uses"]:
        if use["fate"]!="fulfilled": continue
        for product in use["products"]:
            if product["member_id"] is not None or product["kind_contract"] not in kinds: continue
            pin=VisualEvidencePin(use_id=use["use_id"],product_id=product["product_id"],derivation_id=use["derivation_id"])
            reply=_read(conn,selected,pin,"header",budget)
            assert isinstance(reply,VisualHeaderReply)
            header=reply.header
            image=cast(dict[str,Any],header.observation["image"])
            if page_no is not None and image["page_no"]!=page_no: continue
            selection=image["selection"]
            entries.append(VisualObservationEntry(page_no=image["page_no"],pointer=selection.get("pointer"),
                region_index=selection.get("region_index"),rotation=image["rotation"], raw=header.raw,
                mapped=pin if header.mapping_availability!="not_selected" else None,producer=header.producer,
                raw_producer=header.raw_producer,execution_outcome=str(header.observation["provider_outcome"]),
                mapping_availability=header.mapping_availability))
    return VisualObservationManifest(source=source,cut=selected.cut.record,observations=tuple(entries),continuation=page.continuation)


def _charge_rows(budget, count):
    from corpus_structure.semantic.query import ReadLimit

    if budget.rows + count > budget.max_rows:
        raise ReadLimit("visual evidence row-work budget exhausted", reason="work_limit")
    budget.rows += count


def _native_region(row):
    top, bottom = row["top"], row["bottom"]
    if row["origin"] == "bottom_left":
        top, bottom = row["page_height"] - top, row["page_height"] - bottom
    elif row["origin"] != "top_left":
        raise ValueError("visual selection has an unsupported original coordinate origin")
    return VisualSourceRegion(left=row["left"], top=top, right=row["right"], bottom=bottom)


def _overlaps(a, b):
    return a.left < b.right and b.left < a.right and a.top < b.bottom and b.top < a.bottom


def _media_region(row, image):
    """Map a published displayed CropBox region into media-relative evidence points."""
    from corpus_structure.ingest.pdf_recognition import inverse_transform_point

    display = _native_region(row)
    sx = image["width"] / float(row["page_width"])
    sy = image["height"] / float(row["page_height"])
    affine = image["transform"]["affine"]
    corners = [
        inverse_transform_point(affine, x * sx, y * sy)
        for x in (display.left, display.right)
        for y in (display.top, display.bottom)
    ]
    xs, ys = zip(*corners, strict=True)
    return VisualSourceRegion(
        left=max(0, min(xs)), top=max(0, min(ys)), right=max(xs), bottom=max(ys)
    )


def _page_incumbent(conn, source, page_no, budget):
    """Select existing projected items on this page before fetching their bounded prose."""
    from sqlalchemy import select

    from corpus_structure.semantic.pdf_record_reader import published_native_table
    from corpus_structure.semantic.pdf_storage import _budgeted_mappings

    regions, items = published_native_table("region"), published_native_table()
    pointers = select(regions.c.pointer).where(
        regions.c.task_id == source.task_id,
        regions.c.product_key == source.product_key,
        regions.c.page_no == page_no,
    )
    query = (
        select(items.c.pointer, items.c.label, items.c.content_layer, items.c.text)
        .where(
            items.c.task_id == source.task_id,
            items.c.product_key == source.product_key,
            items.c.pointer.in_(pointers),
        )
        .order_by(items.c.ordinal)
        .limit(budget.max_rows - budget.rows + 1)
    )
    return _budgeted_mappings(conn, query, budget)


def inspect_pdf_visual_evidence(conn: Connection, request: NativeSourceRequest, *, source: SelectedPdfSource,
    projection_context: PreparedRelease, cancellation: BorrowerCancellation,
    read_budget: PublishedReadBudget) -> NativeSourceResponse:
    from pydantic_core import to_jsonable_python
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.query import ReadLimit
    from corpus_structure.semantic.refusals import InvalidContinuation
    from .native_source import NativeSourceResponse, _published_native_header, _source_cursor, _source_position
    evidence=request.evidence
    if evidence is None: raise ValueError("visual read requires exact selected evidence")
    after=_source_position(request) if request.cursor is not None else 0
    if type(after) is not int or after<0: raise InvalidContinuation("visual cursor differs",reason="invalid_continuation")
    reply=_read(conn,source,evidence,"header",read_budget)
    assert isinstance(reply,VisualHeaderReply)
    selected=reply.header
    observation=selected.observation
    image=cast(dict[str,Any],observation["image"])
    page_no=image["page_no"]
    if request.page_no is not None and request.page_no!=page_no: raise ValueError("visual evidence belongs to another submitted page")
    published=published_record_reader(conn,source.physical,cancellation=cancellation,
        projection_context=projection_context,read_budget=read_budget)
    if published is None: raise ValueError("visual inspection requires selected PDF publication")
    header=_published_native_header(published,runtime=False)
    transform=image["transform"]
    submitted=VisualSourceRegion(left=transform["crop_left"],top=transform["crop_top"],
        right=transform["crop_right"],bottom=transform["crop_bottom"]) if transform["status"]=="coarse" else None
    rows=[]; original_regions=[]; scope_regions=[]; companion=None; following=None; items=()
    mapping=selected.mapping_availability
    if request.pointer is not None:
        rows=published.item_page(pointer=request.pointer,limit=1)
        original_regions=published.regions(request.pointer) if request.region_index is None else [published.region(request.pointer,request.region_index)]
        original_regions=[row for row in original_regions if row["page_no"]==page_no]
        if not rows or not original_regions: raise ValueError("source item is outside submitted visual page")
        selection=image["selection"]
        if selection.get("pointer") is not None:
            if request.pointer!=selection["pointer"] or request.region_index!=selection["region_index"]:
                raise ValueError("visual crop requires exact selected item and region")
            scope_regions=[submitted] if submitted else []
        elif submitted:
            scope_regions=[_media_region(row,image) for row in original_regions]
            if not any(_overlaps(region,submitted) for region in scope_regions): raise ValueError("source item is outside submitted image")
        if submitted is None: mapping="unavailable"
        remaining=read_budget.max_rows-read_budget.rows
        if remaining<2: raise ReadLimit("visual row budget exhausted",reason="work_limit")
        companion=published.source_context((request.pointer,),rows[0].get("section_pointer") or "#/body",row_budget=remaining-1)
        _charge_rows(read_budget,sum(len(companion[name]) for name in ("inputs","occurrences","relations","coverage","mapping_reports"))+
                     sum(len(relation["endpoints"]) for relation in companion["relations"]))
        rows[0]["native_item"]=published.selected_native_items((request.pointer,))[request.pointer]
    elif request.artifact_digest is None: rows=_page_incumbent(conn,source.physical,page_no,read_budget)
    if request.artifact_digest is not None:
        artifact=_read(conn,source,evidence,"artifact",read_budget,artifact_digest=request.artifact_digest,after=after)
        assert isinstance(artifact,VisualArtifactReply)
        content=bytes.fromhex(artifact.content_hex)
        following=artifact.next_offset
        rows=[dict(artifact_digest=artifact.digest,total_bytes=artifact.total_bytes,offset=artifact.offset,
            length=len(content),encoding="base64",media_type=artifact.media_type,data=b64encode(content).decode(),next_offset=following)]
    elif mapping=="available":
        candidates=_read(conn,source,evidence,"rows",read_budget,after=after,limit=request.limit,
            regions=[region.model_dump(mode="json") for region in scope_regions],kind=request.visual_kind,
            query=request.visual_query,occurrence_id=request.occurrence_id,cell_index=request.cell_index)
        assert isinstance(candidates,VisualRowsReply)
        items=candidates.items;following=candidates.next_after
    elif after: raise InvalidContinuation("visual mapping has no continuation",reason="invalid_continuation")
    return NativeSourceResponse(selection=request,cut=source.cut.record,release_id=header.release_id,
        health=to_jsonable_python(header.health),rows=to_jsonable_python(rows),
        next_cursor=_source_cursor(request,following) if following is not None else None,
        companion=to_jsonable_python(companion),visual_evidence=VisualEvidenceRead(evidence=evidence,raw_evidence=selected.raw,
            producer=selected.producer,page_no=page_no,original_artifact_digest=header.artifact_digest,
            original_regions=to_jsonable_python(original_regions),submitted_region=submitted,
            observation_release_id=str(selected.producer["release_id"]),observation=observation,
            observation_health=selected.mapping,mapping_availability=mapping,items=items))
