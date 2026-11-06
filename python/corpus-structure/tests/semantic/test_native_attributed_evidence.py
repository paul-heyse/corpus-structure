"""Forward candidate native address tests on owned disposable databases only."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.invariant_failures import InvariantViolation
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.native_objects import NativeObject, admit_native, native_owner
from corpus_structure.semantic.operations import (
    BoundReader,
    OperationBinding,
    claim_tasks,
    create_run,
    create_task,
)
from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity
from corpus_structure.semantic.records import (
    authenticated_coordinate_texts,
    authenticated_source_record_coordinates,
    read_private_record_reports,
)
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import bypass, candidate, complete, identities
from .native_record_fixtures import private_source as private_source
from .pdf_integration_support import CELL, integrated, prepare, publish
from .pdf_integration_support import native_source as native_source
from .pdf_integration_support import pdf13_db as pdf13_db

ROOT = Path(__file__).resolve().parents[4]
CANDIDATE = (
    ROOT
    / "docs/design_review/evidence/2026-11-03_m1-attributed-evidence"
    / "candidate-attempt-6/candidate/native_operations.json"
)


@pytest.fixture
def semantic_db_engine(native_server, semantic_head_template):
    with native_server.database(
        "cs_sem_m1_attributed_" + uuid4().hex[:12],
        semantic_head_template.name,
        policy=semantic_head_template.policy,
    ) as engine:
        with engine.begin() as conn:
            if current_revision(conn) == "semantic_m1_private_20261103":
                # Development candidate only. Once a forward migration owns these
                # objects, exercise that deployed head and its exact admission fence.
                state = json.loads(CANDIDATE.read_text())
                assert state["predecessor"] == "semantic_m1_private_20261103"
                operations = Operations(MigrationContext.configure(conn))
                for payload in state["operations"]:
                    operations.invoke(NativeTransitionOp.from_payload(payload))
                admit_native(
                    conn, tuple(NativeObject.from_payload(item) for item in state["desired"])
                )
        yield engine


def related(case, conn):
    record = candidate(case)
    previous = record["anchors"][0]["anchor_id"]
    other = (
        conn.execute(
            select(table("kb.source_view")).where(table("kb.source_view").c.id == case.other_view)
        )
        .mappings()
        .one()
    )
    anchor = record["anchors"][0]
    anchor.update(
        pin=dict(
            source=other["key"],
            native_product_task_id=other["native_task_id"],
            product_key=other["native_product_key"],
            product_digest=other["native_content_digest"],
            projection_digest=other["projection_digest"],
            recipe_digest=other["recipe_digest"],
            source_view_id=other["id"],
        ),
        pointer=case.sibling,
        binding=dict(
            version=2, relationship="selected_context", policy="attributed-selected-source-2"
        ),
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    for evidence in record["evidence_sets"]:
        old = evidence["set_id"]
        evidence["anchors"] = tuple(
            anchor["anchor_id"] if key == previous else key for key in evidence["anchors"]
        )
        evidence["set_id"] = evidence_set_identity(evidence)
        for field in record["fields"]:
            field["evidence_sets"] = tuple(
                evidence["set_id"] if key == old else key for key in field["evidence_sets"]
            )
    return identities(case, record)


def test_native_related_context_round_trip_and_helper_acl(private_source):
    case = private_source
    with case.writer.begin() as conn:
        record = related(case, conn)
        complete(case, conn, (record,))
    with case.writer.connect() as conn:
        report = BoundReader(conn, case.run, case.prepared, analysis=False).source_record_report(
            case.task
        )
        assert report.records is not None
        assert (
            report.records[0].model_dump(mode="python")["anchors"][0]["pin"]["source_view_id"]
            == case.other_view
        )
        assert conn.execute(
            text(
                "SELECT has_function_privilege('corpus_sem_reader',"
                "'ops.record_captured_recognition_text(bigint,text,text,text,jsonb)','EXECUTE')"
            )
        ).scalar_one()
        assert not conn.execute(
            text(
                "SELECT EXISTS(SELECT FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) a "
                "WHERE p.oid='ops.record_captured_recognition_text(bigint,text,text,text,jsonb)'"
                "::regprocedure AND a.grantee=0)"
            )
        ).scalar_one()


@pytest.mark.parametrize(
    "change", ["stale", "unselected", "fabricated_relation", "primary_occurrence", "wrong_spelling"]
)
def test_direct_native_related_forgery_refuses(private_source, change):
    case = private_source
    with case.writer.connect() as conn:
        record = related(case, conn)
    if change == "stale":
        record["anchors"][0]["pin"]["recipe_digest"] = "e" * 64
    elif change == "fabricated_relation":
        record["anchors"][0]["binding"]["relationship"] = "note"
    elif change == "primary_occurrence":
        record["occurrence_anchors"] = (record["anchors"][0]["anchor_id"],)
    elif change == "wrong_spelling":
        record["anchors"][0]["source_piece"] = "99"
    if change == "unselected":
        # A real second run selects only the primary view. The related view is
        # extant with its correct immutable pin, but belongs to the origin's selection.
        with case.writer.begin() as conn:
            run = create_run(
                conn,
                project_id="private-records",
                binding=OperationBinding(case.prepared.release_id, "private-input", 0, b"{}"),
                kind="full",
                options={},
                code_commit="unselected-related-test",
            )
            conn.execute(
                text("SELECT ops.select_source_view(:run,:origin,:view)"),
                dict(run=run, origin=case.run, view=case.view),
            )
            task = create_task(
                conn,
                run_id=run,
                config_id=case.task_row["method_config_id"],
                stage="record",
                unit_type="source_view",
                unit_id=case.view,
                unit_key="private-unit",
                input_hash="private-input-hash",
                fresh=True,
            )
            held = claim_tasks(
                conn, run_id=run, config_id=case.task_row["method_config_id"], holder="records"
            )[0]
            task_row = dict(
                conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
                .mappings()
                .one()
            )
        case = SimpleNamespace(
            **{**vars(case), "run": run, "task": task, "held": held, "task_row": task_row}
        )
    with (
        case.writer.begin() as conn,
        pytest.raises((DBAPIError, InvariantViolation)),
        conn.begin_nested(),
    ):
        bypass(case, conn, (deepcopy(record),))


def recognition_address(db, values):
    relation = next(
        row
        for row in values["relations"]
        if any(end["role"] == "output" and end["occurrence_id"] == CELL for end in row["endpoints"])
    )
    observed = db.observations[0].values()
    return dict(
        selected_occurrence_id=CELL,
        task_id=db.job.task,
        product_key="pass-a",
        content_digest=db.observations[0].digest,
        occurrence_id="block-0",
        relation_id=relation["relation_id"],
        endpoint_role="evidence",
        relation_kind="decision",
        relation_outcome="selected",
        provider_occurrence_json=json.dumps(observed["occurrences"][0]),
        observation_json=json.dumps(observed["observation"]),
    )


def read_captured(conn, db, digest, address):
    return conn.execute(
        text(
            "SELECT ops.record_captured_recognition_text("
            ":task,'selected',:digest,'#/tables/0',CAST(:address AS jsonb))"
        ),
        dict(task=db.job.task, digest=digest, address=json.dumps(address)),
    ).scalar_one()


def test_native_captured_recognition_preserves_block_precision(pdf13_db):
    db = pdf13_db
    values = integrated(db.source, db.inputs)
    digest = publish(db, prepare(values, db.source))
    address = recognition_address(db, values)
    with db.writer.connect() as conn:
        assert read_captured(conn, db, digest, address) == "equal"
    assert json.loads(address["provider_occurrence_json"])["precision"] == "block"
    assert "start" not in json.loads(address["provider_occurrence_json"])


@pytest.mark.parametrize(
    "change",
    [
        "equal_other_occurrence",
        "wrong_product",
        "wrong_selected",
        "unsupported_relation",
        "provider_precision",
        "image_provenance",
    ],
)
def test_native_captured_lineage_and_precision_forgery_refuse(pdf13_db, change):
    db = pdf13_db
    values = integrated(db.source, db.inputs)
    digest = publish(db, prepare(values, db.source))
    address = recognition_address(db, values)
    if change == "equal_other_occurrence":
        address["occurrence_id"] = "block-1"
    elif change == "wrong_product":
        address["content_digest"] = "d" * 64
    elif change == "wrong_selected":
        address["selected_occurrence_id"] = "#/texts/0"
    elif change == "unsupported_relation":
        address["relation_kind"] = "correspondence"
    elif change == "provider_precision":
        provider = json.loads(address["provider_occurrence_json"])
        provider.update(precision="exact", start=0, end=5)
        address["provider_occurrence_json"] = json.dumps(provider)
    elif change == "image_provenance":
        provider = json.loads(address["observation_json"])
        provider["image"]["precision"] = "exact"
        address["observation_json"] = json.dumps(provider)
    with db.writer.begin() as conn, pytest.raises(DBAPIError), conn.begin_nested():
        read_captured(conn, db, digest, address)


@pytest.mark.parametrize("disposition", ["selected", "retained_alternative"])
def test_native_selected_decision_alternative_is_readable_without_promoting_disposition(
    pdf13_db, disposition
):
    db = pdf13_db
    values = integrated(db.source, db.inputs)
    relation = next(
        row
        for row in values["relations"]
        if any(end["role"] == "output" and end["occurrence_id"] == CELL for end in row["endpoints"])
    )
    relation["endpoints"].append(dict(role="alternative", input_index=1, occurrence_id="block-1"))
    if disposition == "retained_alternative":
        retained = deepcopy(relation)
        retained.update(relation_id="retained-input-reading", outcome=disposition)
        values["relations"].append(retained)
    digest = publish(db, prepare(values, db.source))
    address = recognition_address(db, values)
    address.update(
        endpoint_role="alternative",
        relation_id="retained-input-reading"
        if disposition == "retained_alternative"
        else address["relation_id"],
        relation_outcome=disposition,
        occurrence_id="block-1",
        provider_occurrence_json=json.dumps(db.observations[0].values()["occurrences"][1]),
    )
    with db.writer.connect() as conn:
        assert read_captured(conn, db, digest, address) == "equal"
    assert address["relation_outcome"] == disposition
    assert address["endpoint_role"] == "alternative"


def test_completed_report_shared_guard_requires_exact_body_and_internal_acl(
    private_source, semantic_db_engine
):
    case = private_source
    with case.writer.begin() as conn:
        complete(case, conn, (candidate(case),))
    with case.writer.connect() as conn:
        body = conn.execute(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == case.task
            )
        ).scalar_one()
        assert not conn.execute(
            text(
                "SELECT has_function_privilege('corpus_sem_writer',"
                "'ops.validate_source_record_report(bigint,jsonb)','EXECUTE')"
            )
        ).scalar_one()
    with semantic_db_engine.begin() as conn, native_owner(conn, "corpus_sem_publisher"):
        conn.execute(
            text("SELECT ops.validate_source_record_report(:task,CAST(:body AS jsonb))"),
            dict(task=case.task, body=json.dumps(body)),
        )
        forged = deepcopy(body)
        forged["records"][0]["anchors"][0]["source_piece"] = "99"
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(
                text("SELECT ops.validate_source_record_report(:task,CAST(:body AS jsonb))"),
                dict(task=case.task, body=json.dumps(forged)),
            )


def test_bulk_reports_preserve_order_origin_and_reuse_one_product_hydration(
    private_source, monkeypatch
):
    from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader

    case = private_source
    with case.writer.begin() as conn:
        complete(case, conn, (candidate(case),))
        second = create_task(
            conn,
            run_id=case.run,
            config_id=case.task_row["method_config_id"],
            stage="record-again",
            unit_type="source_view",
            unit_id=case.view,
            unit_key="private-unit",
            input_hash="private-input-hash",
            fresh=True,
        )
        held = claim_tasks(
            conn, run_id=case.run, config_id=case.task_row["method_config_id"], holder="records"
        )[0]
        task_row = dict(
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == second))
            .mappings()
            .one()
        )
        other = SimpleNamespace(
            **{**vars(case), "task": second, "held": held, "task_row": task_row}
        )
        complete(other, conn, (candidate(other),))
    original = PublishedPdfReader.selected_native_items
    hydrated = []

    def observed(self, pointers):
        hydrated.append(tuple(pointers))
        return original(self, pointers)

    monkeypatch.setattr(PublishedPdfReader, "selected_native_items", observed)
    with case.writer.connect() as conn:
        reader = BoundReader(conn, case.run, case.prepared, analysis=False)
        reports = read_private_record_reports(reader, (second, case.task))
        assert [(row.selected_task_id, row.origin_task_id) for row in reports] == [
            (second, second),
            (case.task, case.task),
        ]
        assert all(row.source == "private-unit" and row.outcome == "produced" for row in reports)
        assert all(row.records is not None and len(row.records) == 1 for row in reports)
        assert hydrated == [(case.table,)]
        with pytest.raises(ValueError, match="unique"):
            read_private_record_reports(reader, (case.task, case.task))
        wrong_cut = SimpleNamespace(
            conn=conn, run_id=case.run, prepared=case.prepared, cut_id=999999
        )
        with pytest.raises(ValueError, match="run/cut"):
            read_private_record_reports(wrong_cut, (case.task,))


def test_bulk_report_absence_and_explicit_empty_remain_distinct(private_source):
    from .native_record_fixtures import (
        complete_absent_and_empty_reports,
    )

    case = private_source
    complete_absent_and_empty_reports(case)
    with case.writer.connect() as conn:
        tasks = table("ops.task")
        selected = tuple(
            conn.execute(
                select(tasks.c.id)
                .where(tasks.c.run_id == case.run, tasks.c.unit_type == "source_view")
                .order_by(tasks.c.id)
            ).scalars()
        )
        reports = read_private_record_reports(
            BoundReader(conn, case.run, case.prepared, analysis=False), selected
        )
        assert tuple(report.records for report in reports) == (None, ())


def test_source_coordinates_are_standing_neutral_without_weakening_private_fence(
    private_source, semantic_db_engine
):
    case = private_source
    record = candidate(case)
    record["standing"] = "accepted"
    signature = "ops.validate_source_record_coordinates(bigint,bigint,text,jsonb)"
    with case.writer.begin() as conn:
        for role in ("corpus_sem_writer", "corpus_sem_reader", "corpus_sem_evaluator"):
            assert not conn.execute(
                text("SELECT has_function_privilege(:role,:signature,'EXECUTE')"),
                dict(role=role, signature=signature),
            ).scalar_one()
        with pytest.raises(InvariantViolation), conn.begin_nested():
            bypass(case, conn, (record,))
        with pytest.raises(ValueError, match="accepted"):
            authenticated_coordinate_texts(
                conn, case.prepared, case.task_row, "private-unit", (record,)
            )
        coordinates = authenticated_source_record_coordinates(
            conn,
            case.prepared,
            run_id=case.run,
            source_view_id=case.view,
            source="private-unit",
            records=(record,),
        )
        assert any(row["text"] == "12" for row in coordinates)
        with pytest.raises(ValueError, match="release"):
            authenticated_source_record_coordinates(
                conn,
                replace(case.prepared, release_id="release:" + "f" * 64),
                run_id=case.run,
                source_view_id=case.view,
                source="private-unit",
                records=(record,),
            )
        assert (
            conn.execute(
                select(table("ops.task_result").c.task_id).where(
                    table("ops.task_result").c.task_id == case.task
                )
            ).first()
            is None
        )
    with semantic_db_engine.begin() as conn, native_owner(conn, "corpus_sem_publisher"):
        statement = text(
            "SELECT ops.validate_source_record_coordinates("
            ":run,:view,:source,CAST(:records AS jsonb))"
        )
        params = dict(
            run=case.run, view=case.view, source="private-unit", records=json.dumps((record,))
        )
        conn.execute(statement, params)
        forged = deepcopy(record)
        forged["anchors"][0]["source_piece"] = "99"
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(statement, dict(params, records=json.dumps((forged,))))
