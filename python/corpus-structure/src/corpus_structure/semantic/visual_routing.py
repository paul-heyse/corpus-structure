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

from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

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
    inputs: tuple[VisualEvidencePin, ...] = ()
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
    inputs: tuple[VisualEvidencePin, ...] = ()
    artifact_digest: str | None = None


class VisualRouteReport(BaseModel):
    policy: Literal["chandra-dry-routing-v3"] = "chandra-dry-routing-v3"
    source: VisualEvidencePin
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
    pin: VisualEvidencePin
    image: dict
    readings: tuple[_Reading, ...]
    availability: str = "available"


@dataclass(slots=True)
class _PageSignals:
    selected: list[_Region]
    native: list[_Region]
    assessed: bool
    layout: _Observation | None = None
    structural: VisualEvidencePin | None = None
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


def _pin_columns(task, product):
    return (
        task.c.run_id,
        product.c.task_id,
        product.c.product_key,
        product.c.content_digest,
    )


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


def _observation_artifact(conn, pin, digest):
    custody, artifacts = map(table, ("ops.pdf_product_artifact", "kb.source_artifact"))
    # The SQL bound is checked before a raw payload can enter this read.
    row = conn.execute(
        select(case((func.octet_length(artifacts.c.content) <= 1024 * 1024, artifacts.c.content)))
        .select_from(
            custody.join(artifacts, custody.c.artifact_digest == artifacts.c.artifact_digest)
        )
        .where(
            custody.c.task_id == pin.task_id,
            custody.c.product_key == pin.product_key,
            custody.c.artifact_digest == digest,
        )
    ).one_or_none()
    if row is None:
        return None, "missing_artifact"
    if row[0] is None:
        return None, "artifact_over_budget"
    result = bytes(row[0])
    if sha256(result).hexdigest() != digest:
        raise ValueError("retained bytes differ from the archived observation artifact digest")
    return result, "available"


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


def _read_observation(conn, row) -> _Observation:
    pin = VisualEvidencePin.model_validate(
        {key: row[key] for key in VisualEvidencePin.model_fields}
    )
    image = row["image"]
    raw, availability = (
        _observation_artifact(conn, pin, row["raw_digest"])
        if row["raw_digest"]
        else (None, "missing_artifact")
    )
    if raw is None:
        return _Observation(pin, image, (), availability)
    try:
        readings = _readings(raw, image)
    except UnicodeError:
        readings = ()
    return _Observation(pin, image, readings, "available" if readings else "unsupported_reading")


def _scoped_attempt(image: dict, selected: list[_Region]) -> VisualRouteCrop | None:
    transform = image.get("transform") or {}
    if not _comparable_frame(image) or transform["normalization"] != "clipped":
        return None
    box = _box(transform["crop_" + key] for key in _BOX_KEYS)
    return _local_crop(box, image, selected) if box is not None else None


def _region_address(reason: VisualRouteReason) -> tuple:
    crop = reason.crop
    return (
        reason.code,
        reason.kind,
        tuple((pin.task_id, pin.product_key, pin.content_digest) for pin in reason.inputs),
        (crop.pointer, crop.region_index) if crop else None,
        reason.artifact_digest,
    )


def _omitted_crops(conn, row, selected, settled_crop_rows):
    encoding = row["decoding"]
    if not encoding:
        return [], "missing_decisions", None
    digest = json.loads(encoding).get("receipt_digests", {}).get("decisions.json")
    if not digest:
        return [], "missing_decisions", None
    pin = VisualEvidencePin.model_validate(
        {key: row[key] for key in VisualEvidencePin.model_fields}
    )
    retained, availability = _observation_artifact(conn, pin, digest)
    if retained is None:
        return [], availability, digest
    reasons = []
    try:
        decisions = json.loads(retained)
    except UnicodeError, ValueError:
        return [], "unsupported_decisions", digest
    if not isinstance(decisions, list) or any(not isinstance(item, dict) for item in decisions):
        return [], "unsupported_decisions", digest
    for decision in decisions:
        if decision.get("kind") != "crop" or decision.get("omitted") is not True:
            continue
        coords = decision.get("bbox_norm")
        if not isinstance(coords, list) or len(coords) != 4:
            availability = "unsupported_decisions"
            continue
        if (box := _normalized_region(coords, row["image"])) is None:
            availability = "unsupported_decisions"
            continue
        if any(
            (settled := _box(other["image"]["transform"]["crop_" + key] for key in _BOX_KEYS))
            is not None
            and _overlap(box, settled) >= 0.9 * _area(box)
            for other in settled_crop_rows
        ):
            continue
        reasons.append(
            VisualRouteReason(
                code="omitted_crop",
                inputs=(pin,),
                artifact_digest=digest,
                crop=_local_crop(box, row["image"], selected),
            )
        )
    return reasons, availability, digest


