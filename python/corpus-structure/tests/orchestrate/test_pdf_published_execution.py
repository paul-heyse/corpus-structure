"""Parent operation ordering; actual SQL admission has separate native controls."""

import sys
from contextlib import contextmanager, nullcontext
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import psycopg
import pytest
from sqlalchemy import Connection, Engine

from corpus_structure.core.method import PdfRecordPublicationDraft
from corpus_structure.orchestrate.pdf_streaming import publish_pdf_record_draft
from corpus_structure.semantic.pdf_publication import (
    COMPANION_BATCH_BYTES,
    COMPANION_BATCH_ROWS,
    COMPANION_STAGE_TARGETS,
)


def transaction_engine(transaction):
    """Keep ordering controls at the owner's explicit checkout/transaction boundary."""
    driver = MagicMock(spec=psycopg.Connection)
    driver.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
    connection = MagicMock(spec=Connection)
    connection.connection.driver_connection = driver
    connection.begin.side_effect = transaction
    engine = MagicMock(spec=Engine)
    engine.connect.side_effect = lambda: nullcontext(connection)
    return engine


@pytest.mark.parametrize("invalid", [False, True])
def test_validation_precedes_visibility_and_failure_never_seals(monkeypatch, tmp_path, invalid):
    calls = []

    @contextmanager
    def transaction():
        calls.append("begin")
        yield object()
        calls.append("commit")

    engine = transaction_engine(transaction)
    claim: Any = SimpleNamespace(task_id=12, attempt=2)
    build = SimpleNamespace(build_id="owned", release_id="release")
    publication = ModuleType("corpus_structure.semantic.pdf_publication")

    def retain(*args, **kwargs):
        calls.append("recipe")

    def companions(*args, **kwargs):
        calls.append("companions")

    def freeze(*args, **kwargs):
        calls.append("freeze")
        return "frozen"

    def prepare(*args):
        calls.append("prepare")

    def validate(*args, **kwargs):
        calls.append("validate")
        if invalid:
            raise ValueError("native conformance failed")

    def seal(*args, **kwargs):
        calls.append("seal")
        return "published"

    vars(publication).update(
        COMPANION_STAGE_TARGETS=COMPANION_STAGE_TARGETS,
        COMPANION_BATCH_BYTES=COMPANION_BATCH_BYTES,
        COMPANION_BATCH_ROWS=COMPANION_BATCH_ROWS,
        retain_pdf_stage_recipe=retain,
        adopt_prepared_pdf_companion_batches=companions,
        prepared_pdf_companion_batches=lambda prepared: (batch for batch in ()),
        stage_pdf_access_projection=lambda *a, **k: calls.append("access"),
        record_pdf_producer_certification=lambda *a, **k: calls.append("attest"),
        inspect_pdf_build=lambda *a, **k: None,
        freeze_pdf_build=freeze,
        prepare_pdf_build=prepare,
        validate_pdf_build=validate,
        seal_pdf_build=seal,
    )
    monkeypatch.setitem(sys.modules, publication.__name__, publication)
    from corpus_structure.semantic import pdf_staging

    monkeypatch.setattr(pdf_staging, "begin_pdf_build", lambda *a, **k: build)
    from corpus_structure.ingest.pdf_streaming import StreamingPdfResult

    def write(*args, **kwargs):
        calls.append("records")
        return ()

    monkeypatch.setattr(StreamingPdfResult, "write_record_batches", write)
    from corpus_structure.semantic import pdf_certification, pdf_contracts
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

    context = trusted_pdf_context()
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_task", lambda *a: context)
    monkeypatch.setattr(
        "corpus_structure.semantic.pdf_lowering.require_lowering_identity", lambda context: "a" * 64
    )
    monkeypatch.setattr(
        pdf_certification,
        "write_pdf_companion_sets",
        lambda *a, **k: (SimpleNamespace(replay_key="companion", replays=()),),
    )

    class Payloads:
        def __init__(self, *args):
            pass

        def add_replays(self, *args, **kwargs):
            pass

        def add_companion_replays(self, *args, **kwargs):
            pass

        def target_pins(self):
            return ()

        def certify(self, document, projection, **kwargs):
            calls.append("certify")
            projection.write_bytes(b"")
            return SimpleNamespace(to_bytes=lambda: b"{}")

        def close(self):
            pass

    monkeypatch.setattr(pdf_certification, "PdfProducerPayloads", Payloads)
    draft = PdfRecordPublicationDraft(
        {},
        "native",
        b"%PDF-1.7",
        b"{}",
        b"{}",
        {"conversion": "success"},
        companions={"occurrence": ()},
    )

    def run():
        return publish_pdf_record_draft(
            engine, claim, "holder", draft, directory=tmp_path, check_active=lambda: None
        )

    if invalid:
        with pytest.raises(ValueError, match="native conformance"):
            run()
        assert "seal" not in calls
    else:
        assert run() == "published"
        assert calls.index("validate") < calls.index("seal")
    assert calls.index("records") < calls.index("certify") < calls.index("companions")
    assert (
        calls.index("companions")
        < calls.index("access")
        < calls.index("attest")
        < calls.index("freeze")
    )
    assert calls.index("freeze") < calls.index("prepare") < calls.index("validate")


