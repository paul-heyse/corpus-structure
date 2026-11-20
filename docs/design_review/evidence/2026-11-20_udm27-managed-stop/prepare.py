"""Prepare the exact stage original and managed request for actual capture retirement."""

import json
from hashlib import sha256
from pathlib import Path

import pypdfium2 as pdfium

from corpus_structure.core.evidence import document_key

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "docs/design_review/evidence"
DESTINATION = ROOT / "build/udm20-23/managed-stop-control"
PROJECT = "udm27-managed-capture-stop"
SOURCE_KEY = "doc:38d5d93379c3320aa88457511d38fc25"
FIRST_PAGE, LAST_PAGE = 490, 507


def main():
    inventory = json.loads(
        (EVIDENCE / "2026-11-16_ddo-current-native/original-descriptors.json").read_bytes()
    )
    original = next(item for item in inventory["descriptors"] if item["key"] == SOURCE_KEY)
    path = Path(original["original_path"])
    assert sha256(path.read_bytes()).hexdigest() == original["content_hash"]
    DESTINATION.mkdir(parents=True, exist_ok=True)
    excerpt_path = DESTINATION / "managed-capture-stop.pdf"
    with pdfium.PdfDocument(path) as book, pdfium.PdfDocument.new() as excerpt:
        assert len(book) == 518
        excerpt.import_pages(book, pages=list(range(FIRST_PAGE - 1, LAST_PAGE)))
        assert len(excerpt) == LAST_PAGE - FIRST_PAGE + 1
        excerpt.save(excerpt_path)
    digest = sha256(excerpt_path.read_bytes()).hexdigest()
    uri = excerpt_path.name
    key = document_key(PROJECT, uri, digest)
    descriptor = {
        "project_id": PROJECT,
        "key": key,
        "source_uri": uri,
        "content_hash": digest,
        "original_path": str(excerpt_path),
        "mime": "application/pdf",
        "title": f"UDM-27 managed stop fixture, original pages {FIRST_PAGE}\N{EN DASH}{LAST_PAGE}",
        "metadata": {
            "source_document": SOURCE_KEY,
            "source_hash": original["content_hash"],
            "original_first_page": FIRST_PAGE,
            "original_last_page": LAST_PAGE,
        },
    }
    basis = json.loads(
        (
            EVIDENCE / "2026-11-19_udm20-regional-confirmation/raw/n36-standard-release.json"
        ).read_bytes()
    )
    request = {
        "project_id": PROJECT,
        "release_id": basis["release"],
        "runtime_id": basis["runtime_id"],
        "selection": {"kind": "whole_document"},
        "workflow": "capture",
        "pdf_mode": "standard",
        "documents": [key],
        "targets": ["source.pdf/capture"],
    }
    for name, value in {
        "original.json": {"documents": 1, "distinct_paths": 1, "descriptors": [descriptor]},
        "request.json": request,
    }.items():
        (DESTINATION / name).write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
