"""Read-only replay of failed book task 86; no inference or protected publication.

Uses exact admitted task/config/native/input pins. The retained payload is an
evidence artifact so later shape/SQL diagnosis never needs another selection run.
"""
from __future__ import annotations

import gzip
import heapq
import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine, text

from corpus_structure.ingest.pdf_recognition import repetition_recovery_recipe
from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated, PdfIntegratedIngestConfig
from corpus_structure.ingest.pdf_reconciliation import select_pdf_integration
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_contracts import pdf_context_for_task

TASK = 86
RUN = 13
URL = "postgresql+psycopg://corpus_sem_reader@/corpus_pdf_20261031?host=/var/run/postgresql&port=5434"
OUT = Path(__file__).with_name("raw")
PAYLOAD = OUT / "book-task86-prepared.json.gz"
SUMMARY = OUT / "book-task86-prepared-sizes.json"


def reconstruct():
    engine = create_engine(URL)
    try:
        with engine.connect() as conn, conn.begin():
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")
            row = conn.execute(text("""
              SELECT t.run_id,m.params,b.recipe_digest FROM ops.task t
              JOIN ops.method_config m ON m.id=t.method_config_id
              JOIN ops.source_build b ON b.task_id=t.id WHERE t.id=:task
            """), {"task": TASK}).mappings().one()
            assert row["run_id"] == RUN
            cfg = PdfIntegratedIngestConfig.model_validate(row["params"])
            assert cfg.native_product is not None and cfg.integrated_product is None
            recipe_bytes = IngestPdfIntegrated().original_recipe(cfg)
            assert sha256(recipe_bytes).hexdigest() == row["recipe_digest"]
            pin = cfg.native_product.values()
            assert pin == {"task_id": 7, "product_key": "math-enriched", "content_digest": "8468df6fb3af853b1d0757b18facc7ecd2ff25fa301e8f4b8e05aa2930b6948d"}
            native_row = conn.execute(text("""
              SELECT payload,schema_digest,recipe_digest FROM ops.native_document_product
              WHERE task_id=:task_id AND product_key=:product_key AND content_digest=:content_digest
            """), pin).mappings().one()
            native_payload = bytes(native_row["payload"])
            assert sha256(native_payload).hexdigest() == pin["content_digest"]
            native = json.loads(native_payload)
            context = pdf_context_for_task(conn, TASK)
            rows = conn.execute(text("""
              SELECT p.product_key,p.content_digest,b.payload FROM ops.pdf_product p
              JOIN ops.pdf_product_body b USING(task_id,product_key)
              WHERE p.task_id=:task AND p.kind='recognition_observation'
            """), {"task": TASK}).mappings().all()
            observations = []
            for captured in rows:
                payload = bytes(captured["payload"])
                assert sha256(payload).hexdigest() == captured["content_digest"]
                value = json.loads(payload)
                observations.append((
                    {"task_id": TASK, "product_key": captured["product_key"], "content_digest": captured["content_digest"]},
                    value,
                ))
            digests = {
                native["artifact_digest"], native_row["schema_digest"], native_row["recipe_digest"],
                *(value["observation"]["raw_response_digest"] for _, value in observations
                  if value["observation"].get("raw_response_digest")),
            }
            artifacts = {
                digest: bytes(content) for digest, content in conn.execute(text("""
                  SELECT artifact_digest,content FROM kb.source_artifact WHERE artifact_digest=ANY(:digests)
                """), {"digests": list(digests)})
            }
            assert set(artifacts) == digests
            assert all(sha256(content).hexdigest() == digest for digest, content in artifacts.items())
    finally:
        engine.dispose()

    # _parallel_pages yields in requested order (its pending deque is not as_completed).
    # _retain_page yields request ordinals; eligible recovery follows the failed primary page.
    requested = cfg.recognition_pages or tuple(sorted(int(p) for p in native["document"]["pages"]))
    ranks = {page: rank for rank, page in enumerate(requested)}
    primary = cfg.recognition_recipe().digest
    recovery = repetition_recovery_recipe(cfg.recognition_recipe()).digest
    attempts = {}
    def order(entry):
        retained_pin, value = entry
        page = value["observation"]["image"]["page_no"]
        digest = value["recipe_digest"]
        assert page in ranks and digest in {primary, recovery}
        prefix, ordinal = retained_pin["product_key"].rsplit(":request:", 1)
        attempt = prefix.rsplit(":", 1)[1]
        attempts.setdefault((page, digest), set()).add(attempt)
        return ranks[page], digest != primary, int(ordinal)
    observations.sort(key=order)
    assert all(len(names) == 1 for names in attempts.values())
    assert {value["observation"]["image"]["page_no"] for _, value in observations} == set(requested)
    ordered = [
        (retained_pin, value, artifacts.get(value["observation"].get("raw_response_digest"), b""))
        for retained_pin, value in observations
    ]
    provenance = {
        "task_id": TASK, "run_id": RUN, "native_pin": pin,
        "release_id": context.release_id, "contract_digest": context.contract_digest,
        "config_digest": sha256(canonical_bytes(cfg.model_dump(mode="json"))).hexdigest(),
        "recipe_digest": sha256(recipe_bytes).hexdigest(),
        "observation_count": len(ordered), "physical_pages": len(requested),
        "ordered_input_digest": sha256(canonical_bytes([p for p, _, _ in ordered])).hexdigest(),
        "primary_recipe": primary, "recovery_recipe": recovery,
    }
    print(json.dumps({"stage": "retained_inputs_loaded", **provenance}), flush=True)
    selected = select_pdf_integration(
        native, pin, ordered, artifacts[native["artifact_digest"]], recipe_bytes,
        artifacts[native_row["schema_digest"]], policy=cfg.integration_policy, context=context,
    )
    return selected.payload, provenance


