"""Public refusal boundaries retain signatures, native attribution and actual dispatch."""

import pytest

from corpus_structure.semantic.refusal_types import SemanticRefusal
from corpus_structure.semantic.refusals import tool_refusals


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
            assert transient.is_error and "database_serialization" in str(transient.content)

    anyio.run(journey)


def test_cli_adbc_failure_reports_native_fields_and_preserves_programming_defects():
    import json

    import adbc_driver_manager as adbc
    import typer
    from typer.testing import CliRunner

    from corpus_structure.cli.failures import failure_boundary

    app = typer.Typer()
    native = adbc.OperationalError(
        "SECRET SQL",
        status_code=adbc.AdbcStatusCode.IO,
        details=[
            ("PG_DIAG_TABLE_NAME", b"observed_table"),
            ("PG_DIAG_INTERNAL_QUERY", b"SECRET QUERY"),
        ],
    )
    native.vendor_code = 91

    @app.command()
    def command():
        with failure_boundary(True, expected=(ValueError,)):
            raise native

    result = CliRunner().invoke(app, [])
    assert result.exit_code == 1
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "database_io"
    assert error["failure"]["native_status"] == "IO"
    assert error["failure"]["vendor_code"] == 91
    assert error["failure"]["sqlstate"] is None
    assert error["failure"]["effects"] == "uncertain"
    assert error["failure"]["details"] == [["table_name", "observed_table"]]
    assert "SECRET" not in result.stdout
    programming_defect = TypeError("unexpected programming defect")
    with pytest.raises(TypeError) as caught, failure_boundary(True, expected=(ValueError,)):
        raise programming_defect
    assert caught.value is programming_defect
