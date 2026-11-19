"""Shared controlled inputs and builders for formal products support."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FrozenFormalSource,
    formal_product_inputs,
    prepare_formal_evidence,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


@lru_cache(maxsize=1)
def released_profile():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.formal_products import formal_operation_sources
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(), python_sources=formal_operation_sources()
        ),
        PreparationProfile(version="semantic-2"),
    )
    return prepare_formal_evidence(
        prepared, bound_data_operation_model(prepared), grammar=grammar_identity()
    )


@pytest.fixture(scope="module")
def profile():
    return released_profile()


def selected(profile, text="Quantity: 2 kg\nusing the equation x = 2.", **changes):
    value = dict(
        source=dict(
            document="document:original-content",
            section_pointer="#/groups/0",
            membership="descendants",
            projection="b" * 64,
        ),
        text=text,
        pieces=[
            dict(
                kind="native_text",
                start=0,
                end=len(text),
                item_ref="#/texts/0",
                source_field="text",
            )
        ],
        items=[
            dict(self_ref="#/texts/0", label="text", text=text, orig=text, prov=[dict(page_no=1)])
        ],
        recognition=[],
        selectors=[dict(projection="b" * 64, native_pointer="#/texts/0", start=0, end=len(text))],
    )
    value.update(changes)
    return acquire_source(profile, value)


def acquire_source(profile, value):
    from corpus_structure.semantic.source_products import native_projection_identity

    projection = native_projection_identity(
        value["text"],
        value["pieces"],
        value["items"],
        value.get("recognition", ()),
        value.get("ancestors", ()),
    )
    from corpus_structure.semantic.original_documents import original_document_subject

    value["source"]["document_subject"] = original_document_subject(value["source"]["document"])
    value["source"]["projection"] = projection
    for selector in value["selectors"]:
        selector["projection"] = projection
    return FrozenFormalSource.acquire(profile.prepared, value)


def selected_rows(profile, *rows):
    """Literal original/recognition inputs, without a historical task or layer address."""
    text, pieces, items, recognition, selectors = "", [], [], [], []
    for index, (surface, label, latex, health) in enumerate(rows):
        if index:
            pieces.append(dict(kind="synthetic_separator", start=len(text), end=len(text) + 1))
            text += "\n"
        pointer = f"#/texts/{index}"
        start = len(text)
        if surface:
            pieces.append(
                dict(
                    kind="native_text",
                    item_ref=pointer,
                    source_field="orig" if label == "formula" else "text",
                    start=start,
                    end=start + len(surface),
                )
            )
        text += surface
        items.append(
            dict(
                self_ref=pointer,
                label=label,
                text=latex if label == "formula" else surface,
                orig=surface,
                prov=[dict(page_no=index + 1)],
            )
        )
        selector: dict[str, Any] = dict(projection="pending", native_pointer=pointer)
        if surface:
            selector.update(start=start, end=len(text))
        selectors.append(selector)
        if label == "formula":
            recognition.append(dict(pointer=pointer, outcome=health))
    return acquire_source(
        profile,
        dict(
            source=dict(
                document="document:original-content",
                section_pointer="#/groups/0",
                membership="descendants",
                projection="pending",
            ),
            text=text,
            pieces=pieces,
            items=items,
            recognition=recognition,
            selectors=selectors,
        ),
    )


def publication_context(source):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_products import source_subject

    value = source.value
    return SubjectContext(
        "fixture:formal",
        source_subject(value["source"]),
        value["source"]["document"],
        canonical_bytes(dict(source=value["source"], selectors=value["selectors"])),
        subject_definition="original-source-view",
    )
