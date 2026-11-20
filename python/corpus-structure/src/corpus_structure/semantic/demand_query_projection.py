"""Deterministic selected-member projection over an already acquired native page."""

from __future__ import annotations

from dataclasses import dataclass

from .data_operation_json import json_loads, own_json_value
from .data_operation_value_codec import decode_semantic_value, tagged_mapping_field
from .owned_json import FrozenObject, freeze_json, thaw_json


@dataclass(frozen=True)
class DemandQueryProjectionInputs:
    """Detached generated values of the material admitted by native acquisition."""

    page: FrozenObject
    selection: FrozenObject
    decimal_fixed_point_digits: int


def prepare_demand_projection_inputs(
    native: bytes, selection: bytes, *, decimal_fixed_point_digits: int
) -> DemandQueryProjectionInputs:
    """Validate once during acquisition, before selected row derivation.

    The native cut already identifies immutable product bodies; strict generated
    decoding must preserve their complete material rather than transform it.
    """
    from .demand_wire import decode_wire_demand_result

    if type(selection) is not bytes:
        raise TypeError("native projection requires immutable selection bytes")
    page = freeze_json(decode_wire_demand_result(native))
    selected = freeze_json(json_loads(selection))
    if type(page) is not FrozenObject or type(selected) is not FrozenObject:
        raise TypeError("native projection requires a page and selection object")
    return DemandQueryProjectionInputs(
        page=page,
        selection=selected,
        decimal_fixed_point_digits=decimal_fixed_point_digits,
    )


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
            packets = ()
            if type(body) is dict:
                packets = body.get("members", ())
            original_packets = ()
            if packets:
                original_members = tagged_mapping_field(output["body"], "members")
                if (
                    type(original_members) is not list
                    or len(original_members) != 2
                    or original_members[0] != "sequence"
                    or type(original_members[1]) is not list
                ):
                    raise ValueError("selected member collection requires its original sequence")
                original_packets = original_members[1]
            projected = [
                (packet, original)
                for packet, original in zip(packets, original_packets, strict=True)
                if output["member_id"] is None or packet["member_id"] == output["member_id"]
            ]
            if output["member_id"] is not None and len(projected) != 1:
                raise ValueError("selected output member is absent from its canonical product")
            for packet, original in projected:
                if type(packet) is not dict:
                    raise TypeError("selected member packets require owned records")
                context = packet["context"]
                if type(context) is not dict:
                    raise TypeError("selected member context requires an owned record")
                occurrences.append(
                    dict(
                        header,
                        member_id=packet["member_id"],
                        kind_contract=packet["kind_contract"],
                        subject=context["subject"],
                        subject_definition=context["subject_definition"],
                        original_source=context["original_source"],
                        analyzed_scope=context["analyzed_scope"],
                        body=packet["body"],
                        meaning_body=own_json_value(tagged_mapping_field(original, "body")),
                    )
                )
    return tuple(occurrences)


def selected_coverage(page: dict, *, decimal_fixed_point_digits: int):
    """Stream coverage rows without expanding a product's complete coverage array."""
    for row in selected_members(page, decimal_fixed_point_digits=decimal_fixed_point_digits):
        if type(row) is not dict:
            raise TypeError("coverage projection requires an owned row")
        body = row["body"]
        if row["member_id"] is not None:
            continue
        if type(body) is dict:
            if "source" not in body:
                continue
            for coverage in body.get("coverage", ()):
                yield dict(
                    product_id=row["product_id"],
                    use_id=row["use_id"],
                    derivation_id=row["derivation_id"],
                    source=body["source"],
                    coverage=coverage,
                )


def _record_array(value):
    if type(value) is not list:
        raise TypeError("native projection requires an array of records")
    for record in value:
        if type(record) is not dict:
            raise TypeError("native projection requires exact record values")
        yield record


def selected_query_rows(inputs: DemandQueryProjectionInputs):
    if type(inputs) is not DemandQueryProjectionInputs:
        raise TypeError("native projection requires its owned immutable input snapshot")
    native = thaw_json(inputs.page)
    selection = thaw_json(inputs.selection)
    if type(native) is not dict or type(selection) is not dict:
        raise TypeError("native projection requires owned record inputs")
    decimal_fixed_point_digits = inputs.decimal_fixed_point_digits
    if (
        type(decimal_fixed_point_digits) is not int
        or not 1 <= decimal_fixed_point_digits <= 2_147_483_647
    ):
        raise ValueError("native projection requires a positive model-derived decimal limit")
    if selection["view"] == "operations":
        uses = tuple(_record_array(native["uses"]))
        rows = (
            dict(
                obligation=obligation,
                uses=[use for use in uses if use["obligation_id"] == obligation["obligation_id"]],
            )
            for obligation in _record_array(native["obligations"])
        )
    elif selection["view"] in {"sources", "support"}:
        support = native["support_page"]
        if type(support) is not dict:
            raise TypeError("native projection requires an exact support page")
        rows = (
            row
            for row in _record_array(support["records"])
            if selection["view"] == "support" or row["relation"] == "ops.original_source_admission"
        )
    elif selection["view"] == "coverage":
        rows = selected_coverage(native, decimal_fixed_point_digits=decimal_fixed_point_digits)
    else:
        rows = selected_members(native, decimal_fixed_point_digits=decimal_fixed_point_digits)
    filters = dict(kind_contract=selection["kind_contract"], member_id=selection["member_id"])
    if selection["view"] in {"members", "coverage"}:
        filters["product_id"] = selection["product_id"]
    for row in rows:
        if type(row) is not dict:
            raise TypeError("selected projection requires an owned row")
        body = row.get("body", row.get("coverage"))
        record_type, family = None, None
        if type(body) is dict:
            record_type = body.get("record_type")
            family = body.get("family")
        if (
            (not selection["containers_only"] or row.get("member_id") is None)
            and (selection["record_type"] is None or record_type == selection["record_type"])
            and (selection["family"] is None or family == selection["family"])
            and all(value is None or row.get(key) == value for key, value in filters.items())
        ):
            yield row
