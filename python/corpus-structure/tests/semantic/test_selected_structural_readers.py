"""Independent selected-root, original-coordinate and immutable population controls."""

from contextlib import contextmanager, nullcontext
from types import SimpleNamespace

import pytest

from corpus_structure.methods.structural_products import produce_structural_dossier
from corpus_structure.semantic.selected_structural_projection import (
    dossier_member_page,
    selected_root,
)
from corpus_structure.semantic.serving_identity import _installed_read_basis
from corpus_structure.serve import structural_products as reader
from corpus_structure.serve.selected_structural import SelectedStructuralRoot
from corpus_structure.serve.source_decision_journey import (
    SelectedJourneyLayer,
    SelectedOpportunity,
    selected_journey_layer,
    selected_source_state,
)
from corpus_structure.serve.structural_gaps import SelectedGapRequest, selected_gap_rows
from semantic.selected_query_cache_support import complete_serving_code as complete_serving_code
from semantic.test_dossier_products import _predecessor

pytestmark = pytest.mark.usefixtures("complete_serving_code")

ROOT = SelectedStructuralRoot.model_validate(
    dict(
        product_id="native:report",
        member_id=None,
        use_id="use:actual",
        derivation_id="derivation:actual",
    )
)


def test_structural_read_implementation_owns_actual_bootstrapped_helper_objects():
    from corpus_structure.semantic.serving_identity import installed_read_implementation

    # This checks the actual warm module objects, including this family's new
    # selected owner. A source bundle alone cannot authenticate a prior plain import.
    with installed_read_implementation(
        reader.SelectedStructuralRequest,
        entry=reader.__name__,
        profile="selected-structural-read-v1",
        callables=("corpus_structure.serve.selected_structural.structural_scope",),
    ) as implementation:
        assert len(implementation) == 64


def test_dossier_row_identity_closes_independently_of_the_serving_identity(monkeypatch):
    from corpus_structure.semantic import dossier_row_projection, serving_identity
    from corpus_structure.semantic.serving_code import reusable_serving_code

    monkeypatch.setattr(serving_identity, "_installed_read_basis", _installed_read_basis)
    with serving_identity.installed_read_implementation(
        reader.SelectedDossierRequest,
        entry="corpus_structure.semantic.selected_structural_projection",
        profile="selected-structural-read-v1",
        callables=reader.STRUCTURAL_QUERY_ROOTS,
    ) as serving:
        assert serving.code.unknowns
        assert serving.reuse_identity is None
        with serving_identity.installed_read_implementation(
            reader.SelectedDossierRequest,
            entry=dossier_row_projection.__name__,
            profile="selected-dossier-rows-v1",
            callables=(dossier_row_projection.__name__ + ".dossier_rows",),
        ) as rows:
            assert rows != serving and rows.reuse_identity is not None
            assert reusable_serving_code(rows.reuse_identity)
            assert not reusable_serving_code(serving)
        assert not reusable_serving_code()


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
    first = dossier_member_page(dossier, population="membership", offset=0, limit=1)
    second = dossier_member_page(dossier, population="membership", offset=1, limit=1)
    assert [first["members"][0]["member_id"], second["members"][0]["member_id"]] == keys
    assert first["next_offset"] == 1 and second["next_offset"] is None
    assert first["full_member_count"] == 2
    assert first["citations"][0]["citation"]["text"] in {"term", "def"}
    assert first["citations"][0]["source"]["source_product"] == "source:actual"
    display = dossier_member_page(dossier, population="display", offset=0, limit=100)
    assert [member["member_id"] for member in display["members"]] == list(
        dossier.dossier.representation.selected
    )
    assert dossier.model_dump(mode="json") == before


