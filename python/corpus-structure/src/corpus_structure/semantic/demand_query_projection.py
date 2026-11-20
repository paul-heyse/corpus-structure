"""Deterministic selected-member projection over an already acquired native page."""

from __future__ import annotations

from dataclasses import dataclass

from .data_operation_json import json_loads, wire_json_loads
from .data_operation_value_codec import decode_semantic_value
from .data_operation_value_codec import native_semantic_value as semantic_value


@dataclass(frozen=True)
class DemandQueryProjectionInputs:
    """Owned native wire bytes and the already validated semantic query selection."""

    native: bytes
    selection: bytes
    decimal_fixed_point_digits: int


def selected_members(page: dict, *, decimal_fixed_point_digits: int) -> tuple[dict, ...]:
    """Project actual selected packets without acquiring another product body."""
    if page["view"] != "products":
        raise ValueError("member reads require a body-bearing selected result")
    occurrences = []
    for use in page["uses"]:
        if use["fate"] != "fulfilled":
            continue
        for output in use["products"]:
            body = decode_semantic_value(
                output["body"], decimal_fixed_point_digits=decimal_fixed_point_digits
            )
            header = dict(
                use_id=use["use_id"],
                derivation_id=use["derivation_id"],
                product_id=output["product_id"],
                role=output["role"],
                output_member_id=output["member_id"],
                position=output["position"],
                multiplicity=output["multiplicity"],
            )
            if output["member_id"] is None:
                occurrences.append(
                    dict(
                        header,
                        member_id=None,
                        kind_contract=output["kind_contract"],
                        subject=output["subject"],
                        subject_definition=output["subject_definition"],
                        original_source=output["original_source"],
                        analyzed_scope=output["analyzed_scope"],
                        body=body,
                        meaning_body=output["body"],
                    )
                )
            packets = body.get("members", ()) if isinstance(body, dict) else ()
            projected = [
                packet
                for packet in packets
                if output["member_id"] is None or packet["member_id"] == output["member_id"]
            ]
            if output["member_id"] is not None and len(projected) != 1:
                raise ValueError("selected output member is absent from its canonical product")
            occurrences.extend(
                dict(
                    header,
                    member_id=packet["member_id"],
                    kind_contract=packet["kind_contract"],
                    **packet["context"],
                    body=packet["body"],
                    meaning_body=semantic_value(
                        packet["body"], decimal_fixed_point_digits=decimal_fixed_point_digits
                    ),
                )
                for packet in projected
            )
    return tuple(occurrences)


def selected_query_rows(inputs: DemandQueryProjectionInputs):
    if type(inputs) is not DemandQueryProjectionInputs:
        raise TypeError("native projection requires its owned immutable input snapshot")
    if type(inputs.native) is not bytes or type(inputs.selection) is not bytes:
        raise TypeError("native projection requires immutable wire bytes")
    decimal_fixed_point_digits = inputs.decimal_fixed_point_digits
    if (
        type(decimal_fixed_point_digits) is not int
        or not 1 <= decimal_fixed_point_digits <= 2_147_483_647
    ):
        raise ValueError("native projection requires a positive model-derived decimal limit")
    native: dict = wire_json_loads(inputs.native)
    selection: dict = json_loads(inputs.selection)
    if selection["view"] == "operations":
        rows = (
            dict(
                obligation=obligation,
                uses=[
                    use
                    for use in native["uses"]
                    if use["obligation_id"] == obligation["obligation_id"]
                ],
            )
            for obligation in native["obligations"]
        )
    elif selection["view"] in {"sources", "support"}:
        rows = (
            row
            for row in native["support_page"]["records"]
            if selection["view"] == "support" or row["relation"] == "ops.original_source_admission"
        )
    elif selection["view"] == "coverage":
        rows = (
            dict(
                product_id=row["product_id"],
                use_id=row["use_id"],
                derivation_id=row["derivation_id"],
                source=row["body"]["source"],
                coverage=coverage,
            )
            for row in selected_members(
                native, decimal_fixed_point_digits=decimal_fixed_point_digits
            )
            if row["member_id"] is None
            and isinstance(row["body"], dict)
            and "source" in row["body"]
            for coverage in row["body"].get("coverage", ())
        )
    else:
        rows = selected_members(native, decimal_fixed_point_digits=decimal_fixed_point_digits)
    filters = dict(kind_contract=selection["kind_contract"], member_id=selection["member_id"])
    if selection["view"] in {"members", "coverage"}:
        filters["product_id"] = selection["product_id"]
    for row in rows:
        body = row.get("body", row.get("coverage"))
        if (
            (not selection["containers_only"] or row.get("member_id") is None)
            and (
                selection["record_type"] is None
                or (isinstance(body, dict) and body.get("record_type") == selection["record_type"])
            )
            and (
                selection["family"] is None
                or (isinstance(body, dict) and body.get("family") == selection["family"])
            )
            and all(value is None or row.get(key) == value for key, value in filters.items())
        ):
            yield row
