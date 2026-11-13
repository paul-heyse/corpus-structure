"""Rendering admits its own archived leaf implementation without preparing mathematics."""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection, Engine

from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic import analysis_contracts, native_requests, pdf_contracts, releases
from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import BoundReader, OperationBinding
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.types import PreparationError, RegistryRow


@pytest.fixture
def different_implementation():
    from corpus_structure.semantic.contracts import (
        ImplementationSnapshot,
        current_implementation,
        implementation_override,
    )

    installed = current_implementation()
    analysis = tuple(
        replace(item, content=item.content + b"\n") if item.name == "libraries.json" else item
        for item in installed.analysis_inputs
    )
    changed = ImplementationSnapshot(
        replace(
            installed.execution_inputs,
            implementations=tuple(
                replace(item, content=item.content + b"\n")
                if item.name == "libraries.json"
                else item
                for item in installed.execution_inputs.implementations
            ),
        ),
        analysis,
    )
    with implementation_override(changed):
        yield


@pytest.fixture(scope="module")
def renderer_archive():
    inputs = trusted_execution_inputs()
    model = compile_execution_model(inputs)
    base = prepare_release(inputs.schema)
    prepared = replace(
        base,
        execution_model_id=model.model_id,
        registry_rows=(
            *base.registry_rows,
            RegistryRow("execution_model", model.model_id, model.content),
        ),
    )
    libraries = next(
        item.content for item in inputs.implementations if item.name == "libraries.json"
    )
    return prepared, libraries


def renderer_connection(libraries):
    conn = MagicMock(spec=Connection)
    conn.execute.return_value.scalar_one.return_value = libraries
    return conn


def test_renderer_refuses_changed_runtime_without_preparing_mathematics(
    renderer_archive, different_implementation, monkeypatch
):
    prepared, libraries = renderer_archive
    conn = renderer_connection(libraries)
    # Creating a reader is lazy; only requesting analytical ownership admits math.
    reader = BoundReader(conn, 17, prepared)
    with pytest.raises(PreparationError, match="admitted semantic determinant bytes"):
        analysis_contracts.bind_analysis_family(reader.prepared, "source")

    from corpus_structure.semantic.runtime_bindings import RuntimeBindingError

    def forbidden(*args, **kwargs):
        pytest.fail("rendering must not prepare unrelated mathematics")

    monkeypatch.setattr(analysis_contracts, "bind_analysis_family", forbidden)
    monkeypatch.setattr(analysis_contracts, "prepare_interpretation_context", forbidden)
    with pytest.raises(RuntimeBindingError, match="runtime semantic assets differ"):
        native_requests.prepare_native_renderer(conn, prepared)


def test_renderer_qualifies_the_explicit_runtime_binding(renderer_archive, monkeypatch):
    from corpus_structure.semantic import runtime_bindings
    from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding

    prepared, libraries = renderer_archive
    binding = prepare_runtime_binding(prepared)
    qualify = MagicMock(return_value=binding)
    monkeypatch.setattr(runtime_bindings, "require_installed_runtime", qualify)
    renderer = native_requests.prepare_native_renderer(
        renderer_connection(libraries), prepared, runtime_binding=binding
    )
    qualify.assert_called_once_with(prepared, binding)
    archived = json.loads(binding.input("libraries.json").content)
    assert renderer == {
        "implementation_digest": binding.input("pdf/regions.py").digest,
        "pypdfium2": archived["pypdfium2"],
        "Pillow": archived["Pillow"],
    }


def test_renderer_refuses_unqualified_runtime(renderer_archive, monkeypatch):
    from corpus_structure.semantic import runtime_bindings

    prepared, libraries = renderer_archive
    qualify = MagicMock(side_effect=ValueError("installed runtime differs"))
    monkeypatch.setattr(runtime_bindings, "require_installed_runtime", qualify)
    with pytest.raises(ValueError, match="installed runtime differs"):
        native_requests.prepare_native_renderer(renderer_connection(libraries), prepared)


