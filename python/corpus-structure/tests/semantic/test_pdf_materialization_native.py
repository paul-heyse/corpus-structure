"""An actual sealed PDF is bounded before whole-product bytes cross to Python."""

import pytest

from corpus_structure.semantic.pdf_publication import freeze_pdf_build, prepare_pdf_build, seal_pdf_build, validate_pdf_build
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import ReadLimit
from pdf_acceptance_support import stage_complete_native
from semantic.pdf_staging_support import private_build as private_build


def test_exact_pdf_materialization_bound_admits_small_source_and_refuses_before_body(private_build, commit_writer_engine, commit_reader_engine, tmp_path, monkeypatch):
    build = private_build
    stage_complete_native(commit_writer_engine, build, tmp_path)
    with commit_writer_engine.begin() as connection:
        frozen = freeze_pdf_build(connection, build, kind="native")
        prepare_pdf_build(connection, frozen)
    validate_pdf_build(commit_writer_engine, frozen)
    with commit_writer_engine.begin() as connection:
        publication = seal_pdf_build(connection, frozen, "native")
    pin = ProductReference(publication.task_id, publication.product_key, publication.logical_digest)
    with commit_reader_engine.connect() as connection:
        reader = PublishedPdfReader(connection, pin, read_budget=PublishedReadBudget(100_000, 16 * 1024 * 1024))
        bound = reader.require_materialization_capacity()
        # Independent literal content and its real streamed serialization establish a
        # lower bound. The production scalar may conservatively include other custody.
        encoded = b"".join(reader.iter_native_json())
        assert b"independent expected text" in encoded
        assert bound >= len(encoded) > len(b"independent expected text")
        too_small = PublishedPdfReader(connection, pin, read_budget=PublishedReadBudget(100_000, bound - 1))
        def forbidden_body():
            raise AssertionError("source bytes fetched before aggregate input admission")
        monkeypatch.setattr(too_small, "iter_native_json", forbidden_body)
        with pytest.raises(ReadLimit, match="aggregate materialization"):
            too_small.hydrate_document()
