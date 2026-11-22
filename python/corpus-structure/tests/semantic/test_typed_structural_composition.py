"""Independent exact numerical consequences and retained dossier selection expectations."""

from typing import Any

import pytest

from corpus_structure.methods.structural_products import (
    _difference,
    _succession,
    _typed_member,
    select_dossier,
    threshold_readings,
)
from corpus_structure.methods.structural_products import (
    compare_clauses as compare_captured_clauses,
)
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    DeclaredClauseField,
    DeclaredClauseFieldGroup,
    DeclaredClauseReading,
    DeclaredDossierMember,
    DossierFacet,
    LocatedDefinitionSpan,
)
from corpus_structure.serve.structural_products import dossier_representation_page
from semantic.definition_component_members_support import unadmitted_component_members
from semantic.structural_formal_support import formal_reading_sets
from semantic.structural_products_support import inputs, root_references
from semantic.typed_structural_composition_support import (
    revision_inputs as revision_inputs,
)
from semantic.typed_structural_composition_support import (
    threshold_inputs as threshold_inputs,
)


def compare_clauses(value, **kwargs):
    return compare_captured_clauses(value, primary_readings=formal_reading_sets(value), **kwargs)


def read_clause(passage, *, source_inputs, **expected_roles):
    """Nominate exact fixture roles independently of the current retained-frame producer."""
    fields = []
    for name, spelling in expected_roles.items():
        dimension = next(dimension for dimension in DIMENSIONS if dimension == name)
        start = passage.start + passage.text.index(spelling)
        fields.append(
            DeclaredClauseField(
                dimension=dimension,
                lexical_value=spelling,
                evidence=(passage.passage_id,),
                span=LocatedDefinitionSpan(
                    passage_id=passage.passage_id,
                    start=start,
                    end=start + len(spelling),
                    text=spelling,
                ),
            )
        )
    for dimension, value in (("parent", passage.parent), ("version", passage.effective_version)):
        if value:
            fields.append(
                DeclaredClauseField(
                    dimension=dimension, lexical_value=value, evidence=(passage.passage_id,)
                )
            )
    source = next(
        source for source in source_inputs.sources if source.identity == passage.source_ref
    )
    thresholds = threshold_readings(
        passage, source=source, primary_layers=formal_reading_sets(source_inputs)[source.identity]
    )
    if len(thresholds) == 1:
        assert all(isinstance(field, DeclaredClauseField) for field in thresholds)
        fields.extend(field for field in thresholds if isinstance(field, DeclaredClauseField))
    return DeclaredClauseReading(passage_id=passage.passage_id, fields=tuple(fields))


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
    basis = "\nComparison basis: annual gross revenue."
    value = threshold_inputs(left + basis, right + basis)
    left_field = read_clause(value.passages[0], source_inputs=value).fields[0]
    right_field = read_clause(value.passages[1], source_inputs=value).fields[0]
    assert left_field.typed is not None and right_field.typed is not None
    removed_interval, added_interval, outcome = _difference(left_field.typed, right_field.typed)

    def endpoint(v):
        return None if v is None else (v.lower, v.upper, v.lower_closed, v.upper_closed)

    assert endpoint(removed_interval) == removed
    assert endpoint(added_interval) == added
    assert outcome == "different"
    assert left_field.typed.basis_evidence is not None
    assert left_field.typed.basis_evidence.text == basis[1:]
    assert (
        left_field.typed.primary_formal is not None and left_field.typed.primary_basis is not None
    )
    assert set(left_field.typed.primary_formal) == {"variant", "role", "occurrence", "member_id"}
    assert left_field.typed.primary_formal["role"] == "formal"


def test_missing_unit_and_ambiguous_fields_withhold_typed_conclusion():
    for left, right in (
        ("revenue > 25000 USD", "revenue > 50000 USD"),
        ("revenue > 25000", "revenue > 50000"),
        ("x > 2 kg and y > 3 kg", "x > 5 kg"),
    ):
        value = threshold_inputs(left, right)
        fields = read_clause(value.passages[0], source_inputs=value).fields
        assert len(fields) != 1 or _typed_member(fields[0]) is None


def test_succession_keeps_the_source_direction_when_comparison_is_reversed():
    inputs = revision_inputs(
        "Clause rule.\nRevision R1.\nx > 2 kg",
        "Clause rule.\nRevision R2 supersedes revision R1.\nx > 5 kg",
    )
    newer, older = inputs.passages
    result = _succession(
        newer,
        older,
        sources={source.identity: source for source in inputs.sources},
        primary_layers=None,
        primary_readings=formal_reading_sets(inputs),
    )
    assert result is not None
    assert (result.older_id, result.newer_id) == ("a", "b")
    assert result.evidence.text == "Revision R2 supersedes revision R1."
    assert result.older_evidence.text == "Revision R1."
    assert len(result.primary_witnesses) == 4


