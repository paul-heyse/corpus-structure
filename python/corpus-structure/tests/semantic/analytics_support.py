"""Shared controlled inputs and builders for analytics support."""

from __future__ import annotations

from types import MappingProxyType

import pyarrow as pa

from corpus_structure.semantic import (
    PreparationProfile,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.analytics import AnalyticalPacket, compile_projection
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.contracts import execution_payload
from corpus_structure.semantic.query import SnapshotBinding


def prepared_inputs():
    source = b"""id: https://example/model
name: example
prefixes: {ex: 'https://example/'}
default_prefix: ex
types:
  string: {base: str, uri: "http://www.w3.org/2001/XMLSchema#string"}
classes:
  Thing:
    attributes:
      label: {required: false, multivalued: true}
"""
    bundle, dependencies = analytical_inputs(
        SourceBundle("example", (SourceArtifact("example", source),))
    )
    dependencies = composed_dependencies(dependencies)
    return (
        bundle,
        dependencies,
        prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2")),
    )


def empty_packet(prepared):
    compiled = compile_projection(prepared, SnapshotBinding(prepared.release_id, "z", 0, "cap"))
    return AnalyticalPacket(
        compiled.binding,
        compiled.projection_id,
        compiled.profile.digest,
        MappingProxyType(
            {p.name: pa.Table.from_pylist([], schema=p.schema) for p in compiled.relations}
        ),
        scale=compiled.profile.scale,
        execution_model_id=prepared.execution_model_id,
        execution_contract=execution_payload(prepared),
    )
