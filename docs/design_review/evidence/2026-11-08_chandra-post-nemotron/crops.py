"""Create original-pixel crop probes with reversible page transforms."""

import argparse
import hashlib
import json
from pathlib import Path

import pypdfium2
from PIL import Image

CROPS = {
    "joint-distribution": (151, (0.36, 0.24, 0.64, 0.37), False),
    "markov-arrays": (416, (0.29, 0.27, 0.73, 0.78), False),
    "appendix-upright": (509, (0.19, 0.16, 0.81, 0.88), True),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    book = pypdfium2.PdfDocument(args.pdf)
    ledger = {}
    for name, (number, fractions, rotate) in CROPS.items():
        page = book[number - 1]
        rendered = page.render(scale=3)
        source = rendered.to_pil().convert("RGB")
        w, h = source.size
        left, top, right, bottom = [
            round(fraction * size) for fraction, size in zip(fractions, (w, h, w, h), strict=True)
        ]
        crop = source.crop((left, top, right, bottom))
        if rotate:
            # PIL ROTATE_270 turns source left-to-right columns into upright rows.
            crop = crop.transpose(Image.Transpose.ROTATE_270)
        path = args.out / f"{name}.png"
        crop.save(path)
        ledger[name] = {
            "physical_page": number,
            "page_size_pdf_points": list(page.get_size()),
            "raster_size": [w, h],
            "crop_box_top_left_pixels": [left, top, right, bottom],
            "crop_rotation_clockwise": 90 if rotate else 0,
            "crop_size": list(crop.size),
            "crop_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        rendered.close()
        page.close()
    book.close()
    (args.out / "frames.json").write_text(json.dumps(ledger, indent=2) + "\n")


if __name__ == "__main__":
    main()
