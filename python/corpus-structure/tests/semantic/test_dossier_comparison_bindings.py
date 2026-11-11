"""Exact side custody, directed roles and native composition parity."""

from pathlib import Path

import pytest
from sqlalchemy import text

from corpus_structure.methods.structural_products import compare_clauses, derive_dossier_members
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    ClauseField,
    ClauseFieldGroup,
    ClauseReading,
    DefinitionComponentsProduct,
    Dimension,
    DossierComparisonSelection,
    LocatedDefinitionSpan,
    RetainedComponentRef,
    RetainedStructuralRef,
    StructuralProductReport,
    definition_component,
)

from .test_structural_products import inputs


def side_inputs():
    value = inputs()
    left, right = (
        p.model_copy(
            update=dict(text=t, start=0, end=len(t), scope="rules", effective_version="R2")
        )
        for p, t in zip(
            value.passages,
            ("Apply measure except in test runs.", "Measure is a control rule."),
            strict=True,
        )
    )
    return value.model_copy(update=dict(passages=(left, right), scope="rules"))


def span(passage, literal):
    start = passage.start + passage.text.index(literal)
    return LocatedDefinitionSpan(
        passage_id=passage.passage_id, start=start, end=start + len(literal), text=literal
    )


def custody(source, task_id):
    return dict(
        project_id=source.project_id,
        run_id=source.run_id,
        cut_id=source.cut_id,
        release_id=source.release_id,
        result_revision=source.result_revision,
        selected_task_id=task_id,
        origin_task_id=task_id,
        runtime_fingerprint="runtime",
    )


def fixture(value=None, *, exception=True, root_on_left=False, primary_layers=None):
    value = value or side_inputs()
    left, right = value.passages
    sources = {s.identity: s for s in value.sources}
    left_source, right_source = sources[left.source_ref], sources[right.source_ref]
    root_passage = left if root_on_left else right
    root = definition_component(
        term=span(root_passage, "Measure"),
        content=span(root_passage, "control rule"),
        scope=root_passage.scope,
        effective_version=root_passage.effective_version,
        interpretation="definition",
        basis="matched_cue",
        evidence=(root_passage.passage_id,),
        reason="Located definition component fixture.",
    )
    definition = StructuralProductReport(
        kind="definition_components",
        inputs=value,
        definition_components=DefinitionComponentsProduct(components=(root,), stages=()),
    )
    root_ref = RetainedComponentRef(
        **custody(sources[root_passage.source_ref], 30),
        component_id=root.component_id,
        product_id=definition.product_id,
        dependencies=value.dependencies,
        operation_id="structure.definition_components",
        operation_version="8",
    )
    empty = {dimension: ClauseFieldGroup(state="absent") for dimension in DIMENSIONS}
    groups: dict[Dimension, ClauseFieldGroup] = empty
    if exception:
        field = ClauseField(
            dimension="exception",
            lexical_value="except in test runs",
            evidence=(left.passage_id,),
            spans=(span(left, "except in test runs"),),
            contribution_id="source-contribution:" + "a" * 64,
        )
        groups = {
            **empty,
            "exception": ClauseFieldGroup(state="present", grouping="singleton", members=(field,)),
        }
    comparison = compare_clauses(
        value,
        primary_layers=primary_layers,
        left=ClauseReading(passage_id=left.passage_id, groups=groups),
        right=ClauseReading(passage_id=right.passage_id, groups=empty),
        left_reading=dict(
            contribution_id="source-contribution:" + "b" * 64, **custody(left_source, 31)
        ),
        right_reading=dict(
            contribution_id="source-contribution:" + "c" * 64, **custody(right_source, 32)
        ),
    )
    reference = RetainedStructuralRef(product_id=comparison.product_id, **custody(left_source, 33))
    selected = []
    relationships = {}
    for side, passage, source, literal, relation in (
        ("left", left, left_source, "measure", "specializes"),
        ("right", right, right_source, "Measure", "denotes"),
    ):
        rel_ref = RetainedRelationshipDecisionRef(
            **custody(source, 34 if side == "left" else 35),
            operation_key="contextual-operation",
            decision_id="decision-" + side,
            edge_id="edge-" + side,
            occurrence_contribution_id="occurrence-" + side,
        )
        selected.append(
            DossierComparisonSelection(
                comparison_product_id=comparison.product_id, side=side, relationship_ref=rel_ref
            )
        )
        relationships[rel_ref] = dict(
            decision=dict(scope=passage.scope, effective_version=passage.effective_version),
            edge=dict(relation=relation, member_target_ids=(root.component_id,)),
            source_view_id=source.source_view_id,
            component_targets=[dict(reference=root_ref.model_dump(mode="json"))],
            located_occurrence=[span(passage, literal).model_dump(exclude={"passage_id"})],
        )
    value = value.model_copy(
        update=dict(
            dependencies=(
                *value.dependencies,
                comparison.product_id,
                *(s.relationship_ref.edge_id for s in selected),
            )
        )
    )
    payload = dict(
        report=comparison.model_dump(mode="json"),
        public_assertions=[
            dict(assessment_id="exact-comparison-grade", statement=structural_statement(comparison))
        ],
    )
    return value, root, root_ref, reference, payload, selected, relationships


