"""Capture the wire compiler, exact JSON codec and nominal type authorities."""

from __future__ import annotations

from pathlib import Path

from .types import SourceArtifact


def wire_native_sources(nominal_types: bytes) -> tuple[SourceArtifact, ...]:
    return (
        SourceArtifact(
            "native/data-operation-wire-types.py",
            Path(__file__).with_name("_data_operation_wire.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-wire-types.yaml",
            nominal_types,
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
