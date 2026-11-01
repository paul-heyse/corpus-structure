"""Replay retained actual book native graph through PDF22 lowering; no inference or DB writes."""

from __future__ import annotations

import gc
import json
import resource
import sys
import time
from collections import Counter
from hashlib import sha256
from pathlib import Path

import psycopg
import pyarrow as pa
from docling_core.types.doc import DoclingDocument

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.pdf_staging import MAX_BATCH_BYTES, stage_schema


def rss_kib() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def main() -> None:
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    with psycopg.connect(
        "host=/var/run/postgresql port=5434 dbname=corpus_pdf_20261031"
    ) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT native_json::text,release_id,schema_digest,recipe_digest,"
                "content_digest,health FROM ops.native_document_product "
                "WHERE task_id=2 AND product_key='native'"
            )
            native, release_id, schema, recipe_digest, content_digest, health = cursor.fetchone()
            cursor.execute(
                "SELECT content FROM kb.source_artifact WHERE artifact_digest=%s",
                (recipe_digest,),
            )
            recipe = bytes(cursor.fetchone()[0])
            cursor.execute(
                "SELECT artifact_digest FROM ops.pdf_product "
                "WHERE task_id=2 AND product_key='native'"
            )
            source_digest = cursor.fetchone()[0]
    fetched = time.perf_counter()
    native_bytes = len(native.encode())
    native_text_digest = sha256(native.encode()).hexdigest()
    document = DoclingDocument.model_validate_json(native)
    del native
    gc.collect()
    hydrated = time.perf_counter()
    hydrate_rss = rss_kib()
    collections = {
        name: len(getattr(document, name))
        for name in ("pages", "texts", "tables", "pictures", "groups", "key_value_items", "form_items")
    }
    assert collections["pages"] == 1589, collections
    counts: Counter[str] = Counter()
    native_types: Counter[str] = Counter()
    largest_batch = 0
    ipc_bytes = 0
    ipc_files = 0

    def adopted(replay) -> None:
        nonlocal largest_batch, ipc_bytes, ipc_files
        replay.verify()
        ipc_files += 1
        ipc_bytes += replay.byte_length
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            assert reader.schema.equals(stage_schema(replay.family), check_metadata=True)
            for index in range(reader.num_record_batches):
                batch = reader.get_batch(index)
                largest_batch = max(largest_batch, batch.nbytes)
                assert batch.nbytes <= MAX_BATCH_BYTES
                counts[replay.family] += batch.num_rows
                if replay.family == "native":
                    native_types.update(batch.column("native_type").to_pylist())

    # This historical source supplies an already-finalized global graph. No page
    # raster/assembly spools exist for that retained conversion; those paths have
    # separate actual two-page provider coverage. Its exact archived recipe is retained.
    result = StreamingPdfResult(
        document, PdfStreamSpool(output / "pages"), "success", (), recipe, ()
    )
    replays = result.write_record_batches(
        output / "records",
        build_id="retained-book-pdf22-replay",
        release_id=release_id,
        source_digest=source_digest,
        on_batch=adopted,
    )
    finished = time.perf_counter()
    assert len(replays) == ipc_files
    assert counts["header"] == 1
    assert native_types["DoclingDocument"] == 1
    assert native_types["PageItem"] == collections["pages"]
    assert native_types["TableItem"] == collections["tables"]
    assert native_types["PictureItem"] == collections["pictures"]
    receipt = {
        "outcome": "passed",
        "date": "2026-11-01",
        "scope": "actual retained whole-book native graph hydration and PDF22 record/IPC lowering only",
        "not_exercised": ["fresh inference", "page assembly/raster streaming", "PostgreSQL adoption", "global reading-order construction", "integrated companion graph"],
        "source": {
            "database": "corpus_pdf_20261031", "task_id": 2, "product_key": "native",
            "content_digest": content_digest, "source_digest": source_digest,
            "native_json_text_bytes": native_bytes,
            "native_json_text_sha256": native_text_digest,
            "schema_digest": schema, "recipe_digest": recipe_digest,
            "release_id": release_id,
            "retained_health_ready": health.get("ready"),
        },
        "native_collections": collections,
        "native_record_types": dict(sorted(native_types.items())),
        "rows_by_family": dict(sorted(counts.items())),
        "ipc_files": ipc_files,
        "ipc_bytes": ipc_bytes,
        "largest_batch_bytes": largest_batch,
        "profile_max_batch_bytes": MAX_BATCH_BYTES,
        "elapsed_seconds": {
            "read_only_fetch": fetched-started,
            "hydrate_and_gc": hydrated-fetched,
            "lower_and_verify_ipc": finished-hydrated,
            "total": finished-started,
        },
        "max_rss_kib_after_hydration": hydrate_rss,
        "max_rss_kib_total": rss_kib(),
        "residual_global_graph": "materialized; this does not establish bounded book-size graph memory",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == "__main__":
    main()