def derive(value, root, root_ref, reference, payload, selected, relationships):
    return derive_dossier_members(
        value,
        ((reference, payload),),
        root=root,
        root_ref=root_ref,
        comparison_selections=selected,
        relationships=relationships,
    )


def binding(member):
    result = member.comparison_binding
    assert result is not None
    return result


def test_side_binding_keeps_opposite_context_and_requires_own_membership():
    value, root, root_ref, reference, payload, selected, relationships = fixture()
    members, facets = derive(value, root, root_ref, reference, payload, selected[:1], relationships)
    assert {(m.role, m.citation.text) for m in members} == {
        ("relationship", "Apply measure except in test runs."),
        ("exception", "except in test runs"),
    }
    assert {binding(m).side for m in members} == {"left"}
    assert {binding(m).opposite_citation.text for m in members} == {"Measure is a control rule."}
    assert {f.assessment_id for f in facets} == {"exact-comparison-grade"}
    assert [f.assessment_scope for f in facets] == ["comparison_statement"]
    assert {m.qualification for m in members} == {"proposed"}
    both, _ = derive(value, root, root_ref, reference, payload, selected, relationships)
    assert {(binding(m).side, m.role) for m in both} == {
        ("left", "relationship"),
        ("left", "exception"),
        ("right", "relationship"),
    }
    assert {m.member_id for m in members} < {m.member_id for m in both}


@pytest.mark.parametrize("failure", ["scope", "version", "target_custody", "source", "occurrence"])
def test_comparison_qualification_rejects_substitution(failure):
    value, root, root_ref, reference, payload, selected, relationships = fixture()
    relationship = relationships[selected[0].relationship_ref]
    match = "exact scoped root relationship"
    if failure == "scope":
        relationship["decision"]["scope"] = "other"
    elif failure == "version":
        relationship["decision"]["effective_version"] = "R1"
    elif failure == "target_custody":
        relationship["component_targets"][0]["reference"]["cut_id"] += 1
    elif failure == "source":
        relationship["source_view_id"] += 10
    else:
        relationship["located_occurrence"][0]["start"] += 1
        relationship["located_occurrence"][0]["end"] += 1
        match = "outside the exact comparison side"
    with pytest.raises(ValueError, match=match):
        derive(value, root, root_ref, reference, payload, selected[:1], relationships)


def test_comparison_root_witness_cannot_bind_another_focus_in_the_same_passage():
    from corpus_structure.methods.structural_products import _comparison_member_roles

    value, root, root_ref, reference, payload, selected, relationships = fixture()
    report = StructuralProductReport.model_validate(payload["report"])
    assert report.comparison is not None
    left = next(p for p in value.passages if p.passage_id == report.comparison.left_id)
    report = report.model_copy(
        update={
            "comparison": report.comparison.model_copy(update={"left_focus": span(left, "Apply")})
        }
    )
    with pytest.raises(ValueError, match="outside the exact comparison focus"):
        tuple(
            _comparison_member_roles(
                reference,
                report,
                selected[:1],
                relationships,
                root_ref,
                root,
                require_focus=True,
            )
        )


