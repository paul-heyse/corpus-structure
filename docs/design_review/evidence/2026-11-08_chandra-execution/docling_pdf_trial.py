"""Run the matched Chandra PDF-level trial under the shared GPU handoff."""

import argparse
import json
import subprocess
import sys
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from time import monotonic

from PIL import Image

from corpus_structure.ingest.pdf_capacity import suspend_resident_nemotron
from corpus_structure.ingest.pdf_chandra import ChandraRuntime
from corpus_structure.semantic.pdf_visual_mapping import render_visual_input
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_requests import _load_visual_source
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.settings import Settings

_MATCHED = (506, 510)
_CONTROLS = (108, 151, 301, 398, 416, 439)


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _legacy(args):
    started = monotonic()
    args.output.mkdir()
    original = args.pdf.read_bytes()
    runtime = ChandraRuntime(args.artifacts)
    prepared = monotonic()
    runtime._load_model()
    loaded = monotonic()
    pages = []
    try:
        for page in range(args.first, args.last + 1):
            entered = monotonic()
            png, transform = render_visual_input(original, page, None)
            rendered = monotonic()
            with Image.open(BytesIO(png)) as image:
                prediction = runtime.recognize(image)
            inferred = monotonic()
            directory = args.output / str(page)
            directory.mkdir()
            (directory / "submitted.png").write_bytes(png)
            (directory / "response.html").write_bytes(prediction.text.encode())
            _write(directory / "prediction.json", prediction.model_dump(mode="json"))
            row = {
                "page_no": page,
                "frame_sha256": sha256(png).hexdigest(),
                "transform": transform,
                "render_seconds": round(rendered - entered, 3),
                "inference_seconds": round(inferred - rendered, 3),
                "stop": prediction.stop_reason.value,
            }
            pages.append(row)
            print(json.dumps(row), flush=True)
        _write(args.output / "report.json", {
            "preparation_seconds": round(prepared - started, 3),
            "model_load_seconds": round(loaded - prepared, 3),
            "pages": pages,
        })
    finally:
        runtime.close()


def _native(args):
    from docling.datamodel.progress import PageCompletedProgress

    from corpus_structure.ingest.pdf_chandra_document import ChandraDocumentRuntime

    def progress(event):
        if isinstance(event, PageCompletedProgress):
            print(event.model_dump_json(), flush=True)

    with ChandraDocumentRuntime(
        args.artifacts, batch_size=args.batch_size, renderer=args.renderer
    ) as worker:
        if args.arm == "native-controls":
            args.output.mkdir()
            ranges = [(page, page) for page in _CONTROLS]
        elif args.arm == "native-full":
            ranges = [(1, args.last)]
        else:
            ranges = [_MATCHED]
        for first, last in ranges:
            output = args.output / str(first) if args.arm == "native-controls" else args.output
            entered = monotonic()
            report = worker.convert(
                args.pdf, output,
                page_range=None if args.arm == "native-full" else (first, last),
                progress_callback=progress,
            )
            print(json.dumps({
                "first": first, "last": last, "seconds": round(monotonic() - entered, 3),
                "status": report.get("status"),
            }), flush=True)
            expected = list(range(first, last + 1))
            if report["raw_page_nos"] != expected or report["typed_page_nos"] != expected:
                raise RuntimeError(f"Docling did not capture every page in range {first}–{last}")


def _controller(args):
    source = VisualEvidencePin.model_validate_json(args.pin.read_bytes())
    settings = Settings()
    with open_runtime_engine(settings, "docling-pdf-trial", purpose="read") as engine:
        with engine.connect() as conn:
            _, _, original, _ = _load_visual_source(conn, source)
    if args.pdf.read_bytes() != original:
        raise ValueError("trial PDF differs from the exact protected comparator original")
    args.output.mkdir()
    if args.arm == "legacy-matched":
        sessions = [(506, 509), (510, 510)]
    elif args.arm == "native-full":
        from pypdfium2 import PdfDocument

        with PdfDocument(original) as document:
            sessions = [(1, len(document))]
    else:
        sessions = [_MATCHED]
    receipt = {
        "arm": args.arm,
        "source": source.model_dump(mode="json"),
        "original_sha256": sha256(original).hexdigest(),
        "sessions": [],
    }
    for first, last in sessions:
        output = args.output / f"run-{first}" if args.arm == "legacy-matched" else args.output / "native"
        began = monotonic()
        with suspend_resident_nemotron(settings.nemotron.endpoint):
            acquired = monotonic()
            result = subprocess.run(
                [
                    sys.executable, __file__, args.pin.as_posix(), args.pdf.as_posix(),
                    args.artifacts.as_posix(), output.as_posix(), "--arm", args.arm,
                    "--batch-size", str(args.batch_size), "--renderer", args.renderer, "--child",
                    "--first", str(first), "--last", str(last),
                ],
                check=False,
            )
            exited = monotonic()
        settled = monotonic()
        receipt["sessions"].append({
            "first": first,
            "last": last,
            "wall_seconds": round(settled - began, 3),
            "handoff_in_seconds": round(acquired - began, 3),
            "worker_seconds": round(exited - acquired, 3),
            "handoff_out_seconds": round(settled - exited, 3),
            "exit_code": result.returncode,
        })
        _write(args.output / "timing.json", receipt)
        if result.returncode != 0:
            raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pin", type=Path)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--arm", choices=("native-matched", "native-controls", "native-full", "legacy-matched"), required=True)
    parser.add_argument("--batch-size", type=int, choices=(1, 2), default=1)
    parser.add_argument("--renderer", choices=("docling-parse", "pdfium-reference"), default="docling-parse")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--first", type=int, default=506, help=argparse.SUPPRESS)
    parser.add_argument("--last", type=int, default=510, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.child:
        _controller(args)
    elif args.arm == "legacy-matched":
        _legacy(args)
    else:
        _native(args)


if __name__ == "__main__":
    main()
