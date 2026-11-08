"""Freeze a 518-page comparison from complete managed v2 dry route reports."""

import argparse
import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from archive_study import freeze_overlay, study_regions

from corpus_structure.ingest.pdf_chandra import ChandraRuntime, chandra_parser_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_dispatch import visual_dispatch_selections
from corpus_structure.semantic.visual_requests import (
    _CROP_POLICY,
    _RENDER_POLICY,
    VisualSelection,
    _load_visual_source,
)
from corpus_structure.semantic.visual_routing import VisualRouteReport, _page_items, read_visual_routes
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.settings import Settings

_ORIGINAL = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"
_PAGE_COUNT = 518
_STRUCTURES = {"caption", "formula", "picture", "table"}
_AGREEMENT = {
    202: "Table 5.2 populated cells and coordinates",
    218: "Signed density derivative for decreasing phi",
    241: "Theorem 6.3 expectation identity in the compared formula fragments",
}
_AGREEMENT_REVIEW = "../2026-11-08_nce-full-book/review/pages-174-346.md"


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


def _baseline(source: VisualEvidencePin):
    with (
        open_runtime_engine(Settings(), "chandra-book-baseline", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        _, _, original, reader = _load_visual_source(conn, source)
        if sha256(original).hexdigest() != _ORIGINAL:
            raise ValueError("the published comparator differs from the reviewed book original")
        regions, _ = _page_items(conn, source, 1, _PAGE_COUNT)
        return reader.revision["release_id"], {
            page: {part.kind for part in rows if part.kind in _STRUCTURES}
            for page, rows in regions.items()
        }


def _sample(pages, prior_controls: set[int], structural_kinds) -> dict[str, list[int]]:
    strata: dict[str, set[int]] = defaultdict(set)
    for row in pages:
        number = row.page_no
        if number in prior_controls:
            continue
        for reason in row.reasons:
            strata[f"{row.action}/{reason.kind or reason.code}"].add(number)
        if row.action == "skip" and any(reason.code == "no_supported_trigger" for reason in row.reasons):
            for kind in structural_kinds.get(number) or {"no_located_typed_region"}:
                strata[f"unflagged/{kind}"].add(number)
        if number in _AGREEMENT:
            strata["agreement/reviewed_incumbent_fields"].add(number)
    return {
        key: sorted(
            sorted(
                numbers,
                key=lambda page: sha256(
                    f"chandra-held-out-v2:{_ORIGINAL}:{key}:{page}".encode()
                ).digest(),
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
    parser.add_argument("--pilot-page", type=int, action="append", default=[])
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
    selective = [
        selection.model_dump(mode="json", exclude_none=True, exclude={"source"})
        for report in reports
        for selection in visual_dispatch_selections(report, "selective")
    ]
    # The prior source-qualified control established this turn. Use only a locator
    # nominated by the frozen comparator, and retain the ordinary selective frame.
    sideways = [
        _selection(509, **reason.crop.model_dump(), rotation=90)
        for reason in pages[508].reasons
        if reason.kind == "table" and reason.crop is not None
        and _selection(509, **reason.crop.model_dump()) in selective
    ]
    explicit = [_selection(page) for page in (108, 151, 301, 398, 416, 439, 509)] + sideways
    known = json.loads(
        (Path(__file__).parent.parent / "2026-11-08_chandra-post-nemotron" / "cases.json").read_bytes()
    )
    if known["source_sha256"] != _ORIGINAL:
        raise ValueError("source witnesses belong to another original")
    pilot = set(args.pilot_page)
    if any(not 1 <= page <= _PAGE_COUNT for page in pilot):
        raise ValueError("pilot pages must lie within the original physical page range")
    controls = set(map(int, known["pages"])) | {1, 4, 119, 327} | pilot
    source_release, structural_kinds = _baseline(source)
    held_out = _sample(pages, controls, structural_kinds)
    priority_pages = controls | {page for sample in held_out.values() for page in sample}
    priority = [_selection(page) for page in sorted(priority_pages)]
    receipt_root = Path(__file__).parent
    cohort = receipt_root / "mixed-cohort" / "cohort.json"
    cohort_receipt = receipt_root / "raw" / "mixed-cohort-shadow.json"
    retention = json.loads(cohort_receipt.read_bytes())
    manifest = {
        "manifest_version": "chandra-book-shadow-v2",
        "source": source.model_dump(),
        "source_release": source_release,
        "original_sha256": _ORIGINAL,
        "semantic_release": args.semantic_release,
        "realization": args.realization,
        "artifacts": str(args.artifacts),
        "source_family": "born_digital_probability_textbook",
        "incumbent_repair": {
            "mode": "witnessed_archive_overlay" if overlay else "exact_published_integrated",
            "witness": "incumbent-recovery.md#original-source-witnesses",
        },
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
        "pilot_pages": sorted(pilot),
        "prior_agreement_control": {
            "page_no": 327,
            "item": "Table 8.1",
            "source_review": _AGREEMENT_REVIEW,
        },
        "held_out_agreement": {
            "source_review": _AGREEMENT_REVIEW,
            "fields": {
                number: _AGREEMENT[number]
                for number in held_out.get("agreement/reviewed_incumbent_fields", ())
            },
        },
        "held_out": held_out,
        "adjudication": {
            "basis": "Original physical page, exact admitted incumbent and attributed Chandra evidence",
            "review": ["known controls", "frozen held-out strata", "material candidate changes and harms"],
            "dispositions": [
                "supported_addition", "supported_correction", "confirmed_agreement",
                "rejected_candidate", "shared_incumbent_defect", "unresolved_witness",
            ],
            "unsampled": "unadjudicated",
        },
        "mixed_cohort": {
            "definition": str(cohort.relative_to(receipt_root)),
            "definition_sha256": sha256(cohort.read_bytes()).hexdigest(),
            "receipt": str(cohort_receipt.relative_to(receipt_root)),
            "receipt_sha256": sha256(cohort_receipt.read_bytes()).hexdigest(),
            "physical_pages": retention["physical_pages"],
            "groups": len(retention["groups"]),
        },
        "study_routes": [page.model_dump(mode="json") for page in pages],
        "selections": _deduplicate(source, explicit + priority + all_page + selective),
    }
    if overlay:
        manifest["archive_study"] = overlay
    else:
        manifest["recipe"] = {
            "execution": "serial_inside_managed_group",
            "runtime": ChandraRuntime(args.artifacts).identity(),
            "parser": chandra_parser_identity(),
            "render_policy": _RENDER_POLICY,
            "crop_policy": _CROP_POLICY,
        }
    with args.output.open("x") as output:
        output.write(json.dumps(manifest, indent=2) + "\n")
    print(
        f"{len(all_page)} whole-page selections, "
        f"{len(manifest['selections']) - len(all_page)} distinct additional crops"
    )


if __name__ == "__main__":
    main()