def read_visual_routes(
    conn,
    source: VisualEvidencePin,
    *,
    first: int,
    limit: int,
    study_regions: Mapping[int, tuple[StudyRegion, ...]] | None = None,
) -> VisualRouteReport:
    """Assess a bounded physical-page range without rendering or starting recognition."""
    from pypdfium2 import PdfDocument

    from corpus_structure.ingest.pdf_recognition import _PDFIUM_LOCK

    from .visual_requests import VisualSelection, _load_selection

    if first < 1 or not 1 <= limit <= 64:
        raise ValueError("visual routing requires a positive page and a limit of 1 to 64")
    _, _, original, _ = _load_selection(conn, VisualSelection(source=source, page_no=first))
    with _PDFIUM_LOCK, PdfDocument(original) as document:
        page_count = len(document)
    if first > page_count:
        raise ValueError("visual routing starts outside the original")
    last = min(page_count, first + limit - 1)
    product, inputs, task, bodies = map(
        table, ("ops.pdf_product", "ops.pdf_product_input", "ops.task", "ops.pdf_product_body")
    )
    edges = inputs.join(
        product,
        (product.c.task_id == inputs.c.input_task_id)
        & (product.c.product_key == inputs.c.input_product_key)
        & (product.c.content_digest == inputs.c.input_content_digest),
    ).join(task, task.c.id == product.c.task_id)
    scope = (inputs.c.task_id == source.task_id, inputs.c.product_key == source.product_key)
    structural_row = (
        conn.execute(
            select(*_pin_columns(task, product))
            .select_from(edges)
            .where(*scope, inputs.c.role == "structural")
        )
        .mappings()
        .one_or_none()
    )
    structural = VisualEvidencePin.model_validate(dict(structural_row)) if structural_row else None
    selected, furniture = _page_items(conn, source, first, last)
    native, _ = _page_items(conn, structural, first, last) if structural is not None else ({}, {})
    ocr_incomplete = defaultdict(list)
    ocr_assessed = set()
    if structural is not None:
        reader = published_record_reader(
            conn,
            ProductReference(structural.task_id, structural.product_key, structural.content_digest),
        )
        if reader is not None:
            for batch in reader.iter_payload_batches(
                page_nos=range(first, last + 1), columns=("page_no", "ocr_regions")
            ):
                page = batch.column("page_no")[0].as_py()
                ocr_assessed.add(page)
                regions = batch.column("ocr_regions")[0].as_py()
                ocr_incomplete[page].extend(
                    region
                    for region in regions or ()
                    if region["outcome"] in {"partial", "failed", "incomplete"}
                )

    observation = bodies.c.descriptor["observation"]
    page_no = observation["image"]["page_no"].as_integer()
    observed = observation["outcome"].as_string()
    role = observation["pass_role"].as_string()
    finish = observation["finish_reason"].as_string()
    digest = observation["raw_response_digest"].as_string()
    by_page = defaultdict(list)
    query = (
        select(
            *_pin_columns(task, product),
            page_no.label("page_no"),
            role.label("role"),
            observed.label("outcome"),
            finish.label("finish"),
            digest.label("raw_digest"),
            observation["image"].label("image"),
            observation["binding"]["decoding_json"].as_string().label("decoding"),
        )
        .select_from(
            edges.join(
                bodies,
                (bodies.c.task_id == product.c.task_id)
                & (bodies.c.product_key == product.c.product_key),
            )
        )
        .where(
            *scope,
            inputs.c.role == "recognition",
            page_no.between(first, last),
            role.in_(("A", "B", "C")),
        )
        .order_by(inputs.c.input_index)
    )
    for row in conn.execute(query).mappings():
        by_page[row["page_no"]].append(row)
    pages = []
    # Keep PDFium's serialized section limited to candidate blank pages. No
    # document/PDFium handle remains borrowed during a database read.
    signals_by_page = {
        page: _page_signals(
            conn,
            by_page[page],
            selected[page],
            native.get(page, []),
            structural,
            ocr_incomplete[page],
            ocr_assessed=page in ocr_assessed,
        )
        for page in range(first, last + 1)
    }
    if study_regions:
        for page, signals in signals_by_page.items():
            signals.study_regions = study_regions.get(page, ())
    blank_candidates = [
        page
        for page, signals in signals_by_page.items()
        if signals.layout
        and not signals.selected
        and not signals.study_regions
        and not signals.requests
        and all(reading.kind in _FURNITURE for reading in signals.layout.readings)
    ]
    if blank_candidates:
        with _PDFIUM_LOCK, PdfDocument(original) as document:
            for page in blank_candidates:
                signals = signals_by_page[page]
                assert signals.layout is not None
                with closing(document[page - 1]) as native_page:
                    signals.blank = _original_blank_body(
                        native_page, signals.layout, furniture[page]
                    )
    for page, signals in signals_by_page.items():
        pages.append(_decide(page, signals))
    return VisualRouteReport(
        source=source, structural_input=structural, page_count=page_count, pages=tuple(pages)
    )


