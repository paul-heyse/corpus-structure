"""Independent scope correspondences preserve outcome and custody distinctions."""

import pytest

from corpus_structure.semantic.pm2_coverage import ScopeCoverage
from corpus_structure.serve.coverage_comparison import compare_scope_rows
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.native_record_fixtures import private_source as private_source


def scope(outcome="succeeded", **changes):
    return ScopeCoverage.model_validate(
        dict(
            source_view_id=1,
            extent=(0, 4),
            question="locate",
            operation_version="1",
            outcome=outcome,
            **changes,
        )
    )


def test_scope_matching_preserves_outcomes_and_does_not_rank_quality():
    for outcome in (
        "succeeded",
        "empty",
        "failed",
        "unscheduled",
        "ineligible",
        "cancelled",
        "limited",
    ):
        result = compare_scope_rows([scope()], [scope(outcome)], same_release=True)
        assert result[0].standing == "matched"
        assert result[0].right[0].outcome == outcome
        assert "improved" not in result[0].model_dump()


def test_contexts_and_parallel_scopes_remain_distinct():
    first = scope()
    other_view = first.model_copy(update={"source_view_id": 2})
    assert [x.standing for x in compare_scope_rows([first], [other_view], same_release=True)] == [
        "left_only",
        "right_only",
    ]
    assert compare_scope_rows([first], [first], same_release=False)[0].standing == "incomparable"
    other_version = first.model_copy(update={"operation_version": "2"})
    assert (
        compare_scope_rows([first], [other_version], same_release=True)[0].reason
        == "operation_version_differs"
    )
    assert compare_scope_rows([first, first], [first], same_release=True)[0].standing == "ambiguous"
    child = first.model_copy(update={"extent": (0, 2), "outcome": "succeeded"})
    assert (
        len(
            compare_scope_rows(
                [first.model_copy(update={"outcome": "limited"}), child], [first], same_release=True
            )
        )
        == 2
    )


