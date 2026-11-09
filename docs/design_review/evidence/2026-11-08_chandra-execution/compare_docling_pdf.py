"""Compare exact native-PDF Chandra trials with the frozen book and legacy evidence."""

import argparse
import io
import json
import math
import re
import subprocess
from collections import Counter
from contextlib import closing
from hashlib import sha256
from itertools import combinations
from pathlib import Path

from docling_core.types.doc import ContentLayer, DocItem, DoclingDocument
from group_shadow_compare import _require_campaign_group, differences
from PIL import Image
from pypdfium2 import PdfDocument
from sqlalchemy import select

from corpus_structure.ingest.pdf_chandra import parse_chandra_response
from corpus_structure.ingest.pdf_hierarchy import native_nodes
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.pdf_visual_mapping import map_visual_result
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_requests import (
    VisualSelection,
    _load_visual_source,
    _open_observation,
)
from corpus_structure.semantic.visual_routing import _page_items, _pin_columns
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin, VisualEvidenceRead
from corpus_structure.settings import Settings

_AUTHOR_DIRECTORY = (
    Path(__file__).resolve().parents[3]
    / "statistics_corpus/corpus/grinstead_snell/latex_source"
)


def _digest(content):
    return sha256(content).hexdigest()


def _pixels(content):
    with Image.open(io.BytesIO(content)) as image, image.convert("RGB") as rgb:
        return rgb.size, _digest(rgb.tobytes())


def _checked_bytes(path, expected):
    value = path.read_bytes()
    if _digest(value) != expected:
        raise ValueError(f"content digest differs for {path}")
    return value


def _legacy_members(conn, campaign, manifest_bytes, manifest, source, pages):
    """Read only matching protected whole-page receipts from the frozen campaign."""
    for path in sorted((campaign / "groups").glob("group-*.result.json")):
        group = json.loads(path.read_bytes())
        wanted = [
            member
            for member in group["members"]
            if member["selection"]["page_no"] in pages and not member["selection"].get("pointer")
        ]
        if not wanted:
            continue
        _require_campaign_group(conn, manifest, _digest(manifest_bytes), source, path, group)
        for member in wanted:
            selection = VisualSelection.model_validate(member["selection"])
            if selection.source != source or member["run_id"] != group["run_id"]:
                raise ValueError("legacy member differs from its source or managed run")
            yield selection, member


def _nemotron_inputs(conn, source, page_nos):
    products, inputs, tasks, bodies = map(
        table, ("ops.pdf_product", "ops.pdf_product_input", "ops.task", "ops.pdf_product_body")
    )
    observation = bodies.c.descriptor["observation"]
    page = observation["image"]["page_no"].as_integer()
    role = observation["pass_role"].as_string()
    rows = conn.execute(
        select(
            *_pin_columns(tasks, products),
            page.label("page_no"),
            role.label("pass_role"),
            observation["outcome"].as_string().label("outcome"),
            observation["finish_reason"].as_string().label("finish_reason"),
            observation["raw_response_digest"].as_string().label("raw_response_digest"),
        )
        .select_from(inputs)
        .join(
            products,
            (products.c.task_id == inputs.c.input_task_id)
            & (products.c.product_key == inputs.c.input_product_key)
            & (products.c.content_digest == inputs.c.input_content_digest),
        )
        .join(tasks, tasks.c.id == products.c.task_id)
        .join(
            bodies,
            (bodies.c.task_id == products.c.task_id)
            & (bodies.c.product_key == products.c.product_key),
        )
        .where(
            inputs.c.task_id == source.task_id,
            inputs.c.product_key == source.product_key,
            inputs.c.role == "recognition",
            page.in_(page_nos),
            role.in_(("A", "B", "C")),
        )
        .order_by(inputs.c.input_index)
    ).mappings()
    by_page = {page_no: [] for page_no in page_nos}
    for row in rows:
        by_page[row["page_no"]].append(dict(row))
    return by_page


def _tables(document):
    return [table.data.model_dump(mode="json") for table in document.tables]


