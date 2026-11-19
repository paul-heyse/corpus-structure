"""Trusted mechanical read of selected original native facts, with no recapture."""

from __future__ import annotations

from pathlib import Path

from .native_objects import (
    NativeDefinition,
    definition_from_sql,
    native_sql_script,
)
from .native_program_registry import ProgramDeclaration
from .source_admission_native import source_admission_native_programs, source_admission_native_sql
from .source_capture_native import source_capture_native_programs, source_capture_native_sql
from .types import SourceArtifact


def source_native_sources(
    *, physical_sources=None, linkml_types=None, target_metadata=None
) -> tuple[SourceArtifact, ...]:
    from .data_operation_visual_read import visual_read_sources
    from .original_document_contracts import source_admission_sources

    if target_metadata is None:
        if physical_sources is None:
            from .metadata import get_metadata

            target_metadata = get_metadata()
        else:
            from corpus_structure.schema.physical import compile_physical

            target_metadata = compile_physical(physical_sources, linkml_types=linkml_types)
    return (
        SourceArtifact(
            "native/data-operation-source-capture.sql",
            source_capture_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/source-capture-native.py",
            Path(__file__).with_name("source_capture_native.py").read_bytes(),
        ),
        *source_admission_sources(target_metadata=target_metadata),
        *visual_read_sources(target_metadata=target_metadata),
        SourceArtifact(
            "native/data-operation-source-admission.sql",
            source_admission_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/source-admission-native.py",
            Path(__file__).with_name("source_admission_native.py").read_bytes(),
        ),
        SourceArtifact("native/data-operation-source-native.py", Path(__file__).read_bytes()),
    )


def source_native_programs(*, target_metadata=None, sources=None) -> tuple[ProgramDeclaration, ...]:
    """Declare source providers and their prerequisites without scanning captured SQL."""
    from dataclasses import replace

    import yaml

    from .data_operation_visual_read import visual_read_declarations
    from .data_operation_wire import PROTOCOL_SOURCE
    from .original_document_contracts import source_original_declarations

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
    captured = (
        source_native_sources(target_metadata=target_metadata)
        if sources is None
        else tuple(sources)
    )
    by_name = {item.name: item.content for item in captured}
    capture = source_capture_native_programs(target_metadata)
    if (
        source_capture_native_sql(target_metadata).encode()
        != by_name["native/data-operation-source-capture.sql"]
    ):
        raise ValueError("source capture declarations differ from captured model statements")
    if (
        source_admission_native_sql(target_metadata).encode()
        != by_name["native/data-operation-source-admission.sql"]
    ):
        raise ValueError("source admission declarations differ from captured model statements")
    declarations = (
        *source_admission_native_programs(target_metadata, capture_programs=capture),
        *source_original_declarations(target_metadata=target_metadata, sources=captured),
        *visual_read_declarations(target_metadata=target_metadata, sources=captured),
    )
    protocol = by_name.get(
        PROTOCOL_SOURCE, target_metadata.info["physical_sources"]["data-operation-native.yaml"]
    )
    # Renaming consumes the operation names themselves. It does not need the
    # unrelated wire-schema companion expansions used by JSON request validation.
    public = {item["name"] for item in yaml.safe_load(protocol)["operations"]}
    return tuple(
        replace(item, routine=replace(item.routine, name="ddo_impl_" + item.routine.name))
        if item.routine.name in public
        else item
        for item in declarations
    )


def source_native_sql(sources=None, *, target_metadata=None) -> str:
    """Render the owned source declarations after their wire-name projection."""
    return native_sql_script(
        item.routine.render()
        for item in source_native_programs(target_metadata=target_metadata, sources=sources)
    )


def source_native_definitions(
    connection, *, sources=None, target_metadata=None
) -> tuple[NativeDefinition, ...]:
    return tuple(
        definition_from_sql(
            connection,
            item.routine.render(),
            source=item.source,
            owner=item.owner,
            program_access=item.access,
        )
        for item in source_native_programs(target_metadata=target_metadata, sources=sources)
    )
