"""Explicit source fixtures through the actual formal producer, without providers."""

from functools import lru_cache
from pathlib import Path

from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.formal_evidence import build_formal_layer, grammar_identity
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView


@lru_cache(maxsize=1)
def release():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


def formal_layers(inputs):
    layers = {}
    for source in inputs.sources:
        passages = sorted(
            (passage for passage in inputs.passages if passage.source_ref == source.identity),
            key=lambda passage: passage.start,
        )
        if not passages:
            continue
        size = max(passage.end for passage in passages)
        text = [" "] * size
        pieces, items = [], []
        for number, passage in enumerate(passages):
            text[passage.start : passage.end] = passage.text
            pointer = f"#/texts/{number}"
            pieces.append(
                dict(
                    kind="native_text",
                    source_field="text",
                    item_ref=pointer,
                    start=passage.start,
                    end=passage.end,
                )
            )
            items.append(dict(self_ref=pointer, label="text", text=passage.text))
        view = PreparedSourceView(
            SourceViewRef(
                source.source_view_id,
                "formal-fixture",
                1,
                ProductReference(
                    source.native_task_id, source.native_product_key, source.native_content_digest
                ),
                "#/groups/0",
                "descendants",
                source.projection_digest,
                source.recipe_digest,
            ),
            "".join(text),
            tuple(pieces),
            tuple(items),
            (),
            {},
        )
        layer = build_formal_layer(
            view,
            release(),
            dict(
                key="text.formal_evidence",
                version="1",
                runtime="fixture",
                model="none",
                grammar=grammar_identity(),
                configuration="fixture",
                input="fixture",
                context="source-only",
            ),
        )
        layers[layer.reference(1000 + source.source_view_id)] = layer
    return layers