def _table_witnesses(original_pdf, page):
    """Use Poppler's independent positioned columns to establish selected book literals."""
    if page not in {151, 398, 508, 509, 510}:
        return ()
    lines = [
        line.split()
        for line in subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(original_pdf), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    ]
    numeric = re.compile(r"-?(?:\d+|\d*\.\d+)")
    if page == 151:
        rows = [row for row in lines if len(row) == 3 and "/60" in row[1]]
        if rows != [["0", "40/60", "10/60"], ["1", "7/60", "3/60"]]:
            raise ValueError("source does not contain the independently checked p151 fractions")
        expected = {
            (r + 2, c + 1): value for r, row in enumerate(rows) for c, value in enumerate(row)
        }
        expected.update({(0, 2): "S", (1, 2): "0", (1, 3): "1", (2, 0): "C"})
        return (("C/S and joint fractions", (4, 4), expected, {(0, 2): (1, 4), (2, 0): (4, 1)}),)
    if page == 398:
        rows = [row for row in lines if len(row) == 13 and all(map(numeric.fullmatch, row))]
        if len(rows) != 20 or rows[6][4] != "2":
            raise ValueError("source does not contain the independently checked p398 grid")
        expected = {(r + 1, c): value for r, row in enumerate(rows) for c, value in enumerate(row)}
        expected[(0, 12)] = "Profit"
        return (("Profit and all data anchors", (21, 13), expected, {}),)
    if page == 508:
        rows = [row for row in lines if len(row) == 11 and all(map(numeric.fullmatch, row))]
        headers = next(row for row in lines if row == [f".{i:02d}" for i in range(10)])
        if len(rows) != 40 or rows[9][5] != ".3264":
            raise ValueError("source does not contain the independently checked p508 grid")
        grid = [["", *headers], *rows]
        expected = {(r, c): value for r, row in enumerate(grid) for c, value in enumerate(row)}
        return (("Normal table grid", (41, 11), expected, {}),)
    if page == 509:
        rows = [
            row for row in lines
            if row and re.fullmatch(r"(?:6[4-9]|7[0-2])\.5", row[0]) and len(row) == 18
        ]
        if len(rows) != 9:
            raise ValueError("source does not contain the independently checked p509 rows")
        return (("Sideways table values in printed row order", None, rows, {}),)
    rows = [row for row in lines if len(row) == 8 and all(map(numeric.fullmatch, row))]
    first = ["0", "100000", "100000", "100000", "43", "94707", "92840", "96626"]
    if len(rows) != 43 or rows[0] != first:
        raise ValueError("source does not contain the independently checked p510 grid")
    expected = {(r + 2, c): value for r, row in enumerate(rows) for c, value in enumerate(row)}
    return (("Life table data", (45, 8), expected, {}),)


def _table_score(tables, witness):
    name, shape, wanted, spans = witness
    alternatives = []
    for table_data in tables:
        cells = table_data["table_cells"]
        if shape and (table_data["num_rows"], table_data["num_cols"]) != shape:
            continue
        anchors = {}
        for cell in cells:
            pos = cell["start_row_offset_idx"], cell["start_col_offset_idx"]
            anchors.setdefault(pos, []).append(cell)
        expected = wanted
        if shape is None:
            expected = {}
            for source_row, row in enumerate(wanted):
                label, *values = row
                choices = [
                    position for position, group in anchors.items()
                    if position[1] == 0 and len(group) == 1 and group[0]["text"].strip() == label
                ]
                row_number = choices[0][0] if len(choices) == 1 else -1 - source_row
                expected.update({(row_number, c + 1): value for c, value in enumerate(values)})
        mismatches = []
        for position, value in expected.items():
            group = anchors.get(position, ())
            found = [cell["text"].strip() for cell in group]
            if found != [value]:
                mismatches.append({"row_col": position, "expected": value, "found": found})
            elif position in spans and (
                group[0]["end_row_offset_idx"], group[0]["end_col_offset_idx"]
            ) != spans[position]:
                mismatches.append({"row_col": position, "expected_span_end": spans[position]})
        alternatives.append(
            {
                "expected_anchors": len(expected),
                "mismatch_count": len(mismatches),
                "examples": mismatches[:10],
                "row_header_flags": sum(cell["row_header"] for cell in cells),
                "column_header_flags": sum(cell["column_header"] for cell in cells),
                **(
                    {
                        "independent_header_binding": "unqualified",
                        "distinct_below_and_62_2": {"Below", "62.2"}.issubset(
                            {cell["text"].strip() for cell in cells if cell["column_header"]}
                        ),
                        "totals_literals_present": {"928", "205"}.issubset(
                            {cell["text"].strip() for cell in cells}
                        ),
                    }
                    if shape is None
                    else {}
                ),
            }
        )
    if not alternatives:
        return {"witness": name, "outcome": "missing_qualified_shape", "expected_shape": shape}
    result = min(alternatives, key=lambda value: value["mismatch_count"])
    return {
        "witness": name,
        "outcome": "mismatch" if result["mismatch_count"] else "all_checked_anchors_agree",
        **result,
    }


