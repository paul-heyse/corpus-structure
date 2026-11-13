"""Trusted wire schemas lowered once into PostgreSQL's existing schema validator."""

from __future__ import annotations

from pathlib import Path

from .identity import canonical_bytes
from .types import SourceArtifact


def wire_native_sources() -> tuple[SourceArtifact, ...]:
    return (
        SourceArtifact(
            "native/data-operation-wire.sql",
            Path(__file__).with_name("sql").joinpath("data_operation_wire.sql").read_bytes(),
        ),
        SourceArtifact("native/data-operation-wire-native.py", Path(__file__).read_bytes()),
        SourceArtifact(
            "native/data-operation-wire.py",
            Path(__file__).with_name("data_operation_wire.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-json.py",
            Path(__file__).with_name("data_operation_json.py").read_bytes(),
        ),
    )


def wire_native_sql(sources: tuple[SourceArtifact, ...]) -> str:
    from .data_operation_wire import wire_contracts

    supplied = {source.name: source.content for source in sources}
    template = supplied["native/data-operation-wire.sql"].decode()
    if template.count("__DDO_WIRE_CONTRACTS__") != 1:
        raise ValueError("captured native wire template differs")
    # This encodes a JSON constant, never candidate SQL or a SQL identifier.
    schemas = canonical_bytes(wire_contracts(sources)).decode().replace("'", "''")
    return template.replace("__DDO_WIRE_CONTRACTS__", schemas)


def wire_native_definitions(connection, sources: tuple[SourceArtifact, ...] | None = None):
    from .data_operation_storage import native_protocol_sources
    from .native_objects import definition_from_sql

    captured = native_protocol_sources() if sources is None else sources
    return (
        definition_from_sql(
            connection,
            wire_native_sql(captured),
            source="data-operation-wire:forward",
            owner="corpus_sem_publisher",
        ),
    )