def test_comparison_conflict_requires_exact_applicability_and_both_authored_readings():
    from corpus_structure.methods.structural_products import _comparison_member_roles
    from corpus_structure.semantic.structural_products import (
        ApplicabilityPremise,
        DefinitionProduct,
        StructuralDefinitionReading,
    )

    value, root, root_ref, reference, payload, selected, relationships = fixture(exception=False)
    report = StructuralProductReport.model_validate(payload["report"])
    assert report.comparison is not None
    left, right = value.passages
    left_focus, right_focus = span(left, "Apply measure"), span(right, "Measure is a control rule")
    located_usage = span(left, "measure")
    usage = left.model_copy(
        update={
            "passage_id": "exact-usage",
            "start": located_usage.start,
            "end": located_usage.end,
            "text": located_usage.text,
        }
    )
    report = report.model_copy(
        update={
            "comparison": report.comparison.model_copy(
                update={
                    "left_focus": left_focus,
                    "right_focus": right_focus,
                    "applicability": "co_applicable",
                }
            )
        }
    )
    premise = StructuralProductReport(
        kind="definition_applicability",
        inputs=value.model_copy(
            update={
                "passages": (*value.passages, usage),
                "dependencies": tuple(
                    dict.fromkeys(
                        (
                            *value.dependencies,
                            root.component_id,
                            root_ref.product_id,
                            selected[0].relationship_ref.edge_id,
                        )
                    )
                ),
            }
        ),
        definition=DefinitionProduct(
            usage_id=usage.passage_id,
            candidate_list_id="candidate-list",
            eligible_targets=(root.component_id,),
            candidate_targets=(root.component_id,),
            readings=(
                StructuralDefinitionReading(
                    target_id=root.component_id,
                    component_ref=root_ref,
                    link_ref=selected[0].relationship_ref,
                    component=root,
                    outcome="applicable_definition",
                    evidence=(left.passage_id,),
                    premises=tuple(
                        ApplicabilityPremise(
                            dimension=dimension,
                            state="compatible",
                            evidence=(left.passage_id,),
                            reason="Exact scoped fixture.",
                        )
                        for dimension in (
                            "sense",
                            "scope",
                            "parent",
                            "parameterization",
                            "convention",
                            "version",
                        )
                    ),
                    reason="Source witnesses this exact relation.",
                ),
            ),
        ),
    )
    premise_ref = reference.model_copy(update={"product_id": premise.product_id})
    text = f'"{left_focus.text}" contradicts "{right_focus.text}".'
    proof = left.model_copy(
        update={
            "passage_id": "authored-contradiction",
            "start": 0,
            "end": len(text),
            "text": text,
        }
    )
    choice = selected[0].model_copy(
        update={
            "applicability_ref": premise_ref,
            "conflict_passage_id": proof.passage_id,
        }
    )

    def roles(witness):
        return tuple(
            _comparison_member_roles(
                reference,
                report,
                (choice,),
                relationships,
                root_ref,
                root,
                require_focus=True,
                applicability_reports={premise_ref: premise},
                dossier_passages={proof.passage_id: witness},
            )
        )

    conflict, relationship = roles(proof)
    assert conflict[0] == "conflict" and relationship[0] == "relationship"
    assert conflict[2].conflict_evidence is not None
    assert conflict[2].conflict_evidence.text == text
    with pytest.raises(ValueError, match="explicit contradiction"):
        roles(proof.model_copy(update={"text": text.replace("contradicts", "discusses")}))


