"""Actual native reference custody/isolation on a governed disposable candidate.

The controlled source is two cells spelling 12. Expected reference roles and values below
are authored independently of any production candidate; no retained reference data is read.
These are machinery controls, never model-quality or independent-population evidence.
"""

from copy import deepcopy
from dataclasses import replace

import pytest
from semantic import test_private_records as source_fixture
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
from semantic.test_private_records import private_source as private_source
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame
from corpus_structure.evaluate.record_references import (
    PROTOCOL,
    assign_origin,
    author_packet,
    create_reference_set,
    decode_frame,
    reference_inputs,
    source_binding,
)
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from native_test_support import principal_engine


@pytest.fixture
def reference_source(monkeypatch, request):
    original = source_fixture.observation_inputs
    monkeypatch.setattr(
        source_fixture, "observation_inputs", lambda bundle: reference_inputs(original(bundle))
    )
    case = request.getfixturevalue("private_source")
    # An explicit empty CPU report keeps a source-ready cut independent of predictions.
    with case.writer.begin() as conn:
        source_fixture.complete(case, conn, ())
        case.cut = seal_cut(conn, case.run, "source-ready-references", final=False)
    return case


def expected_reading(case, logical_source):
    view = case.view_row
    pin = dict(
        source=logical_source,
        native_product_task_id=view["native_task_id"],
        product_key=view["native_product_key"],
        product_digest=view["native_content_digest"],
        projection_digest=view["projection_digest"],
        recipe_digest=view["recipe_digest"],
        source_view_id=case.view,
    )
    pointer = case.table + "/data/table_cells/0"
    anchors = [
        dict(
            pin=pin,
            space="native",
            pointer=pointer,
            precision="exact",
            start=0,
            end=2,
            source_piece="12",
        ),
        dict(pin=pin, space="native", pointer=pointer, precision="item"),
    ]
    for anchor in anchors:
        anchor["anchor_id"] = anchor_identity(anchor)
    sets = [
        dict(role=role, ordering="ordered", usage=usage, anchors=(anchor["anchor_id"],))
        for role, usage, anchor in zip(
            ("value", "location"), ("literal", "native"), anchors, strict=True
        )
    ]
    for evidence in sets:
        evidence["set_id"] = evidence_set_identity(evidence)
    fields = (
        dict(
            role="value",
            kind="literal",
            state="present",
            meaning_changing=True,
            evidence_status="available",
            evidence_sets=(sets[0]["set_id"],),
            value=dict(kind="decimal", lexical="12"),
            original="12",
            reason="source-read",
        ),
        dict(
            role="location",
            kind="native",
            state="present",
            meaning_changing=True,
            evidence_status="available",
            evidence_sets=(sets[1]["set_id"],),
            value=dict(kind="native_location", pointer=pointer),
        ),
    )
    row = dict(
        contract="FixtureRecordFields",
        family="table",
        occurrence_recipe="source-anchor-membership-1",
        pin=pin,
        occurrence_anchors=(anchors[1]["anchor_id"],),
        standing="accepted",
        policy_version="reference-reading-1",
        anchors=tuple(anchors),
        evidence_sets=tuple(sets),
        fields=fields,
    )
    row["record_id"] = record_identity(case.prepared.release_id, row)
    row["interpretation_id"] = interpretation_identity(row)
    scopes = tuple(
        {
            key: value
            for key, value in anchor.items()
            if key in {"pin", "space", "pointer", "precision", "start", "end"}
        }
        for anchor in anchors
    )
    frame = RecordEvaluationFrame(
        view["key"],
        case.prepared.release_id,
        "independent-cell-guideline-1",
        "reference-reading-1",
        "m1-candidate-only-1",
        pin,
        frozenset(),
        anchor_scopes=scopes,
    )
    return row, frame


