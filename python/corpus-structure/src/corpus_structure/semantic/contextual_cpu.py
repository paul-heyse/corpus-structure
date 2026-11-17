"""Shared contextual source correspondence and existing scalar projection kernels."""

from __future__ import annotations

from .data_operation_cpu_basis import cpu_authority_reply, cpu_basis_values


def checked_frame_source(frame_record, source):
    """One exact actual source header/body projection for contextual CPU consumers."""
    from .declared_record_sources import DeclaredNativeFrameSource

    return checked_native_frame(DeclaredNativeFrameSource(**frame_record), source)


def checked_native_frame(frame, source):
    """Check the already prepared immutable view without decoding it again."""
    from .data_operation_identity import semantic_value
    from .data_operation_model import json_context_meaning
    from .identity import canonical_bytes

    pin, context = frame.pin.values(), source.context
    if (
        pin["source"] != canonical_bytes([source.product_id, source.member_id]).decode()
        or (
            canonical_bytes(semantic_value(frame.value))
            != canonical_bytes(semantic_value(source.body))
        )
        or (
            pin["source_product"],
            pin["kind_contract"],
            pin["project_id"],
            pin["subject"],
            pin["subject_definition"],
            pin["original_source"],
            pin["analyzed_scope_meaning"],
        )
        != (
            source.product_id,
            source.kind_contract,
            context.project_id,
            context.subject,
            context.subject_definition,
            context.original_source,
            json_context_meaning(context.analyzed_scope).decode(),
        )
    ):
        raise ValueError("query frame differs from its actual processed source product/context")
    return frame


def execute_contextual_projection_kernel(
    input_basis: list, operation: str, member_contract: str, *, check_active
) -> dict:
    from .contextual_operations import contextual_inventory_values
    from .contextual_target_products import (
        component_target_population,
        curated_target_population,
        materialize_target,
        selected_vector_frame,
    )

    check_active()
    populations = {
        "retrieve.contextual_targets/curated": (("selection",), ()),
        "retrieve.contextual_targets/components": (("report",), ()),
        "retrieve.contextual_target/declared": (("target",), ()),
        "retrieve.contextual_inventory/declared": (("selection",), ()),
        "retrieve.contextual_vectors/selection": (("inventory", "query"), ("targets",)),
    }
    if operation not in populations:
        raise ValueError("contextual projection belongs to another captured operation")
    scalars, sets = populations[operation]
    roles, context = cpu_basis_values(input_basis, scalar_roles=scalars, set_roles=sets)

    def one(name):
        return roles[name][0].body

    if operation == "retrieve.contextual_targets/curated":
        if context.original_source is not None:
            raise ValueError("curated targets cannot acquire a query original")
        result = curated_target_population(one("selection"), kind_contract=member_contract)
    elif operation == "retrieve.contextual_targets/components":
        result = component_target_population(
            one("report"), original_source=context.original_source, kind_contract=member_contract
        )
    elif operation == "retrieve.contextual_target/declared":
        result = materialize_target(one("target"), context=context)
    elif operation == "retrieve.contextual_inventory/declared":
        result = contextual_inventory_values(one("selection"))
    elif operation == "retrieve.contextual_vectors/selection":
        targets = roles.get("targets", ())
        if any(row.body.get("original_source") != row.context.original_source for row in targets):
            raise ValueError("target vector differs from its actual original custody")
        query = one("query")
        if query.get("original_source") != context.original_source:
            raise ValueError("query vector differs from its actual original custody")
        result = selected_vector_frame(one("inventory"), query, tuple(row.body for row in targets))
    else:
        raise ValueError("contextual projection belongs to another captured operation")
    check_active()
    return cpu_authority_reply(input_basis, result)
