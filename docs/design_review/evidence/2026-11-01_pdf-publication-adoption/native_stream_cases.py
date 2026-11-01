"""Fresh finite-worker controls for native form/table replay and formula crop scale."""

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

import pyarrow as pa

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
    assets = prepare_pdf_assets(recipe, cache=Path.home() / ".cache/docling/models", offline=True)
    recipe = replace(recipe, model_artifacts=assets.files, model_revisions=assets.repositories)
    receipts = []
    with OwnedPdfSource.acquire(
        Path("docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf"),
        output / "source",
        expected_digest="e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9",
    ) as source:
        for number in (20, 1211):
            root = output / str(number)
            root.mkdir()
            replays = []

            def received(replay):
                replay.verify()
                replays.append(asdict(replay))

            worker = PdfWorker(recipe, assets=assets)
            try:
                result = worker.stream(
                    source, spool_root=root / "pages", record_root=root / "records",
                    build_id=f"fresh-page-{number}", release_id="standalone-provider-qualification",
                    page_range=(number, number), on_replay=received,
                )
            finally:
                worker.close()
            assert result.conversion_status == "success", result.errors
            assert len(result.page_replays) == 1
            page = json.loads(result.page_replays[0].path.read_bytes())
            assert page["scale"] == 1.67
            assert set(page["assembly_types"]) == {"elements", "body", "headers"}
            types = set()
            for replay in result.record_replays:
                if replay.family != "native":
                    continue
                with pa.memory_map(str(replay.path), "r") as mapping:
                    reader = pa.ipc.open_file(mapping)
                    for index in range(reader.num_record_batches):
                        types.update(reader.get_batch(index).column("native_type").to_pylist())
            if number == 1211:
                assert "TableItem" in types
            receipts.append(dict(page=number, status=result.conversion_status, native_types=sorted(types), replays=replays))
            print("passed fresh native stream page", number, flush=True)
    (output / "receipt.json").write_text(json.dumps({"scope": "fresh selected-page native producer only; no database publication or whole-book claim", "cases": receipts}, default=str, indent=2) + "\n")


if __name__ == "__main__":
    main()
