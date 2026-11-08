"""Freeze a 518-page comparison from complete managed v2 dry route reports."""

import argparse
import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from archive_study import freeze_overlay, study_regions

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_requests import VisualSelection
from corpus_structure.semantic.visual_routing import VisualRouteReport, read_visual_routes
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.settings import Settings

_ORIGINAL = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"
_PAGE_COUNT = 518
_RECOGNITION = {
    "missing_structure",
    "incomplete_request",
    "incomplete_ocr_region",
    "located_disagreement",
    "omitted_crop",
}


def _read_routes(directory: Path, source: VisualEvidencePin, overlay):
    for start in range(1, _PAGE_COUNT + 1, 64):
        data = json.loads((directory / f"{start}.json").read_bytes())
        if overlay:
            if data.get("study_overlay_digest") != overlay["digest"]:
                raise ValueError(f"book dry route range {start} differs from the frozen overlay")
            data = data["report"]
        report = VisualRouteReport.model_validate(data)
        expected = list(range(start, min(start + 64, _PAGE_COUNT + 1)))
        if (
            report.source != source
            or report.policy != "chandra-dry-routing-v2"
            or report.page_count != _PAGE_COUNT
            or [row.page_no for row in report.pages] != expected
        ):
            raise ValueError(f"book dry route range {start} does not match the frozen comparator")
        yield report


def _capture_routes(directory: Path, source: VisualEvidencePin, *, archive_overlay: bool):
    """Run the CLI's bounded owner using one read engine and one source snapshot."""
    directory.mkdir(exist_ok=False)
    with (
        open_runtime_engine(Settings(), "chandra-book-freeze", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        overlay = freeze_overlay(conn, source) if archive_overlay else None
        study = study_regions(overlay) if overlay else None
        for start in range(1, _PAGE_COUNT + 1, 64):
            report = read_visual_routes(conn, source, first=start, limit=64, study_regions=study)
            data = (
                json.dumps(
                    {
                        "study_overlay_digest": overlay["digest"],
                        "report": report.model_dump(mode="json"),
                    }
                )
                if overlay
                else report.model_dump_json()
            )
            (directory / f"{start}.json").write_text(data)
        return overlay


def _sample(pages, prior_controls: set[int]) -> dict[str, list[int]]:
    strata: dict[str, set[int]] = defaultdict(set)
    for row in pages:
        if row.page_no not in prior_controls:
            for reason in row.reasons:
                strata[f"{row.action}/{reason.kind or reason.code}"].add(row.page_no)
    return {
        key: sorted(
            sorted(
                numbers,
                key=lambda page: sha256(f"chandra-held-out-v1:{_ORIGINAL}:{page}".encode()).digest(),
            )[:3]
        )
        for key, numbers in sorted(strata.items())
    }


def _selection(page: int, **scope) -> dict[str, Any]:
    return {"page_no": page, **scope}


def _deduplicate(source: VisualEvidencePin, values):
    unique = {}
    for value in values:
        selection = VisualSelection.model_validate(dict(value, source=source))
        unique[canonical_bytes(selection.scope())] = value
    return list(unique.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=int)
    parser.add_argument("pin", type=Path)
    parser.add_argument("ranges", type=Path)
    parser.add_argument("semantic_release")
    parser.add_argument("realization")
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--read-live", action="store_true")
    parser.add_argument(
        "--archive-overlay",
        action="store_true",
        help="Read live and freeze the witnessed, study-only view of the sealed archive.",
    )
    args = parser.parse_args()

    source = VisualEvidencePin.model_validate(
        dict(json.loads(args.pin.read_bytes()), run_id=args.run)
    )
    overlay = None
    if args.read_live or args.archive_overlay:
        overlay = _capture_routes(args.ranges, source, archive_overlay=args.archive_overlay)
    reports = list(_read_routes(args.ranges, source, overlay))
    if any(report.structural_input != reports[0].structural_input for report in reports):
        raise ValueError("the comparator's admitted Standard input changed across routing ranges")
    pages = [page for report in reports for page in report.pages]
    all_page = [_selection(page.page_no) for page in pages]
    selective = []
    sideways = None
    for page in pages:
        if page.action != "recognize":
            continue
        for reason in page.reasons:
            if reason.code not in _RECOGNITION:
                continue
            if reason.crop is None:
                selective.append(_selection(page.page_no))
                continue
            scope = reason.crop.model_dump()
            if page.page_no == 509 and reason.kind == "table":
                # The prior source-qualified control established this quarter turn.
                # The locator itself must come from the new comparator's dry route.
                scope["rotation"] = 90
                sideways = _selection(page.page_no, **scope)
            selective.append(_selection(page.page_no, **scope))
    explicit = [_selection(page) for page in (108, 151, 416, 509)]
    if sideways:
        explicit.append(sideways)
    known = json.loads(
        (Path(__file__).parent.parent / "2026-11-08_chandra-post-nemotron" / "cases.json").read_bytes()
    )
    if known["source_sha256"] != _ORIGINAL:
        raise ValueError("source witnesses belong to another original")
    controls = set(map(int, known["pages"])) | {1, 4, 119}
    manifest = {
        "source": source.model_dump(),
        "original_sha256": _ORIGINAL,
        "semantic_release": args.semantic_release,
        "realization": args.realization,
        "artifacts": str(args.artifacts),
        "policy": reports[0].policy,
        "structural_input": reports[0].structural_input.model_dump()
        if reports[0].structural_input
        else None,
        "arms": {
            "incumbent_only": [],
            "explicit": _deduplicate(source, explicit),
            "selective": _deduplicate(source, selective),
            "all_page_shadow": all_page,
        },
        "known_development_controls": sorted(controls),
        "prior_agreement_control": {
            "page_no": 327,
            "item": "Table 8.1",
            "source_review": "../2026-11-08_nce-full-book/review/pages-174-346.md",
        },
        "held_out": _sample(pages, controls),
        "selections": _deduplicate(source, all_page + selective + explicit),
    }
    if overlay:
        manifest.update(
            source_release=overlay["source_release"],
            archive_study=overlay,
            study_routes=[page.model_dump(mode="json") for page in pages],
        )
    with args.output.open("x") as output:
        output.write(json.dumps(manifest, indent=2) + "\n")
    print(
        f"{len(all_page)} whole-page selections, "
        f"{len(manifest['selections']) - len(all_page)} distinct additional crops"
    )


if __name__ == "__main__":
    main()