def _graph(document):
    """Preserve candidate types and lineage without equating regenerated text to source truth."""
    nodes = native_nodes(document)
    labels = Counter()
    controls = []
    for pointer, node in nodes.items():
        label = node.label.value
        labels[label] += 1
        if label in {
            "caption", "code", "field_region", "formula", "page_header", "page_footer", "picture",
            "section_header", "title",
        }:
            row = node.model_dump(mode="json", exclude_none=True)
            if label == "picture":
                row.pop("image", None)
            controls.append({"pointer": pointer, **row})
    return {"labels": dict(labels), "controls": controls, "tables": _tables(document)}


def _text_witnesses(document, page):
    nodes = tuple(native_nodes(document).values())
    if page == 506:
        body = [
            node.self_ref
            for node in nodes
            if isinstance(node, DocItem) and node.content_layer == ContentLayer.BODY
        ]
        return {"control": "verified blank body", "candidate_body_items": body}
    if page == 507:
        heading = [
            node.self_ref for node in nodes
            if node.label.value in {"title", "section_header"}
            and getattr(node, "text", "").strip() == "Appendices"
        ]
        return {"control": "Appendices heading", "exact_heading_candidates": heading}
    if page in {108, 301}:
        printed_ids = ("3.5",) if page == 108 else ("7.2", "7.3")
        return {
            "control": "printed figure captions and candidate picture associations",
            "printed_ids": printed_ids,
            "exact_caption_candidates": {
                printed_id: [
                    node.self_ref for node in nodes
                    if node.label.value == "caption" and re.search(
                        rf"\bFigure\s+{re.escape(printed_id)}\b", node.text, re.IGNORECASE
                    )
                ] for printed_id in printed_ids
            },
            "picture_captions": {
                picture.self_ref: [ref.cref for ref in picture.captions]
                for picture in document.pictures
            },
        }
    if page != 416:
        return None
    author = (_AUTHOR_DIRECTORY / "ch11.tex").read_text()
    section = author.split("compute the successive powers", 1)[1].split(
        r"\label{table 11.1}", 1
    )[0]
    decimals = re.compile(r"(?<![\d.])0?\.(\d{3})(?!\d)")
    expected = decimals.findall(section)
    if len(expected) != 54:
        raise ValueError("author source matrix witness no longer contains six sets of nine values")
    formulas = [
        node.text for node in nodes
        if node.label.value == "formula"
        and all(name in node.text for name in ("Rain", "Nice", "Snow"))
    ]
    numbers = [value for formula in formulas for value in decimals.findall(formula)]
    return {
        "control": "six author matrix literal readings",
        "matrix_candidate_count": len(formulas),
        "expected_literals": len(expected),
        "candidate_literals": len(numbers),
        "ordered_numeric_literals_agree": numbers == expected,
        "positioned_interpretation": "unqualified",
    }


def _page_trial(directory, page, original_digest):
    root = directory / "pages" / str(page)
    receipt = json.loads((root / "receipt.json").read_bytes())
    if (
        receipt["original_sha256"] != original_digest
        or receipt["page_no"] != page
        or receipt["batch_page_nos"].count(page) != 1
    ):
        raise ValueError(f"wrong page or duplicate submission for {root}")
    payloads = {
        name: _checked_bytes(root / name, receipt["files"][name])
        for name in ("submitted.png", "response.html", "prediction.json", "document.json")
    }
    dimensions, pixel_digest = _pixels(payloads["submitted.png"])
    frame = receipt["frame"]
    if dimensions != (frame["width"], frame["height"]):
        raise ValueError(f"decoded image differs from the frame in {root}")
    prediction = json.loads(payloads["prediction.json"])
    raw = payloads["response.html"].decode()
    replay = parse_chandra_response(
        raw, image_size=dimensions, page_no=page, stop_reason=prediction["stop_reason"]
    )
    typed = DoclingDocument.model_validate_json(payloads["document.json"])
    return (
        receipt,
        pixel_digest,
        _digest(payloads["response.html"]),
        replay,
        typed,
        prediction,
    )


