"""Parent operation ordering; actual SQL admission has separate native controls."""

import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from corpus_structure.core.method import PdfRecordPublicationDraft
from corpus_structure.orchestrate.pdf_streaming import publish_pdf_record_draft


@pytest.mark.parametrize("invalid", [False, True])
def test_validation_precedes_visibility_and_failure_never_seals(monkeypatch, tmp_path, invalid):
    calls = []

    @contextmanager
    def transaction():
        calls.append("begin")
        yield object()
        calls.append("commit")

    engine: Any = SimpleNamespace(begin=transaction)
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
        retain_pdf_stage_recipe=retain,
        adopt_pdf_companion_batch=companions,
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
    assert calls.index("records") < calls.index("companions") < calls.index("freeze")
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

    engine: Any = SimpleNamespace(begin=transaction)
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
def test_computed_draft_never_silently_replaces_frozen_or_published_content(
    monkeypatch, tmp_path, state_name
):
    from hashlib import sha256

    original, schema, recipe = b"%PDF-1.7", b"{}", b"{}"
    build = SimpleNamespace(
        task_id=12,
        release_id="release",
        source_digest=sha256(original).hexdigest(),
        recipe_digest=sha256(recipe).hexdigest(),
        schema_digest=sha256(schema).hexdigest(),
    )
    state = SimpleNamespace(
        build=build,
        state=state_name,
        published=SimpleNamespace(kind="native") if state_name == "published" else None,
        frozen=SimpleNamespace(kind="native") if state_name == "frozen" else None,
    )
    publication = ModuleType("corpus_structure.semantic.pdf_publication")

    def forbidden(*args, **kwargs):
        raise AssertionError("frozen or published content must not be changed")

    vars(publication).update(
        inspect_pdf_build=lambda *a, **k: state,
        retain_pdf_stage_recipe=lambda *a, **k: None,
        adopt_pdf_companion_batch=forbidden,
        freeze_pdf_build=forbidden,
        prepare_pdf_build=forbidden,
        validate_pdf_build=forbidden,
        seal_pdf_build=forbidden,
    )
    monkeypatch.setitem(sys.modules, publication.__name__, publication)

    @contextmanager
    def transaction():
        yield object()

    engine: Any = SimpleNamespace(begin=transaction)
    claim: Any = SimpleNamespace(task_id=12, attempt=2, release_id="release")
    draft = PdfRecordPublicationDraft(
        {"changed": "native value"}, "native", original, schema, recipe, {"conversion": "success"}
    )
    with pytest.raises(ValueError, match="explicit retained-product reuse"):
        publish_pdf_record_draft(
            engine, claim, "holder", draft, directory=tmp_path, check_active=lambda: None
        )
