"""Trusted mechanical read of selected original native facts, with no recapture."""

from __future__ import annotations

from pathlib import Path

from pglast import ast

from .native_objects import NativeDefinition, definition_from_sql
from .prepared_sql import prepare_sql
from .types import SourceArtifact

_SQL = Path(__file__).with_name("sql") / "data_operation_source_admission.sql"


def source_native_sources() -> tuple[SourceArtifact, ...]:
    return (
        SourceArtifact("native/data-operation-source-admission.sql", _SQL.read_bytes()),
        SourceArtifact("native/data-operation-source-native.py", Path(__file__).read_bytes()),
    )


def source_native_sql() -> str:
    return _SQL.read_text()


def source_native_definitions(connection) -> tuple[NativeDefinition, ...]:
    source = "data-operation-source-admission:forward"
    prepared = prepare_sql(source_native_sql(), source=source)
    definitions = []
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if not isinstance(statement, ast.CreateFunctionStmt) or not statement.funcname:
            raise ValueError("source admission requires explicit native function declarations")
        definitions.append(
            definition_from_sql(
                connection,
                prepared.excerpt(index),
                source=source,
                owner="corpus_sem_publisher",
                grants=(("corpus_sem_writer", "EXECUTE", False),)
                if statement.funcname[-1].sval == "ddo_pdf_capture_source"
                else (),
            )
        )
    return tuple(definitions)
