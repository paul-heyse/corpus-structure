"""Bind the book study's repaired baseline to exact archived and original evidence."""

from collections import defaultdict
from hashlib import sha256

from corpus_structure.ingest.pdf_incumbent_recovery import (
    FIGURE_CAPTION,
    ORIGINAL,
    PANEL_LABELS,
    PREDECESSOR,
    RECIPE,
    TABLE_CAPTION,
    read_source_witness,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.visual_requests import _load_visual_source
from corpus_structure.semantic.visual_routing import (
    StudyRegion,
    VisualRouteCrop,
    _area,
    _matches,
    _overlap,
    _page_items,
)
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

VERSION = "chandra-archive-study-v1"
ARCHIVE = VisualEvidencePin(run_id=309, **PREDECESSOR)
_FORMULA_POINTER = "#/texts/2550"
_FORMULA_DIGEST = "1508f789b24611a648bac9a83d37c3653bedda12ce78311c8c0fb67351e83b16"
_REVIEW = "incumbent-recovery.md#original-source-witnesses"


def _coords(box):
    return (box.l, box.t, box.r, box.b)


def _exact_region(regions, pointer, kind):
    matches = [row for row in regions if row.kind == kind and row.crop.pointer == pointer]
    if len(matches) != 1:
        raise ValueError(f"archive study lacks a unique reviewed {kind} region at {pointer}")
    return matches[0]


def _entry(item_id, page, kind, box, frame, reading, **evidence):
    left, top, right, bottom = box
    if not (0 <= left < right <= frame[0] and 0 <= top < bottom <= frame[1]):
        raise ValueError(f"archive study witness is outside its physical page: {item_id}")
    return {
        "id": item_id,
        "page_no": page,
        "kind": kind,
        "box": box,
        "frame": frame,
        "reading": reading,
        "witness": _REVIEW,
        **evidence,
    }


def freeze_overlay(conn, source: VisualEvidencePin):
    """Compute the fixed overlay from admitted bytes and the producer's native reader."""
    if source != ARCHIVE:
        raise ValueError("archive study requires the exact reviewed producing PDF pin")
    _, _, original, reader = _load_visual_source(conn, source)
    witness = read_source_witness(original)
    figure = _page_items(conn, source, 108, 108)[0][108]
    table = _page_items(conn, source, 151, 151)[0][151]
    formula = _page_items(conn, source, 416, 416)[0][416]
    upper = _exact_region(figure, "#/pictures/37", "picture")
    lower = _exact_region(figure, "#/pictures/38", "picture")
    caption = _exact_region(table, "#/texts/898", "caption")
    matrix = _exact_region(formula, _FORMULA_POINTER, "formula")
    addresses = (upper.crop.pointer, lower.crop.pointer, caption.crop.pointer, _FORMULA_POINTER)
    items = reader.native_items(addresses)

    caption_box = _coords(witness.caption)
    caption_id = "p108-figure-3.5-caption"
    if upper.frame != lower.frame or any(
        row.kind == "caption" and _matches(row.box, caption_box) for row in figure
    ):
        raise ValueError("archive study shared caption or panel frame differs from review")
    entries = [
        _entry(
            caption_id,
            108,
            "caption",
            caption_box,
            upper.frame,
            {"text": FIGURE_CAPTION, "orig": FIGURE_CAPTION},
        )
    ]
    for index, (panel, box, label) in enumerate(
        zip((upper, lower), witness.panel_boxes, PANEL_LABELS, strict=True), start=1
    ):
        box = _coords(box)
        native = items[panel.crop.pointer]
        meta = native.get("meta") or {}
        if (
            _overlap(panel.box, box) < 0.8 * _area(box)
            or meta.get("tabular_chart", {}).get("title") != label
            or native.get("captions")
        ):
            raise ValueError("archive study panel binding differs from its source witness")
        entries.append(
            _entry(
                f"p108-panel-{index}",
                108,
                "picture",
                box,
                panel.frame,
                {"meta": meta},
                archive_address=panel.crop.model_dump(),
                shared_caption=caption_id,
            )
        )

    table_box = _coords(witness.table_box)
    if (
        items[caption.crop.pointer].get("text") != TABLE_CAPTION
        or not _matches(caption.box, _coords(witness.table_caption))
        or any(row.kind == "table" and _overlap(row.box, table_box) > 0 for row in table)
    ):
        raise ValueError("archive study Table 4.2 locus differs from its source witness")
    entries.append(
        _entry(
            "p151-table-4.2",
            151,
            "table",
            table_box,
            caption.frame,
            {"data": witness.table.model_dump(mode="json", exclude={"grid"})},
            caption_address=caption.crop.model_dump(),
        )
    )

    original_text = items[_FORMULA_POINTER].get("orig")
    if (
        not isinstance(original_text, str)
        or len(original_text) != 515
        or sha256(original_text.encode()).hexdigest() != _FORMULA_DIGEST
    ):
        raise ValueError("archive study readable formula differs from the witnessed spelling")
    entries.append(
        _entry(
            "p416-readable-formula",
            416,
            "formula",
            matrix.box,
            matrix.frame,
            {"text": original_text, "orig": original_text},
            archive_address=matrix.crop.model_dump(),
            orig_digest=_FORMULA_DIGEST,
        )
    )

    body = {
        "version": VERSION,
        "source": source.model_dump(mode="json"),
        "source_release": reader.revision["release_id"],
        "original_sha256": ORIGINAL,
        "recovery_recipe": RECIPE,
        "entries": entries,
    }
    return {**body, "digest": sha256(canonical_bytes(body)).hexdigest()}


def validate_overlay(conn, source, frozen):
    expected = freeze_overlay(conn, source)
    if canonical_bytes(frozen) != canonical_bytes(expected):
        raise ValueError("frozen archive study overlay differs from the original-source witnesses")
    return expected


def study_regions(overlay):
    by_page = defaultdict(list)
    for entry in overlay["entries"]:
        address = entry.get("archive_address")
        by_page[entry["page_no"]].append(
            StudyRegion(
                entry["kind"],
                tuple(entry["box"]),
                tuple(entry["frame"]),
                replaces=VisualRouteCrop.model_validate(address) if address else None,
            )
        )
    return {page: tuple(regions) for page, regions in by_page.items()}


def scoped_entries(overlay, selection):
    """Use the exact archive address for crops and page scope for new occurrences."""
    if overlay is None:
        return ()
    pointer = selection.get("pointer")
    crop = {"pointer": pointer, "region_index": selection.get("region_index")}
    return tuple(
        entry
        for entry in overlay["entries"]
        if entry["page_no"] == selection["page_no"]
        and (pointer is None or entry.get("archive_address") == crop)
    )
