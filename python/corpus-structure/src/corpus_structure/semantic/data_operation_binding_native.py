"""Trusted native evaluator definitions for the shared closed binding artifact.

The SQL evaluator consumes the frozen compiler AST. This module contributes its
complete sources to native correspondence; it defines no alternative predicates.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Connection

from .binding_admission_native import binding_admission_native_programs
from .binding_operand_native import (
    binding_parameter_native_programs,
    binding_values_native_programs,
)
from .binding_predicate_native import binding_predicate_native_programs
from .binding_recursive_native import (
    _render_binding_programs,
    binding_branch_native_programs,
    binding_consumed_producers_programs,
    binding_exact_float_programs,
    binding_population_native_programs,
)
from .binding_scalar_native import scalar_binding_native_programs
from .binding_support_native import binding_support_native_programs
from .native_objects import NativeDefinition, definition_from_sql
from .native_program_registry import ProgramDeclaration
from .source_set_native import binding_source_native_programs, source_set_native_programs
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


def _binding_groups(model):
    """One producer tuple owns both typed installation and exact capture layout."""
    return (
        ("", "", source_set_native_programs()),
        ("\n", "", binding_source_native_programs()),
        ("\n", "", scalar_binding_native_programs()),
        ("\n", "", binding_parameter_native_programs()),
        ("\n", "", binding_values_native_programs()),
        ("\n", "", binding_exact_float_programs()),
        ("", "\n", binding_branch_native_programs()),
        ("", "\n", binding_population_native_programs()),
        ("", "\n", binding_support_native_programs(model)),
        ("", "", binding_predicate_native_programs()),
        ("", "", binding_consumed_producers_programs()),
        ("", "", binding_admission_native_programs(model)),
    )


def _render_groups(groups):
    return "".join(
        prefix + _render_binding_programs(programs, separator=separator)
        for prefix, separator, programs in groups
    )


def binding_native_programs(
    *, target_metadata=None, sources=None
) -> tuple[ProgramDeclaration, ...]:
    """Acquire explicit providers against the same captured physical model."""
    if target_metadata is None:
        physical = {
            item.name.removeprefix("native/projection-physical/"): item.content
            for item in sources or ()
            if item.name.startswith("native/projection-physical/")
        }
        if physical:
            from corpus_structure.schema.physical import compile_physical

            linkml = next(
                item.content
                for item in sources or ()
                if item.name == "native/projection-linkml-types.yaml"
            )
            target_metadata = compile_physical(physical, linkml_types=linkml)
        else:
            from .metadata import get_metadata

            target_metadata = get_metadata()
    groups = _binding_groups(target_metadata)
    if sources is not None:
        captured = {item.name: item.content for item in sources}[
            "native/data-operation-bindings.sql"
        ]
        if _render_groups(groups).encode() != captured:
            raise ValueError(
                "binding declarations differ from captured physical/provider statements"
            )
    return tuple(program for _, _, programs in groups for program in programs)


def binding_native_sql(*, target_metadata=None) -> str:
    if target_metadata is None:
        from .metadata import get_metadata

        target_metadata = get_metadata()
    return _render_groups(_binding_groups(target_metadata))


def binding_native_definitions(
    connection: Connection, *, sources=None, target_metadata=None
) -> tuple[NativeDefinition, ...]:
    """Normalize owned single declarations without parsing a captured text stream."""
    return tuple(
        definition_from_sql(
            connection,
            item.routine.render(),
            source=item.source,
            owner=item.owner,
            program_access=item.access,
        )
        for item in binding_native_programs(target_metadata=target_metadata, sources=sources)
    )
