"""Retained source joins supply assessable private membership with full endpoint custody."""

import copy
import json
from pathlib import Path

import pytest
from methods.test_m1_source_preparation import native_table_source, table_cell
from methods.test_scoped_relations import complete_native_fields
from pydantic import ValidationError
from sqlalchemy import text

from corpus_structure.methods.dossier_contributions import derive_contribution_members
from corpus_structure.methods.scoped_relations import discover_relations
from corpus_structure.methods.structural_products import StructuralDossierConfig, select_dossier
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)


def source_fixture():
    frame = native_source_frame(
        complete_native_fields(
            native_table_source(
                (
                    table_cell("Probability %", 0, 1, column_header=True),
                    table_cell("50", 1, 1),
                )
            )
        ),
        (),
    )
    rows = discover_relations(frame)["contributions"]
    relation = next(
        r
        for r in rows
        if r["kind"] == "relation" and source_python(r["value"])["relation"] == "unit"
    )
    ids = set(relation["members"]) | {relation["contribution_id"]}
    closure = [r for r in rows if r["contribution_id"] in ids]
    pin = record_source_pin(frame)
    source = ExternalSourceRef(
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        source_view_id=pin["source_view_id"],
        native_task_id=pin["native_product_task_id"],
        native_product_key=pin["product_key"],
        native_content_digest=pin["product_digest"],
        projection_digest=pin["projection_digest"],
        recipe_digest=pin["recipe_digest"],
        coordinate_version=3,
    )
    inputs = StructuralInput(
        question="Structure corpus",
        scope="corpus",
        inventory_id="i",
        policy_id="p",
        sources=(source,),
        passages=(
            StructuralPassage(
                passage_id="table",
                source_ref=source.identity,
                start=0,
                end=len(frame.text),
                text=frame.text,
                scope="table",
            ),
        ),
        dependencies=(relation["contribution_id"],),
    )
    ref = RetainedContributionRef(
        contribution_id=relation["contribution_id"],
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="runtime",
    )
    native = json.loads(frame.native_context)
    payload = dict(
        contributions=closure,
        sources=[
            dict(
                source_view_id=frame.source_view_id,
                pin=pin,
                projection=dict(text=frame.text, pieces=native["pieces"]),
            )
        ],
    )
    return inputs, ref, payload


def test_source_join_enters_dossier_with_both_endpoint_citations_and_no_borrowed_support():
    inputs, ref, payload = source_fixture()
    payload["public_assertions"] = [
        dict(assessment_id="source-geometry-is-not-meaning", statement="quote")
    ]
    members = derive_contribution_members(inputs, ref, payload)
    assert len(members) == 1
    member = members[0]
    assert member.role == "relationship" and member.qualification == "proposed"
    assert member.assessment_id is None and member.scope.startswith(
        inputs.sources[0].identity + ":"
    )
    assert {c.span.text for c in member.contribution_citations} == {"50", "Probability %"}
    assert set(member.computation_dependencies) >= {
        r["contribution_id"] for r in payload["contributions"]
    }
    cfg = StructuralDossierConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        root_id="corpus",
        contribution_predecessors=(ref,),
    )
    report = select_dossier(
        inputs,
        root_id=cfg.root_id,
        members=members,
        contribution_predecessors=(ref,),
        member_budget=1,
    )
    assert len(report.dossier.members) == 1 and report.dossier.supported_facets == ()
    assert "definition" in report.dossier.missing_sections


@pytest.mark.parametrize("field", ["run_id", "origin_task_id", "selected_task_id"])
def test_reference_forbids_loose_identifiers(field):
    _, ref, _ = source_fixture()
    with pytest.raises(ValidationError):
        RetainedContributionRef.model_validate({**ref.model_dump(), field: "1"})
    with pytest.raises(ValidationError):
        RetainedContributionRef.model_validate({**ref.model_dump(), "supported": True})


