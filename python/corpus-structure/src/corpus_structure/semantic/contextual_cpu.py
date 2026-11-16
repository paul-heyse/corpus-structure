"""Contextual scalar authority replies on the existing owned CPU execution path."""

from __future__ import annotations

from .data_operation_cpu_basis import cpu_authority_reply
from .data_operation_identity import decode_semantic_value
from .data_operation_json import json_bytes
from .data_operation_model import SubjectContext


def contextual_basis_values(input_basis):
    from .data_operation_cpu_basis import _require_current_basis

    _require_current_basis(input_basis)
    basis = decode_semantic_value(input_basis)
    if basis["version"] != "cpu-input-basis-2":
        raise ValueError("contextual computation requires its actual typed input basis")
    roles = {}
    for row in basis["roles"]:
        if row["multiplicity"] != 1:
            raise ValueError("contextual scalar computation requires distinct selected inputs")
        roles.setdefault(row["role"], []).append(row)
    raw = basis["context"]
    context = SubjectContext(
        raw["project_id"],
        raw["subject"],
        raw["original_source"],
        json_bytes(raw["analyzed_scope"]),
        subject_definition=raw["subject_definition"],
    )
    return roles, context


def contextual_input_role(row):
    from .data_operation_cpu_basis import CPUInputRole
    from .data_operation_support import read_support_references

    raw = row["context"]
    context = SubjectContext(
        raw["project_id"],
        raw["subject"],
        raw["original_source"],
        json_bytes(raw["analyzed_scope"]),
        subject_definition=raw["subject_definition"],
    )
    return CPUInputRole(
        row["role"],
        row["position"],
        row["multiplicity"],
        row["product_id"],
        row["member_id"],
        row["kind_contract"],
        context,
        row["body"],
        read_support_references(row["support"]),
    )


def checked_frame_source(frame_record, source):
    """One exact actual source header/body projection for contextual CPU consumers."""
    from .data_operation_identity import semantic_value
    from .data_operation_model import json_context_meaning
    from .declared_record_sources import DeclaredNativeFrameSource
    from .identity import canonical_bytes

    frame = DeclaredNativeFrameSource(**frame_record)
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


def contextual_authority_reply(input_basis, products):
    return cpu_authority_reply(input_basis, products)


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
    roles, context = contextual_basis_values(input_basis)

    def one(name):
        if len(roles.get(name, ())) != 1:
            raise ValueError("contextual projection requires one exact " + name)
        return roles[name][0]["body"]

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
        if any(
            row["body"].get("original_source") != row["context"]["original_source"]
            for row in targets
        ):
            raise ValueError("target vector differs from its actual original custody")
        query = one("query")
        if query.get("original_source") != context.original_source:
            raise ValueError("query vector differs from its actual original custody")
        result = selected_vector_frame(
            one("inventory"), query, tuple(row["body"] for row in targets)
        )
    else:
        raise ValueError("contextual projection belongs to another captured operation")
    check_active()
    return contextual_authority_reply(input_basis, result)
