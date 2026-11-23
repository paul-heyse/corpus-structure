"""Exact selected member acquisition controls, without native/provider claims."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.semantic import contextual_selection as owner
from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.selected_support import SelectedSupportAcquisition
from semantic.demand_result_support import demand_result_page
from semantic.test_contextual_workflow_preparation import unadmitted_frame


def selection_case():
    frame, context = unadmitted_frame("Ada acts.")
    page = demand_result_page()
    page.update(project_id=context.project_id, demand_id="unadmitted:demand")
    cut = CutSelection.from_native(page)

    def entry(product, member):
        return SelectedSourceSetEntry.from_selected_header(
            dict(
                product_id=product,
                member_id=member,
                subject=context.subject,
                subject_definition=context.subject_definition,
                original_source=context.original_source,
                analyzed_scope=json_loads(context.analyzed_scope),
                use_id="unadmitted:use",
                derivation_id="unadmitted:episode",
                output_member_id=None,
                role="result",
                position=0,
                multiplicity=1,
            ),
            cut,
        )

    source = entry("unadmitted:product", "unadmitted:member")
    occurrence = entry("unadmitted:report", "unadmitted:carrier")
    return frame, context, cut, source, occurrence


def test_acquisition_retains_source_and_carrier_member_proofs(monkeypatch):
    frame, context, cut, source, occurrence = selection_case()
    selectors = [
        owner.ContextualSelectedProduct(
            cut.record["demand_id"], value.entry.product, member_id=value.entry.member
        )
        for value in (source, occurrence)
    ]
    bodies: dict[str, Any] = {
        source.entry.product: frame.value,
        occurrence.entry.product: dict(
            pin=frame.pin.values(), anchors=[dict(start=0, end=3, source_piece="Ada")]
        ),
    }

    def selected(connection, selection, **kwargs):
        value = source if selection == selectors[0] else occurrence
        return bodies[value.entry.product], value, cut, "unadmitted:source-kind"

    monkeypatch.setattr(owner, "_selected_product_with_kind", selected)
    acquired = owner.acquire_contextual_query_selection(
        None, project_id=context.project_id, source=selectors[0], occurrence=selectors[1]
    )
    assert acquired.query_context == context
    assert acquired.cuts == (cut, cut)
    assert [value.name for value in acquired.source_sets] == [
        "contextual-query-source",
        "contextual-query-occurrence",
    ]
    assert [value.entries for value in acquired.source_sets] == [
        (source.entry,),
        (occurrence.entry,),
    ]
    for selected_set, selected_entry in zip(
        acquired.source_sets, (source, occurrence), strict=True
    ):
        assert isinstance(selected_set.acquisition, SelectedSupportAcquisition)
        assert selected_set.acquisition.reads[0].proofs == (selected_entry.proof,)
    bodies[occurrence.entry.product] = deepcopy(bodies[occurrence.entry.product])
    bodies[occurrence.entry.product]["pin"]["source_member"] = "another-member"
    with pytest.raises(ValueError, match="exact selected native source/context"):
        owner.acquire_contextual_query_selection(
            None, project_id=context.project_id, source=selectors[0], occurrence=selectors[1]
        )


def test_selected_member_uses_its_own_nominal_kind_and_body(monkeypatch):
    from corpus_structure.semantic import demand_results

    _frame, context, cut, _source, occurrence = selection_case()
    selector = owner.ContextualSelectedProduct(
        cut.record["demand_id"], occurrence.entry.product, member_id=occurrence.entry.member
    )
    expected = dict(
        contribution_id="unadmitted:carrier", anchors=[dict(start=0, end=3, source_piece="Ada")]
    )

    header = dict(
        product_id=selector.product_id,
        member_id=selector.member_id,
        kind_contract="member-kind",
        kind="urn:carrier",
        meaning_body=semantic_value(expected),
        subject=context.subject,
        subject_definition=context.subject_definition,
        original_source=context.original_source,
        analyzed_scope=json_loads(context.analyzed_scope),
        use_id="unadmitted:use",
        derivation_id="unadmitted:episode",
        output_member_id=None,
        role="result",
        position=0,
        multiplicity=1,
    )
    headers = [header]

    def answer(connection, program, demand, **request):
        assert program == "read_selected_outputs" and demand == selector.demand_id
        assert request["scope"] == {"product_ids": [selector.product_id]}
        assert request["product_id"] == selector.product_id
        assert request["member_id"] == selector.member_id
        assert request["body"] is True and request["containers_only"] is False
        assert request["limit"] == 2
        return dict(cut=cut.record, rows=headers, answer_after=None, oversized=None)

    monkeypatch.setattr(demand_results, "read_selected_answer", answer)
    body, entry, actual_cut = owner._selected_product(
        None, selector, project_id=context.project_id, kind_name="urn:carrier"
    )
    assert body == expected and entry == occurrence and actual_cut == cut
    with pytest.raises(ValueError, match="nominal contract"):
        owner._selected_product(
            None, selector, project_id=context.project_id, kind_name="urn:parent"
        )

    headers.append({**header, "use_id": "unadmitted:other-use"})
    with pytest.raises(ValueError, match="one exact selected fulfilled output proof"):
        owner._selected_product(
            None, selector, project_id=context.project_id, kind_name="urn:carrier"
        )
    headers.clear()
    with pytest.raises(ValueError, match="one exact selected fulfilled output proof"):
        owner._selected_product(
            None, selector, project_id=context.project_id, kind_name="urn:carrier"
        )
