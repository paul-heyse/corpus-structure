"""I24: actual selected-page custody, detached validation and columnar use.

The native producer/publication receipts own the earlier encode/COPY/frozen-validation
steps. This read-only journey retains their published locators and exact selected bytes;
it neither writes an alternate PostgreSQL representation nor benchmarks synthetic IPC.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pyarrow.compute as pc
from sqlalchemy import text

from corpus_structure.ingest.pdf_candidate_geometry import CandidateGeometry, candidate_page_status
from corpus_structure.ingest.pdf_candidate_source import ReplayCandidatePageSource
from corpus_structure.ingest.pdf_streaming import _atomic_bytes
from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
from corpus_structure.semantic.pdf_payloads import FAMILY, PROFILE, prepare_payload_family
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.pdf_storage import read_native_regions
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--producer-receipt", action="append", default=[], type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    selection = json.loads(args.selection.read_bytes())
    reference = ProductReference(**{
        key: selection[key] for key in ("task_id", "product_key", "content_digest")
    })
    os.environ["CORPUS_DATABASE__URL"] = args.database
    report = {
        "verified_at": datetime.now(UTC).isoformat(), "outcome": "partial",
        "scope": "I24 actual selected candidate page; no alternate-store or performance ranking",
        "selection": selection, "completed": [],
        "producer_receipts": [
            {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}
            for path in args.producer_receipt
        ],
    }
    try:
        with (
            open_runtime_engine(Settings(), "ci-candidate-page-journey", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            reader = PublishedPdfReader(conn, reference)
            regions = read_native_regions(
                conn, **reference.values(), pointer=selection["formula_pointer"]
            )
            if not regions:
                raise ValueError("selected formula has no physical page context")
            page_no = regions[0]["page_no"]
            page_height = regions[0]["page_height"]
            context = pdf_context_for_task(conn, reference.task_id)
            family = prepare_payload_family(context)
            rows = list(reader._metadata_rows(FAMILY, page_nos=[page_no]))
            if len(rows) != 1:
                    raise ValueError(
                        "selected page requires exactly one published candidate payload"
                    )
            row = rows[0]
            if len(row.get("_fields", ())) != 1:
                raise ValueError("selected page payload field is absent or ambiguous")
            field, = row["_fields"]
            body = row["body"]
            if (
                field["field_name"] != "value"
                or field["encoding_profile"] != PROFILE
                or body["payload_codec"] != PROFILE
            ):
                raise ValueError("selected page lacks the released Arrow encoding")
            payload = b"".join(reader.scalar(field["stream_id"]))
            # Use the actual release schema once; the same prepared object is
            # carried into the detached source after this snapshot settles.
            family.read_batch(
                payload, schema_digest=body["payload_schema_digest"],
                logical_digest=body["payload_logical_digest"],
            )
            report.update(
                revision=reader.revision, page_no=page_no, envelope=row,
                native_page_height=page_height,
                storage_policy=[dict(value) for value in conn.execute(text("""
                    SELECT n.nspname AS schema_name,c.relname,a.attname,
                           a.attstorage,a.attcompression,
                           current_setting('default_toast_compression') AS default_compression
                    FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
                    JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='ops' AND c.relname='pdf_artifact_part'
                      AND a.attname='body' AND a.attnum>0 AND NOT a.attisdropped
                """)).mappings()],
            )
            report["completed"].append("exact published selected-page retrieval and bindings")
        # Every database borrower is closed before detached decode/computation.
        replay = replace(
            _atomic_bytes(args.output / "selected-page.arrow", payload, "candidate_payload"),
            rows=1, page_no=page_no, schema_digest=body["payload_schema_digest"],
            logical_digest=body["payload_logical_digest"],
        )
        source = ReplayCandidatePageSource({page_no: replay}, family)
        batch, = source.iter_batches([page_no])
        candidate_count = pc.call_function(
            "list_value_length", [batch.column("candidates")]
        )[0].as_py() or 0
        document_context = SimpleNamespace(pages={
            page_no: SimpleNamespace(size=SimpleNamespace(height=float(page_height)))
        })
        with CandidateGeometry(document_context, source, [page_no]) as geometry:
            inventory = geometry.connection.execute("""
                SELECT count(*),count(DISTINCT candidate_index),
                       min(candidate_index),max(candidate_index) FROM candidate_geometry
            """).fetchone()
        if inventory is None:
            raise ValueError("columnar geometry inventory is unavailable")
        count, distinct_ordinals, first, last = inventory
        if count != candidate_count or distinct_ordinals != candidate_count:
            raise ValueError("columnar geometry omitted or renumbered original page candidates")
        if candidate_count and (first != 0 or last != candidate_count - 1):
            raise ValueError("original candidate ordinal universe changed")
        logical = family.decode(
            replay.path.read_bytes(), schema_digest=replay.schema_digest,
            logical_digest=replay.logical_digest,
        )
        if logical["page_no"] != page_no or len(logical.get("candidates", ())) != candidate_count:
            raise ValueError("detached logical page differs from selected columnar page")
        reencoded = family.encode(logical)
        if family.logical_digest(logical) != replay.logical_digest:
            raise ValueError("re-encoding source logical identity differs")
        # One real candidate is retained for source-custody inspection. Native font/
        # vector candidates are never relabelled as OCR words.
        candidates = logical.get("candidates", ())
        sample_index = next((index for index, value in enumerate(candidates)
                             if value.get("basis") == "ocr-word-token-v1"), 0)
        sample = candidates[sample_index] if candidates else None
        ocr_source = None
        if sample is not None and sample.get("basis") == "ocr-word-token-v1":
            region = logical["ocr_regions"][sample["ocr_region_index"]]
            line = region["lines"][sample["ocr_line_index"]]
            word = line["words"][sample["ocr_word_index"]]
            ocr_source = {"region": {
                key: value for key, value in region.items() if key != "lines"
            }, "line_text": line["text"], "word": word}
        report.update(
            outcome="passed", candidate_count=candidate_count,
            original_ordinals={"count": distinct_ordinals, "first": first, "last": last},
            availability={key: asdict(value)
                          for key, value in candidate_page_status(source, [page_no]).items()},
            sample_candidate={"original_index": sample_index, "value": sample}
            if sample is not None else None,
            sample_ocr_source=ocr_source,
            source_bytes={"sha256": replay.digest, "length": replay.byte_length},
            reencoded_default_ipc={
                "compression": None, "sha256": sha256(reencoded).hexdigest(),
                "length": len(reencoded), "same_bytes": reencoded == payload,
                "logical_digest": replay.logical_digest,
            },
            boundaries={
                "preparation": "one exact released payload family reused through detached use",
                "retrieval": (
                    "one page located before byte retrieval; parts joined into owned bytes"
                ),
                "detach": "exact bytes copied to owned replay; no database owner in source",
                "use": "Arrow list counts and existing DuckDB geometry over selected-page batches",
                "hydrate": (
                    "one selected page reconstructed explicitly for model validation/re-encode"
                ),
                "store": (
                    "published artifact located here; earlier encode/COPY/adoption and "
                    "frozen-validation execution belongs to linked native-build receipts"
                ),
                "semantic_validation": (
                    "published complete frozen validation reused; local decode checks "
                    "released JSON Schema and logical binding"
                ),
                "compression": (
                    "catalog policy is recorded; no TOAST physical-size or throughput claim"
                ),
                "comparison": (
                    "JSON/native mapping remains explicit hydration; no alternate storage "
                    "benchmark or universal codec claim"
                ),
            },
        )
        report["completed"].append("closed-reader detached validation and nested columnar use")
    except BaseException as error:
        report.update(outcome="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        (args.output / "receipt.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"outcome": report["outcome"], "receipt": str(args.output / 'receipt.json')}))


if __name__ == "__main__":
    main()
