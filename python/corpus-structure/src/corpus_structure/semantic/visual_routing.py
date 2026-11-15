"""Dry Chandra nominations from exact published PDF inputs."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import case, func, select

from corpus_structure.semantic.visual_evidence import VisualEvidencePin
from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference

from .metadata import table
from .pdf_payloads import _from_arrow
from .pdf_record_reader import published_native_table, published_record_reader
from .product_reference import ProductReference

_LAYOUT_KINDS = {
    "Caption": "caption",
    "Chart": "picture",
    "Picture": "picture",
    "Formula": "formula",
    "Table": "table",
}
_FURNITURE = {"Page-header", "Page-footer", "Page-number"}
_CROP_KINDS = {"table", "picture", "formula"}
_BOX_KEYS = ("left", "top", "right", "bottom")
_QUANTITIES = re.compile(r"(?<![\\\w])[\u2212+-]?\d+(?:[.,]\d+)*(?:[%‰])?(?![\w])")
_Box = tuple[float, float, float, float]


class DemandVisualEvidencePin(BaseModel):
    """Actual selected product/member and cut; physical publisher pins stay separate."""

    version: Literal["demand-visual-evidence-v1"] = "demand-visual-evidence-v1"
    project_id: str
    demand_id: str
    read_id: str
    product_id: str
    member_id: str | None
    derivation_id: str


type VisualEvidenceReference = VisualEvidencePin | DemandVisualEvidencePin


class VisualRouteCrop(BaseModel):
    """An address in the report's selected product, usable by VisualSelection."""

    pointer: str
    region_index: int


class VisualRouteReason(BaseModel):
    code: Literal[
        "incumbent_structure",
        "missing_structure",
        "incomplete_request",
        "incomplete_ocr_region",
        "located_disagreement",
        "omitted_crop",
        "verified_blank_body",
        "unassessed",
        "no_supported_trigger",
    ]
    kind: str | None = None
    inputs: tuple[VisualEvidenceReference, ...] = ()
    crop: VisualRouteCrop | None = None
    artifact_digest: str | None = None


class VisualPageRoute(BaseModel):
    page_no: int
    action: Literal["repair", "recognize", "unresolved", "skip"]
    reasons: tuple[VisualRouteReason, ...]
    crop: VisualRouteCrop | None = None
    cues: tuple[VisualCueAssessment, ...] = ()


class VisualCueAssessment(BaseModel):
    cue: Literal["layout", "whole_recognition", "crop_comparison", "crop_coverage", "ocr_regions"]
    status: Literal["positive", "negative", "inconclusive", "unassessed"]
    reason: str
    inputs: tuple[VisualEvidenceReference, ...] = ()
    artifact_digest: str | None = None
    crop: VisualRouteCrop | None = None
    crop_bounds: _Box | None = None


class VisualRouteReport(BaseModel):
    policy: Literal["chandra-dry-routing-v4"] = "chandra-dry-routing-v4"
    source: SelectedPdfSourceReference
    structural_input: VisualEvidencePin | None
    page_count: int
    pages: tuple[VisualPageRoute, ...]


@dataclass(frozen=True, slots=True)
class _Region:
    kind: str
    crop: VisualRouteCrop
    box: _Box
    frame: tuple[float, float]


@dataclass(frozen=True, slots=True)
class StudyRegion:
    """Witnessed presence in an evaluation view, with no published crop authority."""

    kind: str
    box: _Box
    frame: tuple[float, float]
    replaces: VisualRouteCrop | None = None


@dataclass(frozen=True, slots=True)
class _Reading:
    kind: str
    box: _Box
    text: str


@dataclass(frozen=True, slots=True)
class _Observation:
    pin: VisualEvidenceReference
    image: dict
    readings: tuple[_Reading, ...]
    availability: str = "available"


@dataclass(slots=True)
class _PageSignals:
    selected: list[_Region]
    native: list[_Region]
    assessed: bool
    layout: _Observation | None = None
    structural: VisualEvidenceReference | None = None
    requests: list[VisualRouteReason] = field(default_factory=list)
    blank: bool = False
    study_regions: tuple[StudyRegion, ...] = ()
    cues: tuple[VisualCueAssessment, ...] = ()


