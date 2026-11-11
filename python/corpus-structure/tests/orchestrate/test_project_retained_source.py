"""Project initialization binds retained originals before incidental pack acquisition."""

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from corpus_structure.orchestrate import project
from corpus_structure.orchestrate.phase0 import registry
from corpus_structure.semantic.product_reference import ProductReference

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def initialization(monkeypatch, tmp_path):
    from corpus_structure.orchestrate import pdf_source
    from corpus_structure.semantic import _operation_calls, contracts, operations, releases

    raw = b"%PDF-1.7\nretained Grinstead source\n"
    original = tmp_path / "grinstead_snell/book.pdf"
    original.parent.mkdir()
    original.write_bytes(raw)
    prepared = SimpleNamespace(release_id="release")
    document = pdf_source.RetainedDocument(
        45, "book", sha256(raw).hexdigest(), "grinstead_snell/book.pdf"
    )
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.__iter__.side_effect = lambda: iter(
        [dict(id=45, key="book", content_hash=document.content_hash)]
    )
    initialized, registered = MagicMock(), MagicMock()
    monkeypatch.setattr(releases, "load_release", lambda *a: prepared)
    monkeypatch.setattr(contracts, "require_bound_operation", lambda *a: None)
    monkeypatch.setattr(_operation_calls, "initialize_source_project", initialized)
    monkeypatch.setattr(operations, "register_document", registered)
    authenticated = MagicMock(return_value=document)
    monkeypatch.setattr(pdf_source, "retained_source_document", authenticated)
    return SimpleNamespace(
        conn=conn,
        initialized=initialized,
        registered=registered,
        authenticated=authenticated,
        document=document,
        original=original,
        raw=raw,
        corpus=tmp_path,
    )


def invoke(f, **kwargs):
    return project.init_bound_project(
        f.conn,
        domain="statistics",
        corpus=f.corpus,
        release_id="release",
        realization_id="source",
        name="grinstead",
        registry=kwargs.pop("registry", registry(ROOT / "domains/statistics")),
        **kwargs,
    )


@pytest.mark.parametrize("kind", ["native", "integrated"])
def test_retained_initialization_reuses_the_authenticated_original_without_descriptor_rewrite(
    initialization, kind
):
    f = initialization
    pin = ProductReference(1627, kind, "a" * 64)
    result = invoke(f, **{kind + "_product": pin})
    assert result.documents == 1
    assert f.initialized.call_count == 1
    f.registered.assert_not_called()
    auth = f.authenticated.call_args
    assert auth.args == (f.conn, pin)
    assert auth.kwargs["project_id"] == "grinstead" and auth.kwargs["role"] == kind
    assert auth.kwargs["documents"] == [
        dict(id=45, key="book", content_hash=f.document.content_hash)
    ]


def test_foreign_or_absent_retained_original_refuses_before_project_effects(initialization):
    f = initialization
    f.authenticated.side_effect = ValueError("retained product belongs to another project")
    with pytest.raises(ValueError, match="another project"):
        invoke(f, integrated_product=ProductReference(1627, "integrated", "a" * 64))
    f.initialized.assert_not_called()
    f.registered.assert_not_called()


def test_changed_file_cannot_be_registered_as_the_retained_original(initialization):
    f = initialization
    f.original.write_bytes(b"%PDF-1.7\nchanged source\n")
    with pytest.raises(project.ProjectError, match="authenticated original"):
        invoke(f, integrated_product=ProductReference(1627, "integrated", "a" * 64))
    f.registered.assert_not_called()


def test_initialization_refuses_conflicting_product_roles_before_effects(initialization):
    f = initialization
    pin = ProductReference(1627, "integrated", "a" * 64)
    with pytest.raises(project.ProjectError, match="mutually exclusive"):
        invoke(f, native_product=pin, integrated_product=pin)
    f.initialized.assert_not_called()
    f.registered.assert_not_called()


def test_unpinned_initialization_still_registers_configured_original_bytes(initialization):
    from corpus_structure.orchestrate.phase0 import bind_pdf_selection

    f = initialization
    configured = bind_pdf_selection(registry(ROOT / "domains/statistics"), document=f.document)
    result = invoke(f, registry=configured)
    assert result.documents == 1
    f.authenticated.assert_not_called()
    assert f.initialized.call_count == 1 and f.registered.call_count == 1
    registered = f.registered.call_args.kwargs
    assert registered["source_uri"] == "grinstead_snell/book.pdf"
    assert registered["original"] == f.raw
    assert registered["original_path"] == str(f.original.resolve())
