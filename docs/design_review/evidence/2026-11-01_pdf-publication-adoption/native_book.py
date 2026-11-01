"""Actual full-book native streaming qualification; durable replay, no database writes."""
from dataclasses import asdict, replace
from pathlib import Path
import json
import sys
import time

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource
from corpus_structure.ingest.pdf_worker import PdfWorker


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    recipe = PdfRecipe(
        "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8",
        "ecedbe111d15c2dc60bfd4a823cbe80127b58af4",
        recipe_id="docling-standard-pdf-stream-v1",
    )
    assets = prepare_pdf_assets(recipe, cache=Path.home()/".cache/docling/models", offline=True)
    recipe = replace(recipe, model_artifacts=assets.files, model_revisions=assets.repositories)
    started = time.monotonic()
    count = 0
    with (output/"replay.jsonl").open("x") as journal:
        def received(replay):
            nonlocal count
            replay.verify()
            journal.write(json.dumps(asdict(replay), default=str)+"\n")
            journal.flush()
            count += 1
            if count % 50 == 0:
                print("verified replay descriptors", count, "elapsed", time.monotonic()-started, flush=True)
        with OwnedPdfSource.acquire(
            Path("docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf"),
            output/"source",
            expected_digest="e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9",
        ) as source:
            worker = PdfWorker(recipe, assets=assets)
            try:
                result = worker.stream(
                    source, spool_root=output/"pages", record_root=output/"records",
                    build_id="actual-native-book-qualification",
                    release_id="standalone-provider-qualification", on_replay=received,
                )
            finally:
                worker.close()
    receipt = {"result": asdict(result), "elapsed_seconds": time.monotonic()-started,
               "scope": "actual native full-book page/record stream; no PostgreSQL adoption or companions"}
    (output/"receipt.json").write_text(json.dumps(receipt, default=str, indent=2)+"\n")
    print(result.conversion_status, "pages", len(result.page_replays), "record files", len(result.record_replays), flush=True)
    assert result.conversion_status == "success"
    assert len(result.page_replays) == 1589


if __name__ == "__main__":
    main()
