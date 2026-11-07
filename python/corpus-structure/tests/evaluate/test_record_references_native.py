"""Actual native reference custody/isolation on a governed disposable candidate.

The controlled source is two cells spelling 12. Expected reference roles and values below
are authored independently of any production candidate; no retained reference data is read.
These are machinery controls, never model-quality or independent-population evidence.
"""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import create_model
from semantic.conftest import (
    semantic_db_engine as semantic_db_engine,
)
from semantic.conftest import (
    semantic_evaluator_engine as semantic_evaluator_engine,
)
from semantic.conftest import (
    semantic_reader_engine as semantic_reader_engine,
)
from semantic.conftest import (
    semantic_writer_engine as semantic_writer_engine,
)
from semantic.native_record_fixtures import private_source as private_source
from semantic.native_record_fixtures import qualified_view_draft
from semantic.reference_scenarios import (
    create_case,
    expected_reading,
    native_pass,
)
from semantic.reference_scenarios import (
    private_source_options as private_source_options,
)
from semantic.reference_scenarios import (
    reference_source as reference_source,
)
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import SourceViewDraft
from corpus_structure.evaluate.record_references import (
    assign_origin,
    author_packet,
    decode_frame,
    source_binding,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import complete_unit_result, seal_cut
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    interpretation_identity,
)
from native_test_support import principal_engine


def test_native_early_source_cut_keeps_independent_bytes_and_rejects_forged_scope(
    reference_source, semantic_evaluator_engine, semantic_reader_engine
):
    case = reference_source
    with semantic_evaluator_engine.begin() as conn:
        _, unit, row, frame = create_case(conn, case, "development")
        packet = author_packet(conn, unit["id"])
        assert set(packet) == {
            "protocol",
            "unit_id",
            "unit_ref",
            "release_id",
            "guideline",
            "guideline_text",
            "guideline_digest",
            "source_frame",
            "native_contexts",
            "authored_schema",
        }
        assert not conn.scalar(
            select(table("ops.completed_result").c.run_id).where(
                table("ops.completed_result").c.run_id == case.run
            )
        )
        a = native_pass(conn, unit, row, frame, "A", "independent-A")
        b = native_pass(conn, unit, row, frame, "B", "independent-B")
        c = native_pass(conn, unit, row, frame, "C", "independent-C", (a, b))
        assert c > b > a
        stored = conn.scalar(
            select(table("eval.reference_pass").c.authored).where(
                table("eval.reference_pass").c.id == c
            )
        )
        assert bytes(stored).find(b'"lexical":"12"') >= 0
        bad = deepcopy(row)
        bad["anchors"][0]["source_piece"] = "13"
        with pytest.raises(DBAPIError), conn.begin_nested():
            native_pass(conn, unit, bad, frame, "A", "independent-A")
        with pytest.raises(DBAPIError), conn.begin_nested():
            native_pass(conn, unit, row, frame, "B", "independent-A")
        with pytest.raises(DBAPIError), conn.begin_nested():
            native_pass(conn, unit, row, frame, "C", "independent-C", (b, a))
        provenance = conn.scalar(
            select(table("eval.reference_origin_group").c.provenance).where(
                table("eval.reference_origin_group").c.project_id == "private-records"
            )
        )
        with pytest.raises(DBAPIError), conn.begin_nested():
            assign_origin(
                conn,
                project_id="private-records",
                origin_group="one-original-fixture",
                partition="feature_fit",
                source_uris=("another-copy.pdf",),
                provenance=provenance,
            )
        for engine in (case.writer, semantic_reader_engine):
            with engine.connect() as source_conn:
                with pytest.raises(DBAPIError) as refusal, source_conn.begin_nested():
                    author_packet(source_conn, unit["id"])
                assert getattr(refusal.value.orig, "sqlstate", None) == "42501"


