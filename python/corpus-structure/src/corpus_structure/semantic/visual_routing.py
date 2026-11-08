"""Dry Chandra nominations from exact published PDF inputs."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import func, select

from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

from .metadata import table
from .pdf_record_reader import published_native_table, published_record_reader
from .product_reference import ProductReference

_LAYOUT_KINDS = {
    "Caption": "caption",
    "Chart": "picture",
    "Picture": "picture",
    "Formula": "formula",
    "Table": "table",
}


class VisualRouteReason(BaseModel):
    code: Literal[
        "incumbent_structure",
        "missing_structure",
        "incomplete_request",
        "incomplete_ocr_region",
        "unassessed",
        "no_supported_trigger",
    ]
    kind: str | None = None
    inputs: tuple[VisualEvidencePin, ...] = ()


class VisualPageRoute(BaseModel):
    page_no: int
    action: Literal["repair", "recognize", "unresolved", "skip"]
    reasons: tuple[VisualRouteReason, ...]


class VisualRouteReport(BaseModel):
    policy: Literal["chandra-dry-routing-v1"] = "chandra-dry-routing-v1"
    source: VisualEvidencePin
    structural_input: VisualEvidencePin | None
    page_count: int
    pages: tuple[VisualPageRoute, ...]


@dataclass
class _PageSignals:
    selected: Counter[str]
    native: Counter[str]
    layout: Counter[str]
    layout_pins: tuple[VisualEvidencePin, ...]
    incomplete: tuple[VisualEvidencePin, ...]
    ocr_incomplete: bool
    assessed: bool


def _decide(page_no: int, signals: _PageSignals) -> VisualPageRoute:
    repair = []
    requests = []
    for kind, count in sorted(signals.layout.items()):
        if count <= signals.selected[kind]:
            continue
        if signals.native[kind] >= count:
            repair.append(
                VisualRouteReason(code="incumbent_structure", kind=kind, inputs=signals.layout_pins)
            )
        else:
            requests.append(
                VisualRouteReason(code="missing_structure", kind=kind, inputs=signals.layout_pins)
            )
    if signals.incomplete:
        requests.append(VisualRouteReason(code="incomplete_request", inputs=signals.incomplete))
    if signals.ocr_incomplete:
        requests.append(VisualRouteReason(code="incomplete_ocr_region"))
    if requests:
        return VisualPageRoute(
            page_no=page_no, action="recognize", reasons=tuple(repair + requests)
        )
    if repair:
        return VisualPageRoute(page_no=page_no, action="repair", reasons=tuple(repair))
    return VisualPageRoute(
        page_no=page_no,
        action="skip" if signals.assessed else "unresolved",
        reasons=(
            VisualRouteReason(code="no_supported_trigger" if signals.assessed else "unassessed"),
        ),
    )


def _layout_inventory(raw: bytes) -> Counter[str] | None:
    from corpus_structure.ingest.pdf_recognition import _BLOCK

    labels: Counter[str] = Counter()
    located = False
    for match in _BLOCK.finditer(raw.decode("utf-8")):
        x1, y1, x2, y2 = (float(match[index]) for index in (1, 2, 4, 5))
        kind = _LAYOUT_KINDS.get(match[6])
        if not all(map(math.isfinite, (x1, y1, x2, y2))) or x1 == x2 or y1 == y2:
            continue
        located = True
        if kind is not None:
            labels[kind] += 1
    return labels if located else None


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
        select(regions.c.page_no, items.c.label, func.count(func.distinct(items.c.pointer)))
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
            items.c.content_layer == "body",
        )
        .group_by(regions.c.page_no, items.c.label)
    )
    by_page: dict[int, Counter[str]] = defaultdict(Counter)
    for page, label, count in conn.execute(query):
        by_page[page][label] = count
    return by_page


def _raw_layout(conn, pin, digest):
    custody, artifacts = map(table, ("ops.pdf_product_artifact", "kb.source_artifact"))
    # The SQL bound is checked before a raw payload can enter this read.
    raw = conn.scalar(
        select(artifacts.c.content)
        .select_from(
            custody.join(artifacts, custody.c.artifact_digest == artifacts.c.artifact_digest)
        )
        .where(
            custody.c.task_id == pin.task_id,
            custody.c.product_key == pin.product_key,
            custody.c.artifact_digest == digest,
            func.octet_length(artifacts.c.content) <= 1024 * 1024,
        )
    )
    if raw is None:
        return None
    result = bytes(raw)
    if sha256(result).hexdigest() != digest:
        raise ValueError("retained B layout bytes differ from the archived observation digest")
    return result


def read_visual_routes(
    conn, source: VisualEvidencePin, *, first: int, limit: int
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
    selected = _page_items(conn, source, first, last)
    native = _page_items(conn, structural, first, last) if structural is not None else {}
    ocr_incomplete = set()
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
                regions = batch.column("ocr_regions")[0].as_py()
                if any(
                    region["outcome"] in {"partial", "failed", "incomplete"}
                    for region in regions or ()
                ):
                    ocr_incomplete.add(page)

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
    for page in range(first, last + 1):
        layout: Counter[str] = Counter()
        layout_pins = []
        incomplete = []
        full_page = False
        for row in by_page[page]:
            pin = VisualEvidencePin.model_validate(
                {key: row[key] for key in VisualEvidencePin.model_fields}
            )
            if row["outcome"] in {"failed", "partial"} or row["finish"] == "length":
                incomplete.append(pin)
            elif row["outcome"] == "succeeded":
                if row["role"] == "A":
                    full_page = True
                elif row["role"] == "B" and row["raw_digest"]:
                    raw = _raw_layout(conn, pin, row["raw_digest"])
                    inventory = _layout_inventory(raw) if raw is not None else None
                    if inventory is not None:
                        layout |= inventory
                        layout_pins.append(pin)
        pages.append(
            _decide(
                page,
                _PageSignals(
                    selected[page],
                    native.get(page, Counter()),
                    layout,
                    tuple(layout_pins),
                    tuple(incomplete),
                    page in ocr_incomplete,
                    full_page and bool(layout_pins) and bool(selected[page]),
                ),
            )
        )
    return VisualRouteReport(
        source=source, structural_input=structural, page_count=page_count, pages=tuple(pages)
    )
