"""Enumerate typed shadow differences for independent source adjudication."""

import argparse
import json
from pathlib import Path

from archive_study import scoped_entries, validate_overlay

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_requests import VisualSelection, _load_selection
from corpus_structure.semantic.visual_routing import _matches, _page_items
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.pdf_visual_evidence import (
    VisualEvidencePin,
    visual_observation_manifest,
)
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


def differences(member, observation, regions, reader, entries=()):
    overlay_by_id = {entry["id"]: entry for entry in entries}
    replaced = [entry.get("archive_address") for entry in entries]
    regions = [part for part in regions if part.crop.model_dump() not in replaced]
    for item in observation.items:
        row = item.model_dump(mode="json", exclude_none=True)
        kind = row["kind"]
        region = item.source_region
        pointer = None
        overlay_id = None
        reason = "additional_typed_field"
        if kind in _STRUCTURES:
            label = "caption" if kind == "caption_candidate" else kind
            if region is None or region.enclosing_occurrence_id is not None:
                reason = "independent_location_missing"
            else:
                box = (region.left, region.top, region.right, region.bottom)
                matches = {
                    (part.crop.pointer, None)
                    for part in regions
                    if part.kind == label and _matches(box, part.box)
                } | {
                    ((entry.get("archive_address") or {}).get("pointer"), entry["id"])
                    for entry in entries
                    if entry["kind"] == label and _matches(box, tuple(entry["box"]))
                }
                if len(matches) != 1:
                    reason = "no_unique_incumbent_location"
                else:
                    ((pointer, overlay_id),) = matches
                    selected = (
                        overlay_by_id[overlay_id]["reading"]
                        if overlay_id is not None
                        else reader.native_items((pointer,))[pointer]
                    )
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
            **({"incumbent_overlay": overlay_id} if overlay_id is not None else {}),
        }


def _arm_scopes(manifest, source):
    return {
        arm: {
            canonical_bytes(VisualSelection.model_validate(dict(scope, source=source)).scope())
            for scope in scopes
        }
        for arm, scopes in manifest["arms"].items()
    }


def _require_retained_member(conn, selection, member):
    mapped = VisualEvidencePin.model_validate(member["mapped"])
    raw = VisualEvidencePin.model_validate(member["raw"])
    manifest = visual_observation_manifest(
        conn,
        selection.source,
        page_no=selection.page_no,
        after_task=mapped.task_id - 1,
        limit=1,
    )
    entry = next(iter(manifest.observations), None)
    if (
        entry is None
        or entry.mapped != mapped
        or entry.raw != raw
        or (entry.pointer, entry.region_index, entry.rotation or 0)
        != (selection.pointer, selection.region_index, selection.rotation or 0)
    ):
        raise ValueError("retained evidence pins or scope differ from the protected observation")
    if selection.pointer is not None:
        _load_selection(conn, selection)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--retained-group",
        type=Path,
        action="append",
        help="Compare an exact previously settled group without starting a provider run.",
    )
    args = parser.parse_args()
    manifest = json.loads((args.manifest or args.campaign / "manifest.json").read_bytes())
    source = manifest["source"]
    pin = VisualEvidencePin.model_validate(source)
    overlay = None
    scopes = {}
    seen = set()
    assessed = set()
    with open_runtime_engine(
        Settings(), "chandra-shadow-comparison", purpose="read"
    ) as engine:
        if "archive_study" in manifest:
            with read_snapshot(engine) as conn:
                overlay = validate_overlay(conn, pin, manifest["archive_study"])
            if (
                overlay["source_release"] != manifest.get("source_release")
                or overlay["original_sha256"] != manifest.get("original_sha256")
            ):
                raise ValueError("frozen study archive release or original differs from its witness")
            scopes = _arm_scopes(manifest, source)
            for arm in scopes:
                print(json.dumps({
                    "arm": arm,
                    "outcome": "incumbent_repairs",
                    "overlay_digest": overlay["digest"],
                    "entries": [entry["id"] for entry in overlay["entries"]],
                }))
        paths = args.retained_group or sorted(args.campaign.glob("group-*.result.json"))
        for path in paths:
            group = json.loads(path.read_bytes())
            if group["source"] != source:
                raise ValueError("group product differs from the frozen comparison")
            for member in group["members"]:
                page = member["selection"]["page_no"]
                selection = VisualSelection.model_validate(member["selection"])
                if selection.source != pin:
                    raise ValueError("group member source differs from the frozen comparison")
                key = canonical_bytes(selection.scope())
                arms = [arm for arm, allowed in scopes.items() if key in allowed]
                if overlay is not None:
                    if key in seen or not arms:
                        raise ValueError("retained group repeats or lies outside a frozen study scope")
                    seen.add(key)
                membership = {"arms": arms} if overlay is not None else {}
                if member["status"] != "source_ready" or member["mapped"] is None:
                    print(json.dumps({
                        "selection": member["selection"], "outcome": "failed", **membership
                    }))
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
                    if overlay is not None:
                        _require_retained_member(conn, selection, member)
                    by_page, _ = _page_items(conn, pin, page, page)
                    request = NativeSourceRequest(
                        **source,
                        page_no=page,
                        pointer=selection.pointer,
                        region_index=selection.region_index,
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
                                        **membership,
                                    }
                                )
                            )
                            break
                        if overlay is not None and (
                            observation.original_artifact_digest != overlay["original_sha256"]
                            or observation.page_no != page
                        ):
                            raise ValueError("retained evidence differs from the frozen original or page")
                        entries = scoped_entries(overlay, member["selection"])
                        for row in differences(
                            member, observation, by_page.get(page, ()), reader, entries
                        ):
                            print(json.dumps({**row, **membership}, ensure_ascii=False))
                            count += 1
                        cursor = response.next_cursor
                        if cursor is None:
                            assessed.add(key)
                            print(
                                json.dumps(
                                    {
                                        "selection": member["selection"],
                                        "outcome": "compared",
                                        "mapped": member["mapped"],
                                        "nominated_differences": count,
                                        "observation_outcome": observation.observation["outcome"],
                                        **membership,
                                    }
                                )
                            )
                            break
    if overlay is not None:
        for arm, allowed in scopes.items():
            print(json.dumps({
                "arm": arm,
                "outcome": "recognition_coverage",
                "selected": len(allowed),
                "compared": len(allowed & assessed),
                "attempted_unavailable": len(allowed & (seen - assessed)),
                "unassessed": len(allowed - seen),
            }))


if __name__ == "__main__":
    main()