@pytest.mark.parametrize(
    "partition", ["development", "feature_fit", "final_event_calibration", "final_assessment"]
)
def test_actual_fitting_capability_has_only_fit_labels(
    reference_source, semantic_evaluator_engine, native_settings, semantic_db_engine, partition
):
    case = reference_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, row, frame = create_case(conn, case, partition)
        a = native_pass(conn, unit, row, frame, "A", "independent-A")
        b = native_pass(conn, unit, row, frame, "B", "independent-B")
        native_pass(conn, unit, row, frame, "C", "independent-C", (a, b))
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(
                text("SELECT eval.read_record_fitting_references(:s)"), dict(s=created["set_id"])
            )
    fitter = principal_engine(native_settings, "fit", semantic_db_engine.url.database)
    try:
        with fitter.connect() as conn:
            conn.execute(text("SELECT eval.require_record_fitting_principal()"))
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(text("SELECT authored FROM eval.reference_pass"))
            if partition == "feature_fit":
                result = conn.scalar(
                    text("SELECT eval.read_record_fitting_references(:s)"),
                    dict(s=created["set_id"]),
                )
                assert (
                    len(result) == 1
                    and result[0]["authored"]["records"][0]["fields"][0]["value"]["lexical"] == "12"
                )
            else:
                with pytest.raises(DBAPIError), conn.begin_nested():
                    conn.execute(
                        text("SELECT eval.read_record_fitting_references(:s)"),
                        dict(s=created["set_id"]),
                    )
    finally:
        fitter.dispose()


