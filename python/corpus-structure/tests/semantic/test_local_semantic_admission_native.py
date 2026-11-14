"""Protected adjudication and common publication machinery, not quality evidence."""

import json
from dataclasses import asdict, replace
from typing import Any

import psycopg
import pytest
from native_refusals import native_refusal
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.operation_assessment import record_pass
from corpus_structure.semantic.domain_operations import _cut_input, consolidate_cut
from corpus_structure.semantic.local_semantic_admission import semantic_assertion_identity
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from semantic.local_admission_scenarios import JudgedSourceRecipe
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.native_record_fixtures import private_source as private_source


@pytest.fixture
def judged_source(request, scenario_seeds):
    recipe = JudgedSourceRecipe(**getattr(request, "param", {}))
    with scenario_seeds.commit_clone(recipe) as clone:
        yield clone.stage.bind(clone.writer, clone=clone)


@pytest.fixture
def judged_semantic_case(scenario_seeds):
    with scenario_seeds.rollback_family(
        JudgedSourceRecipe(cases=2, grades=2), reader_purpose="write"
    ) as family:
        with family.reader.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT current_user,session_user,current_setting('transaction_read_only')"
            ).one() == (family.reader.url.username, family.reader.url.username, "on")
        yield family.stage.bind(family.reader), family


@pytest.mark.parametrize(
    "judged_source",
    [{"judgment": "ambiguous"}, {"judgment": "unassessed"}, {"partial": True}],
    indirect=True,
)
def test_nonqualifying_case_preserves_private_outputs(judged_source):
    case, run, cut = judged_source
    consolidate_cut(case.writer, cut, "nonqualifying-denotation")
    with read_snapshot(case.writer) as conn:
        page = serve_contributions(conn, ContributionRequest(run_id=run, include_publication=True))
        assert page.inventory_counts["admitted_semantic_claims"] == 0
        assert page.inventory_counts["contributions"] > 0


def test_common_v3_facets_select_exact_products_and_public_assessment_only(judged_source):
    case, run, cut = judged_source
    consolidate_cut(case.writer, cut, "v3-public-assessment")
    with read_snapshot(case.writer) as conn:
        page = serve_contributions(
            conn,
            ContributionRequest(
                run_id=run,
                include_interpretation=True,
                include_assessment=True,
                operation_version="2",
            ),
        )
        assert page.version == "contribution-inspection-3" and page.publication == "not_included"
        assessments = [
            item["row"]
            for item in page.model_dump(mode="json")["items"]
            if item["population"] == "assessment"
        ]
        supported = [row for row in assessments if row["outcome"] == "supported"]
        assert len(supported) == 1
        assert any(row["outcome"] == "no_public_assessment" for row in assessments)
        assert set(supported[0]["witnesses"][0]) >= {
            "evaluation_id",
            "unit_id",
            "pass_id",
            "frame_id",
            "case_id",
            "rubric_version",
            "context_policy",
        }
        assert "authored" not in str(supported) and "reference_snapshot" not in str(supported)
        cid = supported[0]["contribution_id"]
        selected = serve_contributions(
            conn,
            ContributionRequest(
                run_id=run,
                contribution_id=cid,
                include_assessment=True,
                include_interpretation=True,
            ),
        )
        assert selected.inventory_counts["contributions"] == 1
        assert selected.inventory_counts["assessments"] == 1
        assert (
            selected.inventory_counts["operations"] > 1
        )  # Independent zero-output inventory survives.
        missing = serve_contributions(
            conn,
            ContributionRequest(run_id=run, contribution_id="foreign", include_assessment=True),
        )
        assert (
            missing.inventory_counts["contributions"]
            == missing.inventory_counts["assessments"]
            == 0
        )
        no_version = serve_contributions(
            conn, ContributionRequest(run_id=run, operation_version="absent")
        )
        assert (
            no_version.inventory_counts["operations"]
            == no_version.inventory_counts["contributions"]
            == 0
        )
        contribution = next(
            item["row"]
            for item in selected.model_dump(mode="json")["items"]
            if item["population"] == "contribution"
        )
        physical = serve_contributions(
            conn, ContributionRequest(run_id=run, occurrence_id=contribution["occurrence_id"])
        )
        assert all(
            item["row"]["occurrence_id"] == contribution["occurrence_id"]
            for item in physical.model_dump(mode="json")["items"]
            if item["population"] == "contribution"
        )


