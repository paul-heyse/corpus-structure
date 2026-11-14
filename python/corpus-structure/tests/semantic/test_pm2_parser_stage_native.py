"""Preserve actual historical PM2 worklist/query custody without an execution runner."""

import json
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from semantic.native_record_fixtures import complete_contributions
from semantic.native_record_fixtures import private_source as private_source

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "docs/design_review/evidence"


@pytest.fixture
def parser_samples():
    panel = json.loads(
        (EVIDENCE / "2026-11-08_pm2-parsers/raw/reference-operations.json").read_bytes()
    )["cases"]
    return panel[0]["text"], panel[2]["text"], panel[4]["text"]


def test_pm2_unattempted_scope_remains_visible_without_provider_or_contributions(
    parser_source, parser_samples, tmp_path, commit_reader_engine
):
    from copy import deepcopy
    from hashlib import sha256

    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.orchestrate.commands import bound_status
    from corpus_structure.semantic.operations import BoundReader
    from corpus_structure.serve.review_bundle import (
        ReviewSelection,
        capture_review_relations,
        verify_review_bundle,
        write_review_bundle,
    )

    case = parser_source
    with case.writer.begin() as conn:
        complete_contributions(
            case,
            conn,
            UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.EMPTY,
            ),
        )
    finalize_bound_run(case.writer, case.run, "pm2-coverage-origin")
    (_source,) = prepare_structural_sources(
        case.writer,
        (
            StructuralPassageSelection(
                run_id=case.run,
                source_view_id=case.other_view,
                passage_id="coverage",
                start=0,
                end=len(parser_samples[0]),
                scope="coverage",
            ),
        ),
    ).sources
    from types import SimpleNamespace
    from corpus_structure.semantic._operation_calls import select_source_view
    from corpus_structure.semantic._operation_ids import SourceViewId
    from corpus_structure.semantic.operations import binding_of, create_run, start_run
    from corpus_structure.semantic.pm2_coverage import scope_coverage
    from semantic.witnessed_scenario_support import completed_metadata

    # Explicit historical records exercise retained query/export meaning. They do
    # not rerun eligibility, select a provider or represent current demand work.
    intents = [dict(source_view_id=case.other_view, extent=[0, len(parser_samples[0])],
        question="pm2.hanlp.frames", operation_version="1", disposition=disposition,
        reason=reason) for disposition, reason in (
            ("ineligible", "unsupported language: fr"),
            ("unscheduled", "explicit authored historical scope was not scheduled"),
        )]
    with case.writer.begin() as conn:
        run = create_run(conn, project_id=case.project_id, binding=binding_of(conn, case.run),
            kind="slice", options={"pm2_scope_intents": intents},
            code_commit="sealed-pm2-worklist-fixture", prepared=case.prepared)
        start_run(conn, run, prepared=case.prepared)
        select_source_view(conn, run_id=run, source_run_id=case.run,
            source_view_id=SourceViewId(case.other_view), projection_context=case.prepared)
    finalize_bound_run(case.writer, run, "sealed-unattempted-worklist")
    metadata, _, _ = completed_metadata(case, run)
    with case.writer.connect() as conn:
        coverage = scope_coverage(conn, run, intents)
    report = SimpleNamespace(run_id=run, cut_id=metadata["cut_id"], tasks=(), scope_coverage=coverage)
    assert not report.tasks
    with read_snapshot(case.writer) as conn:
        progress = bound_status(conn, report.run_id).run
        reader_coverage = BoundReader(
            conn, report.run_id, case.prepared, report.cut_id
        ).pm2_scope_coverage()
        selection = ContributionRequest(
            run_id=report.run_id, source_view_id=case.other_view, include_scope_coverage=True
        )
        inspection = serve_contributions(conn, selection)
    review = ReviewSelection(selections=(selection,))
    with read_snapshot(commit_reader_engine) as conn:
        captured = list(capture_review_relations(conn, review, OperationCancellation()))
    assert progress is not None
    assert progress.pm2_scope_coverage == reader_coverage == report.scope_coverage
    assert [entry.outcome for entry in report.scope_coverage] == ["ineligible", "unscheduled"]
    assert all(entry.emitted_count == entry.inspected_count == 0 for entry in report.scope_coverage)
    assert inspection.inventory_counts["contributions"] == 0
    assert [item["row"] for item in inspection.items if item["population"] == "scope_coverage"] == [
        entry.model_dump(mode="json") for entry in report.scope_coverage
    ]

    bundle = tmp_path / "review"
    manifest = write_review_bundle(review, bundle, captured)
    expected_digest = sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    assert verify_review_bundle(bundle, manifest_digest=expected_digest) == manifest

    with pytest.raises(ValueError, match="lacks its selected PM2 worklist"):
        write_review_bundle(
            review,
            tmp_path / "missing",
            ((relation, row) for relation, row in captured if relation != "pm2_worklists"),
        )
    changed: list[tuple[str, dict[str, Any]]] = [
        (relation, deepcopy(dict(row))) for relation, row in captured
    ]
    for relation, row in changed:
        if relation == "inventory" and row["row"]["outcome"] == "ineligible":
            row["row"]["reason"] = "different recorded refusal"
    with pytest.raises(ValueError, match="differs from worklist replay"):
        write_review_bundle(review, tmp_path / "mismatch", changed)

    # A detached reader cannot independently run eligibility or know that the
    # producer recorded every refusal. The export digest binds that history.
    (worklist,) = [row["worklist"] for relation, row in changed if relation == "pm2_worklists"]
    worklist["intents"][0]["reason"] = "different recorded refusal"
    rewritten = tmp_path / "rewritten"
    new_manifest = write_review_bundle(review, rewritten, changed)
    assert verify_review_bundle(rewritten) == new_manifest
    with pytest.raises(ValueError, match="integrity differs"):
        verify_review_bundle(rewritten, manifest_digest=expected_digest)


