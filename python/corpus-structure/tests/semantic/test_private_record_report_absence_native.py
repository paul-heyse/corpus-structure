"""A sealed native producer without an envelope is coverage, not an empty report."""

import pytest
from sqlalchemy import select, text

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    BoundReader,
    claim_tasks,
    complete_unit_result,
    create_task,
    seal_cut,
)
from corpus_structure.semantic.records import read_private_record_reports
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import private_source as private_source


def test_sealed_report_absence_preserves_task_custody_and_explicit_empty(private_source):
    case = private_source
    with case.writer.begin() as conn:
        complete_unit_result(
            conn,
            task_id=case.task,
            attempt=case.held.attempt,
            holder="records",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit",
            result=UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.EMPTY,
            ),
            records=(),
        )
        malformed = create_task(
            conn,
            run_id=case.run,
            config_id=case.task_row["method_config_id"],
            stage="record-null-envelope",
            unit_type="source_view",
            unit_id=case.view,
            unit_key="private-null-envelope",
            input_hash="null-envelope",
            fresh=True,
        )
        claim = claim_tasks(
            conn,
            run_id=case.run,
            config_id=case.task_row["method_config_id"],
            holder="null-envelope",
        )[0]
        # JSONB null is a present result row, created through the actual protected
        # terminal API. It must never be relabelled as an absent envelope.
        conn.execute(
            text(
                "SELECT ops.complete_task(:task,:attempt,'null-envelope','[]'::jsonb,"
                "'empty',NULL,'null'::jsonb)"
            ),
            {"task": malformed, "attempt": claim.attempt},
        )
        assert (
            conn.scalar(
                text("SELECT jsonb_typeof(body)='null' FROM ops.task_result WHERE task_id=:task"),
                {"task": malformed},
            )
            is True
        )
        cut = seal_cut(conn, case.run, "report-absence-final", final=True)
    with case.writer.connect() as conn:
        # The real native producer completed empty through the protected API,
        # without an observation/result envelope. No administrative forgery is used.
        assert (
            conn.execute(
                select(table("ops.task_result")).where(
                    table("ops.task_result").c.task_id == case.source_task
                )
            ).first()
            is None
        )
        reader = BoundReader(conn, case.run, case.prepared, cut, analysis=False)
        explicit, absent = read_private_record_reports(reader, (case.task, case.source_task))
        assert explicit.records == () and explicit.outcome == "empty"
        assert absent.records is None and absent.source is None and absent.outcome is None
        assert (absent.selected_task_id, absent.origin_task_id, absent.cut_id) == (
            case.source_task,
            case.source_task,
            cut,
        )
        with pytest.raises(ValueError, match="envelope is not an object"):
            read_private_record_reports(reader, (malformed,))
        wrong_cut = BoundReader(conn, case.run, case.prepared, cut + 999999, analysis=False)
        with pytest.raises(ValueError, match="run/cut"):
            read_private_record_reports(wrong_cut, (case.source_task,))