def _decide(page_no: int, signals: _PageSignals) -> VisualPageRoute:
    repair = []
    requests = list(signals.requests)
    unresolved = []
    cues = signals.cues
    if (layout := signals.layout) is not None:
        selected: Sequence[_Region | StudyRegion] = signals.selected
        if signals.study_regions:
            replaced = [region.replaces for region in signals.study_regions]
            selected = (
                *(region for region in signals.selected if region.crop not in replaced),
                *signals.study_regions,
            )
        seen = set()
        comparable = _comparable_frame(layout.image)
        for reading in layout.readings:
            kind = _LAYOUT_KINDS.get(reading.kind)
            if kind is None or (kind, reading.box) in seen:
                continue
            seen.add((kind, reading.box))
            if not comparable:
                unresolved.append(
                    VisualRouteReason(code="unassessed", kind=kind, inputs=(layout.pin,))
                )
                continue
            if _located(reading.box, layout.image, selected, kind):
                continue
            if signals.structural and _located(reading.box, layout.image, signals.native, kind):
                repair.append(
                    VisualRouteReason(
                        code="incumbent_structure",
                        kind=kind,
                        inputs=(signals.structural, layout.pin),
                    )
                )
            else:
                requests.append(
                    VisualRouteReason(code="missing_structure", kind=kind, inputs=(layout.pin,))
                )
        if repair or len(requests) > len(signals.requests):
            assessment = VisualCueAssessment(
                cue="layout",
                status="positive",
                reason="located_structure_difference",
                inputs=(layout.pin,),
            )
        elif unresolved:
            assessment = VisualCueAssessment(
                cue="layout",
                status="inconclusive",
                reason="unqualified_layout_geometry",
                inputs=(layout.pin,),
            )
        else:
            assessment = VisualCueAssessment(
                cue="layout",
                status="negative",
                reason="assessed",
                inputs=(layout.pin,),
            )
        cues = (assessment, *cues)
    if requests:
        crop = requests[0].crop
        return VisualPageRoute(
            page_no=page_no,
            action="recognize",
            reasons=tuple(repair + requests + unresolved),
            crop=crop if all(reason.crop == crop for reason in requests + unresolved) else None,
            cues=cues,
        )
    if repair:
        return VisualPageRoute(
            page_no=page_no, action="repair", reasons=tuple(repair + unresolved), cues=cues
        )
    if unresolved:
        return VisualPageRoute(
            page_no=page_no, action="unresolved", reasons=tuple(unresolved), cues=cues
        )
    if signals.blank and layout is not None:
        return VisualPageRoute(
            page_no=page_no,
            action="skip",
            reasons=(VisualRouteReason(code="verified_blank_body", inputs=(layout.pin,)),),
            cues=cues,
        )
    assessed = signals.assessed and all(cue.status == "negative" for cue in cues)
    return VisualPageRoute(
        page_no=page_no,
        action="skip" if assessed else "unresolved",
        reasons=(VisualRouteReason(code="no_supported_trigger" if assessed else "unassessed"),),
        cues=cues,
    )


def _box(values) -> _Box | None:
    left, top, right, bottom = map(float, values)
    if not all(map(math.isfinite, (left, top, right, bottom))):
        return None
    return (left, top, right, bottom) if left < right and top < bottom else None


def _comparable_frame(image: dict) -> bool:
    transform = image.get("transform") or {}
    # The selected region is in the physical-page frame. An offset/rotated native
    # page needs a separately qualified correspondence to the media frame.
    return (
        transform.get("status") == "coarse"
        and transform.get("page_rotation") == 0
        and transform.get("source_space") == "pdf_points"
        and transform.get("target_space") == "submitted_pixels"
        and image.get("width", 0) > 0
        and image.get("height", 0) > 0
        and (
            transform.get("normalization") == "clipped"
            or (
                transform.get("normalization") == "none"
                and transform.get("crop_left") == 0
                and transform.get("crop_top") == 0
                and transform.get("crop_right") == transform.get("page_width")
                and transform.get("crop_bottom") == transform.get("page_height")
            )
        )
    )