def test_selected_dossier_cursor_rejects_foreign_read_population_and_membership(
    monkeypatch, dossier
):
    from corpus_structure.semantic.continuation_codec import decode_rich_cursor
    from corpus_structure.semantic.continuation_codec import encode_cursor as _cursor

    selected = SimpleNamespace(release_id="release:producer")
    scope = SimpleNamespace(
        cut=SimpleNamespace(identity="cut:exact", record={"read_id": "read:exact"}),
        implementation="a" * 64,
        decimal_fixed_point_digits=30,
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
    first = reader.inspect_selected_dossier(nullcontext, request)
    assert first["next_cursor"] is not None
    second = reader.inspect_selected_dossier(
        nullcontext, request.model_copy(update={"cursor": first["next_cursor"]})
    )
    assert second["next_cursor"] is None
    assert first["members"][0]["member_id"] != second["members"][0]["member_id"]
    for update in ({"population": "display"}, {"read_id": "foreign", "expected_cut": "cut:other"}):
        with pytest.raises(ValueError, match="continuation differs"):
            reader.inspect_selected_dossier(
                nullcontext, request.model_copy(update={"cursor": first["next_cursor"], **update})
            )
    cursor = decode_rich_cursor(first["next_cursor"])
    cursor["binding"]["membership_digest"] = "f" * 64
    with pytest.raises(ValueError, match="membership/facets/policy"):
        reader.inspect_selected_dossier(
            nullcontext, request.model_copy(update={"cursor": _cursor(cursor)})
        )


def test_dossier_reuses_rows_across_fresh_cuts_after_reauthorizing(monkeypatch, dossier):
    from corpus_structure.semantic import demand_results, selected_query_cache
    from corpus_structure.semantic.selected_query_cache import SELECTED_QUERY_CACHE

    SELECTED_QUERY_CACHE.clear()
    selected = SimpleNamespace(release_id="release:producer")
    launches = []
    verified = []
    calls = []
    state = {"cut": "first", "permit": True, "release": "release:captured"}

    @contextmanager
    def acquire(_conn, request, **_kwargs):
        assert request.read_id is None
        cut = SimpleNamespace(
            identity="cut:" + state["cut"],
            record={"read_id": "read:" + state["cut"], "release_id": state["release"]},
        )
        launches.append(cut.identity)
        yield SimpleNamespace(cut=cut, decimal_fixed_point_digits=30)

    def report(scope, root):
        assert root is selected
        verified.append(scope.cut.identity)
        if not state["permit"]:
            raise ValueError("selected dossier producer was revoked")
        return dossier

    prepare = reader.dossier_row_inputs

    def count(*args, **kwargs):
        calls.append(kwargs["population"])
        return prepare(*args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("dossier cannot acquire a whole-frontier stamp before reuse")

    monkeypatch.setattr(reader, "structural_scope", acquire)
    monkeypatch.setattr(reader, "selected_root", lambda *args: selected)
    monkeypatch.setattr(reader, "structural_report", report)
    monkeypatch.setattr(reader, "dossier_row_inputs", count)
    monkeypatch.setattr(reader, "producer", lambda *args: {"use_id": "use:actual"})
    monkeypatch.setattr(demand_results, "read_selected_operation_frontier", forbidden)
    request = reader.SelectedDossierRequest(
        demand_id="d", project_id="project", root=ROOT, population="membership"
    )
    try:
        first = reader.inspect_selected_dossier(nullcontext, request)
        state["cut"] = "fresh"
        repeated = reader.inspect_selected_dossier(nullcontext, request)
        assert repeated["cut_id"] == "cut:fresh"
        assert first["members"] == repeated["members"]
        assert calls == ["membership"]
        state.update(cut="different-release", release="release:different")
        reader.inspect_selected_dossier(nullcontext, request)
        assert calls == ["membership", "membership"]
        state.update(cut="denied", permit=False)
        with pytest.raises(ValueError, match="revoked"):
            reader.inspect_selected_dossier(nullcontext, request)
        assert calls == ["membership", "membership"]
        assert (
            launches
            == verified
            == [
                "cut:first",
                "cut:fresh",
                "cut:different-release",
                "cut:denied",
            ]
        )
        monkeypatch.setattr(selected_query_cache, "ENTRY_ROWS", 1)
        monkeypatch.setattr(selected_query_cache, "bounded_rows", forbidden)
        state.update(cut="oversize", permit=True)
        oversize = reader.inspect_selected_dossier(
            nullcontext, request.model_copy(update={"limit": 1})
        )
        assert oversize["members"] == first["members"][:1]
        assert oversize["next_cursor"] is not None
        assert calls == ["membership", "membership", "membership"]
    finally:
        SELECTED_QUERY_CACHE.clear()


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


def test_artifact_journey_uses_public_source_and_projected_citation_without_contribution_copy():
    selected = opportunity()
    layer = SelectedJourneyLayer(layer="artifact", root=ROOT)
    record = dict(
        occurrence_id="occurrence:actual",
        contribution_id="artifact:actual",
        citations=[
            dict(
                source_ref=selected.source.identity,
                source_pointer=selected.pointer,
                start=17,
                end=25,
                text="term def",
            )
        ],
    )
    body = dict(
        inputs=dict(sources=[selected.source.model_dump(mode="json", exclude_none=True)]),
        artifact_identity=dict(records=[record], route_counts=[], pairs=[]),
    )
    matched, details = selected_journey_layer(layer, selected, body, ((17, 21),))
    assert matched and details["occurrences"] == [record]
    assert selected_journey_layer(layer, selected, body, ((26, 30),))[0] is False
    foreign = selected.source.model_copy(update={"kind_contract": "kind:foreign"})
    assert (
        selected_journey_layer(
            layer, selected.model_copy(update={"source": foreign}), body, ((17, 21),)
        )[0]
        is False
    )


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


def test_explicit_admission_binding_acquires_both_roots_and_refuses_unselected_report():
    from corpus_structure.serve.structural_products import (
        SelectedStructuralAdmissionBinding,
        SelectedStructuralRequest,
    )

    conclusion = ROOT.model_copy(
        update=dict(
            product_id="native:conclusion",
            use_id="use:conclusion",
            derivation_id="episode:conclusion",
        )
    )
    binding = SelectedStructuralAdmissionBinding(report=ROOT, admission=conclusion)
    request = SelectedStructuralRequest(
        demand_id="d", project_id="p", roots=(ROOT,), admissions=(binding,)
    )
    assert request.selection_roots == (ROOT, conclusion)
    for bindings in (
        (binding, binding),
        (SelectedStructuralAdmissionBinding(report=conclusion, admission=ROOT),),
    ):
        with pytest.raises(ValueError, match="explicit report roots"):
            SelectedStructuralRequest(
                demand_id="d", project_id="p", roots=(ROOT,), admissions=bindings
            )