def _source_projection(conn, pin, page, observation, frame):
    reference = ProductReference(pin.task_id, pin.product_key, pin.content_digest)
    reader = published_record_reader(conn, reference)
    if reader is None:
        raise ValueError(f"published source does not match {pin}")
    body, furniture = _page_items(conn, pin, page, page)
    selected = [*body[page], *furniture[page]]
    same_frame = [
        region
        for region in selected
        if all(math.isclose(a, b, abs_tol=1e-5) for a, b in zip(region.frame, frame, strict=True))
    ]
    cache = {}

    def read_item(pointer):
        if pointer not in cache:
            cache[pointer] = reader.native_items((pointer,))[pointer]
        return cache[pointer]

    candidates = differences(
        {"selection": {"page_no": page}, "mapped": None}, observation, same_frame, read_item
    )
    changed = [
        {
            "reason": row["reason"],
            "candidate": row["candidate"]["occurrence_id"],
            "kind": row["candidate"]["kind"],
            "incumbent_pointer": row["incumbent_pointer"],
        }
        for row in candidates
    ]
    tables = [
        read_item(pointer)["data"]
        for pointer in dict.fromkeys(r.crop.pointer for r in selected if r.kind == "table")
    ]
    return {
        "pin": pin.model_dump(),
        "located_labels": dict(Counter(r.kind for r in selected)),
        "candidate_deltas": changed,
        "tables": tables,
    }


def _observation(typed, original, page, frame):
    with PdfDocument(original) as pdf, closing(pdf[page - 1]) as physical:
        # Frame comparability here covers only the simple book media frame. The
        # independent rotated landmark qualification belongs to the producer.
        if (
            physical.get_rotation()
            or physical.get_bbox() != physical.get_mediabox()
            or physical.get_mediabox()[:2] != (0, 0)
            or physical.get_size() != frame
            or tuple(typed.pages) != (1,)
        ):
            return None
    width, height = frame
    projection = map_visual_result(
        typed,
        page_no=1,
        transform={"affine": [1, 0, 0, 1, 0, 0], "page_width": width, "page_height": height},
        image_size=(int(width), int(height)),
    )
    return VisualEvidenceRead(
        page_no=page,
        original_artifact_digest=_digest(original),
        original_regions=[],
        submitted_region=None,
        observation_release_id="native-pdf-trial",
        observation={},
        mapping_availability="available",
        items=projection.rows,
    )


def _paired_timing(legacy, native, requested):
    def scope(receipt):
        return [
            page
            for row in receipt["sessions"]
            if row["exit_code"] == 0
            for page in range(row["first"], row["last"] + 1)
        ]

    if scope(legacy) != sorted(requested) or scope(native) != sorted(requested):
        return None
    former, newer = (
        sum(session["wall_seconds"] for session in receipt["sessions"])
        for receipt in (legacy, native)
    )
    return {
        "legacy_seconds": former,
        "native_seconds": newer,
        "native_savings_seconds": round(former - newer, 3),
        "boundary": "worker launch, capture and shared GPU handoff; excludes protected publication",
    }


def _matched_legacy(timing_path, timing):
    """Read the detached matched timing arm separately from protected legacy observations."""
    pages = {}
    for session in timing["sessions"]:
        if session["exit_code"] != 0:
            continue
        root = timing_path.parent / f"run-{session['first']}"
        rows = json.loads((root / "report.json").read_bytes())["pages"]
        if [row["page_no"] for row in rows] != list(range(session["first"], session["last"] + 1)):
            raise ValueError(f"matched legacy scope differs from its timing receipt in {root}")
        for row in rows:
            page = row["page_no"]
            if page in pages:
                raise ValueError(f"matched legacy arm repeats physical page {page}")
            output = root / str(page)
            size, pixels = _pixels(_checked_bytes(output / "submitted.png", row["frame_sha256"]))
            raw = (output / "response.html").read_bytes()
            prediction = json.loads((output / "prediction.json").read_bytes())
            if prediction["text"].encode() != raw or prediction["stop_reason"] != row["stop"]:
                raise ValueError(f"matched legacy response differs from prediction for page {page}")
            parsed = parse_chandra_response(
                raw.decode(), image_size=size, page_no=page, stop_reason=row["stop"]
            )
            pages[page] = (pixels, _digest(raw), parsed, row)
    return pages