@pytest.mark.parametrize(
    "private_source", [RecordSourceRecipe()], indirect=True, ids=("record-base",)
)
def test_native_completed_scope_comparison_and_cli(
    private_source, cli, native_settings, record_source_reader
):
    import json

    from sqlalchemy import select
    from sqlalchemy.engine import make_url

    from corpus_structure.core.method import UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.orchestrate.commands import finalize_bound_run
    from corpus_structure.semantic._operation_calls import select_source_view
    from corpus_structure.semantic._operation_ids import SourceViewId
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import binding_of, create_run, start_run
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.serve.coverage_comparison import (
        CoverageComparisonRequest,
        compare_coverage,
    )
    from semantic.native_record_fixtures import complete_contributions

    case = private_source
    with case.writer.begin() as conn:
        complete_contributions(
            case,
            conn,
            UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.EMPTY,
            ),
        )
    from types import SimpleNamespace

    from corpus_structure.semantic.operations import claim_tasks, create_task
    from corpus_structure.semantic.pm2_coverage import read_scope_worklist

    finalize_bound_run(case.writer, case.run, "coverage-origin")
    pins = []
    for index in range(2):
        with case.writer.begin() as conn:
            run = create_run(
                conn,
                project_id=case.project_id,
                binding=binding_of(conn, case.run),
                kind="slice",
                options={
                    "pm2_scope_intents": [
                        dict(
                            source_view_id=case.view,
                            extent=[0, 2],
                            question=q,
                            operation_version="1",
                            disposition="unscheduled",
                            reason="not requested",
                        )
                        for q in ("a", "b")
                    ]
                    + [
                        dict(
                            source_view_id=case.view,
                            extent=[0, 2],
                            question="inspect_caption",
                            operation_version="1",
                            disposition="scheduled",
                            input_digest="a" * 64,
                        )
                    ]
                },
                code_commit="coverage-comparison-native",
                prepared=case.prepared,
            )
            start_run(conn, run, prepared=case.prepared)
            select_source_view(
                conn,
                run_id=run,
                source_run_id=case.run,
                source_view_id=SourceViewId(case.view),
                projection_context=case.prepared,
            )
            task = create_task(
                conn,
                run_id=run,
                config_id=case.task_row["method_config_id"],
                stage="extract",
                unit_type="source_view",
                unit_id=case.view,
                unit_key="private-unit",
                input_hash="a" * 64,
                fresh=True,
            )
            (held,) = claim_tasks(
                conn,
                run_id=run,
                config_id=case.task_row["method_config_id"],
                holder="records",
                limit=1,
            )
            values = dict(vars(case), run=run, task=task, held=held)
            complete_contributions(
                SimpleNamespace(**values),
                conn,
                UnitResult(
                    ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                    outcome=ObservationOutcome.EMPTY,
                    contributions=(),
                    contribution_coordinate_texts=(),
                    contribution_operations=(
                        dict(
                            operation_key="empty",
                            question="inspect_caption",
                            operation_version="1",
                            outcome="empty",
                            inspected_count=1,
                            emitted_count=0,
                        ),
                    ),
                ),
            )
            root = dict(
                source_view_id=case.view,
                extent=[0, 2],
                question="forged",
                operation_version="1",
                disposition="scheduled",
                input_digest="a" * 64,
            )
            assert [x.id for x in read_scope_worklist(conn, run, [root]).settlements] == [task]
            # The caller cannot introduce a question absent from the retained roots.
            assert (
                read_scope_worklist(
                    conn, run, [root], resident_intents=True, question="forged"
                ).settlements
                == ()
            )
            with conn.begin_nested() as probe:
                selected_child = create_task(
                    conn,
                    run_id=run,
                    config_id=case.task_row["method_config_id"],
                    stage="extract",
                    unit_type="source_view",
                    unit_id=case.view,
                    unit_key="private-unit",
                    input_hash="b" * 64,
                    fresh=True,
                    trigger={
                        "pm2_split_scope": dict(
                            source_view_id=case.view,
                            extent=[0, 1],
                            question="inspect_caption",
                            operation_version="1",
                            disposition="scheduled",
                            input_digest="b" * 64,
                            parent_input_digest="a" * 64,
                        )
                    },
                )
                create_task(
                    conn,
                    run_id=run,
                    config_id=case.task_row["method_config_id"],
                    stage="extract",
                    unit_type="source_view",
                    unit_id=case.view,
                    unit_key="private-unit",
                    input_hash="d" * 64,
                    fresh=True,
                )
                unrelated_child = create_task(
                    conn,
                    run_id=run,
                    config_id=case.task_row["method_config_id"],
                    stage="extract",
                    unit_type="source_view",
                    unit_id=case.view,
                    unit_key="private-unit",
                    input_hash="c" * 64,
                    fresh=True,
                    trigger={
                        "pm2_split_scope": dict(
                            source_view_id=case.view,
                            extent=[0, 1],
                            question="unrelated",
                            operation_version="1",
                            disposition="scheduled",
                            input_digest="c" * 64,
                            parent_input_digest="d" * 64,
                        )
                    },
                )
                root["question"] = "inspect_caption"
                selected = read_scope_worklist(
                    conn, run, [root], resident_intents=True, question="inspect_caption"
                )
                assert [row.id for row in selected.settlements] == [task, selected_child]
                assert unrelated_child not in {row.id for row in selected.settlements}
                probe.rollback()
        finalize_bound_run(case.writer, run, "coverage-side-" + str(index))
        with case.writer.connect() as conn:
            cut = conn.scalar(
                select(table("ops.completed_result").c.cut_id).where(
                    table("ops.completed_result").c.run_id == run
                )
            )
        pins.append(dict(run_id=run, cut_id=cut, release_id=case.prepared.release_id))
    request = CoverageComparisonRequest.model_validate(dict(left=pins[0], right=pins[1], limit=1))
    with read_snapshot(record_source_reader) as conn:
        first = compare_coverage(conn, request)
        assert first.selected_count == 3 and first.rows[0].standing == "matched"
        assert first.rows[0].left[0].outcome == "unscheduled"
        assert first.next_cursor is not None
        second = compare_coverage(conn, request.model_copy(update={"cursor": first.next_cursor}))
        assert second.rows[0].question == "b" and second.next_cursor is not None
        third = compare_coverage(conn, request.model_copy(update={"cursor": second.next_cursor}))
        assert third.rows[0].left[0].outcome == "empty" and third.next_cursor is None
        with pytest.raises(ValueError, match="continuation"):
            compare_coverage(
                conn, request.model_copy(update={"cursor": first.next_cursor, "question": "a"})
            )
        with pytest.raises(ValueError, match="pin differs"):
            compare_coverage(
                conn,
                request.model_copy(
                    update={"right": request.right.model_copy(update={"cut_id": 999999})}
                ),
            )
        with pytest.raises(ValueError, match="continuation"):
            compare_coverage(
                conn,
                request.model_copy(
                    update={
                        "left": request.right,
                        "right": request.left,
                        "cursor": first.next_cursor,
                    }
                ),
            )
        with pytest.raises(ValueError, match="byte bound"):
            compare_coverage(conn, request.model_copy(update={"max_bytes": 1}))
    # Read-only CLI uses the exact same request and acquired contexts.
    url = make_url(native_settings.database.url).set(database=case.writer.url.database)
    settings = native_settings.model_copy(
        update={
            "database": native_settings.database.model_copy(
                update={"url": url.render_as_string(hide_password=False)}
            )
        }
    )
    flags = [
        part
        for side, pin in zip(("left", "right"), pins, strict=True)
        for key in ("run_id", "cut_id", "release_id")
        for part in ("--" + side + "-" + key.split("_")[0], str(pin[key]))
    ]
    shown = cli("contributions", "compare-coverage", *flags, "--json", settings=lambda: settings)
    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.stdout)["selected_count"] == 3
    human = cli("contributions", "compare-coverage", *flags, settings=lambda: settings)
    assert human.exit_code == 0, human.output
    assert "coverage-comparison-1" in human.stdout


