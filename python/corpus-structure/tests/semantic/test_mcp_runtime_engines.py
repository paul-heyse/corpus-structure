"""Purpose and lifetime ownership, independent of database/provider behavior."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from corpus_structure.intervene.runtime_engines import McpRuntimeEngines


def test_mcp_engines_are_lazy_shared_by_purpose_and_closed_at_lifespan_end(monkeypatch):
    from corpus_structure.semantic import runtime

    events: list[tuple[str, str, int] | tuple[str, str]] = []

    @contextmanager
    def opened(settings, name, *, max_size, purpose):
        engine = object()
        events.append(("open", purpose, max_size))
        try:
            yield engine
        finally:
            events.append(("close", purpose))

    monkeypatch.setattr(runtime, "open_runtime_engine", opened)
    settings = SimpleNamespace(database=SimpleNamespace(pool_max_size=3))
    engines = McpRuntimeEngines(settings, "ci-test")
    with pytest.raises(RuntimeError, match="active lifespan"):
        engines.engine()
    with engines.lifespan():
        assert events == []
        read = engines.engine("read")
        assert engines.engine("read") is read
        assert engines.engine("write") is not read
        engines.engine("admit")
        assert events == [("open", "read", 3), ("open", "write", 3), ("open", "admit", 3)]
    assert events[3:] == [("close", "admit"), ("close", "write"), ("close", "read")]
    with pytest.raises(RuntimeError, match="active lifespan"):
        engines.engine("write")


def test_injected_read_engine_is_borrowed_without_close_or_settings_acquisition():
    read = object()
    engines = McpRuntimeEngines(None, "ci-test", read_engine=read)
    with engines.lifespan():
        assert engines.engine("read") is read


def test_retained_reader_tools_share_one_engine_and_take_separate_snapshots(monkeypatch):
    import anyio
    from fastmcp import Client

    from corpus_structure.intervene.semantic_server import build_retained_reader_server
    from corpus_structure.semantic import operation_reporting, read_snapshot, releases, runtime
    from corpus_structure.settings import Settings

    events = []
    engine = object()
    compared = dict(
        report_version=5,
        report_schema_digest="controlled-report-schema",
        before_release="release:A",
        after_release="release:B",
        changes=[],
        unknowns=[],
        complete=True,
    )

    @contextmanager
    def opened(*args, **kwargs):
        events.append("engine-open")
        try:
            yield engine
        finally:
            events.append("engine-close")

    @contextmanager
    def snapshot(selected):
        assert selected is engine
        events.append("snapshot-open")
        try:
            yield object()
        finally:
            events.append("snapshot-close")

    class Report:
        def model_dump(self, **kwargs):
            return compared

    monkeypatch.setattr(runtime, "open_runtime_engine", opened)
    monkeypatch.setattr(read_snapshot, "read_snapshot", snapshot)
    monkeypatch.setattr(
        releases,
        "open_release",
        lambda connection, identity: SimpleNamespace(release_id=identity, artifacts=()),
    )
    monkeypatch.setattr(operation_reporting, "compare_semantic_releases", lambda *args: Report())
    server = build_retained_reader_server(settings=Settings())

    async def exercise():
        async with Client(server) as client:
            assert events == []
            for _ in range(2):
                reply = await client.call_tool(
                    "compare_semantic_releases", {"before": "release:A", "after": "release:B"}
                )
                assert reply.structured_content == compared
            assert events == [
                "engine-open",
                "snapshot-open",
                "snapshot-close",
                "snapshot-open",
                "snapshot-close",
            ]
        assert events[-1] == "engine-close"

    anyio.run(exercise)
