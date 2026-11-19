"""Shared authored scenarios and fixtures for sentence products test support."""

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.sentence_products import (
    prepare_sentence_profile,
    sentence_operation_sources,
    sentence_product_inputs,
)
from corpus_structure.semantic.source_products import FrozenNativeSource, native_projection_identity
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


@pytest.fixture(scope="module")
def nominal_schema():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = sentence_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    return bundle, prepare_release(bundle)


@pytest.fixture(scope="module")
def nominal_profile(nominal_schema):
    """Schema-only membership checks require no acquired provider or execution claim."""
    bundle, prepared = nominal_schema
    model = compile_data_operations(
        schema=bundle,
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    return SimpleNamespace(prepared=prepared, model=model)


@pytest.fixture(scope="module")
def profile(nominal_schema):
    bundle, prepared = nominal_schema
    model = compile_data_operations(
        schema=bundle,
        python_sources=sentence_operation_sources(),
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    return prepare_sentence_profile(prepared, model)


def selected(profile, text="The mean is 2. The variance is 4."):
    pieces = (
        [
            dict(
                kind="native_text",
                start=0,
                end=len(text),
                item_ref="#/texts/0",
                source_field="text",
            )
        ]
        if text
        else []
    )
    items = (
        [dict(self_ref="#/texts/0", label="text", text=text, orig=text, prov=[dict(page_no=1)])]
        if text
        else []
    )
    from corpus_structure.semantic.original_documents import original_document_subject

    projection = native_projection_identity(text, pieces, items, [])
    return FrozenNativeSource.acquire(
        profile.prepared,
        dict(
            source=dict(
                document="document:" + sha256(text.encode()).hexdigest(),
                document_subject=original_document_subject(
                    "document:" + sha256(text.encode()).hexdigest()
                ),
                section_pointer="#/groups/0",
                membership="descendants",
                projection=projection,
            ),
            text=text,
            pieces=pieces,
            items=items,
            recognition=[],
            selectors=[
                dict(projection=projection, **(dict(native_pointer="#/texts/0") if text else {}))
            ],
        ),
    )


def publication_context(source, *, document=False):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_products import source_subject

    value = source.value
    return SubjectContext(
        "family-test",
        value["source"]["document"] if document else source_subject(value["source"]),
        value["source"]["document"],
        canonical_bytes({"source": value["source"], "selectors": value["selectors"]}),
        subject_definition="original-source-view",
    )


def controlled_source_pin(source):
    """Controlled input identity for provider checks; no native original-custody claim."""
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.declared_record_sources import (
        DeclaredRecordSource,
        DeclaredSourcePin,
    )

    context = publication_context(source)
    member = BoundRoleMember(
        "controlled-original",
        "controlled-kind",
        context.subject,
        context.original_source,
        context.analyzed_scope,
        b"{}",
        (),
        b"{}",
        subject_definition="original-source-view",
        support_references=(),
    )
    return DeclaredSourcePin(
        canonical_bytes(
            DeclaredRecordSource.from_bound(source, member, project=context.project_id).pin()
        ).decode()
    )