def measure(payload, provenance):
    value = json.loads(payload)
    largest_arrays = []
    def size(item, path):
        if isinstance(item, dict):
            return 2 + max(0, len(item)-1) + sum(
                len(canonical_bytes(key)) + 1 + size(child, f"{path}/{key}")
                for key, child in item.items()
            )
        if isinstance(item, list):
            lengths = [size(child, f"{path}/{index}") for index, child in enumerate(item)]
            total = 2 + max(0, len(item)-1) + sum(lengths)
            entry = (total, path, len(item))
            if len(largest_arrays) < 30:
                heapq.heappush(largest_arrays, entry)
            elif total > largest_arrays[0][0]:
                heapq.heapreplace(largest_arrays, entry)
            return total
        return len(canonical_bytes(item))
    assert size(value, "") == len(payload)
    fields = {}
    for name, item in value.items():
        encoded = canonical_bytes(item)
        details = {"canonical_bytes": len(encoded), "sha256": sha256(encoded).hexdigest()}
        if isinstance(item, list):
            details["array_count"] = len(item)
            top = []
            for index, entry in enumerate(item):
                entry_bytes = canonical_bytes(entry)
                measured = (len(entry_bytes), index, sha256(entry_bytes).hexdigest())
                if len(top) < 10:
                    heapq.heappush(top, measured)
                elif measured[0] > top[0][0]:
                    heapq.heapreplace(top, measured)
            details["largest_entries"] = [
                {"path": f"/{name}/{index}", "canonical_bytes": count, "sha256": digest}
                for count, index, digest in sorted(top, reverse=True)
            ]
        fields[name] = details
    return {
        **provenance, "payload_sha256": sha256(payload).hexdigest(), "payload_bytes": len(payload),
        "compressed_path": str(PAYLOAD), "compressed_bytes": PAYLOAD.stat().st_size,
        "top_fields": fields,
        "largest_arrays": [
            {"path": path, "canonical_bytes": count, "array_count": entries}
            for count, path, entries in sorted(largest_arrays, reverse=True)
        ],
    }


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    if PAYLOAD.exists():
        payload = gzip.decompress(PAYLOAD.read_bytes())
        provenance = json.loads(SUMMARY.read_bytes()) if SUMMARY.exists() else {"task_id": TASK, "run_id": RUN}
    else:
        payload, provenance = reconstruct()
        with PAYLOAD.open("xb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as archive:
            archive.write(payload)
        print(json.dumps({"stage": "canonical_payload_retained", "bytes": len(payload), "sha256": sha256(payload).hexdigest(), "path": str(PAYLOAD)}), flush=True)
    summary = measure(payload, provenance)
    SUMMARY.write_bytes(canonical_bytes(summary))
    print(json.dumps({"stage": "measured", "summary_path": str(SUMMARY), "payload_bytes": summary["payload_bytes"], "largest_arrays": summary["largest_arrays"][:5]}), flush=True)
