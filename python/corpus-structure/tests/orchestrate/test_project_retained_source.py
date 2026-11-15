"""Project initialization authenticates retained original facts without rewriting custody."""

from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from corpus_structure.orchestrate import project
from corpus_structure.semantic.data_operation_support import OriginalDocumentRef


@pytest.fixture
def initialization(monkeypatch, tmp_path):
    from corpus_structure.semantic import (
        data_operation_storage,
        original_document_contracts,
        original_documents,
        releases,
    )

    raw = b"%PDF-1.7\nretained Grinstead source\n"
    original = tmp_path / "corpus/grinstead_snell/book.pdf"
    original.parent.mkdir(parents=True)
    original.write_bytes(raw)
    domain = tmp_path / "domains/statistics"
    domain.mkdir(parents=True)
    (domain / "methods.yaml").write_text(
        "configs:\n  ingest.pdf:\n    default:\n      originals: [grinstead_snell/book.pdf]\n"
    )
    reference = OriginalDocumentRef(
        kind="original-document",
        project_id="grinstead",
        document_key="book",
        content_hash=sha256(raw).hexdigest(),
        mime="application/pdf",
    )
    conn = MagicMock()
    conn.scalar.return_value = "grinstead_snell/book.pdf"
    initialized = MagicMock(
        return_value={
            "project_id": "grinstead",
            "release_id": "release",
            "realization_id": "source",
        }
    )
    registered = MagicMock()
    monkeypatch.setattr(
        releases, "load_release", lambda *args: SimpleNamespace(release_id="release")
    )
    monkeypatch.setattr(
        original_document_contracts, "require_source_operation_context", lambda *args: None
    )
    monkeypatch.setattr(
        data_operation_storage.DataOperationStorage, "initialize_source_project", initialized
    )
    monkeypatch.setattr(original_documents, "register_original_document", registered)
    read_original = MagicMock(return_value=raw)
    monkeypatch.setattr(original_documents, "read_original_document_bytes", read_original)
    authenticated = MagicMock(return_value=SimpleNamespace(reference=reference))
    monkeypatch.setattr(original_documents, "acquire_original_document_selection", authenticated)
    return SimpleNamespace(
        conn=conn,
        initialized=initialized,
        registered=registered,
        read_original=read_original,
        authenticated=authenticated,
        reference=reference,
        original=original,
        raw=raw,
        corpus=tmp_path / "corpus",
        domains=tmp_path / "domains",
    )


def invoke(f, *, originals=()):
    return project.init_bound_project(
        f.conn,
        domain="statistics",
        corpus=f.corpus,
        release_id="release",
        realization_id="source",
        name="grinstead",
        domains=f.domains,
        originals=originals,
    )


def test_retained_original_fact_is_authenticated_without_descriptor_rewrite(initialization):
    f = initialization
    result = invoke(f, originals=(f.reference,))
    assert result.documents == 1 and f.initialized.call_count == 1
    f.registered.assert_not_called()
    f.authenticated.assert_called_once_with(f.conn, project_id="grinstead", document_key="book")


def test_foreign_or_absent_original_refuses_before_project_effects(initialization):
    f = initialization
    with pytest.raises(project.ProjectError, match="another project"):
        invoke(f, originals=(f.reference.model_copy(update={"project_id": "other"}),))
    f.initialized.assert_not_called()
    f.registered.assert_not_called()
    f.authenticated.assert_not_called()


def test_retained_fact_uses_its_authenticated_bytes_when_local_file_changes(initialization):
    f = initialization
    f.original.write_bytes(b"%PDF-1.7\nchanged local file\n")
    result = invoke(f, originals=(f.reference,))
    assert result.documents == 1
    f.read_original.assert_called_once()
    f.registered.assert_not_called()


def test_unavailable_retained_bytes_refuse_before_initialization(initialization):
    from corpus_structure.semantic.original_documents import OriginalDocumentReadRefused

    f = initialization
    f.read_original.side_effect = OriginalDocumentReadRefused(
        "missing", "retained original artifact is unavailable"
    )
    with pytest.raises(OriginalDocumentReadRefused, match="unavailable"):
        invoke(f, originals=(f.reference,))
    f.initialized.assert_not_called()
    f.registered.assert_not_called()


def test_stale_original_fact_refuses_before_registration(initialization):
    f = initialization
    f.authenticated.return_value = SimpleNamespace(
        reference=f.reference.model_copy(update={"content_hash": "a" * 64})
    )
    with pytest.raises(project.ProjectError, match="authenticated metadata"):
        invoke(f, originals=(f.reference,))
    f.initialized.assert_not_called()
    f.registered.assert_not_called()


def test_unpinned_initialization_registers_configured_original_bytes(initialization):
    f = initialization
    result = invoke(f)
    assert result.documents == 1
    f.authenticated.assert_not_called()
    assert f.initialized.call_count == 1 and f.registered.call_count == 1
    registered = f.registered.call_args.kwargs
    assert registered["source_uri"] == "grinstead_snell/book.pdf"
    assert registered["original"] == f.raw and registered["original_path"] == str(
        f.original.resolve()
    )