def _normalized_region(values, image) -> _Box | None:
    from corpus_structure.ingest.pdf_recognition import inverse_transform_point

    if not _comparable_frame(image):
        return None
    try:
        x1, y1, x2, y2 = map(float, values)
    except TypeError, ValueError:
        return None
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        return None
    affine = image["transform"]["affine"]
    x1, y1 = inverse_transform_point(affine, x1 * image["width"], y1 * image["height"])
    x2, y2 = inverse_transform_point(affine, x2 * image["width"], y2 * image["height"])
    return _box((x1, y1, x2, y2))


def _readings(raw: bytes, image: dict) -> tuple[_Reading, ...]:
    from corpus_structure.ingest.pdf_recognition import _BLOCK, _CLASS

    if not _comparable_frame(image):
        return ()
    readings = []
    text = raw.decode("utf-8")
    for match in _BLOCK.finditer(text):
        # This dry route accepts ordinary content-normalized readings only.
        # Mapping and admission of other encodings stay with the PDF mapper.
        if (box := _normalized_region((match[index] for index in (1, 2, 4, 5)), image)) is not None:
            readings.append(_Reading(match[6], box, match[3]))
    return tuple(readings) if len(readings) == sum(1 for _ in _CLASS.finditer(text)) else ()


def _overlap(left: _Box, right: _Box) -> float:
    x = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    y = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return x * y


def _area(box: _Box) -> float:
    return (box[2] - box[0]) * (box[3] - box[1])


def _matches(left: _Box, right: _Box) -> bool:
    return _overlap(left, right) >= 0.55 * max(_area(left), _area(right))


def _located[Region: _Region | StudyRegion](
    box: _Box, image: dict, regions: Sequence[Region], kind: str
) -> list[Region]:
    if not _comparable_frame(image):
        return []
    transform = image["transform"]
    frame = transform["page_width"], transform["page_height"]
    return [
        region
        for region in regions
        if region.kind == kind
        and all(math.isclose(a, b, abs_tol=1e-5) for a, b in zip(region.frame, frame, strict=True))
        and _matches(box, region.box)
    ]


def _local_crop(box: _Box, image: dict, regions: list[_Region]) -> VisualRouteCrop | None:
    candidates = [match for kind in _CROP_KINDS for match in _located(box, image, regions, kind)]
    return candidates[0].crop if len(candidates) == 1 else None


def _original_blank_body(page, layout: _Observation, furniture: list[_Region]) -> bool:
    """Require original drawing objects confined to retained furniture, never absence of OCR."""
    from pypdfium2 import raw

    from corpus_structure.ingest.pdf_recognition import inverse_transform_point

    height = page.get_size()[1]
    if (
        not layout.readings
        or any(
            reading.kind not in _FURNITURE
            or (reading.box[3] > height * 0.2 and reading.box[1] < height * 0.8)
            for reading in layout.readings
        )
        or page.get_rotation() != 0
        or page.get_bbox() != page.get_mediabox()
        or raw.FPDFPage_GetAnnotCount(page.raw) != 0
    ):
        return False
    left, _, _, top = page.get_mediabox()
    transform = layout.image["transform"]
    if inverse_transform_point(transform["affine"], 0, 0) != (0, 0):
        return False
    bounds = [reading.box for reading in layout.readings]
    bounds += [row.box for row in furniture if any(_matches(row.box, box) for box in bounds)]
    for obj in page.get_objects(max_depth=1):
        if obj.type != raw.FPDF_PAGEOBJ_TEXT:
            return False
        x1, y1, x2, y2 = obj.get_bounds()
        box = _box((x1 - left, top - y2, x2 - left, top - y1))
        if box is None or not any(_overlap(box, header) >= 0.8 * _area(box) for header in bounds):
            return False
    return True


