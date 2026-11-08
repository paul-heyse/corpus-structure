"""Measure an isolated two-image Docling batch against identical serial inputs."""

import argparse
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from time import monotonic

from PIL import Image

from corpus_structure.ingest.pdf_capacity import suspend_resident_nemotron
from corpus_structure.ingest.pdf_chandra import ChandraRuntime, parse_chandra_response
from corpus_structure.semantic.pdf_visual_mapping import render_visual_input
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_requests import _load_visual_source
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.settings import Settings


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _describe(prediction, image, page):
    from docling.datamodel.base_models import VlmStopReason

    parsed = parse_chandra_response(
        prediction.text, image_size=image.size, page_no=page, stop_reason=prediction.stop_reason
    )
    return {
        "text_sha256": _digest(prediction.text.encode()),
        "stop": prediction.stop_reason.value,
        "status": parsed.status.value,
        "completion": parsed.completion.value,
        "known_stop": prediction.stop_reason != VlmStopReason.UNSPECIFIED,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pin", type=Path)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("pages", type=int, nargs=2)
    args = parser.parse_args()
    source = VisualEvidencePin.model_validate_json(args.pin.read_bytes())
    settings = Settings()
    with open_runtime_engine(settings, "chandra-batch-control", purpose="read") as engine:
        with engine.connect() as conn:
            _, _, original, _ = _load_visual_source(conn, source)
    rasters = [render_visual_input(original, page, None)[0] for page in args.pages]
    images = [Image.open(BytesIO(data)).convert("RGB") for data in rasters]
    runtime = ChandraRuntime(args.artifacts)
    result = {
        "source": source.model_dump(mode="json"),
        "pages": args.pages,
        "raster_sha256": [_digest(data) for data in rasters],
        "recipe": runtime.identity(),
    }
    with suspend_resident_nemotron(settings.nemotron.endpoint):
        try:
            started = monotonic()
            runtime._load_model()
            result["load_seconds"] = round(monotonic() - started, 3)
            result["device"] = runtime.effective_device
            started = monotonic()
            serial = [runtime.recognize(image) for image in images]
            result["serial_seconds"] = round(monotonic() - started, 3)
            result["serial"] = [
                _describe(prediction, image, page)
                for prediction, image, page in zip(serial, images, args.pages, strict=True)
            ]
            assert runtime._model is not None
            started = monotonic()
            try:
                batch = list(
                    runtime._model.process_images(images, runtime._options.model_spec.prompt)
                )
                result["batch_seconds"] = round(monotonic() - started, 3)
                result["batch"] = [
                    _describe(prediction, image, page)
                    for prediction, image, page in zip(batch, images, args.pages, strict=True)
                ]
                result["exact_output_parity"] = result["batch"] == result["serial"]
            except (RuntimeError, ValueError) as exc:
                result["batch_error"] = f"{type(exc).__name__}: {exc}"
        finally:
            runtime.close()
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
