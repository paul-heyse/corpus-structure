"""Independent exact numerical consequences and retained dossier selection expectations."""

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
    cursor = {**first["continuation"], "membership_digest": "different"}
    with pytest.raises(Exception, match="continuation differs"):
        dossier_representation_page(report, continuation=cursor)