def _page_items(conn, pin, first, last):
    regions, items = published_native_table("region"), published_native_table()
    query = (
        select(
            regions.c.page_no,
            items.c.label,
            items.c.content_layer,
            regions.c.pointer,
            regions.c.region_index,
            regions.c.page_width,
            regions.c.page_height,
            *(regions.c[key] for key in _BOX_KEYS),
            regions.c.origin,
        )
        .select_from(
            regions.join(
                items,
                (items.c.task_id == regions.c.task_id)
                & (items.c.product_key == regions.c.product_key)
                & (items.c.pointer == regions.c.pointer),
            )
        )
        .where(
            regions.c.task_id == pin.task_id,
            regions.c.product_key == pin.product_key,
            regions.c.page_no.between(first, last),
            items.c.content_layer.in_(("body", "furniture")),
        )
        .order_by(regions.c.page_no, items.c.ordinal, regions.c.region_index)
    )
    by_page: dict[int, list[_Region]] = defaultdict(list)
    furniture: dict[int, list[_Region]] = defaultdict(list)
    for row in conn.execute(query):
        width, height = float(row.page_width), float(row.page_height)
        left, top, right, bottom = (float(getattr(row, key)) for key in _BOX_KEYS)
        if row.origin == "bottom_left":
            top, bottom = height - top, height - bottom
        elif row.origin != "top_left":
            continue
        box = _box((left, top, right, bottom))
        if box is not None and 0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height:
            layer = by_page if row.content_layer == "body" else furniture
            layer[row.page_no].append(
                _Region(
                    row.label,
                    VisualRouteCrop(pointer=row.pointer, region_index=row.region_index),
                    box,
                    (width, height),
                )
            )
    return by_page, furniture


def _quantity_disagrees(left: str, right: str) -> bool | None:
    # These are literal disagreement cues, not interpreted formulas or cell bindings.
    # Requiring explicit quantities on both sides avoids treating failed parsing as a conflict.
    a = Counter(_QUANTITIES.findall(left))
    b = Counter(_QUANTITIES.findall(right))
    return a != b if a and b else None


def _disagreements(
    whole: _Observation,
    crop: _Observation,
    regions: list[_Region],
) -> tuple[list[VisualRouteReason], bool]:
    reasons = []
    compared = []
    for reading in crop.readings:
        kind = _LAYOUT_KINDS.get(reading.kind)
        if kind not in {"table", "formula"}:
            continue
        counterparts = [
            other
            for other in whole.readings
            if reading.kind == other.kind and _matches(reading.box, other.box)
        ]
        difference = (
            _quantity_disagrees(reading.text, counterparts[0].text)
            if len(counterparts) == 1
            else None
        )
        compared.append(difference is not None)
        if difference:
            candidates = _located(reading.box, crop.image, regions, kind)
            reasons.append(
                VisualRouteReason(
                    code="located_disagreement",
                    kind=kind,
                    inputs=(whole.pin, crop.pin),
                    crop=candidates[0].crop if len(candidates) == 1 else None,
                )
            )
    return reasons, bool(compared) and all(compared)


def _crop_bounds(image: dict) -> _Box | None:
    transform = image.get("transform") or {}
    if not _comparable_frame(image) or transform["normalization"] != "clipped":
        return None
    return _box(transform["crop_" + key] for key in _BOX_KEYS)


def _scoped_attempt(image: dict, selected: list[_Region]) -> VisualRouteCrop | None:
    box = _crop_bounds(image)
    return _local_crop(box, image, selected) if box is not None else None


def _region_address(reason: VisualRouteReason) -> tuple:
    crop = reason.crop
    return (
        reason.code,
        reason.kind,
        tuple(
            (0, pin.use_id, pin.product_id, pin.derivation_id)
            if isinstance(pin, VisualEvidencePin)
            else (1, pin.product_id, pin.member_id, pin.derivation_id, pin.read_id)
            for pin in reason.inputs
        ),
        (crop.pointer, crop.region_index) if crop else None,
        reason.artifact_digest,
    )


