"""Protected recordless completion, custody and bounded reader controls."""

from typing import Any

import pytest
from psycopg import Error as PsycopgError
from sqlalchemy import event, select
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.invariant_failures import InvariantViolation
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.record_contracts import anchor_identity
from semantic.native_record_fixtures import private_source as private_source
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import (
    bypass_contributions as bypass,
)
from .native_record_fixtures import (
    complete_contributions as complete,
)
from .native_record_fixtures import (
    contribution_drafts as drafts,
)
from .native_record_fixtures import (
    contribution_envelope as envelope,
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
        ("synthetic_gap", "persisted source text"),
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
            # Deliberately mislabel a joined projection interval as continuous
            # native cell text. All content IDs are valid; native custody must
            # reject the fabricated quote across the synthetic separator.
            anchor.update(start=1, end=4, source_piece="2\n1")
        else:
            anchor["source_piece"] = "99"
        anchor["anchor_id"] = anchor_identity(anchor)
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


def test_native_score_state_missing_is_not_zero(private_source):
    case = private_source
    result = drafts(case)
    raw = envelope(case, result)
    proposal = raw["contributions"][1]
    proposal["score"] = {"kind": "integer", "integer": 0}
    proposal["contribution_id"] = contribution_identity(proposal)
    with case.writer.begin() as conn:
        with pytest.raises(DBAPIError, match="score availability"), conn.begin_nested():
            bypass(case, conn, raw)
        proposal["score_state"] = "native"
        proposal["contribution_id"] = contribution_identity(proposal)
        bypass(case, conn, raw)
    with case.writer.connect() as conn:
        values = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            source_view_id=case.view,
            include_details=True,
        ).contributions
        assert "score" not in values[0]
        assert values[1]["score_state"] == "native" and values[1]["score"] == {
            "kind": "integer",
            "integer": 0,
        }


@pytest.mark.parametrize("private_source", [{"include_blank_cell": True}], indirect=True)
def test_actual_blank_cell_subject_survives_native_read_and_source_first_assessment(private_source):
    from dataclasses import replace

    from corpus_structure.evaluate.operation_assessment import (
        OperationCase,
        OperationEvaluationFrame,
        score_cases,
    )
    from corpus_structure.methods.contribution_adapter import adapt_native_groups
    from corpus_structure.methods.record_assembly import native_table_groups
    from corpus_structure.semantic.operations import BoundReader
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice

    case = private_source
    with case.writer.connect() as conn:
        view = BoundReader(conn, case.run, case.prepared, analysis=False).source_view(case.view)
        source = replace(native_source_frame(view, ()), unit_ref="private-unit")
        context = NativeSourceContext(
            source,
            (),
            (SourceSlice(case.view, 0, len(source.text)),),
            "independently selected blank cell",
            "native-test",
            "exact native table subject",
        )
        groups = native_table_groups(
            context, table_pointer=case.table, cells=(2,), row_paths={}, header_paths={}
        )
        batch = adapt_native_groups(
            context, family="table", groups=groups, item_key="actual-blank-cell"
        )
    result = UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
        outcome=ObservationOutcome.PRODUCED,
        contribution_operations=batch.operations,
        contributions=batch.contributions,
        contribution_coordinate_texts=batch.coordinate_texts,
    )
    with case.writer.begin() as conn:
        complete(case, conn, result)
    specified = drafts(case).contributions
    assert specified is not None
    pin = specified[0]["pin"]
    anchor = dict(
        pin=pin, space="native", pointer=case.table + "/data/table_cells/2", precision="item"
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    scope = {key: value for key, value in anchor.items() if key != "anchor_id"}
    with case.writer.connect() as conn:
        inventory = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            source_view_id=case.view,
            anchor_scopes=(scope,),
            include_details=True,
        )
    proposal = next(
        value
        for value in inventory.contributions
        if value["kind"] == "proposal" and value["semantic_type"] == "table.cell_value"
    )
    assert (
        proposal["source_field_state"] == "unstated"
        and proposal["anchor_role"] == "inspection_subject"
    )
    assert not any(name in proposal["anchors"][0] for name in ("source_piece", "start", "end"))
    frame = OperationEvaluationFrame(
        unit="blank-cell",
        release_id=case.prepared.release_id,
        guideline_version="blank-1",
        rubric_version="blank-1",
        context_policy="native-only",
        operation_question="native-cell",
        operation_version="1",
        domain="controlled-table",
        direction="source_first",
        pin=pin,
        anchor_ids=(anchor["anchor_id"],),
        anchor_scopes=(scope,),
    )
    expected = OperationCase(
        case_id="blank-value",
        facet="source_field_state",
        candidate_selector={"semantic_type": "table.cell_value"},
        anchor_ids=frame.anchor_ids,
        inspected_scope="table/cell/2",
        source_state="unstated",
        judgment="supported",
        alternatives=({"source_field_state": "unstated", "anchor_role": "inspection_subject"},),
        explanation=(
            "The independently specified native cell text is blank; "
            "its inspection subject remains attributable."
        ),
        assessor_provenance={"source": "authored fixture"},
    )
    scored = score_cases(frame, (expected,), inventory.contributions)
    assert scored["cases"][0]["capture_outcome"] == "captured_structure"
    assert score_cases(frame, (expected,), ())["cases"][0]["error_category"] == "missing_output"


