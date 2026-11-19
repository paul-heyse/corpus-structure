"""Controlled inputs and builders shared by the record assembly consumers."""

import json
from functools import cache
from pathlib import Path

from statistics_pack_support import statistics_bundle

from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    source_slice,
)
from corpus_structure.semantic.source_products import FrozenNativeSource, source_product_inputs

ROOT = Path(__file__).resolve().parents[4]


@cache
def bundle():
    return source_product_inputs(observation_inputs(statistics_bundle()))


@cache
def release():
    return prepare_release(bundle())


@cache
def model():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations

    return compile_data_operations(bundle())


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
    items = items or [dict(label="text", self_ref=f"#/texts/{identity}", text=text)]
    native = FrozenNativeSource.from_projection(
        release(),
        document="document:record-fixture",
        section_pointer="#/groups/1",
        membership="direct",
        text=text,
        pieces=pieces,
        items=items,
        ancestors=[dict(label="group", self_ref=pointer) for pointer in ancestors],
    )
    member = BoundRoleMember(
        f"product:record-source:{identity}",
        "kind:native-source",
        f"subject:section:{identity}",
        "document:record-fixture",
        canonical_bytes(dict(source=native.value["source"], selectors=native.value["selectors"])),
        b"{}",
        (),
        b"{}",
        member=f"member:section:{identity}",
        subject_definition="original-source-view",
        support_references=(),
    )
    return DeclaredNativeFrameSource.acquire(
        release(), native.value, member, project="project:record-fixture"
    )


def context(text, **kwargs):
    primary = source(text, **kwargs)
    return NativeSourceContext(
        primary,
        (),
        (source_slice(primary, 0, len(text)),),
        "independent reading",
        "test-policy",
        "explicit source selection",
        version=2,
        preparation=PreparedNativeSources((primary,)),
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
