"""Current render transport scope and exact native execution correspondence."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from corpus_structure.intervene.native_render_tools import (
    NativeRenderRequest,
    execute_native_render,
)
from corpus_structure.orchestrate.native_execution import execute_native_intent
from corpus_structure.semantic.native_requests import TARGET
from corpus_structure.settings import AnalyticsSettings, Settings


def test_render_selection_refuses_missing_or_ambiguous_intent_and_physical_aliases():
    for record in (
        {"project_id": "project:one"},
        {"project_id": "project:one", "demand_id": "demand:one", "run_id": 1},
        {"project_id": "project:one", "demand_id": "demand:one", "task_id": 2},
    ):
        with pytest.raises(ValidationError):
            NativeRenderRequest.model_validate(record)


def test_retained_render_target_is_checked_before_any_execution(monkeypatch):
    from corpus_structure.orchestrate import native_execution
    from corpus_structure.semantic import data_operation_service

    @contextmanager
    def begin():
        yield None

    monkeypatch.setattr(native_execution, "acquired_target", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        native_execution,
        "read_data_demand",
        lambda *args, **kwargs: {
            "demand_id": "demand:other",
            "project_id": "project:one",
            "selection": {"targets": ["unrelated/command"]},
        },
    )

    def forbidden(*args, **kwargs):
        pytest.fail("unrelated retained demand reached execution")

    monkeypatch.setattr(data_operation_service, "execute_data_demand", forbidden)
    with pytest.raises(ValueError, match="required explicit targets"):
        execute_native_intent(
            SimpleNamespace(begin=begin),
            None,
            methods=None,
            source_root=None,
            demand="demand:other",
            project="project:one",
            required_targets=(TARGET,),
        )


def test_current_render_uses_shared_executor_and_preserves_exact_native_result(monkeypatch):
    from corpus_structure.orchestrate import native_execution
    from corpus_structure.orchestrate.data_operations import DemandAdvance
    from corpus_structure.semantic import runtime

    opened, calls = [], []

    @contextmanager
    def engine(settings, application_name, *, purpose):
        opened.append(purpose)
        yield purpose

    def execute(engine, admission, **arguments):
        assert (engine, admission) == ("write", "admit")
        calls.append(arguments)
        return DemandAdvance(
            "demand:one", b'{"analyzed_scope":{"value":0.123456789012345678901}}', (), 0
        )

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(native_execution, "execute_native_intent", execute)
    selection = NativeRenderRequest(project_id="project:one", demand_id="demand:one")
    for project, demand in (("project:other", None), ("project:one", "demand:other")):
        with pytest.raises(ValueError, match="another server"):
            execute_native_render(selection, settings=Settings(), project=project, demand=demand)
    assert not opened
    selected = AnalyticsSettings(threads=3, memory_limit="192MB")
    response = execute_native_render(
        selection, settings=Settings(analytics=selected), project="project:one", demand="demand:one"
    )
    assert calls[0]["analytics_settings"] == selected
    assert opened == ["write", "admit"]
    assert calls[0]["required_targets"] == (TARGET,) and calls[0]["demand"] == "demand:one"
    assert calls[0]["project"] == "project:one" and calls[0]["request"] is None
    snapshot = response.result["snapshot"]
    assert isinstance(snapshot, dict)
    assert snapshot["analyzed_scope"] == {"value": float("0.123456789012345678901")}


def test_retained_reader_surface_remains_read_only():
    import anyio
    from fastmcp import Client
    from sqlalchemy import create_engine

    from corpus_structure.intervene.semantic_server import build_retained_reader_server

    engine = create_engine("sqlite://")

    async def check():
        async with Client(
            build_retained_reader_server(read_engine=engine, project="project:one")
        ) as client:
            tools = {tool.name for tool in await client.list_tools()}
            assert "inspect_source" in tools and "render_source_region" not in tools

    try:
        anyio.run(check)
    finally:
        engine.dispose()
