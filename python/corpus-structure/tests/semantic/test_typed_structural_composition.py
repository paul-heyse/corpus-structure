"""Independent exact numerical consequences and retained dossier selection expectations."""

from typing import Any

import pytest

from corpus_structure.methods.structural_products import (
    compare_clauses,
    read_clause,
    select_dossier,
)
from corpus_structure.semantic.structural_products import (
    DossierFacet,
    DossierMember,
    LocatedDefinitionSpan,
)
from corpus_structure.serve.structural_products import dossier_representation_page

from .test_structural_products import inputs


def threshold_inputs(left, right, scope="scope"):
    value = inputs()
    passages = tuple(
        p.model_copy(update=dict(text=t, start=0, end=len(t), scope=scope))
        for p, t in zip(value.passages, (left, right), strict=True)
    )
    return value.model_copy(update=dict(passages=passages))


@pytest.mark.parametrize(
    "left,right,removed,added",
    [
        ("revenue > 25000 USD", "revenue > 50000 USD", ("25000", "50000", False, True), None),
        ("revenue > 50000 USD", "revenue > 25000 USD", None, ("25000", "50000", False, True)),
        ("revenue >= 25000 USD", "revenue > 25000 USD", ("25000", "25000", True, True), None),
        ("revenue < 50000 USD", "revenue <= 25000 USD", ("25000", "50000", False, False), None),
    ],
)
def test_exact_threshold_difference(left, right, removed, added):
    value = threshold_inputs(left, right)
    report = compare_clauses(
        value, left=read_clause(value.passages[0]), right=read_clause(value.passages[1])
    )
    assert report.comparison is not None
    d = report.comparison.dimensions[5]

    def endpoint(v):
        return None if v is None else (v.lower, v.upper, v.lower_closed, v.upper_closed)

    assert endpoint(d.removed_interval) == removed
    assert endpoint(d.added_interval) == added
    assert d.typed_outcome == "different"
    assert report.comparison.applicability == "unestablished"


def test_missing_unit_and_ambiguous_fields_withhold_typed_conclusion():
    for left, right in (
        ("revenue > 25000", "revenue > 50000"),
        ("x > 2 kg and y > 3 kg", "x > 5 kg"),
    ):
        value = threshold_inputs(left, right)
        report = compare_clauses(
            value, left=read_clause(value.passages[0]), right=read_clause(value.passages[1])
        )
        assert report.comparison is not None
        assert report.comparison.dimensions[5].typed_outcome == "unknown"


def members():
    p = inputs().passages[0]
    span = LocatedDefinitionSpan(passage_id=p.passage_id, start=p.start, end=p.end, text=p.text)
    return tuple(
        DossierMember(
            member_id=str(i),
            passage_id=p.passage_id,
            citation=span,
            role="usage",
            sense="unresolved",
            scope=p.scope,
            relation_product_id="upstream",
        )
        for i in range(3)
    )


def test_supported_facets_gain_beats_source_order_without_discarding_members():
    rows = members()
    facets = tuple(
        DossierFacet(
            facet_id=str(i),
            kind="topic:" + str(i),
            scope="scope",
            member_id="2",
            assessment_id="actual-assessment",
            evidence=("a",),
        )
        for i in range(3)
    )
    greedy = select_dossier(
        inputs(), root_id="root", members=rows, supported_facets=facets, member_budget=1
    )
    control = select_dossier(
        inputs(),
        root_id="root",
        members=rows,
        supported_facets=facets,
        member_budget=1,
        policy="source-order-control-1",
    )
    assert greedy.dossier is not None and control.dossier is not None
    assert greedy.dossier.representatives == ("2",)
    assert control.dossier.representatives == ("0",)
    assert len(greedy.dossier.members) == 3
    assert len(greedy.dossier.representation.represented_facets) == 3
    assert not control.dossier.representation.represented_facets


def test_mandatory_overflow_pages_and_rejects_substituted_membership():
    rows = tuple(m.model_copy(update={"role": "exception"}) for m in members())
    report = select_dossier(inputs(), root_id="root", members=rows, member_budget=1)
    first = dossier_representation_page(report, limit=2)
    assert first["mandatory_overflow"] is True
    assert len(first["members"]) == 2
    second = dossier_representation_page(report, limit=2, continuation=first["continuation"])
    assert len(second["members"]) == 1 and second["continuation"] is None
    assert first["continuation"] is not None
    cursor = {**first["continuation"], "membership_digest": "different"}
    with pytest.raises(Exception, match="continuation differs"):
        dossier_representation_page(report, continuation=cursor)


def test_dossier_derives_only_actual_predecessor_roles_and_exact_protected_support():
    from corpus_structure.methods.structural_products import derive_dossier_members
    from corpus_structure.semantic.structural_admission import structural_statement
    from corpus_structure.semantic.structural_products import (
        DefinitionComponentsProduct,
        RetainedStructuralRef,
        StructuralProductReport,
        definition_component,
    )

    value = inputs()
    p = value.passages[0]
    span = LocatedDefinitionSpan(passage_id=p.passage_id, start=p.start, end=p.end, text=p.text)
    component = definition_component(
        term=span,
        content=span,
        interpretation="definition",
        basis="matched_cue",
        scope=p.scope,
        evidence=(p.passage_id,),
        reason="Explicit source cue.",
    )
    predecessor = StructuralProductReport(
        kind="definition_components",
        inputs=value,
        definition_components=DefinitionComponentsProduct(components=(component,), stages=()),
    )
    reference = RetainedStructuralRef(
        product_id=predecessor.product_id,
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="runtime",
    )
    closure = value.model_copy(
        update=dict(dependencies=(*value.dependencies, predecessor.product_id))
    )
    payload: dict[str, Any] = dict(report=predecessor.model_dump(mode="json"), public_assertions=())
    members, facets = derive_dossier_members(closure, ((reference, payload),))
    assert len(members) == 2 and {m.role for m in members} == {"definition", "terminology"}
    assert {m.passage_id for m in members} == {"a"}  # candidate passage b never participated
    assert not facets and all(m.qualification == "proposed" for m in members)
    payload["public_assertions"] = (
        dict(
            assessment_id="protected",
            statement=structural_statement(predecessor, component.component_id),
        ),
    )
    supported, facets = derive_dossier_members(closure, ((reference, payload),))
    assert len(facets) == 2 and all(m.assessment_id == "protected" for m in supported)
    payload["public_assertions"][0]["statement"]["scope"] = "other"
    unsupported, facets = derive_dossier_members(closure, ((reference, payload),))
    assert not facets and all(m.assessment_id is None for m in unsupported)
    with pytest.raises(ValueError, match="substituted"):
        derive_dossier_members(
            closure, ((reference.model_copy(update=dict(product_id="another")), payload),)
        )
