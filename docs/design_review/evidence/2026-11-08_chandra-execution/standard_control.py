"""Compare bounded physical PDF pages on the repository's Standard converter."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from corpus_structure.ingest.pdf import PdfConverter
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_methods import PdfIngestConfig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", type=Path)
    parser.add_argument("scan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    cfg = PdfIngestConfig()
    recipe = cfg.recipe()
    assets = prepare_pdf_assets(recipe, cache=cfg.model_cache, offline=True)
    recipe = replace(recipe, model_artifacts=assets.files, model_revisions=assets.repositories)
    converter = PdfConverter(recipe, assets=assets)
    args.output.mkdir(parents=True, exist_ok=True)
    cases = [(f"book-{page}", args.book, (page, page)) for page in (11, 142, 151, 416, 509, 510)]
    cases.append(("scan", args.scan, (1, 1)))
    for case, path, page_range in cases:
        conversion = converter.convert(path, page_range=page_range)
        data = {
            "source": conversion.original_digest,
            "physical_pages": conversion.page_range,
            "recipe": json.loads(conversion.recipe),
            "packages": dict(conversion.packages),
            "runtime": dict(conversion.runtime),
            "status": conversion.conversion_status,
            "errors": conversion.errors,
            "formula_outcomes": [asdict(outcome) for outcome in conversion.formula_outcomes],
            "candidates": [asdict(page) for page in conversion.inline_candidates],
            "document": json.loads(conversion.native.payload),
        }
        (args.output / f"{case}.json").write_text(json.dumps(data, indent=2, default=str) + "\n")
        print(case, conversion.conversion_status, flush=True)


if __name__ == "__main__":
    main()