@pytest.mark.parametrize(
    "left,same_source",
    [
        ("x > 2 kg", True),
        ("Clause other.\nRevision R1.\nx > 2 kg", True),
        ("Clause rule.\nRevision R1.\nx > 2 kg", False),
    ],
)
def test_caller_labels_cannot_substitute_for_succession_endpoints(left, same_source):
    inputs = revision_inputs(
        left,
        "Clause rule.\nRevision R2 supersedes revision R1.\nx > 5 kg",
        same_source=same_source,
    )
    newer, older = inputs.passages
    assert (
        _succession(
            newer,
            older,
            sources={source.identity: source for source in inputs.sources},
            primary_layers=None,
            primary_readings=formal_reading_sets(inputs),
        )
        is None
    )


def members():
    p = inputs().passages[0]
    span = LocatedDefinitionSpan(passage_id=p.passage_id, start=p.start, end=p.end, text=p.text)
    return tuple(
        DeclaredDossierMember(
            member_id=str(i),
            passage_id=p.passage_id,
            citation=span,
            role="usage",
            sense="1" * 64,
            scope=p.scope,
            relation_product_id="upstream",
        )
        for i in range(3)
    )


def test_supported_facets_gain_beats_source_order_without_discarding_members():
    value = inputs()
    root, predecessor = root_references(value)
    rows = members()
    facets = tuple(
        DossierFacet(
            facet_id=str(i),
            kind="topic:" + str(i),
            scope="scope",
            member_id="2",
            assessment_id="fixture:assessment",
            evidence=("a",),
        )
        for i in range(3)
    )
    greedy = select_dossier(
        value,
        root_id=root.component_id,
        root_component=root,
        predecessors=(predecessor,),
        members=rows,
        supported_facets=facets,
        member_budget=1,
    )
    control = select_dossier(
        value,
        root_id=root.component_id,
        root_component=root,
        predecessors=(predecessor,),
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
    value = inputs()
    root, predecessor = root_references(value)
    report = select_dossier(
        value,
        root_id=root.component_id,
        root_component=root,
        predecessors=(predecessor,),
        members=rows,
        member_budget=1,
    )
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
        DeclaredDefinitionComponentsProduct,
        DeclaredDefinitionComponentsReport,
        DeclaredStructuralRef,
        declared_definition_component,
    )

    value = inputs()
    p = value.passages[0]
    span = LocatedDefinitionSpan(passage_id=p.passage_id, start=p.start, end=p.end, text=p.text)
    component = declared_definition_component(
        term=span,
        content=span,
        interpretation="definition",
        basis="matched_cue",
        scope=p.scope,
        evidence=(p.passage_id,),
        reason="Explicit source cue.",
    )
    predecessor = DeclaredDefinitionComponentsReport(
        kind="definition_components",
        inputs=value,
        members=unadmitted_component_members((component,)),
        definition_components=DeclaredDefinitionComponentsProduct(stages=()),
    )
    source = value.sources[0]
    reference = DeclaredStructuralRef(
        product_id="fixture:structural-definition",
        structural_id=predecessor.product_id,
        kind_contract="kind:fixture-definition",
        project_id=source.project_id,
        subject=source.subject,
        subject_definition=source.subject_definition,
        original_source=source.original_source,
        analyzed_scope_meaning=source.analyzed_scope_meaning,
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
            closure, ((reference.model_copy(update=dict(structural_id="another")), payload),)
        )


def test_independently_located_clause_premises_preserve_threshold_consequence():
    text = "Manager must approve Table 5.1 if revenue > 25000 USD unless account is closed."
    text += "\nComparison basis: annual gross revenue."
    value = threshold_inputs(text, text.replace("25000", "50000"))
    roles = {
        "actor": "Manager",
        "action": "approve",
        "object": "Table 5.1",
        "modality": "must",
        "exception": "unless account is closed",
    }
    left = read_clause(
        value.passages[0], source_inputs=value, **roles, condition="if revenue > 25000 USD"
    )
    right = read_clause(
        value.passages[1], source_inputs=value, **roles, condition="if revenue > 50000 USD"
    )
    left_field = next(field for field in left.fields if field.dimension == "threshold_unit")
    right_field = next(field for field in right.fields if field.dimension == "threshold_unit")
    assert left_field.typed is not None and right_field.typed is not None
    removed, added, outcome = _difference(left_field.typed, right_field.typed)
    assert removed is not None and removed.upper == "50000" and added is None
    assert outcome == "different"
    assert left_field.typed.span.text == "revenue > 25000 USD"


