"""Executable queue choices refuse before discovery, including empty projects."""

from typing import cast

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import Engine

from corpus_structure.intervene.semantic_server import (
    SemanticAgentSession,
    SemanticProjectSession,
    build_semantic_server,
)
from corpus_structure.semantic.proposals import ProposalRefused


def _unexpected_discovery(*args, **kwargs):
    raise AssertionError("unsupported mode reached queue discovery")


@pytest.mark.parametrize("mode", ["adjudicate", "unknown", "", "EXTRACT"])
@pytest.mark.parametrize("kind", ["run", "project"])
def test_unsupported_mode_refuses_before_any_discovery(monkeypatch, mode, kind):
    # No database-capable engine: even interpretation/discovery must not be reached.
    engine = cast(Engine, object())
    if kind == "run":
        session = SemanticAgentSession(engine, 1)
        monkeypatch.setattr(SemanticAgentSession, "interpretation", _unexpected_discovery)
    else:
        session = SemanticProjectSession(engine, "empty")
        monkeypatch.setattr(SemanticProjectSession, "pending_runs", _unexpected_discovery)
    with pytest.raises(ProposalRefused, match="unsupported proposal queue mode"):
        session.next(mode, 1)


def test_registered_queue_schema_refusal_and_supported_empty_project(monkeypatch):
    session = SemanticProjectSession(cast(Engine, object()), "empty")
    discovered = []

    def pending_runs(self):
        discovered.append(self.project_id)
        return ()

    monkeypatch.setattr(SemanticProjectSession, "pending_runs", pending_runs)

    async def journey():
        async with Client(build_semantic_server(session)) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            mode = tools["queue_next"].input_schema["properties"]["mode"]
            assert mode["const"] == "extract"
            assert mode["default"] == "extract"
            unsupported = await client.call_tool(
                "queue_next", {"mode": "adjudicate"}, raise_on_error=False
            )
            assert unsupported.is_error
            assert discovered == []
            valid = await client.call_tool("queue_next", {"mode": "extract"})
            assert not valid.is_error
            assert valid.structured_content == {"tasks": []}
            assert discovered == ["empty"]

    anyio.run(journey)