def test_distinct_versions_on_both_sides_are_not_ambiguous():
    first = scope()
    second = first.model_copy(update={"operation_version": "2"})
    rows = compare_scope_rows([first, second], [first, second], same_release=True)
    assert [row.standing for row in rows] == ["matched", "matched"]


def test_completed_custody_preserves_reuse_and_limited_split_children():
    from corpus_structure.semantic.pm2_coverage import ScopeWorklist, derive_scope_coverage

    parent, child = "a" * 64, "b" * 64
    initial = dict(
        source_view_id=1,
        extent=[0, 4],
        question="locate",
        operation_version="1",
        disposition="scheduled",
        input_digest=parent,
    )
    split = dict(initial, extent=[0, 2], input_digest=child, parent_input_digest=parent)
    rows = [
        dict(
            id=11,
            input_hash=parent,
            unit_type="source_view",
            unit_id=1,
            reused_task_id=None,
            status="done",
            reason=None,
            split_scope=None,
            question="locate",
            operation_version="1",
            outcome="limited",
            provider_outcome=None,
            inspected=1,
            emitted=0,
            result_reason="split required",
            cut_origin=11,
        ),
        dict(
            id=12,
            input_hash=child,
            unit_type="source_view",
            unit_id=1,
            reused_task_id=7,
            status="reused",
            reason=None,
            split_scope=split,
            question="locate",
            operation_version="1",
            outcome="succeeded",
            provider_outcome=None,
            inspected=1,
            emitted=1,
            result_reason=None,
            cut_origin=7,
        ),
    ]
    derived = derive_scope_coverage(
        ScopeWorklist.model_validate(dict(intents=[initial], settlements=rows)), completed=True
    )
    assert [(x.extent, x.outcome, x.task_id, x.origin_task_id) for x in derived] == [
        ((0, 4), "limited", 11, 11),
        ((0, 2), "succeeded", 12, 7),
    ]
    compared = compare_scope_rows(derived, derived, same_release=True)
    assert len(compared) == 2 and all(row.standing == "matched" for row in compared)
    rows[1]["cut_origin"] = 8
    with pytest.raises(ValueError, match="cut custody"):
        derive_scope_coverage(
            ScopeWorklist.model_validate(dict(intents=[initial], settlements=rows)), completed=True
        )