def local_draft(case):
    from dataclasses import replace

    from corpus_structure.methods.local_interpretation import local_question_operation

    result = drafts(case)
    assert result.contributions is not None and result.contribution_operations is not None
    local = local_question_operation(
        question="which unit attaches to this retained cell value?",
        contributions=result.contributions,
        dependency_ids=("retained-cell-source",),
    )
    return replace(result, contribution_operations=(*result.contribution_operations, local))


def test_native_local_question_retains_not_run_beside_useful_cell(private_source):
    case = private_source
    with case.writer.begin() as conn:
        complete(case, conn, local_draft(case))
        inventory = read_source_contributions(
            conn, prepared=case.prepared, run_id=case.run, include_details=True
        )
        questions = [op for op in inventory.operations if "local_interpretation" in op]
        assert len(questions) == 1
        report = questions[0]["local_interpretation"]
        assert report["outcome"] == "not_run" and report["probability_standing"] == "not_computed"
        assert len(report["contribution_ids"]) == len(inventory.contributions) == 2
        assert "result" not in report and "request" not in report
        assert conn.scalar(select(table("data.source_record").c.record_id).limit(1)) is None


@pytest.mark.parametrize("change", ["foreign_input", "forged_digest", "computed_not_run"])
def test_native_local_question_refuses_forged_input_or_probability(private_source, change):
    import json

    from corpus_structure.methods.record_readings import _digest
    from corpus_structure.semantic.observations import source_value

    case = private_source
    raw = envelope(case, local_draft(case))
    report = raw["contribution_operations"][-1]["local_interpretation"]
    if change == "foreign_input":
        report["contribution_ids"] = ["foreign"]
    elif change == "forged_digest":
        report["retained_input_digest"] = "f" * 64
    else:
        report["result"] = json.loads(json.dumps(source_value({"probability": 1})))
    report["seal"] = _digest({k: v for k, v in report.items() if k != "seal"})
    with case.writer.begin() as conn:
        with pytest.raises(DBAPIError, match="local interpretation"), conn.begin_nested():
            bypass(case, conn, raw)
        assert (
            conn.scalar(
                select(table("ops.task").c.status).where(table("ops.task").c.id == case.task)
            )
            == "running"
        )


def test_native_local_question_seals_supplied_model_result_without_admission(private_source):
    from dataclasses import replace

    from corpus_structure.methods.local_interpretation import local_question_operation
    from corpus_structure.semantic.record_interpretation import CandidateSelection
    from semantic.test_local_interpretation import local_request

    case = private_source
    result = drafts(case)
    assert result.contributions is not None and result.contribution_operations is not None
    arguments = dict(
        question="actor versus object under explicit fixture model",
        contributions=result.contributions,
        dependency_ids=("source",),
    )
    scope = local_question_operation(**arguments)["operation_key"]
    request = replace(local_request(), selection=CandidateSelection(scope, ("source",)))
    operation = local_question_operation(**arguments, request=request)
    result = replace(result, contribution_operations=(*result.contribution_operations, operation))
    with case.writer.begin() as conn:
        complete(case, conn, result)
        inventory = read_source_contributions(
            conn, prepared=case.prepared, run_id=case.run, include_details=True
        )
        local = [
            op["local_interpretation"]
            for op in inventory.operations
            if "local_interpretation" in op
        ]
        assert len(local) == 1 and local[0]["outcome"] == "completed"
        assert local[0]["probability_standing"] == "provisional_candidate_relative"
        assert local[0]["request_digest"] and local[0]["result_digest"]
        assert conn.scalar(select(table("data.source_record").c.record_id).limit(1)) is None


def test_native_local_question_refuses_omitted_consumed_dependencies(private_source):
    from dataclasses import replace

    from corpus_structure.methods.local_interpretation import local_question_operation
    from corpus_structure.methods.record_readings import _digest

    case = private_source
    result = drafts(case)
    assert result.contributions is not None and result.contribution_operations is not None
    products = []
    for original in result.contributions:
        row: dict[str, Any] = dict(original, computation_dependencies=("source-profile",))
        row["contribution_id"] = contribution_identity(row)
        products.append(row)
    local = local_question_operation(
        question="which unit?", contributions=products, dependency_ids=("source-profile", "source")
    )
    result = replace(
        result,
        contributions=tuple(products),
        contribution_operations=(*result.contribution_operations, local),
    )
    raw = envelope(case, result)
    report = raw["contribution_operations"][-1]["local_interpretation"]
    report["dependencies"] = ["source"]
    report["seal"] = _digest({k: v for k, v in report.items() if k != "seal"})
    with case.writer.begin() as conn:
        with pytest.raises(DBAPIError, match="local interpretation"), conn.begin_nested():
            bypass(case, conn, raw)
        assert (
            conn.scalar(
                select(table("ops.task").c.status).where(table("ops.task").c.id == case.task)
            )
            == "running"
        )