def test_superseding_adjudication_makes_prior_grade_inapplicable(judged_source):
    case, _, cut = judged_source
    unit, frame, payload = case.semantic_reference
    with case.clone.evaluator.begin() as conn:
        record_pass(
            conn,
            unit_id=unit,
            pass_kind="C",
            actor="new-denotation-C",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
    with pytest.raises(DBAPIError, match="stale"):
        _cut_input(case.writer, cut, "stale-denotation-publication")


def test_writer_cannot_read_raw_adjudication_helper(judged_source):
    case, _, _ = judged_source
    evaluation_id, digest = case.semantic_grade
    with pytest.raises(DBAPIError, match="permission denied"), case.writer.begin() as conn:
        conn.execute(
            text("SELECT data.local_semantic_grade_evidence(:p,:r,:e,:d)"),
            dict(p="private-records", r=case.prepared.release_id, e=evaluation_id, d=digest),
        )


@pytest.mark.parametrize(
    "judged_source",
    [{"partition": "final_event_calibration"}, {"partition": "final_assessment"}],
    indirect=True,
)
def test_writer_cannot_obtain_heldout_admission_contents(judged_source):
    case, _, cut = judged_source
    with pytest.raises(DBAPIError, match="only development-use"):
        _cut_input(case.writer, cut, "heldout-denotation-publication")


@pytest.mark.parametrize(
    "judged_source", [{"partition": "development"}, {"partition": "feature_fit"}], indirect=True
)
def test_independent_denotation_uses_common_publication(judged_source):
    case, run, cut = judged_source
    result = consolidate_cut(case.writer, cut, "judged-publication")
    assert consolidate_cut(case.writer, cut, "judged-publication") == result
    with read_snapshot(case.writer) as conn:
        page = serve_contributions(
            conn, ContributionRequest(run_id=run, include_publication=True, include_support=True)
        )
        assert page.inventory_counts["admitted_semantic_claims"] == 1
        semantic = [
            item["row"] for item in page.items if item["population"] == "local_semantic_assertion"
        ]
        assert len(semantic) == 1
        assert isinstance(semantic[0], dict)
        assert isinstance(semantic[0]["statement"], dict)
        assert semantic[0]["assessment"] == "independently_adjudicated_exact_case"
        target = semantic[0]["statement"]["target"]
        assert isinstance(target, dict)
        term = target["term"]
        assert isinstance(term, dict)
        assert term["text"] == "12"
        assert semantic[0]["canonical_identity"] == "not_established"


@pytest.mark.parametrize(
    "corruption",
    ["statement", "grade", "case", "rubric", "source", "unit", "pass", "frame", "cut", "selected"],
)
def test_native_rejects_forged_judged_semantic_rows(judged_semantic_case, corruption):
    from corpus_structure.semantic.analytics import compile_projection
    from corpus_structure.semantic.arrow_publication import AppendPublication, stage_arrow

    (case, _, cut), family = judged_semantic_case
    inputs = _cut_input(case.writer, cut, "semantic-forged")
    clean = replace(inputs.batch, _analysis_input=None)
    assert len(clean.local_semantic_assertion) == 2
    first = clean.local_semantic_assertion[0]
    change: dict[str, Any] = {
        "statement": dict(statement_json='{"target_id":"forged"}'),
        "grade": dict(evaluation_digest="0" * 64),
        "case": dict(case_id="foreign-case"),
        "rubric": dict(rubric_version="arbitrary-rubric"),
        "source": dict(origin_task_id=case.source_task),
        "unit": dict(unit_id=first.unit_id + 1000000),
        "pass": dict(pass_id=first.pass_id + 1000000),
        "frame": dict(frame_id=first.frame_id + 1000000),
        "cut": dict(cut_id=first.cut_id + 1000000),
        "selected": dict(selected_task_id=case.source_task),
    }[corruption]
    changed = replace(first, **change)
    changed = replace(
        changed,
        assertion_id=semantic_assertion_identity(
            {key: value for key, value in asdict(changed).items() if key != "assertion_id"}
        ),
    )
    batch = replace(clean, local_semantic_assertion=(changed, *clean.local_semantic_assertion[1:]))
    projection = compile_projection(inputs.prepared, inputs.source_binding, kind="candidate")
    with family.principal("write", isolation_level="SERIALIZABLE") as conn:
        if corruption == "unit":
            # Deterministically exercise the cached-plan path across successful
            # publication rollback and recreated temporary staging row types.
            conn.execute(text("SET LOCAL plan_cache_mode='force_generic_plan'"))
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"),
            dict(cut=cut, out=inputs.output_realization_id),
        )

        # The unchanged sibling is accepted by this same publication operation. Its
        # savepoint is rolled back so the forgery still starts from an empty workspace.
        def publish(candidate):
            transport = AppendPublication.from_rows(candidate)
            stage_arrow(conn, transport)
            conn.execute(
                text(
                    "SELECT data.publish_derived_batch_v2(:r,:z,:b,:content,:sr,:sz,:revision,"
                    ":capture,'evaluate',:projection,'candidate',:cut,:profile)"
                ),
                dict(
                    r=candidate.release_id,
                    z=candidate.realization_id,
                    b=candidate.batch_id,
                    content=transport.content,
                    sr=inputs.source_binding.release_id,
                    sz=inputs.source_binding.realization_id,
                    revision=inputs.source_binding.data_revision,
                    capture=inputs.source_binding.capture_id,
                    projection=projection.projection_id,
                    cut=cut,
                    profile=projection.profile.digest,
                ),
            )

        with conn.begin_nested() as accepted:
            publish(clean)
            assert (
                conn.scalar(
                    text(
                        "SELECT count(*) FROM data.local_semantic_assertion WHERE realization_id=:z"
                    ),
                    dict(z=clean.realization_id),
                )
                == 2
            )
            accepted.rollback()
        unique_witness = (
            "semantic publication requires unique exact source, grade unit, "
            "case and operation witnesses"
        )
        applicability = (
            "semantic publication lacks exact independently judged "
            "statement/source/operation applicability"
        )
        expected = {
            "statement": (
                "23514",
                "semantic assertion differs from protected grade and exact source witness",
            ),
            "grade": ("23514", "semantic grade is outside immutable publication dependencies"),
            "case": ("23514", unique_witness),
            "rubric": ("23514", applicability),
            "source": ("23503", "fk_local_semantic_assertion_origin_task_id_contribution_id"),
            "unit": ("23514", unique_witness),
            "pass": ("23514", unique_witness),
            "frame": ("23514", unique_witness),
            "cut": ("23503", "fk_local_semantic_assertion_cut_id"),
            "selected": ("P0002", "query returned no rows"),
        }[corruption]
        with (
            native_refusal(
                expected[0],
                constraint=expected[1] if corruption in {"source", "cut"} else None,
                message=None if corruption in {"source", "cut"} else expected[1],
                context="validate_local_semantic_assertions" if corruption == "selected" else None,
            ),
            conn.begin_nested(),
        ):
            publish(batch)
        if corruption == "unit":
            for _ in range(8):
                with conn.begin_nested() as replay:
                    publish(clean)
                    replay.rollback()
                with native_refusal("23514", message=unique_witness), conn.begin_nested():
                    publish(batch)
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.batch WHERE realization_id=:z"),
                dict(z=clean.realization_id),
            )
            == 0
        )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.local_semantic_assertion WHERE realization_id=:z"),
                dict(z=clean.realization_id),
            )
            == 0
        )
    with case.writer.connect() as conn:
        assert (
            conn.scalar(
                select(table("data.local_semantic_assertion").c.assertion_id).where(
                    table("data.local_semantic_assertion").c.realization_id == "semantic-forged"
                )
            )
            is None
        )


