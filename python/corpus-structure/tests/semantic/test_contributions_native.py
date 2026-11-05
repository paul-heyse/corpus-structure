"""Protected recordless completion, custody and bounded reader controls."""

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.invariant_failures import InvariantViolation
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import bind_result
from corpus_structure.semantic.operations import complete_task, complete_unit_result, seal_cut
from corpus_structure.semantic.record_contracts import anchor_identity
from semantic.test_private_records import candidate
from semantic.test_private_records import private_source as private_source


def drafts(case):
    record = candidate(case)
    anchor = record["anchors"][0]
    # This fixture's independently authored native cell spells exactly 12 at [0,2).
    assert anchor["pointer"] == case.table + "/data/table_cells/0"
    assert anchor["start"] == 0 and anchor["end"] == 2 and anchor["source_piece"] == "12"
    occurrence = dict(
        contract="RetainedContributionSemantics",
        kind="occurrence",
        semantic_type="table.cell_value",
        operation_key="locate-cell-1",
        item_key="cell/0",
        pin=record["pin"],
        anchors=(anchor,),
        occurrence_id=occurrence_identity((anchor,)),
        disposition="unassessed",
        standing="retained_private",
        score_state="missing",
    )
    occurrence["contribution_id"] = contribution_identity(occurrence)
    proposal = dict(
        occurrence,
        kind="proposal",
        semantic_type="unresolved.unit",
        item_key="unit/0",
        disposition="unresolved",
    )
    proposal["contribution_id"] = contribution_identity(proposal)
    operations = (
        dict(
            operation_key="locate-cell-1",
            question="inspect_cell",
            operation_version="1",
            outcome="succeeded",
            inspected_count=1,
            emitted_count=2,
        ),
        dict(
            operation_key="absent-1",
            question="inspect_caption",
            operation_version="1",
            outcome="empty",
            inspected_count=1,
            emitted_count=0,
        ),
    )
    coordinates = (dict(pin=record["pin"], space="native", pointer=anchor["pointer"], text="12"),)
    result = UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
        outcome=ObservationOutcome.PRODUCED,
        contribution_operations=operations,
        contributions=(occurrence, proposal),
        contribution_coordinate_texts=coordinates,
    )
    return result


def complete(case, conn, result):
    return complete_unit_result(
        conn,
        task_id=case.task,
        attempt=case.held.attempt,
        holder="records",
        prepared=case.prepared,
        method=case.method,
        configuration_hash="private-config",
        source="private-unit",
        result=result,
    )


def envelope(case, result):
    return bind_result(
        case.prepared,
        source="private-unit",
        method=case.method.name,
        operation_version="1",
        configuration_hash="private-config",
        input_hash="private-input-hash",
        invocation_key=case.task_row["invocation_key"],
        result=result,
    ).model_dump(mode="json", exclude={"observations"})


def bypass(case, conn, raw):
    return complete_task(
        conn,
        task_id=case.task,
        attempt=case.held.attempt,
        holder="records",
        prepared=case.prepared,
        observations=(),
        outcome="done",
        envelope=raw,
    )


def test_native_recordless_completion_reopen_and_zero_output_operations(private_source):
    case = private_source
    result = drafts(case)
    with case.writer.begin() as conn:
        complete(case, conn, result)
        cut = seal_cut(conn, case.run, "contribution-cut", final=False)
    with case.writer.connect() as conn:
        inventory = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            cut_id=cut,
            source_view_id=case.view,
            include_details=True,
        )
        assert len(inventory.operations) == 2
        assert [op["emitted_count"] for op in inventory.operations] == [2, 0]
        assert [row["semantic_type"] for row in inventory.contributions] == [
            "table.cell_value",
            "unresolved.unit",
        ]
        assert all(
            "score" not in row and row["standing"] == "retained_private"
            for row in inventory.contributions
        )
        assert conn.scalar(select(table("data.source_record").c.record_id).limit(1)) is None
        assert len({row["occurrence_id"] for row in inventory.contributions}) == 1


def test_native_anchorless_occurrence_spoof_refuses_at_protected_completion(private_source):
    case = private_source
    raw = envelope(case, drafts(case))
    row = raw["contributions"][1]
    row.pop("anchors")
    row["contribution_id"] = contribution_identity(row)
    with case.writer.begin() as conn:
        with (
            pytest.raises(DBAPIError, match="unlocated contribution cannot claim"),
            conn.begin_nested(),
        ):
            bypass(case, conn, raw)
        assert (
            conn.scalar(
                select(table("ops.task").c.status).where(table("ops.task").c.id == case.task)
            )
            == "running"
        )
        assert not conn.execute(select(table("kb.source_contribution"))).first()


