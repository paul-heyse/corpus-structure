"""PostgreSQL renders structured refusal diagnostics without a text SQL template."""

import json

import psycopg
import pytest
from sqlalchemy import Text, cast, func, literal
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.native_program import (
    Block,
    Do,
    Local,
    Raise,
    core_variable,
    pg_type,
)


def test_native_refusal_preserves_structured_diagnostic_detail(semantic_bare_engine):
    role = core_variable("role_name", Text())
    detail = cast(
        func.jsonb_build_object(
            "role", role, "candidates", cast(literal('[{"position":0}]'), JSONB())
        ),
        Text(),
    )
    statement = Do(
        Block(
            (Raise(literal("invalid member for ") + role, "23514", detail),),
            (Local("role_name", pg_type("text"), literal("operator's role")),),
        )
    )
    with semantic_bare_engine.connect() as connection:
        with pytest.raises(DBAPIError) as caught:
            connection.exec_driver_sql(statement, execution_options={"no_parameters": True})
        error = caught.value.orig
        assert isinstance(error, psycopg.Error)
        assert error.sqlstate == "23514"
        assert error.diag.message_primary == "invalid member for operator's role"
        diagnostic = error.diag.message_detail
        assert isinstance(diagnostic, str)
        assert json.loads(diagnostic) == {
            "role": "operator's role",
            "candidates": [{"position": 0}],
        }
        connection.rollback()