def test_native_local_question_refuses_resealed_invalid_numerical_products(private_source):
    from copy import deepcopy
    from dataclasses import replace

    from corpus_structure.methods.local_interpretation import local_question_operation
    from corpus_structure.methods.record_readings import _digest
    from corpus_structure.semantic.observations import source_python, source_value
    from corpus_structure.semantic.record_interpretation import CandidateSelection
    from semantic.test_local_interpretation import local_request

    case = private_source
    result = drafts(case)
    assert result.contributions is not None and result.contribution_operations is not None
    arguments = dict(
        question="numerical result forgery controls",
        contributions=result.contributions,
        dependency_ids=("source",),
    )
    scope = local_question_operation(**arguments)["operation_key"]
    request = replace(local_request(), selection=CandidateSelection(scope, ("source",)))
    operation = local_question_operation(**arguments, request=request)
    result = replace(result, contribution_operations=(*result.contribution_operations, operation))
    original = envelope(case, result)
    with case.writer.begin() as conn:
        for mutation in (
            "probability",
            "marginal_decision",
            "normalization",
            "assignment",
            "factor_size",
        ):
            raw = deepcopy(original)
            report = raw["contribution_operations"][-1]["local_interpretation"]
            req, output = source_python(report["request"]), source_python(report["result"])
            if mutation == "probability":
                output["marginals"][0]["probability"] = 2
            if mutation == "marginal_decision":
                output["marginals"][0]["decision"] = "foreign"
            if mutation == "normalization":
                output["marginals"][0]["probability"] = 0
            if mutation == "assignment":
                output["alternatives"][0]["choices"][0]["candidate"] = "foreign"
            if mutation == "factor_size":
                req["potentials"][0]["values"].pop()
            for key, value in (("request", req), ("result", output)):
                report[key] = source_value(value)
                report[key + "_digest"] = _digest(report[key])
            report["seal"] = _digest({k: v for k, v in report.items() if k != "seal"})
            with pytest.raises(DBAPIError, match="local interpretation"), conn.begin_nested():
                bypass(case, conn, raw)


def test_native_located_component_custody_and_basis_refusal(private_source):
    from copy import deepcopy
    from dataclasses import replace

    case = private_source
    result = drafts(case)
    assert result.contributions is not None
    row = dict(deepcopy(result.contributions[1]))
    aid = row["anchors"][0]["anchor_id"]
    row["computation_dependencies"] = ("retained-annotation",)
    row["component"] = dict(
        protocol="witnessed-component-1",
        kind="located_role",
        question="inspect_cell",
        question_version="1",
        scope="native-cell",
        interpretation="unassessed",
        dependencies=("retained-annotation",),
        bases=(dict(kind="matched_cue", dependencies=("retained-annotation",), anchor_ids=(aid,)),),
        rule="native-cell-control",
        variant="named",
        roles=(
            dict(
                role="value", anchor_ids=(aid,), head_token=0, expansion="exact", outcome="complete"
            ),
        ),
    )
    row["contribution_id"] = contribution_identity(row)
    result = replace(result, contributions=(result.contributions[0], row))
    raw = envelope(case, result)
    invalid = deepcopy(raw)
    invalid["contributions"][1]["component"]["bases"][0]["dependencies"] = ["unavailable-premise"]
    invalid["contributions"][1]["contribution_id"] = contribution_identity(
        invalid["contributions"][1]
    )
    with case.writer.begin() as conn:
        with pytest.raises(DBAPIError) as caught, conn.begin_nested():
            bypass(case, conn, invalid)
        error = caught.value.orig
        assert isinstance(error, PsycopgError)
        assert error.sqlstate == "23514"
        assert error.diag.message_primary == (
            "component basis has unavailable dependency or source anchor"
        )
        assert (
            conn.scalar(
                select(table("ops.task").c.status).where(table("ops.task").c.id == case.task)
            )
            == "running"
        )
        assert not conn.execute(select(table("kb.source_contribution"))).first()
        complete(case, conn, result)
    with case.writer.connect() as conn:
        actual = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            source_view_id=case.view,
            include_details=True,
        )
    components = [c["component"] for c in actual.contributions if "component" in c]
    assert len(components) == 1 and components[0]["roles"][0]["role"] == "value"
