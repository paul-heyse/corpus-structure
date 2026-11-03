"""Actual pinned local spaCy annotation on one retained statistics paragraph.

Run with the repository preparation environment. The source is a detached pinned
development artifact, not a reference answer. Every attempt creates new files.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import time
import traceback
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import spacy

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile, annotate
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, SentenceConfig, make_doc, pipeline, prepare_layout
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_contexts import NativeSourcePin


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    if not args.attempt.isdecimal():
        parser.error("attempt must be a unique decimal number")
    root = Path(__file__).resolve().parent
    source_path = root / "source-paragraph.json"
    receipt_path = root / f"attempt-{int(args.attempt):05d}.json"
    products_path = root / f"products-{int(args.attempt):05d}.json"
    if receipt_path.exists() or products_path.exists():
        raise FileExistsError("attempt artifacts already exist; use a new attempt number")
    profile = AnnotationProfile()
    source = json.loads(source_path.read_text())
    started = time.monotonic()
    receipt = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "claim": "actual local annotation availability, literal coordinates and batching only; no linguistic accuracy, speed benefit, model recall or assembled M1 qualification",
        "source_artifact_sha256": sha(source_path),
        "source_pin": source["pin"],
        "source_snapshot_sha256": source["source_snapshot_sha256"],
        "source_start": source["start"],
        "source_end": source["end"],
        "input_text_sha256": hashlib.sha256(source["text"].encode()).hexdigest(),
        "profile": profile.identity(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "device": "cpu",
        "versions": {name: importlib.metadata.version(name) for name in
                     ("spacy", "en-core-web-sm", "numpy", "thinc", "srsly")},
        "producer_path": str(Path(annotations.__file__).resolve()),
        "producer_sha256": sha(Path(annotations.__file__)),
        "script_sha256": sha(Path(__file__)),
        "documentation": {
            "context7_refreshed": "2026-11-03",
            "library": "/websites/spacy_io",
            "sources": ["https://spacy.io/api/language#pipe", "https://spacy.io/api/doc#has_annotation"],
            "installed_language_sha256": sha(Path(spacy.__file__).parent / "language.py"),
            "installed_doc_source_sha256": sha(Path(spacy.__file__).parent / "tokens" / "doc.pyx"),
        },
    }
    try:
        spacy.require_cpu()
        nlp = pipeline(profile.configuration)
        assert pipeline(profile.configuration) is nlp
        assert SentenceConfig().exclude == ("ner", "lemmatizer")
        assert "lemmatizer" in nlp.pipe_names
        block = Block(source["text"], (), (), ())
        layout = prepare_layout(nlp, block, start=source["start"])
        assert make_doc(nlp, block, layout, start=source["start"]).text == source["text"]
        raw_pin = source["pin"]
        pin = NativeSourcePin(
            raw_pin["id"], raw_pin["key"], ProductReference(**raw_pin["native_product"]),
            raw_pin["section_pointer"], raw_pin["membership"], raw_pin["projection_digest"],
            raw_pin["recipe_digest"], 3,
        )
        request = AnnotationInput(
            pin, "retained-paragraph:29-468", "paragraph", block, layout,
            tuple(ProjectedPiece(**piece) for piece in source["pieces"]),
        )
        tokenizer = nlp.tokenizer

        def refused_tokenizer(text):
            raise AssertionError("prepared Doc was retokenized")

        nlp.tokenizer = refused_tokenizer
        try:
            products = tuple(annotate((request, request), profile))
        finally:
            nlp.tokenizer = tokenizer
        assert len(products) == 2 and products[0] == products[1]
        product = products[0]
        assert all(column.status == "complete" for column in product.availability)
        assert [(token.start, token.end) for token in product.tokens] == [
            (token.start, token.end) for token in layout.tokens
        ]
        assert product.source == pin
        assert all(0 <= token.head < len(product.tokens) for token in product.tokens)
        assert product.block_start == source["start"] and product.block_end == source["end"]
        with products_path.open("x") as output:
            json.dump([asdict(product) for product in products], output, ensure_ascii=False, indent=2)
            output.write("\n")
        receipt.update(
            outcome="passed", products_sha256=sha(products_path), products=2,
            tokens_per_product=len(product.tokens),
            sentences=[asdict(sentence) for sentence in product.sentences],
            availability=[asdict(column) for column in product.availability],
            dependency_digest=product.dependency_digest,
            profile_digest=product.profile_digest,
            pipeline_config_digest=product.pipeline_config_digest,
            components=[asdict(component) for component in product.components],
            prepared_doc_tokenization_bypassed=True,
            resident_pipeline_reused=True,
        )
    except Exception as error:
        receipt.update(outcome="failed", error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
    receipt["wall_seconds"] = time.monotonic() - started
    with receipt_path.open("x") as output:
        json.dump(receipt, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({name: receipt[name] for name in ("outcome", "wall_seconds")}))
    if receipt["outcome"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
