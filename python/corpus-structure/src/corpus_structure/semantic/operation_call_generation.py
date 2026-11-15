"""Generate fixed native calls and positional materializers from the owned call contract."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from hashlib import sha256

from .identity import canonical_bytes
from .native_call_sources import _PRIMITIVES, _integer_bounds


def _legacy_sources(inputs):
    from .contracts import _fail, retained_physical_sources

    artifacts = {item.name: item.content for item in inputs.implementations}
    names = {
        "physical": "pdf/record-physical.yaml",
        "read_projections": "pdf/read-projections.yaml",
        "pdf_records": "pdf/record-model.yaml",
        "pdf_staging": "pdf/staging-model.yaml",
        "companion_projections": "capture/companion-projection-model.yaml",
        "linkml:types": "unified/linkml-types.yaml",
    }
    supplied = {item.name: item.content for item in inputs.schema.sources}
    for name, artifact in names.items():
        if artifact not in artifacts:
            _fail("operation_source", artifact, "required source module is unavailable")
        supplied[name] = artifacts[artifact]
    return supplied, retained_physical_sources(artifacts)


def source_bindings(model, inputs):
    """Legacy compiler entry point; current consumers supply closed sources directly."""
    from .native_call_sources import source_bindings as native_source_bindings

    logical, physical = _legacy_sources(inputs)
    return native_source_bindings(
        tuple((operation.id, call) for operation in model.operations for call in operation.calls),
        logical_sources=logical,
        physical_sources=physical,
    )


def validate_call_bindings(model, inputs):
    """Keep legacy ownership checks at the retiring caller, outside native field resolution."""
    from .contracts import _fail
    from .native_call_sources import resolve_call_bindings

    for operation in model.operations:
        if operation.calls and operation.implementation is None:
            _fail(
                "operation_call",
                "operations/" + operation.id,
                "fixed call needs its trusted implementation owner",
            )
    implementations = {binding.id: binding for binding in model.implementations}
    core_owners = {
        (operation.id, call.id): implementations[operation.implementation].owner
        + "."
        + implementations[operation.implementation].symbol
        for operation in model.operations
        if operation.implementation is not None
        for call in operation.calls
    }
    logical, physical = _legacy_sources(inputs)
    calls = resolve_call_bindings(
        tuple((operation.id, call) for operation in model.operations for call in operation.calls),
        logical_sources=logical,
        physical_sources=physical,
        core_owners=core_owners,
    )
    resolved = {(owner, call.id): call for owner, call in calls}
    return replace(
        model,
        operations=tuple(
            replace(
                operation, calls=tuple(resolved[operation.id, call.id] for call in operation.calls)
            )
            for operation in model.operations
        ),
    )






def render_operation_identifiers(model):
    """Render legacy inputs through the shared, model-independent emitter."""
    from .native_call_generation import render_call_identifiers

    return render_call_identifiers(
        tuple((op.id, call) for op in model.operations for call in op.calls)
    )




def render_operation_calls(model, metadata=None):
    """Render legacy inputs through the shared, model-independent emitter."""
    from .native_call_generation import render_call_bindings

    return render_call_bindings(
        tuple((operation.id, call) for operation in model.operations for call in operation.calls),
        metadata,
        identifiers_module="._operation_ids",
        context_validator=(".operation_value_types", "require_call_context"),
    )




def generated_source() -> str:
    from corpus_structure.schema.generate import _format

    from .contracts import compile_execution_model, trusted_execution_inputs
    from .metadata import metadata

    return _format(
        "semantic/_operation_calls.py",
        render_operation_calls(compile_execution_model(trusted_execution_inputs()), metadata),
    )
