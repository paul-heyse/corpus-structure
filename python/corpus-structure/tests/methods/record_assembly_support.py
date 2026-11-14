"""Controlled inputs and builders shared by the record assembly consumers."""

import json
from functools import cache
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice

ROOT = Path(__file__).resolve().parents[4]


@cache
def release():
    return prepare_release(
        observation_inputs(
            SourceBundle(
                "statistics_semantic",
                (
                    SourceArtifact(
                        "statistics_semantic",
                        (ROOT / "domains/statistics/semantic.yaml").read_bytes(),
                    ),
                    SourceArtifact(
                        "statistics_terminology",
                        (ROOT / "domains/statistics/terminology.yaml").read_bytes(),
                    ),
                    SourceArtifact(
                        "semantic_core",
                        (
                            ROOT
                            / "python/corpus-structure/src/corpus_structure"
                            / "model/semantic/core.yaml"
                        ).read_bytes(),
                    ),
                ),
            )
        )
    )


def source(text, *, identity=1, pieces=None, items=None, ancestors=("#/groups/1",)):
    pieces = pieces or [
        dict(
            kind="native_text",
            item_ref=f"#/texts/{identity}",
            start=0,
            end=len(text),
            source_field="text",
        )
    ]
    items = items or [dict(self_ref=f"#/texts/{identity}", text=text)]
    native = dict(
        pieces=pieces,
        items=items,
        ancestors=[dict(self_ref=pointer) for pointer in ancestors],
        health={"inline_coverage": "unknown"},
    )
    projection = dict(
        text=text,
        pieces=pieces,
        items=[item["self_ref"] for item in items],
        ancestors=list(ancestors),
        health=native["health"],
    )
    return NativeFrameSource(
        f"unit:{identity}",
        text,
        (),
        identity,
        ProductReference(17, "integrated", "a" * 64),
        "#/groups/1",
        "direct",
        sha256(canonical_bytes(projection)).hexdigest(),
        "c" * 64,
        canonical_bytes(native).decode(),
        version=3,
    )


def context(text, **kwargs):
    primary = source(text, **kwargs)
    return NativeSourceContext(
        primary,
        (),
        (SourceSlice(primary.source_view_id, 0, len(text)),),
        "independent reading",
        "test-policy",
        "explicit source selection",
    )


def report(ctx, pack, family, groups):
    return GlinerReport(
        ctx.dependency_digest,
        ctx.dependency_digest,
        "compute:fixture",
        "profile:fixture",
        pack.fingerprint,
        GlinerPreparation(ctx.text, "", 1, 1, len(ctx.text.encode())),
        json.dumps({family: groups}),
        "{}",
        0.0,
        False,
    )


def fields(record):
    return {field["role"]: field for field in record.model_dump(mode="python")["fields"]}


def span(start, end, text):
    return dict(start=start, end=end, text=text)
