"""Rendering admits its own archived leaf implementation without preparing mathematics."""

import importlib.metadata
import importlib.resources
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
from corpus_structure.semantic.parsing_products import ProductReference
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import PreparationError, RegistryRow


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


def test_renderer_admission_is_independent_of_mathematical_implementation(
    renderer_archive, monkeypatch
):
    prepared, libraries = renderer_archive
    conn = renderer_connection(libraries)
    monkeypatch.setattr(analysis_contracts, "_runtime_implementation_digests", lambda: ())
    with pytest.raises(PreparationError, match="admitted implementation bytes"):
        BoundReader(conn, 17, prepared)

    renderer = native_requests.prepare_native_renderer(conn, prepared)

    assert renderer["pypdfium2"] == json.loads(libraries)["pypdfium2"]
    assert renderer["Pillow"] == json.loads(libraries)["Pillow"]
    assert len(renderer["implementation_digest"]) == 64


@pytest.mark.parametrize("mismatch", ["implementation", "manifest", "packages"])
def test_renderer_refuses_its_own_implementation_or_package_drift(
    renderer_archive, monkeypatch, mismatch
):
    prepared, libraries = renderer_archive
    conn = renderer_connection(libraries)
    if mismatch == "implementation":
        changed = MagicMock()
        changed.joinpath.return_value.read_bytes.return_value = b"different renderer"
        monkeypatch.setattr(importlib.resources, "files", lambda package: changed)
        message = "admitted PDF region renderer bytes"
    elif mismatch == "manifest":
        conn.execute.return_value.scalar_one.return_value = libraries + b" "
        message = "package manifest differs"
    else:
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "different-version")
        message = "admitted pypdfium2 and Pillow versions"
    with pytest.raises((PreparationError, ValueError), match=message):
        native_requests.prepare_native_renderer(conn, prepared)


def test_render_request_prepares_only_retained_view_and_renderer(renderer_archive, monkeypatch):
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
    monkeypatch.setattr(analysis_contracts, "_runtime_implementation_digests", lambda: ())

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
