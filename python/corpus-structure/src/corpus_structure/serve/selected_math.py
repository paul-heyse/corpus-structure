"""Selected mathematical results attributed to an authenticated native PDF source."""

from __future__ import annotations

from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.demand_results import selected_record_index


def selected_formula_interpretations(connection, source, pointer, *, read_budget):
    """Read current selected outputs; matching source meaning grants no new admission."""
    from corpus_structure.ingest.pdf_section_views import published_section_projections
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.declared_math_products import (
        DeclaredMathOccurrenceProduct,
        DeclaredMathScopeProduct,
        DeclaredMathSymbolicProduct,
    )
    from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
    from corpus_structure.semantic.source_products import FrozenNativeSource

    classes = {
        "urn:corpus:math:DeclaredMathOccurrenceProduct": DeclaredMathOccurrenceProduct,
        "urn:corpus:math:DeclaredMathSymbolicProduct": DeclaredMathSymbolicProduct,
        "urn:corpus:math:DeclaredMathScopeProduct": DeclaredMathScopeProduct,
    }
    model = bound_data_operation_model(source.prepared)
    contracts = {
        item.key: classes[item.owner]
        for item in model.identities
        if item.domain == "kind" and item.owner in classes
    }
    pins = source.cut.record
    reader = PublishedPdfReader(
        connection, source.physical, projection_context=source.prepared, read_budget=read_budget,
    )
    results, projections = [], {}
    with selected_record_index(
        connection, pins["demand_id"], project_id=pins["project_id"],
        read_id=pins["read_id"], scope=pins["scope"], expected_cut=source.cut.identity,
        capture_frontier=True, max_bytes=read_budget.max_bytes,
        max_total_bytes=read_budget.max_bytes,
    ) as (_, index):
        products = index.mapping("kb.data_product", ("id",))
        members = index.mapping("kb.data_product_member", ("product_id", "member_id"))
        capture = decode_semantic_value(products[source.reference.product_id]["canonical_body"])
        for use in index.frontier_rows("uses"):
            if use["fate"] != "fulfilled":
                continue
            for output in index.rows_for("ops.data_derivation_output", derivation_id=use["derivation_id"]):
                if output["member_id"] is None:
                    product = products[output["product_id"]]
                    contract, body = product["kind_contract"], product["canonical_body"]
                else:
                    member = members[output["product_id"], output["member_id"]]
                    contract, body = member["kind_contract"], member["body"]
                kind = contracts.get(contract)
                if kind is None:
                    continue
                value = kind.model_validate(decode_semantic_value(body))
                if value.source.original_source != capture["document"]:
                    continue
                selected_items = tuple(item for item in value.items if item.get("pointer") == pointer)
                if not selected_items:
                    continue
                reference = value.source
                key = (reference.section_pointer, reference.membership)
                if key not in projections:
                    rows = published_section_projections(
                        reader, selections=(key[0],), membership=key[1], scope=None,
                    )
                    exact = tuple(row for row in rows if row.section_pointer == key[0])
                    if len(exact) != 1:
                        raise ValueError("selected mathematical source has no exact native section")
                    row = exact[0]
                    projections[key] = FrozenNativeSource.from_projection(
                        source.prepared, document=capture["document"], section_pointer=row.section_pointer,
                        membership=row.membership, text=row.text, pieces=row.pieces,
                        items=row.items, ancestors=row.ancestors,
                        recognition=row.health.get("formula_outcomes", ()),
                    ).value["source"]["projection"]
                if projections[key] != reference.projection_digest:
                    continue  # A different retained source meaning is not this PDF projection.
                source_row = (
                    products[reference.source_product]
                    if reference.source_member is None
                    else members[reference.source_product, reference.source_member]
                )
                original = decode_semantic_value(source_row["canonical_body"] if reference.source_member is None else source_row["body"])
                frozen = FrozenNativeSource.acquire(source.prepared, original)
                if frozen.value["source"]["projection"] != reference.projection_digest:
                    raise ValueError("selected mathematical source reference differs from its admitted body")
                if pointer not in {item["self_ref"] for item in frozen.value["items"]}:
                    raise ValueError("selected mathematical occurrence is outside its admitted source")
                record = dict(
                    use_id=use["use_id"], derivation_id=use["derivation_id"],
                    product_id=output["product_id"], member_id=output["member_id"],
                    kind_contract=contract, role=output["role"], position=output["position"],
                    multiplicity=output["multiplicity"], source=reference.model_dump(mode="json"),
                    phase=value.phase, outcome=value.outcome, issues=value.issues, items=selected_items,
                )
                read_budget.value(record)
                results.append(record)
    return dict(
        status="recorded" if results else "not_selected", cut=source.cut.record, results=results,
    )
