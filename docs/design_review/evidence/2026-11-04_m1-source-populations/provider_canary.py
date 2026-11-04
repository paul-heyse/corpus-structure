"""Three source-only pages through existing native and managed recognition operations."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import time
from contextlib import contextmanager
from dataclasses import asdict, replace
from hashlib import file_digest
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SERVICE = ROOT / "services/nemotron-parse"
ENDPOINT = "http://127.0.0.1:8135/v1"


def retain(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def digest(path):
    with Path(path).open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


@contextmanager
def owned_service(output):
    """Launch only an absent dedicated port; retain and settle this process group."""
    output.mkdir(exist_ok=False)
    with socket.socket() as check:
        check.bind(("127.0.0.1", 8135))
    launch = [
        str(SERVICE / ".venv/bin/python"),
        str(SERVICE / "launch.py"),
        "--export",
        str(Path.home() / ".cache/corpus-structure/nemotron-parse-4035ffb"),
        "--runtime",
        str(SERVICE / ".venv/bin/vllm"),
        "--receipts",
        str(output / "generations"),
        "--port",
        "8135",
    ]
    retain(output / "invocation.json", {"argv": launch, "scope": "Owned source intake only"})
    with (output / "startup.log").open("x") as log:
        process = subprocess.Popen(
            launch, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        retain(output / "owned-process.json", {"pid": process.pid, "process_group": process.pid})
        try:
            started = time.monotonic()
            while time.monotonic() - started < 600:
                if process.poll() is not None:
                    raise RuntimeError(f"Owned service stopped at startup: {process.returncode}")
                try:
                    response = httpx.get("http://127.0.0.1:8135/health", timeout=3)
                    if response.status_code == 200:
                        generation = httpx.get(
                            "http://127.0.0.1:8135/corpus/generation", timeout=3
                        )
                        generation.raise_for_status()
                        retain(output / "generation.json", generation.json())
                        print("owned service8135 ready", flush=True)
                except httpx.HTTPError:
                    time.sleep(2)
                    continue
                if response.status_code == 200:
                    yield generation.json()
                    return
                time.sleep(2)
            raise TimeoutError("Managed startup exceeded600seconds")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=30)
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            retain(output / "settlement.json", {"pid": process.pid, "returncode": process.returncode, "owned_parent_settled": process.poll() is not None})


def canary(output):
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
    from corpus_structure.ingest.pdf_capacity import native_before_nemotron
    from corpus_structure.ingest.pdf_recognition import (
        NemotronRecipe,
        PreparedRecognitionSource,
        RecognitionWorker,
    )
    from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource
    from corpus_structure.ingest.pdf_worker import PdfWorker
    from corpus_structure.semantic.pdf_payloads import prepare_payload_family, schema_dump

    population = json.loads((HERE / "source-population.json").read_text())
    cases = list(zip(population["sources"], (8, 4, 8), strict=True))
    family = prepare_payload_family()
    schema = schema_dump(family.json_schema)
    (output / "payload.schema.json").write_bytes(schema)
    recipe = PdfRecipe(
        "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8",
        "ecedbe111d15c2dc60bfd4a823cbe80127b58af4",
        recipe_id="docling-standard-pdf-stream-v1",
    )
    assets = prepare_pdf_assets(recipe, cache=Path.home() / ".cache/docling/models", offline=True)
    recipe = replace(recipe, model_artifacts=assets.files, model_revisions=assets.repositories)
    (output / "native-recipe.json").write_bytes(recipe.to_bytes())
    report = {"scope": "Three real detached source-page canaries; no publication, labels, predictions or family-quality claim", "cases": []}
    with owned_service(output / "service") as generation:
        with native_before_nemotron(ENDPOINT):
            worker = PdfWorker(recipe, assets=assets)
            try:
                for source, number in cases:
                    root = output / source["origin_group"]
                    root.mkdir()
                    path = ROOT / source["excerpt"]["path"]
                    started = time.monotonic()
                    with OwnedPdfSource.acquire(path, root / "source", expected_digest=source["excerpt"]["sha256"]) as original:
                        result = worker.stream(
                            original,
                            spool_root=root / "native-pages",
                            record_root=root / "native-records",
                            build_id="m1-source-canary-" + source["origin_group"],
                            release_id="detached-source-observation-not-admitted",
                            on_replay=lambda replay: replay.verify(),
                            page_range=(number, number),
                            payload_schema=schema,
                        )
                    row = {"origin_group": source["origin_group"], "excerpt_page": number,
                           "parent_page": source["excerpt"]["page_map"][number - 1]["parent_physical_page"],
                           "native_status": result.conversion_status, "native_errors": result.errors,
                           "native_seconds": time.monotonic() - started,
                           "native_page_replays": [asdict(replay) for replay in result.page_replays],
                           "native_record_replays": [asdict(replay) for replay in result.record_replays]}
                    retain(root / "native-result.json", row)
                    report["cases"].append(row)
                    print(f"native {source['origin_group']}:{number} {result.conversion_status}", flush=True)
                    if result.conversion_status != "success":
                        raise RuntimeError("Source native canary did not succeed")
            finally:
                worker.close()
        recognition_recipe = NemotronRecipe(
            generation["artifacts"]["model.safetensors"],
            generation["artifacts"]["tokenizer.json"],
            identity_assurance="trusted_managed_service",
        )
        (output / "recognition-recipe.json").write_bytes(recognition_recipe.to_bytes())
        recognizer = RecognitionWorker(
            python=SERVICE / ".venv/bin/python", script=SERVICE / "worker.py",
            endpoint=ENDPOINT, receipts=output / "recognition", timeout_seconds=1800,
        )
        for (source, number), row in zip(cases, report["cases"], strict=True):
            started = time.monotonic()
            prepared = PreparedRecognitionSource.prepare((ROOT / source["excerpt"]["path"]).read_bytes())
            (page,) = tuple(recognizer.recognize_pages(prepared, recognition_recipe, (number,), reuse=False))
            row["recognition_result"] = page.result
            row["recognition_seconds"] = time.monotonic() - started
            row["request_count"] = len(list(page.requests()))
            row["recognition_succeeded"] = page.succeeded
            retain(output / source["origin_group"] / "recognition-result.json", row)
            print(f"recognition {source['origin_group']}:{number} succeeded={page.succeeded} requests={row['request_count']}", flush=True)
        report["outcome"] = "passed" if all(row["recognition_succeeded"] for row in report["cases"]) else "failed"
    retain(output / "result.json", report)
    print(json.dumps({"outcome": report["outcome"], "cases": len(report["cases"])}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    try:
        canary(output)
    except BaseException as error:
        retain(output / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise


if __name__ == "__main__":
    main()
