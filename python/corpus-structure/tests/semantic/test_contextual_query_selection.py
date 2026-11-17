"""Exact selected member acquisition controls, without native/provider claims."""

from contextlib import contextmanager
from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.semantic import contextual_selection as owner
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.selected_support import SelectedSupportAcquisition
from semantic.test_contextual_workflow_preparation import unadmitted_frame
from semantic.test_demand_results import _page


def selection_case():
    frame, context = unadmitted_frame("Ada acts.")
    page = _page()
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

    class Index:
        def frontier_rows(self, name):
            return (
                dict(fate="fulfilled", use_id="unadmitted:use", derivation_id="unadmitted:episode"),
            )

        def mapping(self, name, key):
            return {
                "kb.data_product": {
                    selector.product_id: dict(
                        kind_contract="parent-kind",
                        canonical_body=semantic_value({"not": "the carrier"}),
                    )
                },
                "kb.data_product_member": {
                    (selector.product_id, selector.member_id): dict(
                        kind_contract="member-kind", body=semantic_value(expected)
                    )
                },
                "sem.data_kind_contract": {
                    "parent-kind": dict(kind="urn:parent"),
                    "member-kind": dict(kind="urn:carrier"),
                },
            }[name]

    @contextmanager
    def index(connection, demand, **kwargs):
        yield cut, Index()

    def selected_entries(index, read, **kwargs):
        assert kwargs["member_id"] == selector.member_id
        return (occurrence,)

    monkeypatch.setattr(demand_results, "selected_record_index", index)
    monkeypatch.setattr(owner, "selected_source_entries", selected_entries)
    body, entry, actual_cut = owner._selected_product(
        None, selector, project_id=context.project_id, kind_name="urn:carrier"
    )
    assert body == expected and entry == occurrence and actual_cut == cut
    with pytest.raises(ValueError, match="nominal contract"):
        owner._selected_product(
            None, selector, project_id=context.project_id, kind_name="urn:parent"
        )
