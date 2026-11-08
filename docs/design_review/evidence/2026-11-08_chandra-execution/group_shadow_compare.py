"""Enumerate typed shadow differences for independent source adjudication."""

import argparse
import json
from pathlib import Path

from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_routing import _matches, _page_items
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.settings import Settings

_STRUCTURES = {"picture", "table", "caption", "caption_candidate", "formula"}
_CELL_FIELDS = (
    "start_row_offset_idx",
    "end_row_offset_idx",
    "start_col_offset_idx",
    "end_col_offset_idx",
    "column_header",
    "row_header",
    "text",
)


def signature(item):
    def text(value):
        return " ".join((value or "").split())

    data = item.get("data", item)
    cells = data.get("table_cells", data.get("cells"))
    if cells is not None:
        return (
            data["num_rows"],
            data["num_cols"],
            sorted(
                tuple(
                    text(cell.get(key))
                    if key == "text"
                    else cell.get(key, False)
                    for key in _CELL_FIELDS
                )
                for cell in cells
            ),
        )
    literal = item.get("text")
    return text(literal), text(item.get("orig", item.get("original_text", literal)))


def differences(member, observation, regions, reader):
    for item in observation.items:
        row = item.model_dump(mode="json", exclude_none=True)
        kind = row["kind"]
        region = item.source_region
        pointer = None
        reason = "additional_typed_field"
        if kind in _STRUCTURES:
            label = "caption" if kind == "caption_candidate" else kind
            if region is None or region.enclosing_occurrence_id is not None:
                reason = "independent_location_missing"
            else:
                matches = {
                    part.crop.pointer
                    for part in regions
                    if part.kind == label
                    and _matches((region.left, region.top, region.right, region.bottom), part.box)
                }
                if len(matches) != 1:
                    reason = "no_unique_incumbent_location"
                else:
                    (pointer,) = matches
                    selected = reader.native_items((pointer,))[pointer]
                    if kind == "picture":
                        reason = "picture_metadata_differs"
                        if row.get("metadata") == selected.get("meta"):
                            continue
                    elif signature(row) == signature(selected):
                        if kind not in {"caption", "caption_candidate"} or not (
                            row.get("parser_attachment_occurrence_ids")
                            or row.get("associated_picture_occurrence_ids")
                        ):
                            continue
                        reason = "caption_association_requires_witness"
                    else:
                        reason = "typed_reading_differs"
        yield {
            "selection": member["selection"],
            "evidence": member["mapped"],
            "incumbent_pointer": pointer,
            "reason": reason,
            "candidate": row,
            "disposition": "source_review_pending",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.campaign / "manifest.json").read_bytes())
    source = manifest["source"]
    pin = VisualEvidencePin.model_validate(source)
    with open_runtime_engine(
        Settings(), "chandra-shadow-comparison", purpose="read"
    ) as engine:
        for path in sorted(args.campaign.glob("group-*.result.json")):
            group = json.loads(path.read_bytes())
            if group["source"] != source:
                raise ValueError("group product differs from the frozen comparison")
            for member in group["members"]:
                page = member["selection"]["page_no"]
                if member["status"] != "source_ready" or member["mapped"] is None:
                    print(json.dumps({"selection": member["selection"], "outcome": "failed"}))
                    continue
                with read_snapshot(engine) as conn:
                    release = open_release(conn, manifest.get("source_release") or manifest["semantic_release"])
                    reader = published_record_reader(
                        conn,
                        ProductReference(pin.task_id, pin.product_key, pin.content_digest),
                        projection_context=release,
                    )
                    if reader is None:
                        raise ValueError("frozen comparator is not readable")
                    by_page, _ = _page_items(conn, pin, page, page)
                    request = NativeSourceRequest(
                        **source,
                        page_no=page,
                        evidence=member["mapped"],
                        view="visual_evidence",
                        max_bytes=8 * 1024 * 1024,
                        limit=1000,
                    )
                    count = 0
                    cursor = None
                    while True:
                        response = inspect_native_source(
                            conn, request.model_copy(update={"cursor": cursor})
                        )
                        observation = response.visual_evidence
                        if observation is None or observation.mapping_availability != "available":
                            print(
                                json.dumps(
                                    {
                                        "selection": member["selection"],
                                        "outcome": "unavailable",
                                        "reader_outcome": response.outcome,
                                    }
                                )
                            )
                            break
                        for row in differences(member, observation, by_page.get(page, ()), reader):
                            print(json.dumps(row, ensure_ascii=False))
                            count += 1
                        cursor = response.next_cursor
                        if cursor is None:
                            print(
                                json.dumps(
                                    {
                                        "selection": member["selection"],
                                        "outcome": "compared",
                                        "mapped": member["mapped"],
                                        "nominated_differences": count,
                                        "observation_outcome": observation.observation["outcome"],
                                    }
                                )
                            )
                            break


if __name__ == "__main__":
    main()