def _page_signals(
    conn, rows, selected, native, structural, ocr_incomplete, *, ocr_assessed
) -> _PageSignals:
    successful = defaultdict(list)
    incomplete = []
    for row in rows:
        if (
            row["outcome"] in {"failed", "partial", "unknown", "unsupported"}
            or row["finish"] == "length"
        ):
            incomplete.append(row)
        elif row["outcome"] == "succeeded":
            successful[row["role"]].append(row)
    layouts = [_read_observation(conn, row) for row in reversed(successful["B"])]
    layout = next((observation for observation in layouts if observation.readings), None)
    signals = _PageSignals(
        selected,
        native,
        bool(successful["A"] and layout and selected),
        layout=layout,
        structural=structural,
    )
    for row in incomplete:
        if any(other["image"] == row["image"] for other in successful[row["role"]]):
            continue
        pin = VisualEvidencePin.model_validate(
            {key: row[key] for key in VisualEvidencePin.model_fields}
        )
        signals.requests.append(
            VisualRouteReason(
                code="incomplete_request",
                inputs=(pin,),
                crop=_scoped_attempt(row["image"], selected) if row["role"] == "C" else None,
            )
        )
    anchor = layout.image if layout else successful["A"][-1]["image"] if successful["A"] else {}
    for region in ocr_incomplete:
        box = _box(
            _from_arrow(region[key], {"type": "number"}, {}, f"#/ocr_regions/{key}")
            for key in _BOX_KEYS
        )
        signals.requests.append(
            VisualRouteReason(
                code="incomplete_ocr_region",
                inputs=(structural,) if structural else (),
                crop=_local_crop(box, anchor, selected) if box is not None else None,
            )
        )
    whole = _read_observation(conn, successful["A"][-1]) if successful["A"] else None
    crops = [_read_observation(conn, row) for row in successful["C"]]
    comparisons = (
        [_disagreements(whole, crop, selected) for crop in crops]
        if whole and whole.readings
        else []
    )
    disagreements = [reason for reasons, _ in comparisons for reason in reasons]
    signals.requests.extend(disagreements)
    omissions, omission_availability, decision_digest = [], "missing_whole_recognition", None
    if successful["A"]:
        omissions, omission_availability, decision_digest = _omitted_crops(
            conn, successful["A"][-1], selected, successful["C"]
        )
        signals.requests.extend(omissions)

    def cue(
        name,
        *,
        observations=(),
        available=False,
        positive=False,
        inconclusive=False,
        reason=None,
        digest=None,
        pins=(),
    ):
        unavailable = next((item.availability for item in observations if not item.readings), None)
        assessed = available and unavailable is None
        detail = reason or ("assessed" if assessed or positive else "missing_input")
        return VisualCueAssessment(
            cue=name,
            status=(
                "positive"
                if positive
                else "negative"
                if assessed
                else "inconclusive"
                if unavailable == "unsupported_reading" or (inconclusive and unavailable is None)
                else "unassessed"
            ),
            reason=detail if positive else unavailable or detail,
            inputs=tuple(item.pin for item in observations) + tuple(pins),
            artifact_digest=digest,
        )

    incomplete_comparison = bool(comparisons) and not all(complete for _, complete in comparisons)
    comparison_reason = (
        "located_quantity_disagreement"
        if disagreements
        else "no_exact_quantity_comparison"
        if incomplete_comparison
        else None
    )
    signals.cues = (
        *((cue("layout", observations=layouts),) if layout is None else ()),
        cue(
            "whole_recognition", observations=(whole,) if whole else (), available=whole is not None
        ),
        cue(
            "crop_comparison",
            observations=((whole,) if whole else ()) + tuple(crops),
            available=bool(comparisons) and not incomplete_comparison,
            positive=bool(disagreements),
            inconclusive=incomplete_comparison,
            reason=comparison_reason,
        ),
        cue(
            "crop_coverage",
            available=omission_availability == "available",
            positive=bool(omissions),
            reason=omission_availability,
            digest=decision_digest,
            pins=(whole.pin,) if whole else (),
        ),
        cue(
            "ocr_regions",
            available=ocr_assessed,
            positive=bool(ocr_incomplete),
            pins=(structural,) if structural else (),
        ),
    )
    signals.requests = list(
        {_region_address(reason): reason for reason in signals.requests}.values()
    )
    return signals
