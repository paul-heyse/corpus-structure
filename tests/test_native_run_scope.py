"""Direct source execution refuses incompatible scopes before registering any run or task."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import Connection, Engine

from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_methods import IngestPdf
from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated
from corpus_structure.methods.math.methods import ExtractMath
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic import pdf_contracts
from corpus_structure.semantic.operations import OperationBinding, OperationConflict
from corpus_structure.semantic.types import PreparationError


class RegistrationBoundary(Exception):
    """Stop after observing the exact attempted run registration, without writing a run."""


@pytest.fixture
def run_scope(monkeypatch):
    context = pdf_contracts.trusted_pdf_context()
    engine = MagicMock(spec=Engine)
    conn = MagicMock(spec=Connection)
    engine.connect.return_value.__enter__.return_value = conn
    engine.begin.return_value.__enter__.return_value = conn
    conn.execute.return_value.mappings.return_value.all.return_value = [
        {
            "key": "retained-pdf",
            "source_uri": "retained.pdf",
            "content_hash": "a" * 64,
            "meta": {},
        }
    ]
    archive = MagicMock(return_value=context)
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_release", archive)
    register = MagicMock(side_effect=RegistrationBoundary)
    tasks = MagicMock(side_effect=AssertionError("must not create tasks in scope controls"))
    monkeypatch.setattr(semantic, "create_run", register)
    monkeypatch.setattr(semantic, "create_task", tasks)

    def execute(scope, method):
        registry = MethodRegistry(
            [method],
            MethodsFile(sections={"math": {}}, configs={method.name: {"default": {}}}),
        )
        return semantic.run_source_methods(
            engine,
            project_id="scope-control",
            prepared=context.boundary,
            binding=OperationBinding(context.boundary.release_id, "input", 0, b"{}"),
            registry=registry,
            graph=Graph(((Stage.INGEST, (Step(method.name + "/default"),)),)),
            method_settings=None,
            scope_record=scope,
        )

    return SimpleNamespace(
        execute=execute, engine=engine, conn=conn, archive=archive, register=register, tasks=tasks
    )


@pytest.mark.parametrize("method", [IngestPdf, IngestPdfIntegrated, ExtractMath])
@pytest.mark.parametrize(
    "scope",
    [
        {"name": "trace", "locators": ["special/Normal.html#rel1"], "hash": "a" * 64},
        {"kind": "rendition", "name": "transfer", "locators": ["inspection.html"]},
    ],
)
def test_direct_native_execution_refuses_legacy_scope_before_writes(run_scope, method, scope):
    with pytest.raises(OperationConflict, match="select a native_sections scope"):
        run_scope.execute(scope, method())
    run_scope.engine.begin.assert_not_called()
    run_scope.register.assert_not_called()
    run_scope.tasks.assert_not_called()


@pytest.mark.parametrize(
    "scope",
    [
        {"kind": "native_sections", "sections": ["Sets"]},
        {
            "kind": "native_sections",
            "name": "bad",
            "sections": {"heading": "Sets"},
            "include_descendants": True,
            "hash": "a" * 64,
        },
    ],
)
def test_direct_native_execution_validates_released_scope_shape_before_writes(run_scope, scope):
    with pytest.raises((ValidationError, PreparationError)):
        run_scope.execute(scope, IngestPdf())
    run_scope.archive.assert_called_once()
    run_scope.engine.begin.assert_not_called()
    run_scope.register.assert_not_called()
    run_scope.tasks.assert_not_called()


@pytest.mark.parametrize("method", [IngestPdf, IngestPdfIntegrated, ExtractMath])
@pytest.mark.parametrize("all_sources", [False, True])
def test_direct_native_execution_preserves_native_and_explicit_all_scope(
    run_scope, method, all_sources
):
    scope = (
        None
        if all_sources
        else {
            "kind": "native_sections",
            "name": "selected",
            "sections": ["1.8: Combinatorial Structures"],
            "include_descendants": True,
            "hash": "a" * 64,
        }
    )
    with pytest.raises(RegistrationBoundary):
        run_scope.execute(scope, method())
    run_scope.register.assert_called_once()
    assert run_scope.register.call_args.kwargs["options"]["scope"] == scope
    run_scope.tasks.assert_not_called()
    if all_sources:
        run_scope.archive.assert_not_called()
    else:
        run_scope.archive.assert_called_once()