@pytest.mark.parametrize(
    ("changed_producer_alias", "failed_without_report"),
    [(False, False), (True, False), (False, True)],
)
def test_native_missing_producer_keeps_denominator_but_real_alias_change_refuses(
    reference_source, semantic_evaluator_engine, changed_producer_alias, failed_without_report
):
    from corpus_structure.core.method import UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.semantic.domain_operations import consolidate_cut
    from corpus_structure.semantic.operations import (
        OperationBinding,
        claim_tasks,
        complete_task,
        complete_unit_result,
        create_run,
        create_task,
    )

    case = reference_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, row, frame = create_case(
            conn, case, "development", include_empty_secondary=True
        )
        a = native_pass(conn, unit, row, frame, "A", "independent-A")
        b = native_pass(conn, unit, row, frame, "B", "independent-B")
        native_pass(conn, unit, row, frame, "C", "independent-C", (a, b))
        secondary = (
            conn.execute(
                select(table("eval.reference_unit")).where(
                    table("eval.reference_unit").c.set_id == created["set_id"],
                    table("eval.reference_unit").c.id != unit["id"],
                )
            )
            .mappings()
            .one()
        )
        secondary_frame = decode_frame(secondary["context"][0])
        aa = native_pass(conn, secondary, None, secondary_frame, "A", "independent-A")
        bb = native_pass(conn, secondary, None, secondary_frame, "B", "independent-B")
        native_pass(conn, secondary, None, secondary_frame, "C", "independent-C", (aa, bb))
    with case.writer.begin() as conn:
        target = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(case.prepared.release_id, "private-input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="independent-empty-target-control",
        )
        conn.execute(
            text("SELECT ops.select_source_view(:r,:origin,:v)"),
            dict(r=target, origin=case.run, v=case.view),
        )
        conn.execute(
            text("SELECT ops.select_source_view(:r,:origin,:v)"),
            dict(r=target, origin=case.run, v=case.other_view),
        )
        task = None
        if changed_producer_alias or failed_without_report:
            task = create_task(
                conn,
                run_id=target,
                config_id=case.task_row["method_config_id"],
                stage="record",
                unit_type="source_view",
                unit_id=case.view,
                unit_key="different-real-producer-alias",
                input_hash="changed-alias-control",
                fresh=True,
            )
            held = claim_tasks(
                conn, run_id=target, config_id=case.task_row["method_config_id"], holder="records"
            )[0]
            if failed_without_report:
                complete_task(
                    conn,
                    task_id=task,
                    attempt=held.attempt,
                    holder="records",
                    prepared=case.prepared,
                    observations=(),
                    outcome="failed",
                    error={"message": "controlled timeout without report", "stage": "worker"},
                )
            else:
                complete_unit_result(
                    conn,
                    task_id=task,
                    attempt=held.attempt,
                    holder="records",
                    prepared=case.prepared,
                    method=case.method,
                    configuration_hash="private-config",
                    source="different-real-producer-alias",
                    result=UnitResult(
                        ref=UnitRef(
                            TaskUnitType.SOURCE_VIEW, case.view, "different-real-producer-alias"
                        ),
                        outcome=ObservationOutcome.EMPTY,
                    ),
                    records=(),
                )
        cut = seal_cut(conn, target, "completed-target", final=True)
    output = consolidate_cut(case.writer, cut, "empty-reference-target")
    with semantic_evaluator_engine.begin() as conn:
        snapshot = conn.scalar(
            text("SELECT eval.native_reference_snapshot(:s)"), dict(s=created["set_id"])
        )
        zero = dict(reference=0, prediction=0, matched=0)
        one = dict(reference=1, prediction=0, matched=0, recall=0.0)
        families = {
            family: {
                tier: dict(one if family == "table" else zero)
                for tier in ("core", "full", "evidence")
            }
            for family in ("definition", "assertion", "measurement", "table", "formula_context")
        }
        tiers = {tier: dict(one) for tier in ("core", "full", "evidence")}
        scored: dict[str, Any] = dict(
            scope="private_validated_records",
            comparison_policy="strict-source-occurrence-1",
            grain="accepted_source_record_occurrence",
            unit=frame.unit,
            release_id=frame.release_id,
            reference_release_id=frame.release_id,
            match_bindings=[],
            guideline_version=frame.guideline_version,
            reference_policy_version=frame.reference_policy_version,
            prediction_policy_version=frame.prediction_policy_version,
            tiers=tiers,
            families=families,
            matches={tier: [] for tier in ("core", "full", "evidence")},
            field_failures=[],
            prediction_standings={},
            producer_reports=[],
            origin_group="one-original-fixture",
        )
        digest = conn.scalar(
            text(
                "SELECT encode(sha256(convert_to(sampling::text,'UTF8')),'hex') "
                "FROM eval.reference_set WHERE id=:s"
            ),
            dict(s=created["set_id"]),
        )
        empty_scored = deepcopy(scored)
        empty_scored.update(
            unit=secondary_frame.unit,
            tiers={key: dict(zero) for key in tiers},
            families={family: {key: dict(zero) for key in tiers} for family in families},
        )
        result: dict[str, Any] = dict(
            protocol="source-record-evaluation-1",
            release_id=frame.release_id,
            reference_release_id=frame.release_id,
            applicability=conn.scalar(
                text("SELECT eval.record_reference_applicability('private-records',:r,:s)"),
                dict(r=target, s=created["set_id"]),
            ),
            output_realization_id=output.realization_id,
            family="source_records",
            comparison_policy="strict-source-occurrence-1",
            grain="accepted_source_record_occurrence",
            tiers=tiers,
            families=families,
            units=[scored, empty_scored],
            reference_units_scored=2,
            partition="development",
            sampling_digest=digest,
            quality_claim="not_established",
        )
        frozen_by_unit = {value["unit_id"]: value for value in snapshot}
        for scored_unit, source_unit in ((scored, unit), (empty_scored, secondary)):
            frozen = frozen_by_unit[source_unit["id"]]
            if changed_producer_alias:
                with pytest.raises(DBAPIError, match="logical source binding"), conn.begin_nested():
                    conn.scalar(
                        text("SELECT eval.record_reference_unit_binding(:r,:u,:p,:f)"),
                        dict(
                            r=target, u=source_unit["id"], p=frozen["pass_id"], f=frozen["frame_id"]
                        ),
                    )
                return
            scored_unit["correspondence"] = conn.scalar(
                text("SELECT eval.record_reference_unit_binding(:r,:u,:p,:f)->'views'"),
                dict(r=target, u=source_unit["id"], p=frozen["pass_id"], f=frozen["frame_id"]),
            )
            scored_unit["gap_evidence"] = conn.scalar(
                text("SELECT eval.source_record_gap_evidence(:r,:u,:p,:f)"),
                dict(r=target, u=source_unit["id"], p=frozen["pass_id"], f=frozen["frame_id"]),
            )
        gap_evidence = scored["gap_evidence"]
        assert len(gap_evidence["gaps"]) == 1
        gap = gap_evidence["gaps"][0]
        assert gap["reference_record_id"] == row["record_id"]
        assert gap["kind"] == "no_output" and gap["earliest_failed_stage"] == "unknown"
        assert gap["predictions"] == []
        assert set(gap["reference_anchor_ids"]) == {a["anchor_id"] for a in row["anchors"]}
        assert empty_scored["gap_evidence"]["gaps"] == []
        statement = text(
            "SELECT eval.record_source_record_reference_evaluation("
            "'private-records',:r,:s,CAST(:n AS jsonb),CAST(:v AS jsonb))"
        )
        parameters = dict(
            r=target,
            s=created["set_id"],
            n=canonical_bytes(snapshot).decode(),
            v=canonical_bytes(result).decode(),
        )
        if changed_producer_alias:
            with pytest.raises(DBAPIError, match="logical source binding"), conn.begin_nested():
                conn.execute(statement, parameters)
        else:
            identity = conn.scalar(statement, parameters)
            stored = conn.scalar(
                select(table("eval.reference_evaluation").c.result).where(
                    table("eval.reference_evaluation").c.id == identity
                )
            )
            assert stored["tiers"]["full"] == one
            if failed_without_report:
                assert len(gap_evidence["tasks"]) == 1
                failure = gap_evidence["tasks"][0]
                assert failure["outcome"] == "failed" and failure["result_present"] is False
                assert failure["cut_member"] is False
                assert failure["selected_task_id"] == failure["origin_task_id"] == task
                import json

                assert json.loads(failure["error"]) == {
                    "message": "controlled timeout without report",
                    "stage": "worker",
                }
            else:
                assert gap_evidence["tasks"] == []
            for change in (
                "omit",
                "foreign_reference",
                "invent_stage",
                "source_cut",
                "fake_task",
                "physical_correspondence",
                "reference_release",
                "unit_correspondence",
                "match_identity",
            ):
                invalid = deepcopy(result)
                evidence = invalid["units"][0]["gap_evidence"]
                if change == "omit":
                    evidence["gaps"] = []
                elif change == "foreign_reference":
                    evidence["gaps"][0]["reference_record_id"] = "foreign-reference"
                elif change == "invent_stage":
                    evidence["gaps"][0]["kind"] = "missing"
                elif change == "source_cut":
                    evidence["source_cut_id"] += 1
                elif change == "fake_task":
                    evidence["tasks"] = [dict(selected_task_id=999)]
                elif change == "physical_correspondence":
                    invalid["applicability"]["views"][0]["physical_digest"] = "e" * 64
                elif change == "reference_release":
                    invalid["reference_release_id"] = "foreign-release"
                elif change == "unit_correspondence":
                    invalid["units"][0]["correspondence"][0]["prediction_pin"]["source"] = (
                        "foreign-alias"
                    )
                else:
                    invalid["units"][0]["match_bindings"] = [
                        dict(reference_record_id="invented-match")
                    ]
                with pytest.raises(DBAPIError), conn.begin_nested():
                    conn.execute(statement, dict(parameters, v=canonical_bytes(invalid).decode()))
            with case.writer.connect() as producer:
                with pytest.raises(DBAPIError) as refusal, producer.begin_nested():
                    producer.scalar(
                        text("SELECT eval.source_record_gap_evidence(:r,:u,:p,:f)"),
                        dict(
                            r=target,
                            u=unit["id"],
                            p=frozen_by_unit[unit["id"]]["pass_id"],
                            f=frozen_by_unit[unit["id"]]["frame_id"],
                        ),
                    )
                assert getattr(refusal.value.orig, "sqlstate", None) == "42501"
            changes = [
                ("unit", "foreign-unit"),
                ("origin_group", "foreign-origin"),
                ("release_id", "foreign-release"),
                ("guideline_version", "foreign-guideline"),
                ("reference_policy_version", "foreign-reference-policy"),
                ("prediction_policy_version", "foreign-prediction-policy"),
            ]
            for field, value in changes:
                invalid = deepcopy(result)
                invalid["units"][0][field] = value
                with (
                    pytest.raises(DBAPIError, match="unit population/origin/version binding"),
                    conn.begin_nested(),
                ):
                    conn.execute(statement, dict(parameters, v=canonical_bytes(invalid).decode()))
            duplicate = deepcopy(result)
            duplicate["units"][1] = deepcopy(duplicate["units"][0])
            with (
                pytest.raises(DBAPIError, match="unit population/origin/version binding"),
                conn.begin_nested(),
            ):
                conn.execute(statement, dict(parameters, v=canonical_bytes(duplicate).decode()))
            reordered = deepcopy(result)
            reordered["units"].reverse()
            assert (
                conn.scalar(statement, dict(parameters, v=canonical_bytes(reordered).decode()))
                > identity
            )