@pytest.mark.parametrize("judged_source", [{"cases": 2, "grades": 2}], indirect=True)
def test_batch_keeps_grade_witnesses_and_excludes_uncaptured_case(judged_source):
    case, run, cut = judged_source
    inputs = _cut_input(case.writer, cut, "semantic-batch-witnesses")
    assertions = inputs.batch.local_semantic_assertion
    # One source prediction captures one of the two independent cases. Both
    # grades retain that witness; the uncaptured case cannot acquire authority.
    assert len(assertions) == 2
    assert {(row.evaluation_id, row.case_id) for row in assertions} == {
        (identity, f"numeral12-denotation-{index}")
        for identity, _ in case.semantic_grades
        for index in range(1)
    }
    consolidate_cut(case.writer, cut, "semantic-batch-witnesses")
    with read_snapshot(case.writer) as conn:
        retained = conn.execute(
            select(
                table("data.local_semantic_assertion").c.evaluation_id,
                table("data.local_semantic_assertion").c.case_id,
            ).where(
                table("data.local_semantic_assertion").c.realization_id
                == "semantic-batch-witnesses"
            )
        ).all()
        assert set(retained) == {(row.evaluation_id, row.case_id) for row in assertions}
        page = serve_contributions(conn, ContributionRequest(run_id=run, include_publication=True))
        assert page.inventory_counts["admitted_semantic_claims"] == 1
        assert page.inventory_counts["local_semantic_assertion_witnesses"] == 2


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
def test_writer_cannot_prepare_consolidation_by_direct_run_status_update(private_source):
    case = private_source
    with case.writer.begin() as conn:
        before = conn.scalar(
            select(table("ops.run").c.status).where(table("ops.run").c.id == case.run)
        )
        with pytest.raises(DBAPIError) as caught, conn.begin_nested():
            conn.execute(
                text("UPDATE ops.run SET status='consolidating' WHERE id=:run"), dict(run=case.run)
            )
        assert isinstance(caught.value.orig, psycopg.Error)
        assert caught.value.orig.sqlstate == "42501"
        assert (
            conn.scalar(select(table("ops.run").c.status).where(table("ops.run").c.id == case.run))
            == before
        )
