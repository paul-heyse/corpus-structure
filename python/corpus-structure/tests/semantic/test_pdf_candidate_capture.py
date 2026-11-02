"""Database-free custody controls with real released models and retained byte profiles."""

import json
from contextlib import contextmanager
from dataclasses import replace
from functools import lru_cache
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.contracts import trusted_execution_inputs
from corpus_structure.semantic.operations import BoundReader, OperationConflict
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.pdf_storage import NativeDocumentUnavailable
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.types import (
    PreparationError,
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


@lru_cache(maxsize=4)
def released_context(schema_mode="installed", *, unsupported_read=False):
    from corpus_structure.semantic.pdf_contracts import prepare_pdf_context
    from corpus_structure.semantic.pdf_records import native_schema_bytes

    inputs = trusted_execution_inputs()
    schema = native_schema_bytes()
    if schema_mode != "installed":
        declaration = json.loads(schema)
        if schema_mode == "unsupported":
            declaration["properties"]["name"]["type"] = "integer"
        schema = json.dumps(declaration, sort_keys=True).encode()
        assert sha256(schema).hexdigest() != sha256(native_schema_bytes()).hexdigest()
        inputs = replace(
            inputs,
            implementations=tuple(
                SourceArtifact(item.name, schema)
                if item.name == "pdf/docling-validation.schema.json"
                else item
                for item in inputs.implementations
            ),
        )
    if unsupported_read:
        catalog = yaml.safe_load(inputs.catalog.content)
        binding = next(
            item for item in catalog["implementations"] if item["id"] == "read_pdf_product"
        )
        binding["version"] = "not-qualified"
        inputs = replace(
            inputs, catalog=SourceArtifact(inputs.catalog.name, yaml.safe_dump(catalog).encode())
        )
    bundle = SourceBundle(
        "candidate",
        (
            SourceArtifact(
                "candidate",
                b"""id: https://example.org/candidate
name: candidate
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Thing:
  attributes:
   label: {range: string}
""",
            ),
        ),
    )
    prepared = prepare_release(
        bundle,
        composed_dependencies(ResolvedDependencies(), inputs),
        PreparationProfile(version="semantic-2"),
    )
    staging = next(item for item in inputs.implementations if item.name == "pdf/staging-model.yaml")
    return prepared, prepare_pdf_context(prepared, inputs.schema, staging), schema


class Result:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def mappings(self):
        return self

    def one(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def __iter__(self):
        return iter(self.value)


def reader_fixture(
    monkeypatch,
    *,
    selected=False,
    claim_change=None,
    product_change=None,
    schema_mode="installed",
    schema_custody="retained",
):
    from corpus_structure.semantic import (
        pdf_contracts,
        pdf_payloads,
        pdf_record_reader,
        source_views,
    )
    from corpus_structure.semantic._operation_calls import PdfBuildValidation

    consumer, _, _ = released_context()
    _, producer, schema = released_context(schema_mode)
    pin = ProductReference(11, "organized", "a" * 64)
    receipt = PdfBuildValidation(
        build_id="bound-build",
        frozen_digest="e" * 64,
        logical_digest=pin.content_digest,
        contract_digest="d" * 64,
        native_callbacks=True,
        native_contract_digest="b" * 64,
    )
    identity = dict(kind="native", contract_digest=receipt.contract_digest)
    identity.update(product_change or {})
    revision = dict(
        build_id=receipt.build_id,
        frozen_digest=receipt.frozen_digest,
        logical_digest=pin.content_digest,
        release_id=producer.release_id,
        schema_digest=sha256(schema).hexdigest(),
        recipe_digest="c" * 64,
        source_digest="original",
        kind=identity["kind"],
    )
    claim = dict(
        params={"native_product": pin.values()}, content_hash="original", project_id="project"
    )
    claim.update(claim_change or {})
    operations = []

    def execute(statement):
        query = str(statement)
        operations.append(query)
        if "FROM ops.pdf_product" in query:
            return Result(identity)
        if "FROM kb.source_artifact" in query:
            assert set(statement.compile().params.values()) == {revision["schema_digest"]}
            return Result(
                None
                if schema_custody == "missing"
                else b"changed bytes"
                if schema_custody == "changed"
                else schema
            )
        if "ops.method_config.params" in query:
            return Result([claim])
        if "ops.run.project_id" in query:
            return Result("project")
        raise AssertionError("unexpected query or native-body hydration: " + query)

    connection: Any = SimpleNamespace(execute=execute)
    family = pdf_payloads.prepare_payload_family(producer)
    page = dict(page_no=7, has_words=True, has_chars=False, candidates=[])
    encoded = pdf_payloads.EncodedPagePayload(
        family.encode(page), family.schema_digest, family.logical_digest(page), 7
    )

    class NoDriverCancellation(BorrowerCancellation):
        @contextmanager
        def borrow(self, connection):
            yield  # This I/O fixture never borrows an actual driver.

    class Publication(PublishedPdfReader):
        def __init__(self):
            super().__init__(
                connection,
                pin,
                revision=revision,
                projection_context=consumer,
                cancellation=NoDriverCancellation(),
            )
            self._prepared_payload_context = producer

        def validation_receipt(self):
            return receipt

        def iter_candidate_payloads(self, *, context=None):
            assert context is producer
            yield encoded

        def hydrate_document(self):
            raise AssertionError("candidate capture must not hydrate a native document")

        def native_product_values(self, **_):
            raise AssertionError("candidate capture must not hydrate a native product")

    published = Publication()

    def resolve_published(conn, reference, *, projection_context):
        assert conn is connection and reference == pin and projection_context is consumer
        return published

    def producer_context(conn, task):
        assert conn is connection and task == pin.task_id
        return producer

    monkeypatch.setattr(pdf_contracts, "pdf_context_for_task", producer_context)
    monkeypatch.setattr(pdf_record_reader, "published_record_reader", resolve_published)
    monkeypatch.setattr(
        source_views,
        "selected_source_views",
        lambda conn, run: (SimpleNamespace(native_product=pin),) if selected else (),
    )
    reader: Any = object.__new__(BoundReader)
    reader.conn, reader.run_id, reader.prepared = connection, 22, consumer
    reader.source_tasks = {3: 44}
    return reader, pin, producer, published, encoded, operations


def test_exact_claimed_input_captures_ipc_without_selected_views_or_native_hydration(
    tmp_path, monkeypatch
):
    reader, pin, context, _, encoded, queries = reader_fixture(monkeypatch)
    source = reader.capture_pdf_candidates(pin, tmp_path / "capture")
    assert source.encoded(7) == encoded
    assert source.replays[7].path.read_bytes() == encoded.content
    context.execution.require_operation("read_pdf_product")
    with pytest.raises(PreparationError):
        context.execution.operation("publish_native_document")
    assert not any(
        "native_document_" in query or "pdf_selected_product" in query for query in queries
    )


@pytest.mark.parametrize(
    "change, product, error, match",
    [
        (
            {"params": {"native_product": ProductReference(11, "organized", "b" * 64).values()}},
            {},
            OperationConflict,
            "exact claimed",
        ),
        ({"content_hash": "other-original"}, {}, OperationConflict, "exact claimed"),
        ({"project_id": "other-project"}, {}, OperationConflict, "exact claimed"),
        ({}, {"kind": "integrated"}, OperationConflict, "native input role"),
        (
            {},
            {"contract_digest": "other-contract"},
            NativeDocumentUnavailable,
            "sealed validation receipt",
        ),
    ],
)
def test_claim_capture_refuses_wrong_pin_original_project_role_or_contract(
    tmp_path,
    monkeypatch,
    change,
    product,
    error,
    match,
):
    reader, pin, *_ = reader_fixture(monkeypatch, claim_change=change, product_change=product)
    with pytest.raises(error, match=match):
        reader.capture_pdf_candidates(pin, tmp_path / "capture")
    assert not (tmp_path / "capture").exists()


@pytest.mark.parametrize(
    "schema_mode,custody,accepted",
    [
        ("cosmetic", "retained", True),
        ("unsupported", "retained", False),
        ("installed", "missing", False),
        ("installed", "changed", False),
    ],
)
def test_capture_qualifies_retained_mapping_and_consumer_read_profile(
    tmp_path,
    monkeypatch,
    schema_mode,
    custody,
    accepted,
):
    reader, pin, producer, _, encoded, _queries = reader_fixture(
        monkeypatch,
        schema_mode=schema_mode,
        schema_custody=custody,
    )
    if accepted:
        from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

        assert producer.native_schema_digest != trusted_pdf_context().native_schema_digest
        source = reader.capture_pdf_candidates(pin, tmp_path / "capture")
        assert source.encoded(7) == encoded
    else:
        with pytest.raises((NativeDocumentUnavailable, PreparationError)):
            reader.capture_pdf_candidates(pin, tmp_path / "capture")
        assert not (tmp_path / "capture").exists()


def test_unsupported_consumer_read_profile_refuses_preparation_before_capture(tmp_path):
    with pytest.raises(PreparationError, match="read_pdf_product: required effects differ"):
        released_context(unsupported_read=True)
    assert not (tmp_path / "capture").exists()


def test_selected_pin_keeps_existing_authority_when_no_claim_declares_it(monkeypatch):
    reader, pin, context, published, _, _ = reader_fixture(
        monkeypatch, selected=True, claim_change={"params": {}}
    )
    _, admitted, actual_reader = reader._native_product_input(pin)
    assert admitted is context and actual_reader is published
