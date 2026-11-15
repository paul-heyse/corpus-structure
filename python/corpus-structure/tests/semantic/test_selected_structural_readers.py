"""Independent selected-root, original-coordinate and immutable population controls."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from corpus_structure.methods.structural_products import produce_structural_dossier
from corpus_structure.serve import structural_products as reader
from corpus_structure.serve.selected_structural import SelectedStructuralRoot, selected_root
from corpus_structure.serve.source_decision_journey import (
    SelectedJourneyLayer,
    SelectedOpportunity,
    selected_journey_layer,
    selected_source_state,
)
from corpus_structure.serve.structural_gaps import SelectedGapRequest, selected_gap_rows
from semantic.test_dossier_products import _predecessor

ROOT = SelectedStructuralRoot.model_validate(
    dict(
        product_id="native:report",
        member_id=None,
        use_id="use:actual",
        derivation_id="derivation:actual",
    )
)


def test_structural_read_implementation_owns_actual_bootstrapped_helper_objects():
    from corpus_structure._query_custody import STRUCTURAL_READ_SOURCES
    from corpus_structure.serve.rich_queries import installed_read_implementation

    # This checks the actual warm module objects, including this family's new
    # selected owner. A source bundle alone cannot authenticate a prior plain import.
    with installed_read_implementation(
        reader.SelectedStructuralRequest,
        sources=STRUCTURAL_READ_SOURCES,
        profile="selected-structural-read-v1",
    ) as implementation:
        assert len(implementation) == 64


def test_root_selection_requires_actual_member_use_and_original_episode():
    value = SimpleNamespace(
        reference=SimpleNamespace(member_id=None),
        use_id="use:actual",
        derivation_id="derivation:actual",
        body={},
    )
    scope = SimpleNamespace(products=lambda **kwargs: (value,))
    assert selected_root(scope, ROOT) is value
    for field in ("member_id", "use_id", "derivation_id"):
        assert selected_root(scope, ROOT.model_copy(update={field: "foreign"})) is None


@pytest.fixture
def dossier():
    component, root, predecessor, report, inputs = _predecessor()
    return produce_structural_dossier(
        inputs,
        root_component=root,
        root=component,
        retained=((predecessor, {"report": report}),),
        relationships={},
    )


def test_dossier_pages_preserve_full_membership_and_exact_citations(dossier):
    before = dossier.model_dump(mode="json")
    keys = [member.member_id for member in dossier.dossier.members]
    first = reader.dossier_member_page(dossier, population="membership", offset=0, limit=1)
    second = reader.dossier_member_page(dossier, population="membership", offset=1, limit=1)
    assert [first["members"][0]["member_id"], second["members"][0]["member_id"]] == keys
    assert first["next_offset"] == 1 and second["next_offset"] is None
    assert first["full_member_count"] == 2
    assert first["citations"][0]["citation"]["text"] in {"term", "def"}
    assert first["citations"][0]["source"]["source_product"] == "source:actual"
    display = reader.dossier_member_page(dossier, population="display", offset=0, limit=100)
    assert [member["member_id"] for member in display["members"]] == list(
        dossier.dossier.representation.selected
    )
    assert dossier.model_dump(mode="json") == before


def test_selected_dossier_cursor_rejects_foreign_read_population_and_membership(
    monkeypatch, dossier
):
    from corpus_structure.semantic.demand_queries import _cursor
    from corpus_structure.serve.rich_queries import decode_rich_cursor

    selected = SimpleNamespace()
    scope = SimpleNamespace(
        cut=SimpleNamespace(identity="cut:exact", record={"read_id": "read:exact"}),
        implementation="a" * 64,
    )

    @contextmanager
    def acquire(conn, request, **kwargs):
        assert request.read_id in (None, "read:exact")
        yield scope

    monkeypatch.setattr(reader, "structural_scope", acquire)
    monkeypatch.setattr(reader, "selected_root", lambda *args: selected)
    monkeypatch.setattr(reader, "structural_report", lambda *args: dossier)
    monkeypatch.setattr(reader, "producer", lambda *args: {"use_id": "use:actual"})
    request = reader.SelectedDossierRequest(
        demand_id="d", project_id="project", root=ROOT, population="membership", limit=1
    )
    first = reader.inspect_selected_dossier(None, request)
    assert first["next_cursor"] is not None
    second = reader.inspect_selected_dossier(
        None, request.model_copy(update={"cursor": first["next_cursor"]})
    )
    assert second["next_cursor"] is None
    assert first["members"][0]["member_id"] != second["members"][0]["member_id"]
    for update in ({"population": "display"}, {"read_id": "foreign", "expected_cut": "cut:other"}):
        with pytest.raises(ValueError, match="continuation differs"):
            reader.inspect_selected_dossier(
                None, request.model_copy(update={"cursor": first["next_cursor"], **update})
            )
    cursor = decode_rich_cursor(first["next_cursor"])
    cursor["binding"]["membership_digest"] = "f" * 64
    with pytest.raises(ValueError, match="membership/facets/policy"):
        reader.inspect_selected_dossier(
            None, request.model_copy(update={"cursor": _cursor(cursor)})
        )


def opportunity():
    source = _predecessor()[3].inputs.sources[0]
    return SelectedOpportunity(source=source, pointer="#/texts/0", start=0, end=4)


def test_source_coordinates_separate_projection_omission_outside_selection_and_bad_extent():
    selected = opportunity()
    source = dict(
        items=[dict(self_ref="#/texts/0", text="term def")],
        text="term def",
        pieces=[dict(kind="native_text", item_ref="#/texts/0", start=0, end=8)],
    )
    assert selected_source_state(selected, source) == ("represented", ((0, 4),))
    assert selected_source_state(selected, {**source, "pieces": [], "text": ""}) == (
        "omitted_from_projection",
        (),
    )
    assert selected_source_state(selected, {**source, "items": []}) == ("outside_selection", ())
    with pytest.raises(ValueError, match="escapes"):
        selected_source_state(selected.model_copy(update={"end": 20}), source)


def test_dossier_journey_binds_exact_native_comparison_address_and_side():
    selected = opportunity()
    reference = dict(product_id="comparison:actual", member_id=None, kind_contract="kind:actual")
    layer = SelectedJourneyLayer(layer="dossier", root=ROOT)
    member = dict(member_id="m", comparison_binding=dict(comparison_ref=reference, side="left"))
    body = dict(
        dossier=dict(predecessors=[reference], members=[member], representation=dict(selected=[]))
    )
    assert selected_journey_layer(layer, selected, body, (), comparison=(reference, {"left"})) == (
        True,
        dict(membership=[member], display=[]),
    )
    assert selected_journey_layer(layer, selected, body, (), comparison=(reference, {"right"})) == (
        False,
        dict(membership=[], display=[]),
    )
    assert (
        selected_journey_layer(
            layer,
            selected,
            body,
            (),
            comparison=({**reference, "product_id": "same-body-other-product"}, {"left"}),
        )
        is None
    )


def decision_body(outcome="ambiguous"):
    return dict(
        source_pin={"source": "actual"},
        anchors=[],
        candidate_list=dict(
            list_id="list:actual",
            occurrence_id="occurrence:actual",
            eligible_target_count=0,
            candidates=[],
        ),
        relationship_decision=dict(
            candidate_list_id="list:actual",
            occurrence_id="occurrence:actual",
            scope="selected",
            outcome=outcome,
            reason="Ambiguous recorded reading.",
        ),
    )


def test_binding_gaps_use_actual_decisions_and_never_infer_absence():
    request = SelectedGapRequest(
        demand_id="d", project_id="project", root=ROOT, report="unresolved_binding"
    )
    body = decision_body()
    rows = selected_gap_rows(request, body)
    assert rows[0]["outcome"] == "ambiguous" and rows[0]["status"] == "actionable"
    assert rows[0]["evidence"]["candidate_list"]["eligible_target_count"] == 0
    assert selected_gap_rows(request, decision_body("selected")) == []
    with pytest.raises(ValueError, match="outside"):
        selected_gap_rows(request.model_copy(update={"occurrence_id": "foreign"}), body)
    body["relationship_decision"]["candidate_list_id"] = "other"
    with pytest.raises(ValueError, match="exact candidate"):
        selected_gap_rows(request, body)


def test_comparison_computational_custody_does_not_establish_scientific_support():
    request = SelectedGapRequest(
        demand_id="d", project_id="project", root=ROOT, report="unconnected_supported_comparison"
    )
    rows = selected_gap_rows(
        request, dict(inputs=dict(scope="selected"), comparison={"left_id": "left"})
    )
    assert rows[0]["status"] == "unavailable"
    assert rows[0]["reason"] == "authorized_comparison_support_unavailable"