def test_revision_requires_original_successor_and_direction():
    value = side_inputs()
    left, right = value.passages
    left_text = (
        "Apply measure. Measure is a control rule.\nClause rules.\n"
        "Revision R2 supersedes revision R1."
    )
    right_text = "Measure is a control rule.\nClause rules.\nRevision R1."
    right = right.model_copy(
        update=dict(
            text=right_text,
            source_ref=left.source_ref,
            start=len(left_text) + 1,
            end=len(left_text) + 1 + len(right_text),
            parent="rules",
            effective_version="R1",
        )
    )
    left = left.model_copy(update=dict(text=left_text, end=len(left_text), parent="rules"))
    value = value.model_copy(update=dict(passages=(left, right)))
    from .primary_formal_fixture import formal_layers

    primary = formal_layers(value)
    value, root, root_ref, reference, payload, selected, relationships = fixture(
        value, exception=False, root_on_left=True, primary_layers=primary
    )
    members, _ = derive(value, root, root_ref, reference, payload, selected[:1], relationships)
    assert [(m.role, m.citation.text) for m in members if m.role == "revision"] == [
        ("revision", "Revision R2 supersedes revision R1.")
    ]


def test_native_role_projection_matches_python_and_refuses_stale_target(semantic_db_engine):
    value, root, root_ref, reference, payload, selected, relationships = fixture()
    members, _ = derive(value, root, root_ref, reference, payload, selected[:1], relationships)
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/structural_products.sql"
    statement = text(
        "SELECT role FROM ops.dossier_comparison_roles(CAST(:ref AS jsonb),CAST(:report AS jsonb),"
        "CAST(:selection AS jsonb),CAST(:edge AS jsonb),CAST(:root_ref AS jsonb),"
        "CAST(:root AS jsonb)) role"
    )
    from json import dumps

    from sqlalchemy.exc import DBAPIError

    edge = relationships[selected[0].relationship_ref]
    arguments = dict(
        ref=reference.model_dump_json(),
        report=dumps(payload["report"]),
        selection=selected[0].model_dump_json(),
        edge=dumps(edge),
        root_ref=root_ref.model_dump_json(),
        root=root.model_dump_json(),
    )
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(sql.read_text(), execution_options={"no_parameters": True})
        actual = list(conn.scalars(statement, arguments))
        assert actual == [
            dict(
                role=m.role,
                span=m.citation.model_dump(mode="json"),
                comparison_binding=binding(m).model_dump(mode="json", exclude_none=True),
            )
            for m in members
        ]
        edge["component_targets"][0]["reference"]["cut_id"] += 1
        with pytest.raises(DBAPIError, match="exact scoped root relationship"), conn.begin_nested():
            conn.execute(statement, {**arguments, "edge": dumps(edge)})


def test_typed_source_dependency_keeps_both_endpoints_outside_computational_dependencies():
    from corpus_structure.methods.dossier_contributions import derive_contribution_members
    from corpus_structure.semantic.contributions import contribution_identity
    from corpus_structure.semantic.observations import source_python, source_value

    from .test_dossier_contributions import source_fixture

    value, ref, payload = source_fixture()
    (passage,) = value.passages
    passage = passage.model_copy(update={"effective_version": "R2"})
    initial = derive_contribution_members(value, ref, payload)[0]
    assert initial.contribution_citations is not None
    citations = {c.span.text: c.span for c in initial.contribution_citations}
    root = definition_component(
        term=citations["Probability %"],
        content=citations["50"],
        scope=passage.scope,
        effective_version="R2",
        interpretation="definition",
        basis="matched_cue",
        evidence=(passage.passage_id,),
        reason="Controlled endpoint fixture.",
    )
    attachment = next(c for c in payload["contributions"] if c["kind"] == "relation")
    meaning = source_python(attachment["value"])
    attachment["value"] = source_value({**meaning, "relation": "depends_on"})
    attachment["component"].update(
        attachment_kind="depends_on",
        scope=passage.scope,
        effective_version="R2",
    )
    attachment["contribution_id"] = contribution_identity(attachment)
    ref = ref.model_copy(update={"contribution_id": attachment["contribution_id"]})
    value = value.model_copy(
        update={"passages": (passage,), "dependencies": (ref.contribution_id,)}
    )
    (member,) = derive_contribution_members(value, ref, payload, root=root)
    dependency = member.semantic_dependency
    assert dependency is not None and dependency.relation == "depends_on"
    assert [c.span.text for c in dependency.dependent] == ["50"]
    assert [c.span.text for c in dependency.prerequisite] == ["Probability %"]
    assert member.computation_dependencies and "depends_on" not in member.computation_dependencies