def test_native_producer_reuses_qualified_publication_before_copy_or_inference(
    monkeypatch, tmp_path
):
    from hashlib import sha256

    from corpus_structure.core.method import PdfRecordProducerRequest
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.orchestrate import pdf_streaming

    recipe = PdfRecipe("a" * 40, "b" * 40, recipe_id="docling-standard-pdf-stream-v1")
    original, schema = b"%PDF-1.7", b"{}"
    published = SimpleNamespace(kind="native")
    build = SimpleNamespace(
        task_id=12,
        release_id="release",
        source_digest=sha256(original).hexdigest(),
        recipe_digest=recipe.digest,
        schema_digest=sha256(schema).hexdigest(),
    )
    state = SimpleNamespace(build=build, published=published, frozen=None)
    publication = ModuleType("corpus_structure.semantic.pdf_publication")

    def forbidden(*args, **kwargs):
        raise AssertionError("published reuse must not prepare or infer")

    vars(publication).update(
        COMPANION_STAGE_TARGETS=COMPANION_STAGE_TARGETS,
        COMPANION_BATCH_BYTES=COMPANION_BATCH_BYTES,
        COMPANION_BATCH_ROWS=COMPANION_BATCH_ROWS,
        inspect_pdf_build=lambda *a, **k: state,
        retain_pdf_stage_recipe=forbidden,
        freeze_pdf_build=forbidden,
        prepare_pdf_build=forbidden,
        validate_pdf_build=forbidden,
        seal_pdf_build=forbidden,
    )
    monkeypatch.setitem(sys.modules, publication.__name__, publication)
    monkeypatch.setattr(pdf_streaming, "run_private_native_pdf_build", forbidden)

    @contextmanager
    def transaction():
        yield object()

    engine = transaction_engine(transaction)
    claim: Any = SimpleNamespace(task_id=12, attempt=2, release_id="release")
    assets: Any = None
    request = PdfRecordProducerRequest(recipe, assets, original, schema)
    assert (
        pdf_streaming.produce_published_pdf_records(
            engine,
            claim,
            "holder",
            request,
            directory=tmp_path / "new",
            check_active=lambda: None,
        )
        is published
    )
    assert not (tmp_path / "new").exists()


@pytest.mark.parametrize("state_name", ["frozen", "published"])
def test_draft_finishes_matching_immutable_content_without_lowering(
    monkeypatch, tmp_path, state_name
):
    from hashlib import sha256

    from corpus_structure.orchestrate import pdf_streaming
    from corpus_structure.semantic.identifiers import ReleaseId, TaskAttempt, TaskId
    from corpus_structure.semantic.pdf_publication import FrozenPdfBuildRef
    from corpus_structure.semantic.pdf_staging import PdfBuildRef

    original, schema, recipe = b"%PDF-1.7", b"{}", b"{}"
    build = PdfBuildRef(
        build_id="owned",
        task_id=TaskId(12),
        attempt=TaskAttempt(2),
        holder="holder",
        release_id=ReleaseId("release"),
        source_digest=sha256(original).hexdigest(),
        recipe_digest=sha256(recipe).hexdigest(),
        schema_digest=sha256(schema).hexdigest(),
    )
    published = SimpleNamespace(kind="native")
    state = SimpleNamespace(
        build=build,
        state=state_name,
        published=published if state_name == "published" else None,
        frozen=FrozenPdfBuildRef(build, "f" * 64, "native") if state_name == "frozen" else None,
    )
    finished = []

    def finish(engine, frozen, product_key, check_active, **kwargs):
        finished.append(frozen)
        assert frozen.build is build and product_key == "native"
        return published

    monkeypatch.setattr(pdf_streaming, "_finish_frozen_pdf", finish)
    publication = ModuleType("corpus_structure.semantic.pdf_publication")

    def forbidden(*args, **kwargs):
        raise AssertionError("frozen or published content must not be changed")

    vars(publication).update(
        COMPANION_STAGE_TARGETS=COMPANION_STAGE_TARGETS,
        COMPANION_BATCH_BYTES=COMPANION_BATCH_BYTES,
        COMPANION_BATCH_ROWS=COMPANION_BATCH_ROWS,
        inspect_pdf_build=lambda *a, **k: state,
        retain_pdf_stage_recipe=lambda *a, **k: None,
        adopt_prepared_pdf_companion_batches=forbidden,
        freeze_pdf_build=forbidden,
        prepare_pdf_build=forbidden,
        validate_pdf_build=forbidden,
        seal_pdf_build=forbidden,
    )
    monkeypatch.setitem(sys.modules, publication.__name__, publication)

    @contextmanager
    def transaction():
        yield object()

    engine = transaction_engine(transaction)
    claim: Any = SimpleNamespace(task_id=12, attempt=2, release_id="release")
    draft = PdfRecordPublicationDraft(
        {"changed": "native value"}, "native", original, schema, recipe, {"conversion": "success"}
    )
    assert (
        publish_pdf_record_draft(
            engine,
            claim,
            "holder",
            draft,
            directory=tmp_path / "not-created",
            check_active=lambda: None,
        )
        is published
    )
    assert bool(finished) is (state_name == "frozen")
    assert not (tmp_path / "not-created").exists()
    draft = PdfRecordPublicationDraft(
        {}, "native", original, b"different schema", recipe, {"conversion": "success"}
    )
    with pytest.raises(ValueError, match="source/release/recipe/schema differs"):
        publish_pdf_record_draft(
            engine,
            claim,
            "holder",
            draft,
            directory=tmp_path / "not-created",
            check_active=lambda: None,
        )