def test_grouped_typed_alignment_does_not_derive_interval_from_unresolved_applicability():
    from corpus_structure.methods.structural_products import _literal_reading
    from corpus_structure.semantic.formal_readings import coordination_reading

    value = threshold_inputs(
        "Identifier: Form-A and Date: 2025-01-15. X > 5 kg.\nComparison basis: gross weight.",
        "Identifier: Form-B or Date: 2025-01-16. X > 7 kg.\nComparison basis: gross weight.",
    )
    value = value.model_copy(
        update={
            "passages": tuple(
                passage.model_copy(update={"effective_version": "R1"}) for passage in value.passages
            )
        }
    )
    layers = formal_reading_sets(value)

    def side(passage, form, date, connector, state):
        def span(spelling, start=None):
            start = passage.text.index(spelling) if start is None else start
            return LocatedDefinitionSpan(
                passage_id=passage.passage_id, start=start, end=start + len(spelling), text=spelling
            )

        source = next(s for s in value.sources if s.identity == passage.source_ref)
        primary = layers[source.identity]
        members = []
        for spelling in (f"Identifier: {form}", f"Date: {date}"):
            located = span(spelling)
            literal, reference = _literal_reading(located, source, primary)
            assert literal is not None and reference is not None
            members.append(
                DeclaredClauseField(
                    dimension="object",
                    lexical_value=spelling,
                    evidence=(passage.passage_id,),
                    spans=(located,),
                    literal=literal,
                    primary_formal=reference,
                )
            )
        cue = coordination_reading(
            primary,
            primary.source,
            start=len(f"Identifier: {form}"),
            end=passage.text.index("Date:"),
        )
        assert cue is not None and cue.value == connector
        # An unresolved actor can coexist with an otherwise exact threshold.
        threshold = next(
            x
            for x in threshold_readings(
                passage,
                source=next(
                    source for source in value.sources if source.identity == passage.source_ref
                ),
                primary_layers=layers[source.identity],
            )
            if x.dimension == "threshold_unit"
        )
        groups = {d: DeclaredClauseFieldGroup(state="absent") for d in DIMENSIONS}
        groups["actor"] = DeclaredClauseFieldGroup(state=state)
        groups["object"] = DeclaredClauseFieldGroup(
            state="present",
            grouping="conjunction" if connector == "and" else "disjunction",
            members=tuple(members),
            witnesses=(span(connector, passage.text.index(f" {connector} ") + 1),),
            primary_witnesses=(primary.member_target(cue.reference),),
        )
        groups["threshold_unit"] = DeclaredClauseFieldGroup(
            state="present", grouping="singleton", members=(threshold,)
        )
        return DeclaredClauseReading(passage_id=passage.passage_id, groups=groups)

    def ref(passage, digit):
        source = next(item for item in value.sources if item.identity == passage.source_ref)
        return dict(
            contribution_id="source-contribution:" + digit * 64,
            product_id="fixture:reading:" + digit,
            kind_contract="kind:fixture-reading",
            project_id=source.project_id,
            subject=source.subject,
            subject_definition=source.subject_definition,
            original_source=source.original_source,
            analyzed_scope_meaning=source.analyzed_scope_meaning,
        )

    left, right = value.passages
    report = compare_clauses(
        value,
        left=side(left, "Form-A", "2025-01-15", "and", "unresolved"),
        right=side(right, "Form-B", "2025-01-16", "or", "absent"),
        left_reading=ref(left, "a"),
        right_reading=ref(right, "b"),
        typed_groups=True,
    )
    assert report.comparison is not None
    released = report.model_dump(mode="json")
    object_ = next(d for d in released["comparison"]["dimensions"] if d["dimension"] == "object")
    for side in ("left_group", "right_group"):
        assert object_[side]["primary_witnesses"]
        assert all(member["primary_formal"] for member in object_[side]["members"])
    dimensions = {d.dimension: d for d in report.comparison.dimensions}
    assert dimensions["object"].grouping_outcome == "different"
    assert [
        (d.left_index, d.right_index, d.outcome)
        for d in dimensions["object"].member_comparisons or ()
    ] == [(0, 0, "different"), (1, 1, "different")]
    assert dimensions["threshold_unit"].removed_interval is None
    assert dimensions["threshold_unit"].added_interval is None