def _selected_pdf_publication(page, member, records, capture_kind):
    """Follow this exact derivation's support to its actual capture publication receipt."""
    from pydantic import TypeAdapter

    from .data_operation_identity import decode_semantic_value
    from .data_operation_json import json_bytes
    from .pdf_publication import PdfExecutionReceipt

    relations = defaultdict(list)
    for record in records:
        relations[record["relation"]].append(record["record"])
    ancestors, pending = set(), [member["derivation_id"]]
    while pending:
        current = pending.pop()
        if current in ancestors:
            continue
        ancestors.add(current)
        pending.extend(
            row["support_derivation_id"]
            for row in relations["ops.data_derivation_support"]
            if row["derivation_id"] == current
        )
    image = member["body"]["observation"]["image"]
    if member["original_source"] != image["document"]:
        raise ValueError("visual result differs from its actual original source")
    products = {}
    for product in relations["kb.data_product"]:
        if product["kind_contract"] != capture_kind:
            continue
        body = decode_semantic_value(product["canonical_body"])
        if (
            product["project_id"] == page.cut.record["project_id"]
            and product["original_source"] == member["original_source"]
            and body["document"] == image["document"]
            and body["source_digest"] == image["source_digest"]
            and body["logical_digest"] == image["logical_digest"]
        ):
            products[product["id"]] = body
    episodes = {
        row["derivation_id"]
        for row in relations["ops.data_derivation_output"]
        if row["product_id"] in products and row["derivation_id"] in ancestors
    }
    intents = {row["id"]: row for row in relations["ops.data_completion_intent"]}
    actual = []
    for published in relations["ops.data_publication_receipt"]:
        if published["derivation_id"] not in episodes:
            continue
        intent = intents.get(published["intent_id"])
        if intent is None:
            raise ValueError("selected capture publication lacks its exact retained intent")
        for value in intent["payload"].get("execution_evidence", {}).get("pdf_receipts", []):
            receipt = TypeAdapter(PdfExecutionReceipt).validate_json(json_bytes(value), strict=True)
            publication = receipt.publication
            if (
                publication.logical_digest == image["logical_digest"]
                and publication.source_digest == image["source_digest"]
            ):
                actual.append(publication)
    if len(actual) != 1:
        raise ValueError(
            "selected visual result requires one unambiguous actual PDF publication receipt"
        )
    return actual[0]


@dataclass(frozen=True, slots=True)
class _SelectedVisualSample:
    observation: _Observation
    scope: Literal["page", "crop"]
    raw_digest: str
    complete: bool


def _selected_page_signals(samples: tuple[_SelectedVisualSample, ...], selected: list[_Region]) -> _PageSignals:
    """Compare actual page/crop samples; a retained sample never becomes independent evidence."""
    unique={}
    for sample in samples:
        unique.setdefault((sample.raw_digest, json.dumps(sample.observation.image,sort_keys=True)),sample)
    actual=tuple(unique.values())
    whole=next((sample for sample in actual if sample.scope=="page" and sample.complete),None)
    layout=(whole or next(iter(actual),None))
    signals=_PageSignals(selected,[],False,layout=layout.observation if layout else None)
    cues=[]
    for sample in actual:
        observed=sample.observation
        crop=_scoped_attempt(observed.image,selected) if sample.scope=="crop" else None
        if not sample.complete:
            signals.requests.append(VisualRouteReason(code="incomplete_request",inputs=(observed.pin,),crop=crop))
        if sample.scope!="crop" or whole is None or sample.raw_digest==whole.raw_digest: continue
        differences,complete=_disagreements(whole.observation,observed,selected)
        signals.requests.extend(differences)
        available=bool(observed.readings) and observed.availability=="available"
        cues.append(VisualCueAssessment(cue="crop_comparison",
            status="positive" if differences else "negative" if complete else "inconclusive" if available else "unassessed",
            reason="located_quantity_disagreement" if differences else "no_located_quantity_disagreement" if complete else "no_exact_quantity_comparison" if available else observed.availability,
            inputs=(whole.observation.pin,observed.pin),crop=crop,crop_bounds=_crop_bounds(observed.image)))
    cues.append(VisualCueAssessment(cue="whole_recognition",status="unassessed",
        reason="selected_chandra_samples_do_not_establish_independent_whole_recognition",
        inputs=tuple(sample.observation.pin for sample in actual if sample.scope=="page")))
    signals.cues=tuple(cues)
    signals.requests=list({_region_address(reason):reason for reason in signals.requests}.values())
    return signals


