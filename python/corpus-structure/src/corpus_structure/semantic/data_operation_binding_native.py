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
        SourceArtifact("native/data-operation-bindings.sql", binding_native_sql().encode()),
        SourceArtifact("native/data-operation-binding-native.py", Path(__file__).read_bytes()),
    )


def binding_native_sql() -> str:
    from .identity import canonical_bytes
    from .structural_products import ExternalSourceRef

    # Reuse the authoritative typed domain contract at the native boundary.
    # Capturing the rendered SQL freezes the complete selected schema content.
    schema = canonical_bytes(ExternalSourceRef.model_json_schema()).decode().replace("'", "''")
    return _SQL.read_text().replace("__DDO_EXTERNAL_SOURCE_SCHEMA__", schema)


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
