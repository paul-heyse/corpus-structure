"""Dossier sections, identities and facet credit preserve original reading states."""

import json
from pathlib import Path

import pytest
from sqlalchemy import text

from corpus_structure.methods.structural_products import derive_dossier_members, select_dossier
from corpus_structure.semantic.structural_admission import structural_claim_id, structural_statement
from corpus_structure.semantic.structural_products import (
    DefinitionComponentsProduct,
    LocatedDefinitionSpan,
    RetainedComponentRef,
    RetainedStructuralRef,
    StructuralProductReport,
    definition_component,
)
from semantic.dossier_semantic_states_support import applicability as applicability
from semantic.structural_products_support import inputs


def components():
    value = inputs()
    p = value.passages[0]
    span = LocatedDefinitionSpan(passage_id=p.passage_id, start=p.start, end=p.end, text=p.text)
    return StructuralProductReport(
        kind="definition_components",
        inputs=value,
        definition_components=DefinitionComponentsProduct(
            components=tuple(
                definition_component(
                    term=span,
                    content=span,
                    interpretation=state,
                    basis="matched_cue",
                    scope=p.scope,
                    evidence=(p.passage_id,),
                    reason="Same literal source, distinct original interpretations.",
                )
                for state in ("definition", "explanation", "unresolved")
            ),
            stages=(),
        ),
    )


def retained(report):
    reference = RetainedStructuralRef(
        product_id=report.product_id,
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="runtime",
    )
    value = report.inputs.model_copy(
        update=dict(dependencies=(*report.inputs.dependencies, report.product_id))
    )
    statements = (
        [
            structural_statement(report, c.component_id)
            for c in report.definition_components.components
            if c.interpretation != "unresolved"
        ]
        if report.definition_components
        else [structural_statement(report)]
    )
    payload = dict(
        report=report.model_dump(mode="json", exclude_none=True),
        public_assertions=[
            dict(assessment_id="protected-" + str(i), statement=statement)
            for i, statement in enumerate(statements)
        ],
    )
    return value, reference, payload


def test_component_interpretations_share_citation_without_collapsing_or_false_definition_credit():
    value, reference, payload = retained(components())
    members, facets = derive_dossier_members(value, ((reference, payload),))
    assert len(members) == 6 and len({m.member_id for m in members}) == 6
    assert {(m.role, m.definition_interpretation) for m in members} == {
        ("terminology", "definition"),
        ("definition", "definition"),
        ("terminology", "explanation"),
        ("usage", "explanation"),
        ("terminology", "unresolved"),
        ("unresolved_sense", "unresolved"),
    }
    assert all(
        m.qualification == "proposed"
        for m in members
        if m.definition_interpretation == "unresolved"
    )
    assert {f.kind for f in facets} == {
        "terminology:definition:hello",
        "definition:definition:hello",
        "terminology:explanation:hello",
        "usage:explanation:hello",
    }
    assert not any(
        f.kind.startswith("definition:") and f.definition_interpretation != "definition"
        for f in facets
    )
    public = structural_statement(
        select_dossier(
            value,
            root_id="corpus",
            members=members,
            supported_facets=facets,
            predecessors=(reference,),
        )
    )
    assert {m["definition_interpretation"] for m in public["dossier"]["members"]} == {
        "definition",
        "explanation",
        "unresolved",
    }


def test_same_report_same_content_preserves_every_applicability_outcome_and_facet():
    value, reference, payload = retained(applicability())
    members, facets = derive_dossier_members(value, ((reference, payload),))
    states = {m.applicability_outcome: m for m in members if m.applicability_outcome is not None}
    assert {state: m.role for state, m in states.items()} == {
        "applicable_definition": "definition",
        "applicable_explanation": "usage",
        "mention": "usage",
        "example": "usage",
        "incompatible": "relationship",
        "unresolved": "unresolved_sense",
    }
    assert len({m.member_id for m in states.values()}) == 6
    assert states["applicable_explanation"].definition_interpretation == "explanation"
    assert {f.applicability_outcome for f in facets if f.applicability_outcome} == set(states)
    assert {f.applicability_outcome for f in facets if f.kind.startswith("definition:")} == {
        "applicable_definition"
    }
    claims = set()
    for member in states.values():
        report = select_dossier(
            value, root_id="corpus", members=(member,), predecessors=(reference,)
        )
        public = structural_statement(report)
        assert (
            public["dossier"]["members"][0]["applicability_outcome"] == member.applicability_outcome
        )
        claims.add(structural_claim_id(public))
    assert len(claims) == 6