def test_cancelled_pm2_scope_does_not_gain_an_operation_result(parser_source):
    from hashlib import sha256

    from corpus_structure.orchestrate.commands import bound_status, cancel_bound_run
    from corpus_structure.semantic._operation_calls import select_source_view
    from corpus_structure.semantic._operation_ids import SourceViewId
    from corpus_structure.semantic.operations import binding_of, create_run, create_task, start_run
    from corpus_structure.semantic.pm2_coverage import scope_coverage

    case = parser_source
    with case.writer.begin() as conn:
        complete_contributions(
            case,
            conn,
            UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.EMPTY,
            ),
        )
    finalize_bound_run(case.writer, case.run, "pm2-cancel-origin")
    digest = sha256(b"bounded scope cancelled before inference").hexdigest()
    with case.writer.begin() as conn:
        run = create_run(
            conn,
            project_id=case.project_id,
            binding=binding_of(conn, case.run),
            kind="slice",
            options={
                "pm2_scope_intents": [
                    {
                        "source_view_id": case.other_view,
                        "extent": [0, 2],
                        "question": "pm2.hanlp.frames",
                        "operation_version": "1",
                        "disposition": "scheduled",
                        "input_digest": digest,
                    }
                ]
            },
            code_commit="native-pm2-coverage-test",
            prepared=case.prepared,
        )
        start_run(conn, run, prepared=case.prepared)
        select_source_view(
            conn,
            run_id=run,
            source_run_id=case.run,
            source_view_id=SourceViewId(case.other_view),
            projection_context=case.prepared,
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=case.task_row["method_config_id"],
            stage="extract",
            unit_type="source_view",
            unit_id=case.other_view,
            unit_key="private-unit",
            input_hash=digest,
        )
    assert cancel_bound_run(case.writer, run).tasks_cancelled == 1
    with read_snapshot(case.writer) as conn:
        status = bound_status(conn, run).run
        with pytest.raises(ValueError, match="scope source view differs from its admitted task"):
            scope_coverage(
                conn,
                run,
                [
                    {
                        "source_view_id": case.view,
                        "extent": [0, 2],
                        "question": "pm2.hanlp.frames",
                        "operation_version": "1",
                        "disposition": "scheduled",
                        "input_digest": digest,
                    }
                ],
            )
    assert status is not None and status.pm2_scope_coverage is not None
    (entry,) = status.pm2_scope_coverage
    assert entry.task_id == task
    assert entry.outcome == "cancelled"
    assert entry.origin_task_id is entry.inspected_count is entry.emitted_count is None


@pytest.fixture
def parser_source(parser_samples, commit_db_engine, commit_writer_engine, tmp_path):
    from semantic.native_record_fixtures import RecordSourceRecipe, record_source_for

    return record_source_for(
        RecordSourceRecipe(sibling_references=parser_samples),
        commit_db_engine,
        commit_writer_engine,
        tmp_path,
    )