def test_unused_captured_coordinate_refuses_out_of_view_before_product_lookup(
    reference_source, semantic_evaluator_engine
):
    """Selected-view isolation is unconditional, independent of recognition authenticity.

    This negative uses shape-valid address metadata, not a claimed retained provider pass;
    the separate attributed-source native suite owns genuine captured-product controls.
    """
    case = reference_source
    with semantic_evaluator_engine.begin() as conn:
        logical = source_binding(
            conn, source_run_id=case.run, source_view_id=case.view, source_cut_id=case.cut
        )
        _, frame = expected_reading(case, logical)
        captured = dict(
            pin=frame.pin,
            space="captured_recognition",
            pointer=case.sibling,
            text="12",
            recognition=dict(
                selected_occurrence_id="outside-view",
                task_id=case.source_task,
                product_key="shape-only-negative",
                content_digest="a" * 64,
                occurrence_id="block-0",
                relation_id="outside-view-relation",
                endpoint_role="evidence",
                relation_kind="decision",
                relation_outcome="selected",
                provider_occurrence_json='{"precision":"block","text":"12"}',
                observation_json="{}",
            ),
        )
        case.prepared.validate_json("RecordCoordinateText", canonical_bytes(captured))
        with (
            pytest.raises(DBAPIError, match="pointer is outside frozen selected view"),
            conn.begin_nested(),
        ):
            create_case(conn, case, "development", captured_coordinates=(captured,))


