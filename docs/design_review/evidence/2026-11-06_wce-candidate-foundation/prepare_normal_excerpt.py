"""Bounded same-corpus normal-density excerpt; exact whole parent pages."""

import json
from hashlib import file_digest, sha256
from pathlib import Path

import pypdfium2 as pdfium

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORIGINAL = ROOT / "docs/statistics_corpus/corpus/grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf"
EXPECTED = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"
OUTPUT = HERE / "normal-excerpt002"


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main():
    if digest(ORIGINAL) != EXPECTED:
        raise ValueError("parent book differs from original statistics source inventory")
    OUTPUT.mkdir(exist_ok=False)
    destination = OUTPUT / "grinstead-normal-physical220-222.pdf"
    with pdfium.PdfDocument(ORIGINAL) as source, pdfium.PdfDocument.new() as excerpt:
        excerpt.import_pages(source, pages=[219, 220, 221])
        excerpt.save(destination)
    pages = []
    with pdfium.PdfDocument(ORIGINAL) as source, pdfium.PdfDocument(destination) as excerpt:
        if len(excerpt) != 3:
            raise ValueError("excerpt page population differs")
        for index in range(3):
            original, selected = source[index + 219], excerpt[index]
            try:
                images = (original.render(scale=1).to_pil(), selected.render(scale=1).to_pil())
                try:
                    hashes = tuple(sha256(image.tobytes()).hexdigest() for image in images)
                    if original.get_size() != selected.get_size() or hashes[0] != hashes[1]:
                        raise ValueError("selected page differs from parent geometry/pixels")
                    pages.append({"parent_physical_page": index + 220, "excerpt_physical_page": index + 1, "pixels_sha256": hashes[0], "size_points": list(selected.get_size())})
                finally:
                    for image in images:
                        image.close()
            finally:
                original.close()
                selected.close()
    manifest = {"protocol": "wce-normal-source-cut-1", "parent": str(ORIGINAL.relative_to(ROOT)), "parent_sha256": EXPECTED, "excerpt": str(destination.relative_to(ROOT)), "excerpt_sha256": digest(destination), "pages": pages, "origin_group": "grinstead-snell", "partition": "development", "exposure": "same exposed source family; no unseen-origin claim", "native_intake": "pending", "script_sha256": digest(Path(__file__))}
    with (OUTPUT / "source-cut-001.json").open("x") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"outcome": "passed", "pages": 3, "excerpt_sha256": manifest["excerpt_sha256"]}))


if __name__ == "__main__":
    main()