def create_case(conn, case, partition, *, captured_coordinates=(), include_empty_secondary=False):
    uri = conn.scalar(
        select(table("kb.document").c.source_uri).where(
            table("kb.document").c.id == case.view_row["document_id"]
        )
    )
    assign_origin(
        conn,
        project_id="private-records",
        origin_group="one-original-fixture",
        partition=partition,
        source_uris=(uri,),
        provenance=dict(
            origin="independently authored two-cell native fixture",
            copies_and_editions="all coassigned",
            independence_claim="none",
        ),
    )
    split_documents(
        conn,
        "private-records",
        SplitConfig(forced_dev={uri: "controlled reference source"}),
        release_id=case.prepared.release_id,
    )
    logical = source_binding(
        conn, source_run_id=case.run, source_view_id=case.view, source_cut_id=case.cut
    )
    row, frame = expected_reading(case, logical)
    frames = {frame.unit: frame}
    if include_empty_secondary:
        other = (
            conn.execute(
                select(table("kb.source_view")).where(
                    table("kb.source_view").c.id == case.other_view
                )
            )
            .mappings()
            .one()
        )
        pin = dict(
            source=source_binding(
                conn, source_run_id=case.run, source_view_id=case.other_view, source_cut_id=case.cut
            ),
            native_product_task_id=other["native_task_id"],
            product_key=other["native_product_key"],
            product_digest=other["native_content_digest"],
            projection_digest=other["projection_digest"],
            recipe_digest=other["recipe_digest"],
            source_view_id=other["id"],
        )
        frames[other["key"]] = replace(
            frame,
            unit=other["key"],
            pin=pin,
            anchor_scopes=(
                dict(
                    pin=pin, space="native", pointer=case.sibling, precision="exact", start=0, end=2
                ),
            ),
        )
    created = create_reference_set(
        conn,
        project_id="private-records",
        source_run_id=case.run,
        source_cut_id=case.cut,
        label="independent-cell-reference",
        legacy_split="dev",
        guideline=frame.guideline_version,
        guideline_text=(
            "Read exact cell spelling and source location; preserve faithful complete readings."
        ),
        partition=partition,
        unit_keys=tuple(frames),
        frames=frames,
        captured_coordinates={frame.unit: captured_coordinates},
        reference_policy_version=frame.reference_policy_version,
        prediction_policy_version=frame.prediction_policy_version,
        sampling=dict(
            seed=37,
            strata={key: "independent-source-region" for key in frames},
            inclusion_probabilities={key: 1 for key in frames},
            provenance=dict(source="controlled native source, no producer candidates"),
            cohort="native machinery control",
        ),
    )
    unit = (
        conn.execute(
            select(table("eval.reference_unit")).where(
                table("eval.reference_unit").c.set_id == created["set_id"],
                table("eval.reference_unit").c.unit_key == frame.unit,
            )
        )
        .mappings()
        .one()
    )
    return created, unit, row, frame


def native_pass(conn, unit, row, frame, kind, actor, parents=()):
    authored = canonical_bytes(
        dict(
            protocol=PROTOCOL,
            release_id=frame.release_id,
            unit_ref=frame.unit,
            guideline=frame.guideline_version,
            reference_policy_version=frame.reference_policy_version,
            prediction_policy_version=frame.prediction_policy_version,
            reason=(
                "Independent reading of the complete supported source record, "
                "including explicit empty regions."
            ),
            adjudication_passes=parents,
            records=[] if row is None else [row],
        )
    )
    return conn.scalar(
        text("SELECT eval.record_source_record_reference_pass(:u,:k,:a,:b,CAST(:f AS jsonb))"),
        dict(
            u=unit["id"],
            k=kind,
            a=actor,
            b=authored,
            f=canonical_bytes(unit["context"][0]).decode(),
        ),
    )


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


@pytest.mark.parametrize("changed_producer_alias", [False, True])
def test_native_missing_producer_keeps_denominator_but_real_alias_change_refuses(
    reference_source, semantic_evaluator_engine, changed_producer_alias
):
    from corpus_structure.core.method import UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.semantic.domain_operations import consolidate_cut
    from corpus_structure.semantic.operations import (
        OperationBinding,
        claim_tasks,
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
        if changed_producer_alias:
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
        scored = dict(
            scope="private_validated_records",
            comparison_policy="strict-source-occurrence-1",
            grain="accepted_source_record_occurrence",
            unit=frame.unit,
            release_id=frame.release_id,
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
        result = dict(
            protocol="source-record-evaluation-1",
            release_id=frame.release_id,
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
