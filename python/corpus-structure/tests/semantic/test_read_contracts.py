"""Independent required-universe and public refusal boundary expectations."""

from typing import Literal

import pytest

from corpus_structure.semantic.query import Coverage, CoverageRequirement
from corpus_structure.semantic.refusals import SemanticRefusal, tool_refusals


def witness(
    scope, outcome: Literal["complete", "partial", "unanalysed", "failed"] = "complete", family="f"
):
    return Coverage(
        coverage_id=scope + outcome + family,
        family=family,
        scope=scope,
        outcome=outcome,
        reason=None,
        source_outcome=None,
        required_capability=None,
    )


def test_required_members_are_independent_from_available_coverage():
    requirement = CoverageRequirement("f", frozenset({"a", "b"}))
    assert not requirement.established_by((witness("a"),))
    assert requirement.established_by((witness("a"), witness("b")))
    assert not requirement.established_by((witness("a"), witness("b", "partial")))
    assert not requirement.established_by((witness("*", family="other"),))
    assert requirement.established_by((witness("*"),))
    assert not requirement.established_by((witness("*"), witness("b", "unanalysed")))


def test_empty_unestablished_universe_does_not_prove_absence():
    requirement = CoverageRequirement("f", frozenset())
    assert not requirement.established_by(())
    assert not requirement.established_by((witness("a"),))
    assert requirement.established_by((witness("*"),))


def test_expected_tool_refusal_preserves_signature_and_defects():
    from inspect import signature

    from fastmcp.exceptions import ToolError

    def action(number: int) -> int:
        if number == 0:
            raise SemanticRefusal("unsupported request")
        if number < 0:
            raise RuntimeError("implementation defect")
        return number

    wrapped = tool_refusals(SemanticRefusal)(action)
    assert signature(wrapped) == signature(action)
    assert wrapped(1) == 1
    with pytest.raises(ToolError, match="unsupported request"):
        wrapped(0)
    with pytest.raises(RuntimeError, match="implementation defect"):
        wrapped(-1)


def test_actual_fastmcp_dispatch_keeps_context_schema_and_database_classification():
    import anyio
    import psycopg
    from fastmcp import Client, Context, FastMCP
    from sqlalchemy.exc import OperationalError

    server = FastMCP("read-contract")

    @server.tool
    @tool_refusals(SemanticRefusal)
    def guarded(number: int, ctx: Context) -> int:
        assert ctx is not None
        if number == 0:
            raise SemanticRefusal("unsupported")
        if number < 0:
            raise OperationalError(None, None, psycopg.errors.SerializationFailure("retry"))
        return number

    async def journey():
        async with Client(server) as client:
            tools = await client.list_tools()
            assert tools[0].output_schema is not None
            assert "ctx" not in tools[0].input_schema["properties"]
            assert (await client.call_tool("guarded", {"number": 1})).data == 1
            refused = await client.call_tool("guarded", {"number": 0}, raise_on_error=False)
            transient = await client.call_tool("guarded", {"number": -1}, raise_on_error=False)
            assert refused.is_error and "unsupported" in str(refused.content)
            assert transient.is_error and "database_retry" in str(transient.content)

    anyio.run(journey)


def test_cli_database_failure_is_not_semantic_refusal():
    import json

    import psycopg
    import typer
    from sqlalchemy.exc import OperationalError
    from typer.testing import CliRunner

    from corpus_structure.cli.query import refusal

    app = typer.Typer()

    @app.command()
    def command():
        with refusal(True):
            raise OperationalError(None, None, psycopg.errors.SerializationFailure("retry"))

    result = CliRunner().invoke(app, [])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "database_retry"


def test_native_cut_family_universe_and_document_lifting(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from sqlalchemy import select

    from corpus_structure.orchestrate.commands import finalize_bound_run
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import claim_tasks, complete_task, create_task
    from corpus_structure.semantic.query import bind_completed_result, read_snapshot

    from .test_agent_resubmission import source_task

    prepared, run, task, locator = source_task(
        semantic_db_engine, semantic_writer_engine, tmp_path / "coverage.html", composed=True
    )
    with semantic_writer_engine.begin() as conn:
        tasks = table("ops.task")
        source = conn.execute(select(tasks).where(tasks.c.id == task)).mappings().one()
        create_task(
            conn,
            run_id=run,
            config_id=source["method_config_id"],
            stage=source["stage"],
            unit_type=source["unit_type"],
            unit_id=source["unit_id"],
            unit_key="unit-B",
            input_hash="coverage-B",
            skip_reason="outside_scope",
        )
        claimed = claim_tasks(
            conn,
            run_id=run,
            config_id=source["method_config_id"],
            holder="coverage-source",
            agent=True,
        )[0]
        complete_task(
            conn,
            task_id=task,
            attempt=claimed.attempt,
            holder="coverage-source",
            prepared=prepared,
            observations=[],
            outcome="empty",
        )
        views = table("kb.source_view")
        document = conn.execute(
            select(views.c.document_id).where(views.c.id == source["unit_id"])
        ).scalar_one()
    finalize_bound_run(semantic_writer_engine, run, "coverage-output")
    family = "https://example.org/name"
    a, b = witness(locator, family=family), witness("unit-B", family=family)
    with read_snapshot(semantic_reader_engine) as conn:
        session = bind_completed_result(conn, run)
        requirement = session.required_coverage(run, family)
        assert requirement.members == frozenset({locator, "unit-B"})
        assert requirement.diagnostic is None
        assert not requirement.established_by((a,))
        assert requirement.established_by((a, b))
        assert requirement.established_by((witness("*", family=family),))
        assert not requirement.established_by((witness("*", family="incompatible"),))
        documents = session.required_coverage(run, family, "documents", [document])
        assert documents.members == requirement.members
        assert documents.established_by((a, b))
        assert not documents.established_by((a,))
        assert session.required_coverage(run, family, "units", [locator]).members == frozenset(
            {locator}
        )
        unrelated = session.required_coverage(run, "unbound-family")
        assert unrelated.diagnostic and not unrelated.established_by(
            (witness("*", family="unbound-family"),)
        )
        outside = session.required_coverage(run, family, "documents", [document + 999])
        assert outside.diagnostic and not outside.established_by((witness("*", family=family),))