@pytest.fixture
def compatible_reference_source(reference_source):
    """The source builder returns the exact original preparation inputs."""
    return reference_source


@pytest.mark.parametrize("candidate_output", [False, True])
def test_native_compatible_successor_keeps_original_reference_custody_and_fitter_sidecar(
    compatible_reference_source,
    semantic_db_engine,
    semantic_evaluator_engine,
    native_settings,
    candidate_output,
):
    """A new release/view/alias consumes original native bytes without reauthoring C.

    No PDF conversion or model runs. The successor changes an unrelated declaration;
    source-reading declarations and the complete physical source remain identical.
    """
    import yaml
    from sqlalchemy import insert

    from corpus_structure.core.method import UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.semantic import SourceArtifact, prepare_release
    from corpus_structure.semantic.domain_operations import consolidate_cut
    from corpus_structure.semantic.operations import (
        OperationBinding,
        claim_tasks,
        complete_task,
        create_run,
        create_task,
        record_method,
    )
    from corpus_structure.semantic.pdf_contracts import store_pdf_original
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.source_views import store_source_view

    case = compatible_reference_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, row, frame = create_case(conn, case, "feature_fit", anchor_ids_only=True)
        a = native_pass(conn, unit, row, frame, "A", "independent-A")
        b = native_pass(conn, unit, row, frame, "B", "independent-B")
        c = native_pass(conn, unit, row, frame, "C", "independent-C", (a, b))
        original_pass = dict(
            conn.execute(
                select(table("eval.reference_pass")).where(table("eval.reference_pass").c.id == c)
            )
            .mappings()
            .one()
        )
    bundle, dependencies, profile = case.preparation_inputs
    sources = []
    for source in bundle.sources:
        if source.name == "domain":
            domain = yaml.safe_load(source.content)
            domain["classes"]["UnconsumedSuccessorMarker"] = {}
            source = SourceArtifact(source.name, yaml.safe_dump(domain).encode())
        sources.append(source)
    bundle = replace(bundle, sources=tuple(sources))
    successor = prepare_release(bundle, dependencies, profile)
    assert successor.release_id != case.prepared.release_id
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, successor)
        conn.execute(
            insert(table("data.realization")).values(
                project_id="private-records",
                realization_id="successor-input",
                release_id=successor.release_id,
            )
        )
        recipe = conn.scalar(
            select(table("kb.source_artifact").c.content).where(
                table("kb.source_artifact").c.artifact_digest == case.view_row["recipe_digest"]
            )
        )
    with case.writer.begin() as conn:
        run = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(successor.release_id, "successor-input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="compatible-successor-control",
        )
        method = SimpleNamespace(
            name="private.source",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("PrivateSourceConfig"),
        )
        config = record_method(
            conn, method, "default", {}, "private-source-config", prepared=successor
        )
        source_config = config
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=case.view_row["document_id"],
            unit_key="source.pdf",
            input_hash="successor-retained-source",
        )
        held = claim_tasks(conn, run_id=run, config_id=config, holder="successor-source")[0]
        store_pdf_original(
            conn,
            task_id=task,
            attempt=held.attempt,
            holder="successor-source",
            original=b"%PDF-1.7\nprivate source record fixture",
            recipe_bytes=b'{"recipe":"private-records-1"}',
        )
        view = case.view_row
        projection = view["projection"]
        draft = SourceViewDraft(
            "compatible-successor-view",
            view["document_id"],
            ProductReference(
                view["native_task_id"], view["native_product_key"], view["native_content_digest"]
            ),
            view["section_pointer"],
            view["membership"],
            projection["text"],
            tuple(projection["pieces"]),
            tuple(projection["items"]),
            tuple(projection.get("ancestors", ())),
            projection["health"],
            bytes(recipe),
            analysis_eligible=view["analysis_eligible"],
        )
        draft = qualified_view_draft(draft, successor.release_id)
        actual_view = store_source_view(
            conn,
            run_id=run,
            task_id=task,
            attempt=held.attempt,
            holder="successor-source",
            draft=draft,
            position=0,
        )
        # An extra selected source with changed physical eligibility is unrelated
        # to this frozen unit. It must neither replace nor erase its exact mapping.
        changed_view = store_source_view(
            conn,
            run_id=run,
            task_id=task,
            attempt=held.attempt,
            holder="successor-source",
            draft=qualified_view_draft(
                replace(draft, analysis_eligible=False), successor.release_id
            ),
            position=1,
        )
        complete_task(
            conn,
            task_id=task,
            attempt=held.attempt,
            holder="successor-source",
            prepared=successor,
            observations=[],
            outcome="empty",
        )
        prediction = None
        prediction_task = None
        if candidate_output:
            method = SimpleNamespace(
                name="extract.m1_candidates",
                version="3",
                family="extract",
                tier="encoder",
                confidence_source=None,
                unit_type=TaskUnitType.SOURCE_VIEW,
                Config=case.method.Config,
            )
            config = record_method(
                conn, method, "default", {}, "successor-record-config", prepared=successor
            )
            prediction_task = create_task(
                conn,
                run_id=run,
                config_id=config,
                stage="record",
                unit_type="source_view",
                unit_id=actual_view,
                unit_key=draft.key,
                input_hash="successor-controlled-candidate",
            )
            claim = claim_tasks(conn, run_id=run, config_id=config, holder="successor-records")[0]
            actual_case = SimpleNamespace(
                prepared=successor,
                view=actual_view,
                table=case.table,
                view_row=dict(
                    conn.execute(
                        select(table("kb.source_view")).where(
                            table("kb.source_view").c.id == actual_view
                        )
                    )
                    .mappings()
                    .one()
                ),
            )
            # Fresh actual-view coordinates/identities, not a retagged original C.
            # Normal completion binds this record to the actual native source.
            prediction, _ = expected_reading(actual_case, draft.key)
            prediction["standing"] = "candidate"
            prediction["policy_version"] = frame.prediction_policy_version
            prediction["interpretation_id"] = interpretation_identity(prediction)
            complete_unit_result(
                conn,
                task_id=prediction_task,
                attempt=claim.attempt,
                holder="successor-records",
                prepared=successor,
                method=method,
                configuration_hash="successor-record-config",
                source=draft.key,
                result=UnitResult(
                    ref=UnitRef(TaskUnitType.SOURCE_VIEW, actual_view, draft.key),
                    outcome=ObservationOutcome.PRODUCED,
                    records=(prediction,),
                ),
                records=(prediction,),
            )
        cut = seal_cut(conn, run, "successor-source-ready", final=True)
    output = consolidate_cut(case.writer, cut, "compatible-empty-successor")
    with semantic_evaluator_engine.begin() as conn:
        snapshot = conn.scalar(
            text("SELECT eval.native_reference_snapshot(:s)"), dict(s=created["set_id"])
        )
        frozen = snapshot[0]
        args = dict(r=run, u=unit["id"], p=c, f=frozen["frame_id"])
        applicability = conn.scalar(
            text("SELECT eval.record_reference_applicability('private-records',:r,:s)"),
            dict(r=run, s=created["set_id"]),
        )
        assert applicability["reference_release_id"] == case.prepared.release_id
        assert applicability["prediction_release_id"] == successor.release_id
        assert applicability["views"][0]["reference_view_id"] == case.view
        assert applicability["views"][0]["prediction_view_id"] == actual_view != case.view
        binding = conn.scalar(text("SELECT eval.record_reference_unit_binding(:r,:u,:p,:f)"), args)
        assert binding["views"][0]["reference_pin"] == frame.pin
        actual_pin = binding["views"][0]["prediction_pin"]
        assert actual_pin["source"] == draft.key != frame.pin["source"]
        assert binding["prediction_frame"]["evaluation_frame"]["anchor_ids"] == sorted(
            frame.anchor_ids
        )
        actual_anchor = dict(row["anchors"][0], pin=actual_pin)
        actual_anchor["anchor_id"] = anchor_identity(actual_anchor)
        statement = text(
            "SELECT eval.record_reference_anchor_allowed(CAST(:a AS jsonb),"
            "CAST(:v AS jsonb),CAST(:f AS jsonb))"
        )
        allowed_args = dict(
            a=canonical_bytes(actual_anchor).decode(),
            v=canonical_bytes(binding["views"]).decode(),
            f=canonical_bytes(unit["context"][0]["evaluation_frame"]).decode(),
        )
        foreign = dict(actual_anchor, pointer=case.table + "/data/table_cells/1")
        foreign["anchor_id"] = anchor_identity(foreign)
        with semantic_db_engine.connect() as maintenance:
            assert maintenance.scalar(statement, allowed_args) is True
            assert (
                maintenance.scalar(
                    statement, dict(allowed_args, a=canonical_bytes(foreign).decode())
                )
                is False
            )
        gap = conn.scalar(text("SELECT eval.source_record_gap_evidence(:r,:u,:p,:f)"), args)
        assert (
            gap["source_view_id"] == case.view and gap["prediction_source_view_id"] == actual_view
        )
        assert gap["gaps"][0]["reference_record_id"] == row["record_id"]
        assert gap["gaps"][0]["kind"] == ("unaccepted" if candidate_output else "no_output")
        if candidate_output:
            assert prediction is not None
            assert gap["gaps"][0]["predictions"] == [
                dict(
                    record_id=prediction["record_id"],
                    interpretation_id=prediction["interpretation_id"],
                    standing="candidate",
                )
            ]
            assert prediction["record_id"] != row["record_id"]
            assert gap["match_bindings"] == []
        policy_frame = conn.scalar(
            text(
                "SELECT eval.record_policy_prediction_frame('private-records',:r,:s,"
                "'table','feature_fit')"
            ),
            dict(r=run, s=created["set_id"]),
        )
        assert policy_frame["release_id"] == successor.release_id
        assert policy_frame["reference_release_id"] == case.prepared.release_id
        assert policy_frame["units"][0]["reference_records"][0]["record_id"] == row["record_id"]
        assert policy_frame["units"][0]["source_view_id"] == actual_view
        if candidate_output:
            reports = policy_frame["units"][0]["reports"]
            assert len(reports) == 1
            assert canonical_bytes(reports[0]["records"]) == canonical_bytes([prediction])
            with semantic_db_engine.connect() as maintenance:
                assert (
                    maintenance.scalar(
                        text(
                            "SELECT eval.record_policy_full_correct(:r,CAST(:c AS jsonb),"
                            "CAST(:e AS jsonb),CAST(:v AS jsonb))"
                        ),
                        dict(
                            r=successor.release_id,
                            c=canonical_bytes(reports[0]["records"][0]).decode(),
                            e=canonical_bytes(
                                policy_frame["units"][0]["reference_records"]
                            ).decode(),
                            v=canonical_bytes(policy_frame["units"][0]["correspondence"]).decode(),
                        ),
                    )
                    is True
                )
        else:
            assert policy_frame["units"][0]["reports"] == []
        zero = dict(reference=0, prediction=0, matched=0)
        one = dict(reference=1, prediction=0, matched=0, recall=0.0)
        tiers = {tier: dict(one) for tier in ("core", "full", "evidence")}
        families = {
            family: {tier: dict(one if family == "table" else zero) for tier in tiers}
            for family in ("definition", "assertion", "measurement", "table", "formula_context")
        }
        scored = dict(
            scope="private_validated_records",
            comparison_policy="strict-source-occurrence-1",
            grain="accepted_source_record_occurrence",
            unit=frame.unit,
            release_id=successor.release_id,
            reference_release_id=case.prepared.release_id,
            guideline_version=frame.guideline_version,
            reference_policy_version=frame.reference_policy_version,
            prediction_policy_version=frame.prediction_policy_version,
            tiers=tiers,
            families=families,
            matches={tier: [] for tier in tiers},
            match_bindings=[],
            field_failures=[],
            prediction_standings={"candidate": 1} if candidate_output else {},
            producer_reports=[
                dict(
                    selected_task_id=prediction_task,
                    origin_task_id=prediction_task,
                    cut_id=cut,
                    source=draft.key,
                    outcome="produced",
                    records_present=True,
                )
            ]
            if candidate_output
            else [],
            origin_group="one-original-fixture",
            correspondence=binding["views"],
            gap_evidence=gap,
        )
        report = dict(
            protocol="source-record-evaluation-1",
            release_id=successor.release_id,
            reference_release_id=case.prepared.release_id,
            applicability=applicability,
            output_realization_id=output.realization_id,
            family="source_records",
            comparison_policy="strict-source-occurrence-1",
            grain="accepted_source_record_occurrence",
            tiers=tiers,
            families=families,
            units=[scored],
            reference_units_scored=1,
            partition="feature_fit",
            sampling_digest=conn.scalar(
                text(
                    "SELECT encode(sha256(convert_to(sampling::text,'UTF8')),'hex') "
                    "FROM eval.reference_set WHERE id=:s"
                ),
                dict(s=created["set_id"]),
            ),
            quality_claim="not_established",
        )
        evaluation = conn.scalar(
            text(
                "SELECT eval.record_source_record_reference_evaluation('private-records',"
                ":r,:s,CAST(:n AS jsonb),CAST(:v AS jsonb))"
            ),
            dict(
                r=run,
                s=created["set_id"],
                n=canonical_bytes(snapshot).decode(),
                v=canonical_bytes(report).decode(),
            ),
        )
        assert evaluation > 0
        current_pass = dict(
            conn.execute(
                select(table("eval.reference_pass")).where(table("eval.reference_pass").c.id == c)
            )
            .mappings()
            .one()
        )
        assert current_pass == original_pass
    fitter = principal_engine(native_settings, "fit", semantic_db_engine.url.database)
    try:
        with fitter.connect() as conn:
            rows = conn.scalar(
                text("SELECT eval.read_record_fitting_references(:s,:r)"),
                dict(s=created["set_id"], r=run),
            )
            assert rows[0]["authored"]["records"][0]["record_id"] == row["record_id"]
            assert rows[0]["source_frame"] == unit["context"][0]
            assert rows[0]["prediction_binding"] == binding
            assert rows[0]["applicability"] == applicability
    finally:
        fitter.dispose()
    # A selected, admitted view with a changed physical premise cannot stand in
    # for the frozen source, even when its literal projection is unchanged.
    with case.writer.begin() as conn:
        changed_run = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(successor.release_id, "successor-input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="changed-physical-source-control",
        )
        conn.execute(
            text("SELECT ops.select_source_view(:r,:o,:v)"),
            dict(r=changed_run, o=run, v=changed_view),
        )
        changed_cut = seal_cut(conn, changed_run, "changed-physical-source", final=True)
    consolidate_cut(case.writer, changed_cut, "changed-physical-source-result")
    with (
        semantic_evaluator_engine.begin() as conn,
        pytest.raises(DBAPIError, match="correspondence missing or ambiguous"),
        conn.begin_nested(),
    ):
        conn.scalar(
            text("SELECT eval.record_reference_applicability('private-records',:r,:s)"),
            dict(r=changed_run, s=created["set_id"]),
        )
    # A caller cannot manufacture a second identity for the same native recipe
    # and physical closure to make the protected correspondence ambiguous.
    with case.writer.begin() as conn:
        ambiguous_run = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(successor.release_id, "successor-input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="ambiguous-physical-source-control",
        )
        conn.execute(
            text("SELECT ops.select_source_view(:r,:o,:v)"),
            dict(r=ambiguous_run, o=run, v=actual_view),
        )
        task = create_task(
            conn,
            run_id=ambiguous_run,
            config_id=source_config,
            stage="ingest",
            unit_type="document",
            unit_id=case.view_row["document_id"],
            unit_key="source.pdf",
            input_hash="ambiguous-source-control",
        )
        held = claim_tasks(
            conn, run_id=ambiguous_run, config_id=source_config, holder="ambiguous-source"
        )[0]
        store_pdf_original(
            conn,
            task_id=task,
            attempt=held.attempt,
            holder="ambiguous-source",
            original=b"%PDF-1.7\nprivate source record fixture",
            recipe_bytes=b'{"recipe":"private-records-1"}',
        )
        with pytest.raises(DBAPIError, match="key differs"), conn.begin_nested():
            store_source_view(
                conn,
                run_id=ambiguous_run,
                task_id=task,
                attempt=held.attempt,
                holder="ambiguous-source",
                draft=replace(draft, key="ambiguous-physical-clone"),
                position=1,
            )
