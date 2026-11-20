"""Create the bounded UDM-20 originals from their exact retained book pages."""

import json
from hashlib import sha256
from pathlib import Path

import pypdfium2 as pdfium
from corpus_structure.core.evidence import document_key

root = Path("/home/paul/corpus-structure")
folder = Path(__file__).resolve().parent
output = root / "build/udm20-regional/excerpts"
output.mkdir(parents=True, exist_ok=True)
inventory = json.loads(
    (
        root
        / "docs/design_review/evidence/2026-11-16_ddo-current-native/original-descriptors.json"
    ).read_bytes()
)
(original,) = (
    item
    for item in inventory["descriptors"]
    if item["key"] == "doc:38d5d93379c3320aa88457511d38fc25"
)
source = Path(original["original_path"])
assert sha256(source.read_bytes()).hexdigest() == original["content_hash"]
selected = (
    ("largest-failed-pages", 413, 478, "#/groups/614"),
    ("failed-records-contrast", 233, 292, "#/groups/489"),
    ("successful-control", 479, 506, "#/groups/653"),
)
descriptors = []
with pdfium.PdfDocument(source) as book:
    assert len(book) == 518
    for name, start, end, pointer in selected:
        path = output / f"{name}.pdf"
        with pdfium.PdfDocument.new() as excerpt:
            excerpt.import_pages(book, pages=list(range(start - 1, end)))
            assert len(excerpt) == end - start + 1
            excerpt.save(path)
        raw = path.read_bytes()
        digest = sha256(raw).hexdigest()
        project = "udm20-regional-" + name
        uri = "udm20-" + name + ".pdf"
        descriptors.append(
            {
                "project_id": project,
                "key": document_key(project, uri, digest),
                "source_uri": uri,
                "content_hash": digest,
                "original_path": str(path),
                "mime": "application/pdf",
                "title": f"UDM-20 pages {start}–{end}",
                "metadata": {
                    "source_document": original["key"],
                    "source_hash": original["content_hash"],
                    "original_first_page": start,
                    "original_last_page": end,
                    "historical_section": pointer,
                },
            }
        )
result = {
    "documents": len(descriptors),
    "distinct_paths": len(descriptors),
    "descriptors": descriptors,
}
(folder / "excerpt-descriptors.json").write_text(json.dumps(result, indent=2) + "\n")
policy = {
    "workers": 1,
    "max_submissions": 1,
    "max_regions": 1,
    "max_claims": 8,
    "provider_threads": 4,
    "provider_interop_threads": 1,
    "cpu_native_threads": 1,
    "max_provider_jobs": 1,
    "max_owned_bytes": 17179869184,
    "max_packet_bytes": 603979776,
    "max_reply_bytes": 201326592,
    "max_source_read_rows": 1000000,
    "max_native_request_bytes": 8 * 1024**2,
    "max_native_reply_bytes": 8 * 1024**2,
    "max_idle_capsule_bytes": 256 * 1024**2,
    "max_idle_capsules": 2,
    "native_keep_warm_seconds": 0,
}
(folder / "regional-execution-policy.json").write_text(
    json.dumps(policy, indent=2) + "\n"
)
print(
    json.dumps(
        {
            "excerpts": [
                (
                    d["project_id"],
                    d["metadata"]["original_first_page"],
                    d["metadata"]["original_last_page"],
                )
                for d in descriptors
            ]
        }
    )
)
