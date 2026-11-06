"""Native deterministic replay checks, separate from source-custody qualification."""

import json
from pathlib import Path

import pytest
from sqlalchemy import text

from corpus_structure.methods.structural_products import compare_clauses, read_clause
from corpus_structure.semantic.structural_admission import structural_statement

from .test_typed_structural_composition import threshold_inputs


@pytest.mark.parametrize(
    "left,right",
    [
        ("revenue > 25000 USD", "revenue > 50000 USD"),
        ("revenue >= 25000 USD", "revenue > 25000 USD"),
        ("revenue < 50000 USD", "revenue <= 25000 USD"),
        ("x > 2", "x > 5"),
        ("x > 2 kg and y > 3 kg", "x > 5 kg"),
        ("prefix. x ≥ +2.00e2 kg", "x >= 200 kg"),
        ("x > 2. kg", "x > 2 kg"),
        (
            "Manager must approve Table 5.1 if revenue > 25000 USD unless account is closed.",
            "Manager must approve Table 5.1 if revenue > 50000 USD unless account is closed.",
        ),
        (
            "Table 5.1 must be approved by Manager if revenue > 25000 USD.",
            "Table 5.1 must be approved by Analyst if revenue > 25000 USD.",
        ),
        (
            "If revenue > 25000 USD, Manager must approve Table 5.1 before signing.",
            "Nothing is prescribed.",
        ),
        ("Manager must approve Table; Analyst may reject Form.", "Manager may review Table."),
    ],
)
def test_native_comparison_replays_same_source_route(semantic_db_engine, left, right):
    inputs = threshold_inputs(left, right)
    expected = compare_clauses(
        inputs, left=read_clause(inputs.passages[0]), right=read_clause(inputs.passages[1])
    )
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql"
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(
            (sql / "structural_products.sql").read_text(), execution_options={"no_parameters": True}
        )
        conn.exec_driver_sql(
            (sql / "structural_publication.sql").read_text(),
            execution_options={"no_parameters": True},
        )
        actual = conn.scalar(
            text("SELECT ops.structural_comparison(CAST(:inputs AS jsonb),:left,:right)"),
            dict(
                inputs=inputs.model_dump_json(),
                left=inputs.passages[0].passage_id,
                right=inputs.passages[1].passage_id,
            ),
        )
        comparison = expected.model_dump(mode="json", exclude_none=True)["comparison"]
        assert actual == comparison
        public = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:report AS jsonb),NULL)"),
            dict(report=expected.model_dump_json(exclude_none=True)),
        )
        assert public == structural_statement(expected)


def test_native_dossier_replays_membership_after_reader_boundary(semantic_db_engine):
    """Isolate composition after the reader; this is not reader/provider qualification."""
    from corpus_structure.methods.structural_products import derive_dossier_members, select_dossier
    from corpus_structure.semantic.structural_products import (
        DefinitionComponentsProduct,
        LocatedDefinitionSpan,
        RetainedStructuralRef,
        StructuralProductReport,
        definition_component,
    )

    inputs = threshold_inputs("term is defining content", "unrelated candidate context")
    p = inputs.passages[0]
    term = LocatedDefinitionSpan(passage_id=p.passage_id, start=0, end=4, text="term")
    content = LocatedDefinitionSpan(
        passage_id=p.passage_id, start=8, end=24, text="defining content"
    )
    component = definition_component(
        term=term,
        content=content,
        interpretation="definition",
        basis="matched_cue",
        scope=p.scope,
        evidence=(p.passage_id,),
        reason="Explicit source cue.",
    )
    predecessor = StructuralProductReport(
        kind="definition_components",
        inputs=inputs,
        definition_components=DefinitionComponentsProduct(components=(component,), stages=()),
    )
    ref = RetainedStructuralRef(
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
    inputs = inputs.model_copy(
        update=dict(dependencies=(*inputs.dependencies, predecessor.product_id))
    )
    payload = dict(
        report=predecessor.model_dump(mode="json", exclude_none=True),
        public_assertions=[
            dict(
                assessment_id="protected-reader-fixture",
                statement=structural_statement(predecessor, component.component_id),
            )
        ],
    )
    members, facets = derive_dossier_members(inputs, ((ref, payload),))
    report = select_dossier(
        inputs,
        root_id="root",
        members=members,
        supported_facets=facets,
        predecessors=(ref,),
        member_budget=1,
    )
    config = dict(
        root_id="root",
        predecessors=[ref.model_dump(mode="json")],
        member_budget=1,
        policy="supported-facet-greedy-1",
    )
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql"
    with semantic_db_engine.connect() as conn, conn.begin():
        for file in ("structural_products.sql", "structural_publication.sql"):
            conn.exec_driver_sql(
                (sql / file).read_text(), execution_options={"no_parameters": True}
            )
        conn.execute(
            text("SELECT set_config('test.structural_payload',:payload,true)"),
            dict(payload=json.dumps(payload)),
        )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.resolve_retained_structural_report(ref jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $$ "
            "SELECT current_setting('test.structural_payload')::jsonb $$"
        )
        actual = conn.scalar(
            text("SELECT ops.structural_dossier(CAST(:inputs AS jsonb),CAST(:config AS jsonb))"),
            dict(inputs=inputs.model_dump_json(exclude_none=True), config=json.dumps(config)),
        )
        assert report.dossier is not None
        assert actual == report.dossier.model_dump(mode="json", exclude_none=True)
        public = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:report AS jsonb),NULL)"),
            dict(report=report.model_dump_json(exclude_none=True)),
        )
        assert public == structural_statement(report)
        assert len(actual["members"]) == 2 and {m["passage_id"] for m in actual["members"]} == {"a"}


def test_native_representation_projects_only_selected_member_closure(semantic_db_engine):
    from corpus_structure.methods.structural_products import select_dossier
    from corpus_structure.semantic.structural_products import DossierMember, LocatedDefinitionSpan
    from corpus_structure.serve.structural_products import _DOSSIER_SLICE_SQL

    inputs = threshold_inputs("retained source", "uncited source")
    p = inputs.passages[0]
    citation = LocatedDefinitionSpan(passage_id=p.passage_id, start=p.start, end=p.end, text=p.text)
    members = tuple(
        DossierMember(
            member_id=str(i),
            passage_id=p.passage_id,
            citation=citation,
            role="exception",
            scope=p.scope,
            sense="unresolved",
            relation_product_id="upstream",
        )
        for i in range(3)
    )
    report = select_dossier(inputs, root_id="root", members=members, member_budget=1)
    sql = _DOSSIER_SLICE_SQL.replace(
        "SELECT body->'structural_product' report FROM ops.task_result WHERE task_id=:origin_id",
        "SELECT CAST(:report AS jsonb) report",
    ).replace("{projection}", "body")
    with semantic_db_engine.connect() as conn:
        result = conn.scalar(
            text(sql),
            dict(report=report.model_dump_json(exclude_none=True), offset=1, end_offset=2),
        )
    assert [m["member_id"] for m in result["members"]] == ["1"]
    assert (
        len(result["citations"]) == 1
        and result["citations"][0]["citation"]["text"] == "retained source"
    )
    assert result["citations"][0]["source"] == inputs.sources[0].model_dump(mode="json")
    assert result["supported_facets"] == []
