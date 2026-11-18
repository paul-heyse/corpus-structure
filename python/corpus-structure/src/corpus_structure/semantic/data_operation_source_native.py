"""Trusted mechanical read of selected original native facts, with no recapture."""

from __future__ import annotations

from pathlib import Path

from pglast import ast

from .native_objects import NativeDefinition, definition_from_sql, native_sql_script
from .prepared_sql import prepare_sql
from .source_admission_native import source_admission_native_sql
from .source_capture_native import source_capture_native_sql
from .types import SourceArtifact


def source_native_sources(
    *, physical_sources=None, linkml_types=None, target_metadata=None
) -> tuple[SourceArtifact, ...]:
    from .data_operation_visual_read import visual_read_sources
    from .original_document_contracts import source_admission_sources

    if target_metadata is None:
        if physical_sources is None:
            from .metadata import metadata

            target_metadata = metadata
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


def source_native_sql(sources=None) -> str:
    from .data_operation_storage import _rename_native_entrypoints
    from .data_operation_visual_read import visual_read_sql
    from .data_operation_wire import wire_operations
    from .original_document_contracts import source_original_sql

    selected = None if sources is None else {source.name: source.content for source in sources}
    if selected is None:
        from .metadata import metadata

        admission_sql = source_admission_native_sql(metadata)
        capture_sql = source_capture_native_sql(metadata)
    else:
        admission_sql = selected["native/data-operation-source-admission.sql"].decode()
        capture_sql = selected["native/data-operation-source-capture.sql"].decode()
    prepared = prepare_sql(admission_sql, source="generated source admission")
    programs = []
    for index, raw in enumerate(prepared.statements):
        declaration = raw.stmt
        if isinstance(declaration, ast.CreateFunctionStmt) and tuple(
            part.sval for part in declaration.funcname or ()
        ) == ("ops", "read_selected_pdf_source"):
            programs.append(capture_sql)
        programs.append(prepared.excerpt(index))
    sql = native_sql_script((*programs, source_original_sql(sources), visual_read_sql(sources)))

    return _rename_native_entrypoints(sql, {item["name"] for item in wire_operations(sources)})


def source_native_definitions(connection, *, sources=None) -> tuple[NativeDefinition, ...]:
    source = "data-operation-source-admission:forward"
    prepared = prepare_sql(source_native_sql(sources), source=source)
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
                grants=(
                    (("corpus_sem_writer", "EXECUTE", False),)
                    if statement.funcname[-1].sval
                    in {
                        "ddo_pdf_capture_source",
                        "ddo_pdf_observation_source",
                        "register_original_document",
                    }
                    else tuple(
                        (role, "EXECUTE", False)
                        for role in (
                            "corpus_sem_writer",
                            "corpus_sem_reader",
                            "corpus_sem_admitter",
                            "corpus_sem_evaluator",
                        )
                    )
                    if statement.funcname[-1].sval == "require_source_admission"
                    else ()
                ),
            )
        )
    return tuple(definitions)
