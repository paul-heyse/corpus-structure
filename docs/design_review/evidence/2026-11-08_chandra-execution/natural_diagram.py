"""Use the pinned local reference on independently inspected NIST flowcharts."""

import argparse
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image

from corpus_structure.ingest.pdf_capacity import pdf_gpu_slot
from corpus_structure.ingest.pdf_chandra import ChandraRuntime, parse_chandra_response
from corpus_structure.semantic.pdf_visual_mapping import map_visual_result, render_visual_input


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    original = args.source.read_bytes()
    args.out.mkdir(parents=True, exist_ok=True)
    runtime = ChandraRuntime(args.artifacts)
    with pdf_gpu_slot():
        try:
            for page in (141, 206):
                png, frame = render_visual_input(original, page, None)
                with Image.open(BytesIO(png)) as image:
                    prediction = runtime.recognize(image)
                    raw = prediction.text
                    (args.out / f"pri-{page}.html").write_text(raw)
                    parsed = parse_chandra_response(
                        raw,
                        image_size=image.size,
                        page_no=page,
                        stop_reason=prediction.stop_reason.value,
                    )
                    if parsed.document is not None:
                        artifact = map_visual_result(
                            parsed.document, page_no=page, transform=frame, image_size=image.size
                        )
                        (args.out / f"pri-{page}-typed.json").write_bytes(artifact.artifact_bytes())
                    (args.out / f"pri-{page}-receipt.json").write_text(
                        json.dumps(
                            dict(
                                source_sha256=sha256(original).hexdigest(),
                                submitted_png_sha256=sha256(png).hexdigest(),
                                raw_sha256=sha256(raw.encode()).hexdigest(),
                                physical_page=page,
                                stop=prediction.stop_reason.value,
                                parse=parsed.status,
                                issues=parsed.issues,
                                device=runtime.effective_device,
                            ),
                            indent=2,
                        )
                        + "\n"
                    )
                    print(page, parsed.status, prediction.stop_reason.value, flush=True)
        finally:
            runtime.close()


if __name__ == "__main__":
    main()