def test_render_request_prepares_only_retained_view_and_renderer(renderer_archive, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("rendering must not prepare unrelated mathematics")

    monkeypatch.setattr(analysis_contracts, "bind_analysis_family", forbidden)
    monkeypatch.setattr(analysis_contracts, "prepare_interpretation_context", forbidden)
    prepared, libraries = renderer_archive
    conn = renderer_connection(libraries)
    conn.execute.return_value.mappings.return_value.one.return_value = {
        "release_id": prepared.release_id,
        "project_id": "project",
    }
    conn.execute.return_value.scalar_one_or_none.return_value = 31
    engine = MagicMock(spec=Engine)
    engine.begin.return_value.__enter__.return_value = conn
    engine.connect.return_value.__enter__.return_value = conn
    ref = SourceViewRef(
        31,
        "native-section",
        5,
        ProductReference(23, "organized", "a" * 64),
        "#/groups/0",
        "direct",
        "b" * 64,
        "c" * 64,
    )
    load = MagicMock(return_value=SimpleNamespace(ref=ref))
    monkeypatch.setattr(native_requests, "load_source_view", load)
    monkeypatch.setattr(releases, "open_release", lambda *args: prepared)
    # Rendering must not resolve or validate unrelated mathematical domain-rule contexts.
    dependencies = canonical_bytes(
        {
            "operations": {
                "a": {"parameters": {"math": {"native_domain_rules": [{"rule": "a"}]}}},
                "b": {"parameters": {"math": {"native_domain_rules": [{"rule": "b"}]}}},
            }
        }
    )
    monkeypatch.setattr(
        native_requests,
        "binding_of",
        lambda *args: OperationBinding(prepared.release_id, "z", 0, dependencies),
    )

    class SnapshotPrepared(Exception):
        pass

    boundary = MagicMock()
    boundary.validate_json.side_effect = SnapshotPrepared
    monkeypatch.setattr(
        pdf_contracts, "pdf_context_for_release", lambda *args: SimpleNamespace(boundary=boundary)
    )
    with pytest.raises(SnapshotPrepared):
        native_requests.request_source_view(
            engine,
            source_run_id=17,
            source_view_id=31,
            demand="render",
            pointer="#/texts/0",
            region_index=0,
            code_commit="render-control",
        )
    load.assert_called_once_with(conn, 31, analysis=False)
    config = json.loads(boundary.validate_json.call_args.args[1])
    assert config["demand"] == "render"
    assert config["domain_rules"] == []
    assert config["renderer"]["pypdfium2"] == json.loads(libraries)["pypdfium2"]
    context = json.loads(config["ancestor_context"])
    assert context["declarations"] == [] and context["source_views"] == []
    assert context["observations"] == []


@pytest.mark.parametrize(
    ("status", "sealed", "cut", "member", "error"),
    [
        ("created", False, None, None, "requires a sealed source-ready cut"),
        ("failed", True, None, None, "requires a sealed source-ready cut"),
        ("consolidating", True, 11, None, "outside the selected archived source view"),
        ("consolidating", True, 11, 31, None),
    ],
)
def test_cross_release_render_binds_only_the_sealed_archive(
    renderer_archive, monkeypatch, status, sealed, cut, member, error
):
    from corpus_structure.semantic import _operation_calls, pdf_record_reader
    from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding

    prepared, libraries = renderer_archive
    archive_release = "release:archive"
    conn = renderer_connection(libraries)
    conn.execute.return_value.mappings.return_value.one.return_value = dict(
        release_id=archive_release,
        project_id="project",
        status=status,
        sealed=sealed,
        input_revision=2,
    )
    conn.execute.return_value.scalar_one_or_none.side_effect = (31, 0)
    conn.execute.return_value.scalar_one.return_value = None
    conn.scalar.side_effect = (cut, member)
    engine = MagicMock(spec=Engine)
    engine.begin.return_value.__enter__.return_value = conn
    engine.connect.return_value.__enter__.return_value = conn
    ref = SourceViewRef(
        31,
        "native-section",
        5,
        ProductReference(23, "organized", "a" * 64),
        "#/groups/0",
        "direct",
        "b" * 64,
        "c" * 64,
    )
    archived_reader = MagicMock()
    monkeypatch.setattr(
        pdf_record_reader, "published_record_reader", MagicMock(return_value=archived_reader)
    )
    monkeypatch.setattr(native_requests, "selected_source_views", lambda *a, **k: (ref,))
    monkeypatch.setattr(releases, "open_release", lambda *args: prepared)
    monkeypatch.setattr(
        native_requests, "binding_of", lambda *a: OperationBinding(archive_release, "z", 2, b"{}")
    )
    select = MagicMock()
    monkeypatch.setattr(_operation_calls, "select_source_view", select)
    load = MagicMock()
    monkeypatch.setattr(native_requests, "load_source_view", load)
    create = MagicMock(return_value=41)
    monkeypatch.setattr(native_requests, "create_run", create)
    schedule = MagicMock(return_value=42)
    monkeypatch.setattr(native_requests, "create_task", schedule)
    monkeypatch.setattr(native_requests, "record_method", MagicMock(return_value=43))
    renderer = prepare_runtime_binding(prepared)
    monkeypatch.setattr(
        "corpus_structure.semantic.runtime_bindings.require_installed_runtime",
        lambda *args: renderer,
    )
    boundary = MagicMock()
    monkeypatch.setattr(
        pdf_contracts, "pdf_context_for_release", lambda *args: SimpleNamespace(boundary=boundary)
    )

    class Scheduled(Exception):
        pass

    monkeypatch.setattr(native_requests, "claim_tasks", MagicMock(side_effect=Scheduled))
    refusal = pytest.raises(ValueError, match=error) if error else pytest.raises(Scheduled)
    with refusal:
        native_requests.request_source_view(
            engine,
            source_run_id=17,
            source_view_id=31,
            demand="render",
            pointer="#/texts/0",
            region_index=0,
            code_commit="render-control",
            writer_release=prepared.release_id,
            writer_realization="writer",
        )
    select.assert_not_called()
    load.assert_not_called()
    if error:
        schedule.assert_not_called()
        return
    archived_reader.region.assert_called_once_with("#/texts/0", 0)
    assert json.loads(create.call_args.kwargs["binding"].dependencies) == {
        "native_render_source": 17,
        "native_render_cut": 11,
    }
    assert schedule.call_args.kwargs["unit_type"] == "document"
    assert schedule.call_args.kwargs["unit_id"] == ref.document_id
