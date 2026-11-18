"""Trusted native evaluator definitions for the shared closed binding artifact.

The SQL evaluator consumes the frozen compiler AST. This module contributes its
complete sources to native correspondence; it defines no alternative predicates.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Connection

from .binding_admission_native import binding_admission_native_sql
from .binding_operand_native import binding_parameter_native_sql, binding_values_native_sql
from .binding_predicate_native import binding_predicate_native_sql
from .binding_recursive_native import (
    binding_branch_native_sql,
    binding_consumed_producers_sql,
    binding_exact_float_sql,
    binding_population_native_sql,
)
from .binding_scalar_native import scalar_binding_native_sql
from .binding_support_native import binding_support_native_sql
from .native_objects import NativeDefinition, definition_from_sql
from .prepared_sql import prepare_sql
from .source_set_native import binding_source_native_sql, source_set_native_sql
from .types import SourceArtifact


def binding_native_sources(*, target_metadata=None) -> tuple[SourceArtifact, ...]:
    return (
        SourceArtifact(
            "native/data-operation-bindings.sql",
            binding_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact("native/data-operation-binding-native.py", Path(__file__).read_bytes()),
        *(
            SourceArtifact("native/" + name, Path(__file__).with_name(name).read_bytes())
            for name in (
                "source_set_native.py",
                "data_operation_source_sets.py",
                "selected_support.py",
                "data_product_reference.py",
                "binding_scalar_native.py",
                "binding_primitives.py",
                "binding_operand_native.py",
                "binding_recursive_native.py",
                "binding_predicate_native.py",
                "binding_admission_native.py",
                "binding_support_native.py",
                "data_operation_model.py",
            )
        ),
    )


def binding_native_sql(*, target_metadata=None) -> str:
    if target_metadata is None:
        from .metadata import metadata

        target_metadata = metadata
    return (
        source_set_native_sql()
        + "\n"
        + binding_source_native_sql()
        + "\n"
        + scalar_binding_native_sql()
        + "\n"
        + binding_parameter_native_sql()
        + "\n"
        + binding_values_native_sql()
        + "\n"
        + binding_exact_float_sql()
        + binding_branch_native_sql()
        + binding_population_native_sql()
        + binding_support_native_sql(target_metadata)
        + binding_predicate_native_sql()
        + binding_consumed_producers_sql()
        + binding_admission_native_sql(target_metadata)
    )


def binding_native_definitions(
    connection: Connection, *, sources=None
) -> tuple[NativeDefinition, ...]:
    """Acquire every helper through the existing native-authoring lifecycle."""
    source = "data-operation-bindings:forward"
    sql = (
        binding_native_sql()
        if sources is None
        else {item.name: item.content for item in sources}[
            "native/data-operation-bindings.sql"
        ].decode()
    )
    prepared = prepare_sql(sql, source=source)
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