@pytest.mark.parametrize(
    "change,reason",
    [
        ("foreign_pin", "pin differs"),
        ("missing_endpoint", "endpoint unavailable"),
        ("synthetic_gap", "source pieces"),
        ("wrong_text", "persisted source text"),
    ],
)
def test_native_contribution_source_and_closure_refusals(private_source, change, reason):
    case = private_source
    raw = envelope(case, drafts(case))
    row = raw["contributions"][1]
    if change == "foreign_pin":
        row["pin"] = dict(row["pin"], source_view_id=case.other_view)
    elif change == "missing_endpoint":
        row["kind"] = "relation"
        row["endpoints"] = [
            dict(role="head", contribution_id="absent"),
            dict(role="tail", contribution_id=raw["contributions"][0]["contribution_id"]),
        ]
    else:
        anchor = row["anchors"][0]
        if change == "synthetic_gap":
            anchor.update(space="selected_projection", start=1, end=4, source_piece="2\n1")
        else:
            anchor["source_piece"] = "99"
        anchor["anchor_id"] = anchor_identity(anchor)
        if change != "synthetic_gap":
            row["occurrence_id"] = occurrence_identity(row["anchors"])
    row["contribution_id"] = contribution_identity(row)
    with case.writer.begin() as conn, pytest.raises((InvariantViolation, DBAPIError)) as error:
        bypass(case, conn, raw)
    assert reason in str(error.value.__cause__ or error.value)


def test_detail_byte_budget_preflights_before_hydration(private_source):
    case = private_source
    with case.writer.begin() as conn:
        complete(case, conn, drafts(case))
    statements = []
    with case.writer.connect() as conn:

        def capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(conn, "before_cursor_execute", capture)
        try:
            with pytest.raises(ValueError, match="before hydration"):
                read_source_contributions(
                    conn,
                    prepared=case.prepared,
                    run_id=case.run,
                    source_view_id=case.view,
                    include_details=True,
                    max_bytes=1,
                )
        finally:
            event.remove(conn, "before_cursor_execute", capture)
    assert any("sum(octet_length" in statement for statement in statements)
    assert not any(
        statement.lstrip().startswith("SELECT r.task_id,jsonb_agg") for statement in statements
    )


def test_scope_and_endpoint_indexes_select_before_detail(private_source):
    from dataclasses import replace

    case = private_source
    result = drafts(case)
    assert result.contributions is not None
    assert result.contribution_operations is not None
    occurrence, proposal = result.contributions
    relation = dict(
        proposal,
        kind="relation",
        semantic_type="table.unit_attachment",
        item_key="attachment",
        anchors=(),
        endpoints=(
            {"role": "cell_value", "contribution_id": occurrence["contribution_id"]},
            {"role": "unit", "contribution_id": proposal["contribution_id"]},
        ),
    )
    relation.pop("occurrence_id")
    relation["contribution_id"] = contribution_identity(relation)
    operation = dict(result.contribution_operations[0], emitted_count=3)
    result = replace(
        result,
        contributions=(*result.contributions, relation),
        contribution_operations=(operation, result.contribution_operations[1]),
    )
    with case.writer.begin() as conn:
        complete(case, conn, result)
    scope = {
        key: value
        for key, value in occurrence["anchors"][0].items()
        if key in {"pin", "space", "pointer", "precision", "start", "end"}
    }
    with case.writer.connect() as conn:
        selected = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            source_view_id=case.view,
            kind="relation",
            anchor_scopes=(scope,),
            anchor_endpoint_roles=("cell_value",),
            include_details=True,
        )
        assert [row["contribution_id"] for row in selected.contributions] == [
            relation["contribution_id"]
        ]
        unselected = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            source_view_id=case.view,
            kind="relation",
            anchor_scopes=(scope,),
            include_details=True,
        )
        assert unselected.contributions == ()
        endpoint = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            source_view_id=case.view,
            contribution_ids=(proposal["contribution_id"],),
            include_details=True,
        )
        assert [row["contribution_id"] for row in endpoint.contributions] == [
            proposal["contribution_id"]
        ]
