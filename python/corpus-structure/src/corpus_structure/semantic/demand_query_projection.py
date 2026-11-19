"""Deterministic selected-member projection over an already acquired native page."""

from collections.abc import Mapping

from .data_operation_values import decode_semantic_value, semantic_value


def selected_members(page: dict) -> tuple[dict, ...]:
    """Project actual selected packets without acquiring another product body."""
    if page["view"] != "products":
        raise ValueError("member reads require a body-bearing selected result")
    occurrences = []
    for use in page["uses"]:
        if use["fate"] != "fulfilled":
            continue
        for output in use["products"]:
            body = decode_semantic_value(output["body"])
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
                    meaning_body=semantic_value(packet["body"]),
                )
                for packet in projected
            )
    return tuple(occurrences)


def selected_query_rows(native: dict, request):
    if request.view == "operations":
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
    elif request.view in {"sources", "support"}:
        rows = (
            row
            for row in native["support_page"]["records"]
            if request.view == "support" or row["relation"] == "ops.original_source_admission"
        )
    elif request.view == "coverage":
        rows = (
            dict(
                product_id=row["product_id"],
                use_id=row["use_id"],
                derivation_id=row["derivation_id"],
                source=row["body"]["source"],
                coverage=coverage,
            )
            for row in selected_members(native)
            if row["member_id"] is None
            and isinstance(row["body"], dict)
            and "source" in row["body"]
            for coverage in row["body"].get("coverage", ())
        )
    else:
        rows = selected_members(native)
    filters = dict(kind_contract=request.kind_contract, member_id=request.member_id)
    if request.view in {"members", "coverage"}:
        filters["product_id"] = request.product_id
    for row in rows:
        body = row.get("body", row.get("coverage"))
        if (
            (not request.containers_only or row.get("member_id") is None)
            and (
                request.record_type is None
                or (isinstance(body, Mapping) and body.get("record_type") == request.record_type)
            )
            and (
                request.family is None
                or (isinstance(body, Mapping) and body.get("family") == request.family)
            )
            and all(value is None or row.get(key) == value for key, value in filters.items())
        ):
            yield row