@pytest.mark.parametrize("predecessor", [components, applicability])
def test_native_dossier_and_public_projection_preserve_literal_semantic_states(
    commit_db_engine, predecessor
):
    """Native replay after authenticated reader boundary; no producer-custody claim."""
    upstream = predecessor()
    value, reference, payload = retained(upstream)
    if upstream.definition_components is not None:
        roots = upstream.definition_components.components
    else:
        assert upstream.definition is not None
        roots = tuple(
            {r.component.component_id: r.component for r in upstream.definition.readings}.values()
        )
    roles, outcomes = set(), set()
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql"
    with commit_db_engine.connect() as conn, conn.begin():
        for name in (
            "dossier_contributions.sql",
            "structural_products.sql",
            "structural_publication.sql",
        ):
            conn.exec_driver_sql(
                (sql / name).read_text(), execution_options={"no_parameters": True}
            )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.resolve_retained_structural_report(ref jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $$ "
            "SELECT current_setting('test.dossier_state_payload')::jsonb->(ref->>'product_id') $$"
        )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.resolve_retained_component(ref jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $$ "
            "SELECT jsonb_build_object('component',current_setting('test.dossier_root')::jsonb) $$"
        )
        for component in roots:
            bound_inputs, refs = value, ((reference, payload),)
            root_report, root_ref = upstream, reference
            if upstream.definition is not None:
                root_report = StructuralProductReport(
                    kind="definition_components",
                    inputs=upstream.inputs,
                    definition_components=DefinitionComponentsProduct(
                        components=(component,), stages=()
                    ),
                )
                _, root_ref, root_payload = retained(root_report)
                refs = (*refs, (root_ref, root_payload))
                bound_inputs = value.model_copy(
                    update={"dependencies": (*value.dependencies, root_report.product_id)}
                )
            root = RetainedComponentRef(
                **root_ref.model_dump(),
                operation_id="structure.definition_components",
                operation_version="5",
                component_id=component.component_id,
                dependencies=root_report.inputs.dependencies,
            )
            predecessors = tuple(ref for ref, _ in refs)
            members, facets = derive_dossier_members(bound_inputs, refs, root=component)
            report = select_dossier(
                bound_inputs,
                root_id=root.component_id,
                root_component=root,
                members=members,
                supported_facets=facets,
                predecessors=predecessors,
            )
            config = dict(
                root_component=root.model_dump(mode="json"),
                predecessors=[r.model_dump(mode="json") for r in predecessors],
                contribution_predecessors=[],
                member_budget=12,
                policy="supported-facet-greedy-1",
            )
            conn.execute(
                text("SELECT set_config('test.dossier_state_payload',:payload,true)"),
                dict(payload=json.dumps({r.product_id: row for r, row in refs})),
            )
            conn.execute(
                text("SELECT set_config('test.dossier_root',:component,true)"),
                dict(component=component.model_dump_json(exclude_none=True)),
            )
            actual = conn.scalar(
                text("SELECT ops.structural_dossier(CAST(:i AS jsonb),CAST(:c AS jsonb))"),
                dict(i=bound_inputs.model_dump_json(exclude_none=True), c=json.dumps(config)),
            )
            assert report.dossier is not None
            assert actual == report.dossier.model_dump(mode="json", exclude_none=True)
            assert all(member["sense"] == root.component_id for member in actual["members"])
            public = conn.scalar(
                text("SELECT data.structural_public_statement(CAST(:r AS jsonb),NULL)"),
                dict(r=report.model_dump_json(exclude_none=True)),
            )
            assert public == structural_statement(report)
            from corpus_structure.serve.structural_products import _DOSSIER_SLICE_SQL

            page_sql = _DOSSIER_SLICE_SQL.replace(
                "SELECT body->'structural_product' report FROM ops.task_result "
                "WHERE task_id=:origin_id",
                "SELECT CAST(:report AS jsonb) report",
            ).replace("{projection}", "body")
            page = conn.scalar(
                text(page_sql),
                dict(report=report.model_dump_json(exclude_none=True), offset=0, end_offset=12),
            )
            roles.update((m.get("definition_interpretation"), m["role"]) for m in page["members"])
            outcomes.update(
                m["applicability_outcome"]
                for m in page["members"]
                if m.get("applicability_outcome")
            )
    assert {("definition", "definition"), ("explanation", "usage")} <= roles
    if predecessor is applicability:
        assert outcomes == {
            "applicable_definition",
            "applicable_explanation",
            "mention",
            "example",
            "incompatible",
            "unresolved",
        }
