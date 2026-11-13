"""Trusted native evaluator definitions for the shared closed binding artifact.

The SQL evaluator consumes the frozen compiler AST. This module contributes its
complete sources to native correspondence; it defines no alternative predicates.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Connection

from .native_objects import NativeDefinition, definition_from_sql
from .prepared_sql import prepare_sql
from .types import SourceArtifact

_SQL = Path(__file__).with_name("sql") / "data_operation_bindings.sql"


def binding_native_sources() -> tuple[SourceArtifact, ...]:
    return (
        SourceArtifact("native/data-operation-bindings.sql", _SQL.read_bytes()),
        SourceArtifact("native/data-operation-binding-native.py", Path(__file__).read_bytes()),
    )


def binding_native_sql() -> str:
    return _SQL.read_text()


def binding_native_definitions(connection: Connection) -> tuple[NativeDefinition, ...]:
    """Acquire every helper through the existing native-authoring lifecycle."""
    source = "data-operation-bindings:forward"
    prepared = prepare_sql(binding_native_sql(), source=source)
    return tuple(
        definition_from_sql(
            connection,
            prepared.excerpt(index),
            source=source,
            owner="corpus_sem_publisher",
            grants=(),
        )
        for index, _ in enumerate(prepared.statements)
    )