@pytest.mark.parametrize("corruption", ["identity", "endpoint", "source", "citation", "passage"])
def test_source_membership_rejects_forged_closure(corruption):
    inputs, ref, payload = source_fixture()
    payload = copy.deepcopy(payload)
    if corruption == "identity":
        payload["contributions"][0]["disposition"] = "forged"
    elif corruption == "endpoint":
        payload["contributions"] = [
            r for r in payload["contributions"] if r["contribution_id"] == ref.contribution_id
        ]
    elif corruption == "source":
        inputs = inputs.model_copy(
            update=dict(
                sources=(inputs.sources[0].model_copy(update=dict(native_content_digest="d" * 64)),)
            )
        )
    elif corruption == "citation":
        payload["sources"][0]["projection"]["text"] = "!" * len(
            payload["sources"][0]["projection"]["text"]
        )
    else:
        inputs = inputs.model_copy(
            update=dict(
                passages=(
                    inputs.passages[0].model_copy(
                        update=dict(text="!" * len(inputs.passages[0].text))
                    ),
                )
            )
        )
    with pytest.raises(ValueError):
        derive_contribution_members(inputs, ref, payload)


def test_native_source_member_replay_preserves_all_endpoint_citations(semantic_db_engine):
    """Composition parity after owned-reader boundary; no claim of custody qualification."""
    inputs, ref, payload = source_fixture()
    expected = derive_contribution_members(inputs, ref, payload)[0]
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql"
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(
            (sql / "dossier_contributions.sql").read_text(),
            execution_options={"no_parameters": True},
        )
        # Real native resolver rejects nonexistent exact origin before a report can be supplied.
        with (
            pytest.raises(Exception, match="cannot resolve exact selected origin"),
            conn.begin_nested(),
        ):
            conn.scalar(
                text("SELECT ops.resolve_retained_source_contribution(CAST(:r AS jsonb))"),
                dict(r=ref.model_dump_json()),
            )
        conn.execute(
            text("SELECT set_config('test.source_contribution_payload',:p,true)"),
            dict(p=json.dumps(payload)),
        )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.resolve_retained_source_contribution(ref jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $$ "
            "SELECT current_setting('test.source_contribution_payload')::jsonb $$"
        )
        actual = conn.scalar(
            text("SELECT ops.dossier_contribution_member(CAST(:i AS jsonb),CAST(:r AS jsonb))"),
            dict(i=inputs.model_dump_json(), r=ref.model_dump_json()),
        )
        assert actual == expected.model_dump(mode="json", exclude_none=True)
        conn.exec_driver_sql(
            (sql / "structural_products.sql").read_text(), execution_options={"no_parameters": True}
        )
        cfg = StructuralDossierConfig(
            inputs=inputs,
            structural_input_digest=inputs.identity,
            root_id="corpus",
            contribution_predecessors=(ref,),
        )
        actual = conn.scalar(
            text("SELECT ops.structural_dossier(CAST(:i AS jsonb),CAST(:c AS jsonb))"),
            dict(i=inputs.model_dump_json(), c=cfg.model_dump_json()),
        )
        report = select_dossier(
            inputs, root_id="corpus", members=(expected,), contribution_predecessors=(ref,)
        )
        assert actual == report.dossier.model_dump(mode="json", exclude_none=True)
        from corpus_structure.semantic.structural_admission import structural_statement

        conn.exec_driver_sql(
            (sql / "structural_publication.sql").read_text(),
            execution_options={"no_parameters": True},
        )
        public = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:r AS jsonb),NULL)"),
            dict(r=report.model_dump_json(exclude_none=True)),
        )
        assert public == structural_statement(report)
        assert len(public["dossier"]["members"][0]["endpoint_citations"]) == 2
        assert public["dossier"]["admission_scope"] == "membership_assembly_not_member_truth"
        from corpus_structure.serve.structural_products import _DOSSIER_SLICE_SQL

        page_sql = _DOSSIER_SLICE_SQL.replace(
            "SELECT body->'structural_product' report FROM ops.task_result "
            "WHERE task_id=:origin_id",
            "SELECT CAST(:report AS jsonb) report",
        ).replace("{projection}", "body")
        page = conn.scalar(
            text(page_sql), dict(report=report.model_dump_json(), offset=0, end_offset=1)
        )
        assert len(page["citations"]) == 2
        assert {c["citation"]["text"] for c in page["citations"]} == {"50", "Probability %"}
