"""Protected adjudication and common publication machinery, not quality evidence."""

import json
from dataclasses import asdict, replace
from typing import Any

import psycopg
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    OperationCase,
    OperationEvaluationFrame,
    create_reference_set,
    record_pass,
    reference_evaluate,
)
from corpus_structure.evaluate.record_references import (
    assign_origin,
    reference_inputs,
    source_binding,
)
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.domain_operations import _cut_input, consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.local_semantic_admission import (
    CONTEXT_POLICY,
    QUESTION,
    RUBRIC,
    semantic_assertion_identity,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.operations import OperationBinding, create_run, create_task, seal_cut
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from semantic.native_record_fixtures import complete_contributions as complete
from semantic.reference_scenarios import expected_reading

from . import native_record_fixtures as source_fixture
from .native_record_fixtures import contextual_result, curated_case
from .native_record_fixtures import private_source as private_source


@pytest.fixture
def private_source_options():
    return dict(bundle_transform=reference_inputs)


@pytest.fixture
def judged_source(private_source, request, semantic_evaluator_engine):
    selected = getattr(request, "param", {})
    partition = selected.get("partition", "development")
    original_case = private_source
    with original_case.writer.begin() as conn:
        source_fixture.complete(original_case, conn, ())
    case = curated_case(original_case)
    result, _, inventory = contextual_result(case, denotation=True)
    with case.writer.begin() as conn:
        complete(case, conn, result)
        cut = seal_cut(conn, case.run, "semantic-source-final", final=True)
    consolidate_cut(case.writer, cut, "semantic-source-private")
    with semantic_evaluator_engine.begin() as conn:
        uri = conn.scalar(
            select(table("kb.document").c.source_uri).where(
                table("kb.document").c.id == case.view_row["document_id"]
            )
        )
        assign_origin(
            conn,
            project_id="private-records",
            origin_group="denotation-control",
            partition=partition,
            source_uris=(uri,),
            provenance={"source": "controlled native12"},
        )
        split_documents(
            conn,
            "private-records",
            SplitConfig(forced_dev={uri: "controlled source"}),
            release_id=case.prepared.release_id,
        )
        logical = source_binding(
            conn, source_run_id=case.run, source_view_id=case.view, source_cut_id=cut
        )
        reading, old_frame = expected_reading(case, logical)
        anchor = reading["anchors"][0]
        frame = OperationEvaluationFrame(
            unit=old_frame.unit,
            release_id=case.prepared.release_id,
            guideline_version="denotation-control-1",
            rubric_version=RUBRIC,
            context_policy=CONTEXT_POLICY,
            operation_question=QUESTION,
            operation_version="1",
            domain="scientific-source",
            direction="source_first",
            pin=old_frame.pin,
            anchor_ids=(anchor["anchor_id"],),
            anchor_scopes=old_frame.anchor_scopes,
        )
        created = create_reference_set(
            conn,
            project_id="private-records",
            source_run_id=case.run,
            source_cut_id=cut,
            label="controlled-denotation",
            legacy_split="dev",
            guideline=frame.guideline_version,
            guideline_text="Resolve only numeral12 to declared target12.",
            partition=partition,
            frames={frame.unit: frame},
            sampling=dict(
                seed=1,
                strata={frame.unit: "controlled"},
                inclusion_probabilities={frame.unit: 1},
                provenance={"selection": "controlled native12"},
                cohort="native-denotation-control",
            ),
        )
        unit = conn.scalar(
            select(table("eval.reference_unit").c.id).where(
                table("eval.reference_unit").c.set_id == created["set_id"]
            )
        )
        target = next(t for t in inventory.targets if t.target_id == "t1")
        expected = OperationCase(
            case_id="numeral12-denotation",
            facet="denotation",
            anchor_ids=(anchor["anchor_id"],),
            inspected_scope=case.table + "/data/table_cells/0",
            source_state="stated",
            judgment="supported",
            alternatives=(
                dict(
                    semantic_type="contextual.denotation",
                    value=source_value(
                        dict(
                            target_id="t1",
                            target_source_binding=target.source_binding,
                            relation="denotes",
                            scope="chapter5",
                            effective_version=None,
                        )
                    ),
                ),
            ),
            explanation="Controlled source cell12 denotes supplied numeral12.",
            assessor_provenance={"assistance": "none; independent fixed expectation"},
        )
        if "judgment" in selected:
            expected = replace(expected, judgment=selected["judgment"])
        if selected.get("partial"):
            expected = replace(expected, alternatives=({"semantic_type": "contextual.denotation"},))
        payload = dict(
            protocol=PROTOCOL,
            release_id=frame.release_id,
            unit_ref=frame.unit,
            guideline=frame.guideline_version,
            rubric_version=RUBRIC,
            context_policy=CONTEXT_POLICY,
            operation_question=QUESTION,
            operation_version="1",
            domain=frame.domain,
            direction="source_first",
            reason="Independent controlled source expectation",
            cases=[
                asdict(replace(expected, case_id=f"numeral12-denotation-{index}"))
                if selected.get("cases", 1) > 1
                else asdict(expected)
                for index in range(selected.get("cases", 1))
            ],
            adjudication_passes=[],
        )
        a = record_pass(
            conn,
            unit_id=unit,
            pass_kind="A",
            actor="denotation-A",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        b = record_pass(
            conn,
            unit_id=unit,
            pass_kind="B",
            actor="denotation-B",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        payload["adjudication_passes"] = [a, b]
        record_pass(
            conn,
            unit_id=unit,
            pass_kind="C",
            actor="denotation-C",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        grade = reference_evaluate(
            conn, project_id="private-records", run_id=case.run, set_id=created["set_id"]
        )
        digest = conn.scalar(
            select(table("eval.reference_evaluation").c.content_digest).where(
                table("eval.reference_evaluation").c.id == grade.id
            )
        )
        case.semantic_reference = (unit, frame, payload)
        case.semantic_grade = (grade.id, digest)
        case.semantic_grades = [case.semantic_grade]
        for _ in range(selected.get("grades", 1) - 1):
            additional = reference_evaluate(
                conn, project_id="private-records", run_id=case.run, set_id=created["set_id"]
            )
            additional_digest = conn.scalar(
                select(table("eval.reference_evaluation").c.content_digest).where(
                    table("eval.reference_evaluation").c.id == additional.id
                )
            )
            case.semantic_grades.append((additional.id, additional_digest))
    with case.writer.begin() as conn:
        manifest = {
            "local_semantic_admission": [
                dict(evaluation_id=identity, evaluation_digest=content)
                for identity, content in case.semantic_grades
            ]
        }
        run = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(
                case.prepared.release_id, "private-input", 0, canonical_bytes(manifest)
            ),
            kind="full",
            options={},
            code_commit="semantic-publication-followup",
        )
        conn.execute(
            text("SELECT ops.select_source_view(:r,:old,:v)"),
            dict(r=run, old=case.run, v=case.view),
        )
        selected = create_task(
            conn,
            run_id=run,
            config_id=case.task_row["method_config_id"],
            stage="record",
            unit_type="source_view",
            unit_id=case.view,
            unit_key="private-unit",
            input_hash="private-input-hash",
        )
        assert conn.execute(
            select(table("ops.task").c.status, table("ops.task").c.reused_task_id).where(
                table("ops.task").c.id == selected
            )
        ).one() == ("reused", case.task)
        final = seal_cut(conn, run, "judged-publication-final", final=True)
    return case, run, final


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
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


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
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
                operation_version="1",
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


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_superseding_adjudication_makes_prior_grade_inapplicable(
    judged_source, semantic_evaluator_engine
):
    case, _, cut = judged_source
    unit, frame, payload = case.semantic_reference
    with semantic_evaluator_engine.begin() as conn:
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


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_writer_cannot_read_raw_adjudication_helper(judged_source):
    case, _, _ = judged_source
    evaluation_id, digest = case.semantic_grade
    with pytest.raises(DBAPIError, match="permission denied"), case.writer.begin() as conn:
        conn.execute(
            text("SELECT data.local_semantic_grade_evidence(:p,:r,:e,:d)"),
            dict(p="private-records", r=case.prepared.release_id, e=evaluation_id, d=digest),
        )


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
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
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
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
        assert semantic[0]["statement"]["target_id"] == "t1"
        assert semantic[0]["canonical_identity"] == "not_established"


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
@pytest.mark.parametrize("judged_source", [{"cases": 2, "grades": 2}], indirect=True)
@pytest.mark.parametrize(
    "corruption",
    ["statement", "grade", "case", "rubric", "source", "unit", "pass", "frame", "cut", "selected"],
)
def test_native_rejects_forged_judged_semantic_rows(judged_source, corruption):
    from corpus_structure.semantic.analytics import compile_projection
    from corpus_structure.semantic.arrow_publication import AppendPublication, stage_arrow

    case, _, cut = judged_source
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
    with (
        case.writer.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin() as transaction,
    ):
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
        with pytest.raises(DBAPIError) as caught, conn.begin_nested():
            publish(batch)
        assert isinstance(caught.value.orig, psycopg.Error)
        diagnostic = caught.value.orig.diag
        assert (
            caught.value.orig.sqlstate,
            diagnostic.constraint_name
            if corruption in {"source", "cut"}
            else diagnostic.message_primary,
        ) == expected
        if corruption == "selected":
            assert diagnostic.context is not None
            assert "validate_local_semantic_assertions" in diagnostic.context
        if corruption == "unit":
            for _ in range(8):
                with conn.begin_nested() as replay:
                    publish(clean)
                    replay.rollback()
                with pytest.raises(DBAPIError) as retry, conn.begin_nested():
                    publish(batch)
                assert isinstance(retry.value.orig, psycopg.Error)
                assert (retry.value.orig.sqlstate, retry.value.orig.diag.message_primary) == (
                    "23514",
                    unique_witness,
                )
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
        transaction.rollback()
    with case.writer.connect() as conn:
        assert (
            conn.scalar(
                select(table("data.local_semantic_assertion").c.assertion_id).where(
                    table("data.local_semantic_assertion").c.realization_id == "semantic-forged"
                )
            )
            is None
        )


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
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
