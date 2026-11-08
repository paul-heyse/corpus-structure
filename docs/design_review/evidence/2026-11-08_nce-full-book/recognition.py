"""Prefill exact managed recognition receipts while Standard publication settles."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from intake import PARENT, PDF

from corpus_structure.ingest.pdf_recognition import PreparedRecognitionSource, RecognitionWorker
from corpus_structure.ingest.pdf_recognition_methods import PdfIntegratedIngestConfig
from corpus_structure.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    source = PreparedRecognitionSource.prepare((args.work / "corpus" / PDF).read_bytes())
    if source.digest != PARENT:
        raise ValueError("recognition input differs from the frozen full-book parent")
    settings = Settings().nemotron
    recipe = PdfIntegratedIngestConfig().recognition_recipe()
    output = args.work / "integrated-source"
    output.mkdir(exist_ok=True)
    worker = RecognitionWorker(
        python=settings.python,
        script=settings.worker,
        endpoint=settings.endpoint,
        receipts=output / "recognition",
        timeout_seconds=settings.timeout_seconds,
    )
    outcomes = Counter()
    with (output / "primary-recognition.jsonl").open("x") as receipt:
        for page in worker.recognize_pages(
            source, recipe, tuple(range(1, 519)), concurrency=4, reuse_failures=True
        ):
            requests = [
                dict(
                    kind=row["stage"],
                    outcome=row["outcome"],
                    generation=row.get("service_generation"),
                )
                for row, _, _ in page.requests()
            ]
            outcomes[page.result["outcome"]] += 1
            print(
                json.dumps(
                    dict(
                        page=page.page_no,
                        outcome=page.result["outcome"],
                        requests=requests,
                        directory=str(page.directory),
                    )
                ),
                file=receipt,
                flush=True,
            )
    print(json.dumps(dict(parent=PARENT, recipe=recipe.digest, outcomes=outcomes)), flush=True)


if __name__ == "__main__":
    main()
