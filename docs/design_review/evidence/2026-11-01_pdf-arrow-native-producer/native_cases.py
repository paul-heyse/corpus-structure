"""Fresh native-only finite-worker qualification of current page IPC and replay contracts."""

from __future__ import annotations

import argparse
import json
import platform
import time
import traceback
from dataclasses import asdict, replace
from hashlib import file_digest, sha256
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
from docling.datamodel.base_models import Page
from docling_core.types.doc import BoundingBox
from PIL import Image

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_candidate_source import encoded_replay
from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool
from corpus_structure.ingest.pdf_worker import PdfWorker
from corpus_structure.semantic.pdf_payloads import prepare_payload_family, schema_dump

SOURCE = Path("docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf")
SOURCE_DIGEST = "e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9"


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def inspect_replay(root, result, candidates, family):
    assert result.conversion_status == "success", result.errors
    assert len(result.page_replays) == len(candidates) == 1
    replay = result.page_replays[0]
    raw = json.loads(replay.path.read_bytes())
    assert raw["scale"] == 1.67
    assert raw["serialization_profile"] == "pydantic-native-page-envelope-v1"
    spool = PdfStreamSpool(root / "restore-control", payload_family=family)
    spool.pages = {raw["page"]["page_no"]: replay}
    control = SimpleNamespace(pages=[Page(page_no=raw["page"]["page_no"])])
    spool.restore_pages(control)
    restored = control.pages[0]
    classes = {}
    for group in ("elements", "body", "headers"):
        classes[group] = [type(value).__name__ for value in getattr(restored.assembled, group)]
        assert classes[group] == raw["assembly_types"][group]
    box = BoundingBox(l=1, t=2, r=7, b=8, coord_origin="TOPLEFT")
    crop = restored.get_image(scale=1.67, cropbox=box)
    assert crop is not None
    with Image.open(raw["raster"]["path"]) as raster:
        # Independent pixel indexing checks the requested point-to-pixel recipe.
        left, top, right, bottom = (round(value * 1.67) for value in (1, 2, 7, 8))
        assert crop.size == (right - left, bottom - top)
        assert all(
            crop.getpixel((x, y)) == raster.getpixel((left + x, top + y))
            for y in range(crop.height)
            for x in range(crop.width)
        )
        raster_pixels = sha256(raster.tobytes()).hexdigest()
        full = restored.get_image(scale=1.67)
        assert full is not None and full.tobytes() == raster.tobytes()
        full.close()
    crop.save(root / "native-replay-crop.png")
    crop_pixels = sha256(crop.tobytes()).hexdigest()
    crop.close()
    try:
        restored.get_image(scale=2.0)
    except ValueError as error:
        scale_refusal = str(error)
    else:
        raise AssertionError("replay silently substituted an uncaptured scale")
    profile = json.loads(result.effective_options)["_preparation"]
    assert profile["image_ownership"]["effective_formula_scale"] == 1.67
    assert profile["image_ownership"]["requested_formula_scale"] == 2.0
    assert profile["arrow_resources"]["ipc_use_threads"] is False
    native_types = set()
    for retained in result.record_replays:
        retained.verify()
        if retained.family == "native":
            with pa.memory_map(str(retained.path), "r") as mapping:
                reader = pa.ipc.open_file(mapping)
                for index in range(reader.num_record_batches):
                    native_types.update(reader.get_batch(index).column("native_type").to_pylist())
    payload = encoded_replay(candidates[0], family)
    logical = family.decode(
        payload.content,
        schema_digest=payload.schema_digest,
        logical_digest=payload.logical_digest,
    )
    assert logical["page_no"] == raw["page"]["page_no"]
    regions = logical.get("ocr_regions", [])
    completion = [json.loads(line) for line in (root / "records/completion.jsonl").read_text().splitlines()]
    formula = [row for row in completion if row["kind"] == "formula"]
    return {
        "page_no": logical["page_no"],
        "native_types": sorted(native_types),
        "assembly_classes": classes,
        "candidate_payload": asdict(payload) | {"content": {"byte_length": len(payload.content), "sha256": sha256(payload.content).hexdigest()}},
        "candidate_count": len(logical.get("candidates", [])),
        "ocr_regions": len(regions),
        "ocr_region_outcomes": [region["outcome"] for region in regions],
        "ocr_words": sum(len(line["words"]) for region in regions for line in region["lines"]),
        "formula_outcomes": formula,
        "prepared_runtime": profile,
        "raster": raw["raster"],
        "raster_pixels_sha256": raster_pixels,
        "crop_pixels_sha256": crop_pixels,
        "crop_box_points": [1, 2, 7, 8],
        "crop_size_pixels": [right - left, bottom - top],
        "unrecorded_scale_refusal": scale_refusal,
        "native_input_classes_preserved": True,
        "post_child_replay_and_pixels": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    family = prepare_payload_family()
    captured_schema = schema_dump(family.json_schema)
    (output / "captured-payload.schema.json").write_bytes(captured_schema)
    recipe = PdfRecipe(
        "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8",
        "ecedbe111d15c2dc60bfd4a823cbe80127b58af4",
        recipe_id="docling-standard-pdf-stream-v1",
    )
    assets = prepare_pdf_assets(recipe, cache=Path.home() / ".cache/docling/models", offline=True)
    recipe = replace(recipe, model_artifacts=assets.files, model_revisions=assets.repositories)
    (output / "recipe.json").write_bytes(recipe.to_bytes())
    (output / "asset-manifest.json").write_bytes(assets.manifest)
    report = {
        "scope": "fresh native Standard/RapidOCR selected pages; no Nemotron, PostgreSQL, publication, whole-book or independent OCR fidelity claim",
        "source_sha256": SOURCE_DIGEST,
        "captured_schema_sha256": sha256(captured_schema).hexdigest(),
        "environment": {"python": platform.python_version(), "machine": platform.machine(), "packages": {name: version(name) for name in ("docling", "docling-core", "pyarrow", "pydantic", "rapidocr", "onnxruntime", "torch")}},
        "cases": [],
    }
    with OwnedPdfSource.acquire(SOURCE, output / "source", expected_digest=SOURCE_DIGEST) as source:
        for number in (20, 1211):
            root = output / str(number)
            root.mkdir()
            replays, candidates = [], []
            started = time.monotonic()

            def received(replay):
                replay.verify()
                replays.append(asdict(replay))
                if replay.family == "candidate_payload":
                    encoded_replay(replay, family)
                    candidates.append(replay)

            worker = PdfWorker(recipe, assets=assets)
            case = {"page_no": number, "outcome": "failed"}
            try:
                result = worker.stream(
                    source,
                    spool_root=root / "pages",
                    record_root=root / "records",
                    build_id=f"arrow-native-page-{number}",
                    release_id="db-free-captured-logical-schema-qualification",
                    page_range=(number, number),
                    on_replay=received,
                    payload_schema=captured_schema,
                )
                worker.close()
                assert worker.pid is None and worker.closed
                case.update(inspect_replay(root, result, candidates, family))
                if number == 1211:
                    assert "TableItem" in case["native_types"]
                case["outcome"] = "passed"
                case["native_worker_settled"] = True
            except Exception:
                case["failure"] = traceback.format_exc()
            finally:
                worker.close()
                case["elapsed_seconds"] = time.monotonic() - started
                case["replays"] = replays
                report["cases"].append(case)
                (output / "results.json").write_text(json.dumps(report, default=str, indent=2) + "\n")
                print(f"{case['outcome']} actual native page {number}", flush=True)
    assert all(case["outcome"] == "passed" for case in report["cases"])


if __name__ == "__main__":
    main()
