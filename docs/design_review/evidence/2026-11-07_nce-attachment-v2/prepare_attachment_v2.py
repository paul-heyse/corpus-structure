"""Prepare the two retained attachment units for independent v2 authoring."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import replace
from pathlib import Path
from runpy import run_path

from corpus_structure.evaluate.operation_assessment import decode_frame, encode_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

GUIDELINE = "nce12-attachment-guide-2"
RUBRIC = "nce12-attachment-role-direction-scope-2"
VIEWS = (113, 124)
SOURCE = Path(__file__).resolve().parent.parent / "2026-11-07_nce07-12"
capture = run_path(str(SOURCE / "freeze_attachment_frame.py"))["capture"]


def native_sections(conn, view, events):
    pointers = {
        re.sub(r"/data/table_cells/[0-9]+$", "", anchor["pointer"])
        for event in events
        for anchors in event["endpoints"].values()
        for anchor in anchors
    }
    source = load_source_view(conn, view, analysis=False)
    items = {item["self_ref"]: item for item in (*source.items, *source.ancestors)}
    sections = {}
    for pointer in sorted(pointers):
        current = pointer
        visited = set()
        while current != "#/body":
            if current in visited or current not in items:
                raise ValueError("attachment authoring lacks exact native section custody")
            visited.add(current)
            item = items[current]
            if item.get("label") in {"section", "chapter"}:
                break
            current = item["parent"]["$ref"]
        sections[pointer] = current
    return sections


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("view_113_count", type=int)
    parser.add_argument("view_124_count", type=int)
    args = parser.parse_args()
    frames, packets = {}, {}
    sampling = {
        "seed": 0,
        "strata": {},
        "inclusion_probabilities": {},
        "provenance": {"selection": "two purposive complete retained source views"},
        "cohort": "gs120-attachment-development-v2",
    }
    with (
        open_runtime_engine(Settings(), "nce12-attachment-v2-freeze", purpose="evaluate") as engine,
        read_snapshot(engine) as conn,
    ):
        for view, expected in zip(VIEWS, (args.view_113_count, args.view_124_count), strict=True):
            retained = capture(conn, view, expected)
            packet = retained["author_packet"]
            unit = packet["unit"]
            frame = replace(
                decode_frame(packet["frame"]), guideline_version=GUIDELINE, rubric_version=RUBRIC
            )
            packet["frame"] = encode_frame(frame)
            packet["native_section_by_pointer"] = native_sections(conn, view, packet["events"])
            frames[unit], packets[view] = packet["frame"], packet
            sampling["strata"][unit] = "one-full-source-view"
            sampling["inclusion_probabilities"][unit] = 1
    args.destination.mkdir(parents=True, exist_ok=False)
    write(args.destination / "sample.json", {"sampling": sampling, "frames": frames})
    for view, packet in packets.items():
        write(args.destination / f"frame-{view}.json", packet["frame"])
        write(args.destination / f"author-{view}.json", packet)
    print(json.dumps({"source_run_id": 161, "source_cut_id": 245, "events": {
        view: len(packet["events"]) for view, packet in packets.items()
    }}))


if __name__ == "__main__":
    main()
