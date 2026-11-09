"""Read the retained definition annotation and diagnose one exact token boundary."""

import argparse
import re
from dataclasses import asdict
from pathlib import Path

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import (
    Block,
    SentenceConfig,
    TextLayout,
    TextToken,
    boundaries,
    make_doc,
    pipeline,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import load_structural_annotations
from corpus_structure.settings import Settings
from spacy.pipeline import Sentencizer

DEFAULT_INPUT = (
    Path(__file__).resolve().parents[1] / "2026-11-09_pm2-adoption/raw/target-inputs.json"
)


def annotation_rows(tokens, text, start):
    return [
        dict(index=index, text=text[token.start - start : token.end - start], **asdict(token))
        for index, token in enumerate(tokens)
    ]


def prepared_layout(product, text, *, split):
    tokens = []
    changed = []
    for row in product.tokens:
        original = TextToken(row.start, row.end, row.space, row.role)
        literal = text[row.start - product.block_start : row.end - product.block_start]
        if split and len(row.piece_indices) == 2 and re.fullmatch(r"[A-Za-z]\.", literal):
            left, right = (product.native_pieces[i] for i in row.piece_indices)
            if (
                left.kind == right.kind == "native_text"
                and left.end == right.start == row.start + 1
            ):
                tokens.extend(
                    (
                        TextToken(row.start, left.end, False, row.role),
                        TextToken(right.start, row.end, row.space, "prose"),
                    )
                )
                changed.append([row.start, left.end, row.end])
                continue
        tokens.append(original)
    layout = TextLayout(
        product.block_start,
        product.block_end,
        product.text_digest,
        tuple(tokens),
        product.display_spans,
        product.layout_recipe,
    )
    return layout, changed


def rerun(product, text, nlp, *, split, prespecify_sentences):
    start = product.block_start
    block = Block(
        text,
        [(t.start - start, t.end - start) for t in product.tokens if t.role == "math"],
        [(a - start, b - start) for a, b in product.display_spans],
        [(t.start - start, t.end - start) for t in product.tokens if t.role == "reference"],
    )
    layout, changed = prepared_layout(product, text, split=split)
    doc = make_doc(nlp, block, layout, start=start, recipe=product.layout_recipe)
    if prespecify_sentences:
        Sentencizer(overwrite=False)(doc)
    doc = nlp(doc)
    if doc.text != text:
        raise ValueError("diagnostic parse did not preserve the source text")
    return {
        "changed_boundaries": changed,
        "sentences": [(start + a, start + b, text[a:b]) for a, b in boundaries(block, doc)],
        "tokens": [
            {
                "index": token.i,
                "start": start + token.idx,
                "end": start + token.idx + len(token),
                "text": token.text,
                "lemma": token.lemma_,
                "pos": token.pos_,
                "dependency": token.dep_,
                "head": token.head.i,
                "sentence_start": token.sent.start,
            }
            for token in doc
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--target", default="binomial-distribution")
    args = parser.parse_args()
    inputs = StructuralInput.model_validate_json(args.inputs.read_bytes())
    (passage,) = [p for p in inputs.passages if p.passage_id == args.target]
    (source,) = [source for source in inputs.sources if source.identity == passage.source_ref]
    profile = AnnotationProfile(SentenceConfig(exclude=("ner",)))
    with (
        open_runtime_engine(Settings(), "pm2-definition-prerequisite", purpose="read") as reader,
        read_snapshot(reader) as conn,
    ):
        retained = load_structural_annotations(conn, inputs, passage.source_ref, profile)
    if retained.errors or retained.annotation_task_id is None:
        raise ValueError("exact retained annotation is unavailable")
    if retained.source.text[passage.start : passage.end] != passage.text:
        raise ValueError("the source selection differs from the retained projection")
    (product,) = [
        product
        for product in retained.annotations
        if product.block_start <= passage.start < passage.end <= product.block_end
    ]
    text = retained.source.text[product.block_start : product.block_end]
    nlp = pipeline(profile.configuration)
    outcome = {
        "source": source.model_dump(mode="json"),
        "annotation_task": retained.annotation_task_id,
        "block": product.block_id,
        "dependency_digest": product.dependency_digest,
        "pipeline": profile.configuration.model_dump(mode="json"),
        "pieces": [asdict(piece) for piece in product.native_pieces],
        "retained": {
            "sentences": [
                (s.start, s.end, retained.source.text[s.start : s.end]) for s in product.sentences
            ],
            "tokens": annotation_rows(product.tokens, text, product.block_start),
        },
        "original_layout": rerun(product, text, nlp, split=False, prespecify_sentences=False),
        "boundary_split": rerun(product, text, nlp, split=True, prespecify_sentences=False),
        "boundary_split_with_sentencizer": rerun(
            product, text, nlp, split=True, prespecify_sentences=True
        ),
    }
    print(canonical_bytes(outcome).decode())


if __name__ == "__main__":
    main()