def _arm_deltas(trials):
    for left, right in combinations(trials, 2):
        by_page = {row["page_no"]: row for row in right["pages"]}
        for first in left["pages"]:
            second = by_page.get(first["page_no"])
            if second is None:
                continue
            yield {
                "left": left["directory"],
                "right": right["directory"],
                "page_no": first["page_no"],
                "same_rgb_pixels": first["rgb_sha256"] == second["rgb_sha256"],
                "same_response_html": first["raw_sha256"] == second["raw_sha256"],
                "same_typed_graph": first["typed"] == second["typed"],
                "left_source_witnesses": first["source_witnesses"],
                "right_source_witnesses": second["source_witnesses"],
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path, help="Exact incumbent shadow campaign directory")
    parser.add_argument("original_pdf", type=Path, help="Exact PDF bytes passed to native Docling")
    parser.add_argument("trial", nargs="+", type=Path, help="Native Docling trial directories")
    parser.add_argument("--legacy-timing", type=Path, help="Fresh matched legacy timing receipt")
    args = parser.parse_args()

    manifest_bytes = (args.campaign / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    source = VisualEvidencePin.model_validate(manifest["source"])
    standard = VisualEvidencePin.model_validate(manifest["structural_input"])
    disk_pdf = _checked_bytes(args.original_pdf, manifest["original_sha256"])
    directories = [
        (directory, json.loads((directory / "report.json").read_bytes()))
        for directory in args.trial
    ]
    page_numbers = {
        int(path.name)
        for directory, _ in directories
        for path in (directory / "pages").iterdir()
        if path.is_dir() and path.name.isdecimal() and (path / "receipt.json").is_file()
    }
    report = {"source": source.model_dump(), "original_sha256": _digest(disk_pdf), "trials": []}
    matched_legacy = {}
    if args.legacy_timing is not None:
        timing = json.loads(args.legacy_timing.read_bytes())
        if (
            timing["source"] != report["source"]
            or timing["original_sha256"] != report["original_sha256"]
        ):
            raise ValueError("matched legacy timing differs from the frozen source")
        report["legacy_timing"] = timing
        matched_legacy = _matched_legacy(args.legacy_timing, timing)
    with (
        open_runtime_engine(Settings(), "chandra-pdf-trial-comparison", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        project, _, original, reader = _load_visual_source(conn, source)
        if disk_pdf != original or reader.revision["release_id"] != manifest["source_release"]:
            raise ValueError("trial original or archived release differs from the frozen book")
        legacy = {}
        for selection, member in _legacy_members(
            conn, args.campaign, manifest_bytes, manifest, source, page_numbers
        ):
            if member["raw"] is None:
                continue
            pin = VisualEvidencePin.model_validate(member["raw"])
            body, raster, raw = _open_observation(conn, pin, project, selection)
            size, pixels = _pixels(raster)
            parsed = parse_chandra_response(
                raw.decode(), image_size=size, page_no=selection.page_no,
                stop_reason=body["observation"].get("finish_reason"),
            )
            legacy[selection.page_no] = (member, pixels, _digest(raw), parsed.document)
        nemotron = _nemotron_inputs(conn, source, page_numbers)
        for directory, summary in directories:
            if summary["original_sha256"] != report["original_sha256"]:
                raise ValueError(f"trial original differs from the frozen PDF in {directory}")
            assembled = DoclingDocument.model_validate_json(
                _checked_bytes(directory / "document.json", summary["document_sha256"])
            )
            numbers = sorted(
                int(path.name)
                for path in (directory / "pages").iterdir()
                if path.is_dir() and path.name.isdecimal() and (path / "receipt.json").is_file()
            )
            if (
                numbers != summary["typed_page_nos"]
                or sorted(assembled.pages) != summary["assembled_page_nos"]
            ):
                raise ValueError(f"physical page coverage differs from its receipts in {directory}")
            first, last = summary["page_range"]
            requested = set(range(first, last + 1))
            if not set(numbers).issubset(requested) or not set(assembled.pages).issubset(requested):
                raise ValueError(f"out-of-scope physical page evidence in {directory}")
            trial = {
                "directory": str(directory),
                "report": summary,
                "unavailable_typed_pages": sorted(requested - set(numbers)),
                "unavailable_assembled_pages": sorted(requested - set(assembled.pages)),
                "pages": [],
            }
            timing_path = directory.parent / "timing.json"
            if "legacy_timing" in report and timing_path.exists():
                native_timing = json.loads(timing_path.read_bytes())
                if (
                    native_timing["source"] != report["source"]
                    or native_timing["original_sha256"] != report["original_sha256"]
                ):
                    raise ValueError(f"native timing differs from the frozen source in {directory}")
                trial["matched_timing"] = _paired_timing(
                    report["legacy_timing"], native_timing, requested
                )
            for page in numbers:
                receipt, pixels, raw, replay, typed, prediction = _page_trial(
                    directory, page, report["original_sha256"]
                )
                dimensions = receipt["frame"]
                frame = dimensions["page_width"], dimensions["page_height"]
                observation = _observation(typed, original, page, frame)
                result = {
                    "page_no": page,
                    "page_receipt_sha256": _digest(
                        (directory / "pages" / str(page) / "receipt.json").read_bytes()
                    ),
                    "batch_page_nos": receipt["batch_page_nos"],
                    "frame": dimensions,
                    "rgb_sha256": pixels,
                    "raw_sha256": raw,
                    "prediction": prediction,
                    "parse_status": replay.status.value,
                    "completion": replay.completion.value,
                    "parse_issues": list(replay.issues),
                    "nemotron_inputs": nemotron[page],
                    "typed": _graph(typed),
                    "comparison_standing": "attributed_candidates",
                }
                witnesses = _table_witnesses(args.original_pdf, page)
                result["source_witnesses"] = [
                    _table_score(result["typed"]["tables"], witness) for witness in witnesses
                ]
                result["text_witnesses"] = _text_witnesses(typed, page)
                if page in matched_legacy:
                    old_pixels, old_raw, old_parse, timing = matched_legacy[page]
                    old_graph = _graph(old_parse.document) if old_parse.document else None
                    result["legacy_matched_trial"] = {
                        "standing": "detached_timing_control",
                        "same_rgb_pixels": pixels == old_pixels,
                        "same_response_html": raw == old_raw,
                        "completion": old_parse.completion.value,
                        "parse_status": old_parse.status.value,
                        "timing": timing,
                        "labels": old_graph["labels"] if old_graph else None,
                        "source_witnesses": [
                            _table_score(old_graph["tables"], witness) for witness in witnesses
                        ] if old_graph else [],
                    }
                if page in legacy:
                    member, old_pixels, old_raw, old_doc = legacy[page]
                    old_graph = _graph(old_doc) if old_doc is not None else None
                    result["legacy"] = {
                        "raw": member["raw"],
                        "mapped": member["mapped"],
                        "same_rgb_pixels": pixels == old_pixels,
                        "same_response_html": raw == old_raw,
                        "same_typed_table_fields": old_graph is not None
                        and canonical_bytes(old_graph["tables"])
                        == canonical_bytes(result["typed"]["tables"]),
                        "labels": old_graph["labels"] if old_graph else None,
                        "source_witnesses": [
                            _table_score(old_graph["tables"], witness) for witness in witnesses
                        ] if old_graph else [],
                    }
                if observation is not None:
                    for name, pin in (("selected", source), ("standard", standard)):
                        comparison = _source_projection(conn, pin, page, observation, frame)
                        tables = comparison.pop("tables")
                        comparison["source_witnesses"] = [
                            _table_score(tables, witness) for witness in witnesses
                        ]
                        result[name] = comparison
                else:
                    result["geometric_comparison"] = "frame_unqualified"
                trial["pages"].append(result)
            report["trials"].append(trial)
    report["native_arm_deltas"] = list(_arm_deltas(report["trials"]))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