def read_demand_visual_routes(
    conn, demand_id, *, project_id, first=1, limit=32, max_bytes=8 * 1024 * 1024, continuation=None
):
    """Route current selected visual results against their actual native source inventory."""
    from pypdfium2 import PdfDocument

    from corpus_structure.ingest.pdf_recognition import _PDFIUM_LOCK

    from .data_operation_admission import bound_data_operation_model
    from .demand_results import read_demand_result, stream_selected_support
    from .releases import load_release

    if first < 1 or not 1 <= limit <= 64:
        raise ValueError("visual routing requires a positive page and a limit of 1 to 64")
    page = read_demand_result(
        conn,
        demand_id,
        project_id=project_id,
        limit=limit,
        max_bytes=max_bytes,
        continuation=continuation,
    )
    prepared = load_release(conn, page.cut.record["release_id"])
    model = bound_data_operation_model(prepared)
    contracts = {(item.owner, item.domain): item.key for item in model.identities}
    mapping_kind = contracts.get(
        ("https://corpus-structure.dev/semantic/data-operation-visual/DdoVisualMapping", "kind")
    )
    capture_kind = contracts.get(
        (
            "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfPublication",
            "kind",
        )
    )
    if mapping_kind is None or capture_kind is None:
        raise ValueError("selected release lacks its declared visual/PDF contracts")
    members = [
        item
        for item in page.members()
        if item["kind_contract"] == mapping_kind
        and first <= item["body"]["observation"]["image"]["page_no"] < first + limit
    ]
    records = tuple(stream_selected_support(conn, page)) if members else ()
    routes = []
    grouped=defaultdict(list)
    for member in members:
        value, image = member["body"], member["body"]["observation"]["image"]
        publication = _selected_pdf_publication(page, member, records, capture_kind)
        # This is the actual publisher's physical reference from retained native
        # evidence, rather than a run/task alias manufactured from the demand.
        selected, furniture = _page_items(conn, publication, image["page_no"], image["page_no"])
        pin = DemandVisualEvidencePin(
            project_id=project_id,
            demand_id=demand_id,
            read_id=page.cut.record["read_id"],
            product_id=member["product_id"],
            member_id=member["member_id"],
            derivation_id=member["derivation_id"],
        )
        observation = value["observation"]
        frame = {
            "width": image["width"],
            "height": image["height"],
            "transform": json.loads(image["transform_json"]),
        }
        layout = _Observation(pin, frame, _readings(observation["raw_response"].encode(), frame))
        requests = []
        if observation["provider_outcome"] != "succeeded" or value["completion"] != "complete":
            selection = image["selection"]
            crop = (
                VisualRouteCrop(
                    pointer=selection["pointer"], region_index=selection["region_index"]
                )
                if "pointer" in selection
                else None
            )
            requests.append(VisualRouteReason(code="incomplete_request", inputs=(pin,), crop=crop))
        grouped[(image["document"],image["logical_digest"],image["page_no"])].append(
            (_SelectedVisualSample(layout,"crop" if image["selection"].get("pointer") is not None else "page",
                observation["response_digest"],observation["provider_outcome"]=="succeeded" and value["completion"]=="complete"),
             publication,selected[image["page_no"]],furniture[image["page_no"]]))
    for (_,_,page_no), group in grouped.items():
        samples=tuple(item[0] for item in group)
        publication=group[0][1]
        signals=_selected_page_signals(samples,group[0][2])
        layout=signals.layout
        assert layout is not None
        pin=layout.pin
        image=next(item["body"]["observation"]["image"] for item in members
                   if item["product_id"]==pin.product_id)
        observation=next(item["body"]["observation"] for item in members if item["product_id"]==pin.product_id)
        if observation["provider_outcome"] == "succeeded" and not layout.readings:
            artifacts = table("kb.source_artifact")
            original = conn.scalar(
                select(artifacts.c.content).where(
                    artifacts.c.artifact_digest == publication.source_digest,
                    func.octet_length(artifacts.c.content) <= max_bytes,
                )
            )
            if original is None or sha256(original).hexdigest() != publication.source_digest:
                raise ValueError(
                    "visual blank-body assessment lacks bounded authentic original bytes"
                )
            with (
                _PDFIUM_LOCK,
                PdfDocument(bytes(original)) as document,
                closing(document[image["page_no"] - 1]) as physical,
            ):
                signals.blank = _original_blank_body(physical, layout, group[0][3])
        routes.append(
            {
                "source": pin.model_dump(mode="json"),
                "route": _decide(image["page_no"], signals).model_dump(mode="json"),
            }
        )
    return {
        "demand_id": demand_id,
        "cut": page.cut.record,
        "continuation": page.continuation,
        "policy": "chandra-dry-routing-v4",
        "evidence_scope": "selected-result-page",
        "routes": routes,
    }
