"""Retain whole-page M1 excerpts with parent provenance, without text reflow.

This is source-only population preparation. It reads no predictions/references,
opens no database and runs no recognition provider. Existing originals are immutable.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from hashlib import file_digest, sha256
from importlib.metadata import version
from pathlib import Path

import pypdfium2 as pdfium

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CORPUS = ROOT / "docs/statistics_corpus/corpus"
CUTS = (
    (
        "grinstead-snell",
        "feature_fit",
        "grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf",
        "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e",
        191,
        200,
        "Discrete distributions, chapter 5 opening through Poisson examples; printed 183-192",
    ),
    (
        "forbes-statistical-distributions",
        "final_event_calibration",
        "forbes_statistical_distributions/STATISTICAL DISTRIBUTIONS  FOURTH EDITION -- Forbes, Catherine, Evans, Merran, Hastings, Nicholas, -- Wiley series in probability and statistics, 4th -- isbn13 9780470390634.pdf",
        "8b84802f96725d63a5cdc02687cfb57f1f866b2096ec940bdb81ee41f1b55ae9",
        39,
        46,
        "Complete chapter 4, Multivariate Distributions; printed 24-31",
    ),
    (
        "nist-ehandbook",
        "final_assessment",
        "nist_ehandbook/pdf/E-Handbook.pdf",
        "c0d71c6fc65eb0a44bbb11107799cd36ceae1c4d81f0d143c439c3d1849eadda",
        218,
        226,
        "Complete 1.3.5.1 Measures of Location and 1.3.5.2 Confidence Limits for the Mean",
    ),
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def write_new(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main() -> None:
    destination = HERE / "population-fixtures"
    destination.mkdir(exist_ok=False)
    sources = []
    for group, partition, relative, expected, first, last, title in CUTS:
        original = CORPUS / relative
        if digest(original) != expected:
            raise ValueError(f"Parent original changed: {group}")
        output = destination / f"{group}.pdf"
        with pdfium.PdfDocument(original) as parent, pdfium.PdfDocument.new() as excerpt:
            parent_pages = len(parent)
            excerpt.import_pages(parent, pages=list(range(first - 1, last)))
            excerpt.save(output)
        pages = []
        with pdfium.PdfDocument(original) as parent, pdfium.PdfDocument(output) as excerpt:
            if len(excerpt) != last - first + 1:
                raise ValueError("Excerpt page count changed")
            for index, original_index in enumerate(range(first - 1, last)):
                original_page, excerpt_page = parent[original_index], excerpt[index]
                try:
                    if original_page.get_size() != excerpt_page.get_size():
                        raise ValueError("Excerpt page geometry changed")
                    original_image = original_page.render(scale=1).to_pil()
                    excerpt_image = excerpt_page.render(scale=1).to_pil()
                    original_pixels = sha256(original_image.tobytes()).hexdigest()
                    excerpt_pixels = sha256(excerpt_image.tobytes()).hexdigest()
                    if original_pixels != excerpt_pixels:
                        raise ValueError(f"Excerpt page pixels changed: {group}:{index + 1}")
                    pages.append(
                        {
                            "excerpt_physical_page": index + 1,
                            "parent_physical_page": original_index + 1,
                            "width_points": excerpt_page.get_size()[0],
                            "height_points": excerpt_page.get_size()[1],
                            "pdfium_render_scale": 1,
                            "render_mode": excerpt_image.mode,
                            "render_size": list(excerpt_image.size),
                            "parent_pixels_sha256": original_pixels,
                            "excerpt_pixels_sha256": excerpt_pixels,
                        }
                    )
                    if index in {0, min(3, len(excerpt) - 1)}:
                        excerpt_image.save(destination / f"{group}-page{index + 1}.png")
                    original_image.close()
                    excerpt_image.close()
                finally:
                    original_page.close()
                    excerpt_page.close()
        parent_text = subprocess.run(
            ["pdftotext", "-layout", "-f", str(first), "-l", str(last), str(original), "-"],
            capture_output=True,
            check=True,
        ).stdout
        excerpt_text = subprocess.run(
            ["pdftotext", "-layout", str(output), "-"], capture_output=True, check=True
        ).stdout
        if parent_text != excerpt_text:
            raise ValueError(f"Poppler extracted text changed: {group}")
        text_path = destination / f"{group}.txt"
        text_path.write_bytes(excerpt_text)
        sources.append(
            {
                "source_id": f"m1-{group}-20261104",
                "origin_group": group,
                "intended_partition": partition,
                "copy_group_rule": "Parent book, editions, excerpt, chapter PDFs, HTML and overlapping windows remain in this origin group",
                "title": title,
                "parent": {
                    "path": str(original.relative_to(ROOT)),
                    "sha256": expected,
                    "bytes": original.stat().st_size,
                    "physical_pages": parent_pages,
                },
                "excerpt": {
                    "path": str(output.relative_to(ROOT)),
                    "source_uri": output.name,
                    "sha256": digest(output),
                    "bytes": output.stat().st_size,
                    "physical_pages": len(pages),
                    "scope": "Whole excerpt PDF; a bounded parent-page selection, not an entire parent book",
                    "text_path": str(text_path.relative_to(HERE)),
                    "text_sha256": sha256(excerpt_text).hexdigest(),
                    "page_map": pages,
                },
                "native_source_pin": None,
                "family_eligibility": "Source-only leads; independent authors decide in-scope records and explicit empty/unreadable outcomes",
            }
        )
        print(json.dumps({"source": group, "pages": len(pages), "sha256": digest(output), "pixel_and_text_identity": "passed"}), flush=True)
    write_new(
        HERE / "source-population.json",
        {
            "frozen_at": datetime.now(UTC).isoformat(),
            "baseline": "71a78774",
            "standing": "Tested source-byte/page-membership freeze; native admission/reference acquisition/provider execution not_run",
            "creation_library": {"pypdfium2": version("pypdfium2")},
            "method": "PdfDocument.new/import_pages/save of exact complete parent pages; no rasterization/reflow in the saved PDF",
            "population_selection": "Purposive finite cuts selected from source structure before predictions and reference labels; no unseen-origin inference",
            "assessment_method": "Intended source-side census of every admitted excerpt unit, including empty, unsupported and unreadable units; native view population must be frozen before reference passes",
            "development_origin": {"origin_group": "siegrist-random", "partition": "development", "prior_evidence": "../2026-11-03_m1-population/manifest.json"},
            "sources": sources,
            "total_pages": sum(source["excerpt"]["physical_pages"] for source in sources),
            "independence": "Three named source-origin groups separated by intended use; no statistical independence or sufficient per-family support claim",
            "references": "not_run; fresh Sol 6.1 high A/B/C through the protected evaluator owner",
            "predictions": "not_run and not read",
        },
    )


if __name__ == "__main__":
    main()
