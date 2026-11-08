"""Original raster geometry and typed, nonselected Chandra projection."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from contextlib import closing
from io import BytesIO
from typing import TYPE_CHECKING, Any

from corpus_structure.ingest.pdf_recognition import crop_transform, render_recognition_page
from corpus_structure.serve.pdf_visual_evidence import (
    VisualCaption,
    VisualCaptionCandidate,
    VisualCellGroup,
    VisualEvidenceArtifact,
    VisualPicture,
    VisualSourceRegion,
    VisualTable,
    VisualTableCell,
    VisualText,
)

if TYPE_CHECKING:
    from docling_core.types.doc import DoclingDocument


def render_visual_input(
    original: bytes, page_no: int, region: Mapping[str, Any] | None, rotation: int = 0
) -> tuple[bytes, dict[str, Any]]:
    """Use the incumbent PDF renderer and compose a qualified crop and orientation."""
    from PIL import Image
    from pypdfium2 import PdfDocument

    if rotation not in (0, 90, 180, 270) or (rotation and region is None):
        raise ValueError("visual rotation requires a qualified crop and a quarter turn")
    scale = 2
    with PdfDocument(original) as document:
        if not 1 <= page_no <= len(document):
            raise ValueError("visual request page is outside the original")
        with closing(document[page_no - 1]) as page:
            width, height = page.get_size()
        pixel_width, pixel_height = math.ceil(width * scale), math.ceil(height * scale)
        if max(pixel_width, pixel_height) > 8192 or pixel_width * pixel_height > 24_000_000:
            raise ValueError("visual request exceeds the raster limit")
        pixels, transform = render_recognition_page(document, page_no, scale)
    if region is None:
        return pixels, transform

    if (
        region["page_no"] != page_no
        or not math.isclose(region["page_width"], width, abs_tol=1e-5)
        or not math.isclose(region["page_height"], height, abs_tol=1e-5)
    ):
        raise ValueError("visual request region differs from the physical page")
    left, top, right, bottom = (float(region[key]) for key in ("left", "top", "right", "bottom"))
    if region["origin"] == "bottom_left":
        top, bottom = height - top, height - bottom
    elif region["origin"] != "top_left":
        raise ValueError("unsupported visual crop coordinate origin")
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("visual crop exceeds the physical page")
    with Image.open(BytesIO(pixels)) as rendered:
        bounds = (
            math.floor(left * rendered.width / width),
            math.floor(top * rendered.height / height),
            math.ceil(right * rendered.width / width),
            math.ceil(bottom * rendered.height / height),
        )
        transform = crop_transform(transform, bounds)
        with rendered.crop(bounds) as crop:
            a, b, c, d, e, f = transform["affine"]
            if rotation:
                orientation, affine = {
                    90: (Image.Transpose.ROTATE_270, [-b, a, -d, c, crop.height - f, e]),
                    180: (
                        Image.Transpose.ROTATE_180,
                        [-a, -b, -c, -d, crop.width - e, crop.height - f],
                    ),
                    270: (Image.Transpose.ROTATE_90, [b, -a, d, -c, f, crop.width - e]),
                }[rotation]
                transform["affine"] = affine
                with crop.transpose(orientation) as upright:
                    return _png(upright), transform
            return _png(crop), transform


def _png(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _original_region(node, *, page_no, transform, image_size):
    provenance = getattr(node, "prov", ())
    if len(provenance) != 1 or provenance[0].page_no != page_no:
        return None
    width, height = image_size
    box = provenance[0].bbox.to_top_left_origin(height)
    if not (0 <= box.l < box.r <= width and 0 <= box.t < box.b <= height):
        return None
    a, b, c, d, e, f = transform["affine"]
    determinant = a * d - b * c
    if not determinant:
        return None
    corners = [
        ((d * (x - e) - c * (y - f)) / determinant, (-b * (x - e) + a * (y - f)) / determinant)
        for x, y in ((box.l, box.t), (box.r, box.t), (box.l, box.b), (box.r, box.b))
    ]
    xs, ys = zip(*corners, strict=True)
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    page_width, page_height = transform["page_width"], transform["page_height"]
    if not (
        -1e-5 <= left < right <= page_width + 1e-5 and -1e-5 <= top < bottom <= page_height + 1e-5
    ):
        return None
    return VisualSourceRegion(
        left=max(0, left),
        top=max(0, top),
        right=min(page_width, right),
        bottom=min(page_height, bottom),
    )


def _parent_first(nodes):
    ordered = {}
    pending = set()

    def visit(pointer):
        if pointer in ordered:
            return
        if pointer in pending:
            raise ValueError("visual evidence contains cyclic containment")
        pending.add(pointer)
        node = nodes[pointer]
        parent = node.parent.cref if node.parent is not None else None
        if parent in nodes:
            visit(parent)
        pending.remove(pointer)
        ordered[pointer] = node

    for pointer in nodes:
        visit(pointer)
    return ordered


def map_visual_result(
    document: DoclingDocument,
    *,
    page_no: int,
    transform: dict[str, Any],
    image_size: tuple[int, int],
) -> VisualEvidenceArtifact:
    """Preserve typed evidence without adding content to a published document."""
    from docling_core.types.doc import CodeItem, GroupItem, PictureItem, RichTableCell, TableItem

    from corpus_structure.ingest.pdf_hierarchy import native_nodes
    from corpus_structure.ingest.pdf_reconciliation import _text
    from corpus_structure.methods.source_preparation import native_table_geometry

    rows = {}
    nodes = native_nodes(document)
    attachments: dict[str, list[str]] = defaultdict(list)
    rich_roots: set[str] = set()
    for node in nodes.values():
        if isinstance(node, (PictureItem, TableItem)):
            for caption in node.captions:
                attachments[caption.cref].append(node.self_ref)
        if isinstance(node, TableItem):
            rich_roots.update(
                cell.ref.cref for cell in node.data.table_cells if isinstance(cell, RichTableCell)
            )
    for pointer, node in _parent_first(nodes).items():
        label = node.label.value
        parent = node.parent
        while parent is not None and parent.cref not in rows:
            parent = parent.resolve(document).parent
        parent_id = parent.cref if parent is not None else None
        parent_row = rows.get(parent_id)
        region = _original_region(node, page_no=page_no, transform=transform, image_size=image_size)
        if region is None and parent_row is not None and parent_row.source_region is not None:
            enclosing = parent_row.source_region
            region = enclosing.model_copy(
                update={
                    "enclosing_occurrence_id": enclosing.enclosing_occurrence_id or parent_id,
                }
            )
        scope = dict(
            occurrence_id=pointer,
            provider_locator=pointer,
            parent_occurrence_id=parent_id,
            source_region=region,
        )
        if pointer in rich_roots or (
            isinstance(node, GroupItem) and isinstance(parent_row, VisualCellGroup)
        ):
            if parent_id is None:
                raise ValueError("rich cell groups require a retained parent")
            rows[pointer] = VisualCellGroup(
                **{**scope, "parent_occurrence_id": parent_id}, native_label=label
            )
        elif isinstance(node, PictureItem):
            meta = node.meta.model_dump(mode="json", exclude_none=True) if node.meta else None
            rows[pointer] = VisualPicture(**scope, metadata=meta)
            description = getattr(node.meta, "description", None)
            if description is not None and description.text:
                rows[pointer + "/description"] = VisualText(
                    kind="picture_description",
                    text=description.text,
                    occurrence_id=pointer + "/description",
                    provider_locator=pointer,
                    parent_occurrence_id=pointer,
                    source_region=region.model_copy(
                        update={
                            "enclosing_occurrence_id": region.enclosing_occurrence_id or pointer,
                        }
                    )
                    if region is not None
                    else None,
                )
        elif isinstance(node, TableItem):
            cells = [
                VisualTableCell(
                    **cell.model_dump(
                        include={
                            "text",
                            "start_row_offset_idx",
                            "end_row_offset_idx",
                            "start_col_offset_idx",
                            "end_col_offset_idx",
                            "column_header",
                            "row_header",
                        }
                    ),
                    content_occurrence_id=(
                        cell.ref.cref if isinstance(cell, RichTableCell) else None
                    ),
                )
                for cell in node.data.table_cells
            ]
            for target in native_table_geometry(
                {"data": {"table_cells": [cell.model_dump() for cell in cells]}}
            ):
                if target.header_path or target.row_path:
                    cells[target.cell_index] = cells[target.cell_index].model_copy(
                        update={
                            "column_header_path": target.header_path,
                            "row_header_path": target.row_path,
                        }
                    )
            rows[pointer] = VisualTable(
                **scope,
                cells=tuple(cells),
                num_rows=node.data.num_rows,
                num_cols=node.data.num_cols,
            )
        elif label == "formula":
            rows[pointer] = VisualText(
                **scope,
                kind="formula",
                text=node.text,
                original_text=node.orig if node.orig != node.text else None,
            )
        elif isinstance(parent_row, VisualCellGroup) and getattr(node, "text", ""):
            rows[pointer] = VisualText(
                **scope, kind="cell_text", text=node.text, native_label=label
            )
        elif label == "caption":
            owners = tuple(dict.fromkeys(attachments.get(pointer, [])))
            if parent_id is not None and isinstance(parent_row, (VisualPicture, VisualTable)):
                rows[pointer] = VisualCaption(
                    **{**scope, "parent_occurrence_id": parent_id},
                    text=_text(node, document),
                    parser_attachment_occurrence_ids=owners,
                )
            else:
                if region is not None and region.enclosing_occurrence_id:
                    scope["source_region"] = None
                rows[pointer] = VisualCaptionCandidate(
                    **{**scope, "parent_occurrence_id": None},
                    text=_text(node, document),
                    parser_attachment_occurrence_ids=owners,
                )
        elif (
            isinstance(node, CodeItem)
            and isinstance(parent_row, VisualPicture)
            and node.text.startswith(
                (
                    "graph ",
                    "flowchart ",
                    "sequenceDiagram",
                    "stateDiagram",
                    "classDiagram",
                    "erDiagram",
                )
            )
        ):
            rows[pointer] = VisualText(**scope, kind="mermaid", text=node.text)
        elif isinstance(parent_row, VisualPicture) and getattr(node, "text", ""):
            rows[pointer] = VisualText(**scope, kind="picture_text", text=node.text)
    return VisualEvidenceArtifact(page_no=page_no, rows=tuple(rows.values()))
