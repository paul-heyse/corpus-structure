"""Current PM2 decoder/native custody; controlled replies give no provider credit."""

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest
from psycopg.errors import RaiseException
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.declared_candidate_products import candidate_member_values
from corpus_structure.semantic.observations import source_python
from semantic.current_pdf_source_support import (
    admit_current_target,
    current_consumer_request,
    selected_current_sources,
)
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.current_pm2_native_support import (
    execute,
    parser_recipe,
    projection_recipe,
    projection_request,
    provider_recipe,
    pure_source,
    register,
    reports,
    table_source,
)
from semantic.current_pm2_native_support import projection_prepared as projection_prepared
from semantic.current_pm2_projection_fixture import project
from semantic.data_operation_kernel_support import prepare_kernel


def test_current_decoder_keeps_empty_raw_answer_and_unresolved_question_distinct(
    projection_prepared,
):
    assert all(item.complete for item in projection_prepared.model.implementation_slices)
    value, frame, context = pure_source(projection_prepared)
    outputs = [
        project(
            projection_prepared.prepared,
            projection_prepared.model,
            value.value,
            frame.pin.values(),
            context,
            mode,
        )
        for mode in ("empty", "mixed")
    ]
    for report, count in zip(outputs, (1, 3), strict=True):
        rows = candidate_member_values(report, candidate_type="contribution")
        assert len(rows) == count
        missing = next(row for row in rows if row["item_key"] == "interpretation:missing")
        assert source_python(missing["value"])["state"] == "unresolved"
        assert not missing["anchors"] and not missing.get("occurrence_id")
    assert json.loads(outputs[0]["diagnostics_json"])["native_reply"]["outcome"] == "empty"
    assert outputs[0]["inspection_outcome"] == "produced"
    occurrence = next(
        row
        for row in candidate_member_values(outputs[1], candidate_type="contribution")
        if row["kind"] == "occurrence"
    )
    assert [(a["start"], a["end"], a["source_piece"]) for a in occurrence["anchors"]] == [
        (0, 2, "12")
    ]


def test_current_field_inversion_refuses_wrong_field_and_preserves_ordered_input_identity(
    projection_prepared,
):
    from corpus_structure.methods.pm2_result import d1_evidence, pm2_input_digest
    from corpus_structure.methods.pm2_source import D1SourceField, MappedSource
    from corpus_structure.semantic.model_characterization import prepare_model_scope

    _, frame, _ = pure_source(projection_prepared)
    scope = prepare_model_scope(frame, (0, 2), (0, 2))
    request = dict(state=dict(source="12"), questions={"second": {}, "first": {}})
    reply = dict(
        outcome="succeeded",
        rendered_state='{"source":"12"}',
        native=dict(answers={"value": dict(span=[11, 13], text="12", path="/source")}),
    )
    field = D1SourceField(reply["rendered_state"], "/source", 11, 13)
    located = d1_evidence(scope.mapping, reply, field=field, source_path="/source", native=True)
    assert isinstance(located["value"], MappedSource)
    assert located["value"].anchors[0]["source_piece"] == "12"
    with pytest.raises(ValueError, match="authorized source path"):
        d1_evidence(scope.mapping, reply, field=field, source_path="/candidate", native=True)
    with pytest.raises(ValueError, match="rendered state"):
        d1_evidence(
            scope.mapping,
            {**reply, "rendered_state": '{"source":"21"}'},
            field=field,
            source_path="/source",
            native=True,
        )
    dimensions = dict(question="locate_literal", operation_version="3", source_path="/source")
    digest = pm2_input_digest(scope.mapping, {"provider": "controlled"}, request, **dimensions)
    changed = deepcopy(request)
    changed["questions"] = dict(reversed(tuple(request["questions"].items())))
    assert digest != pm2_input_digest(
        scope.mapping, {"provider": "controlled"}, changed, **dimensions
    )
    assert digest != pm2_input_digest(
        scope.mapping,
        {"provider": "controlled"},
        request,
        **(dimensions | {"source_path": "/candidate"}),
    )


def test_current_original_projection_cannot_mint_native_occurrence(projection_prepared):
    value, frame, context = pure_source(projection_prepared, "x + y", native_text="x+y")
    report = project(
        projection_prepared.prepared,
        projection_prepared.model,
        value.value,
        frame.pin.values(),
        context,
        "literal",
    )
    rows = candidate_member_values(report, candidate_type="contribution")
    assert not any(row["kind"] == "occurrence" or row.get("occurrence_id") for row in rows)
    assert source_python(rows[0]["value"])["state"] == "unsupported"
    assert (
        json.loads(report["diagnostics_json"])["native_reply"]["native"]["answers"]["value"]["text"]
        == "x + y"
    )


def test_literal_provider_recipe_has_checked_profile_without_claiming_execution(tmp_path):
    from corpus_structure.methods.native_profiles import pm2_selection

    directory = tmp_path / "provider-prepared"
    directory.mkdir()
    # Declared fixture metadata only; no provider process or native publication.
    selected = pm2_selection("d1", tmp_path, {"controlled": "runtime"}, {})
    prepared = prepare_kernel(provider_recipe(tmp_path, selected), directory=directory)
    operation = prepared.model.operation("fixture.pm2_literal_provider")
    assert operation.subject == "original-source-view"
    assert operation.replicate_policy == "retained-observation-single-result"
    assert all(item.complete for item in prepared.model.implementation_slices)
    assert (
        "fixture.pm2_literal_provider" in json.loads(prepared.runtime.manifest)["provider_profiles"]
    )


def test_controlled_cell_mapping_and_unresolved_question_survive_current_native_read(
    scenario_seeds, tmp_path
):
    from corpus_structure.semantic.data_operation_service import read_data_demand

    with table_source(scenario_seeds) as source:
        kernel = admit_current_target(source, projection_recipe(tmp_path), tmp_path / "consumer")
        ((row, original),) = selected_current_sources(source)
        cell = next(piece for piece in original["pieces"] if piece.get("cell_index") == 0)
        assert original["text"][cell["start"] : cell["end"]] == "12"
        for mode in ("empty", "mixed"):
            demand = register(kernel, projection_request(kernel, row, mode=mode))
            assert execute(kernel, demand).receipt_count == 1
            (product,), selected = reports(kernel, demand)
            report = product["body"]
            missing = next(
                item
                for item in candidate_member_values(report, candidate_type="contribution")
                if item["item_key"] == "interpretation:missing"
            )
            assert source_python(missing["value"])["state"] == "unresolved"
            assert not missing["anchors"] and not missing.get("occurrence_id")
            assert json.loads(report["diagnostics_json"])["native_reply"]["outcome"] == (
                "empty" if mode == "empty" else "succeeded"
            )
        rows = candidate_member_values(product["body"], candidate_type="contribution")
        assert len(rows) == 3
        (anchor,) = next(item for item in rows if item["kind"] == "occurrence")["anchors"]
        assert (
            anchor["space"],
            anchor["pointer"],
            anchor["start"],
            anchor["end"],
            anchor["source_piece"],
        ) == ("native", cell["item_ref"] + "/data/table_cells/0", 0, 2, "12")
        assert (
            json.loads(product["body"]["diagnostics_json"])["locations"]["value"][
                "selected_projection"
            ][0]["source_piece"]
            == "12"
        )
        assert execute(kernel, demand).receipt_count == 0
        (resumed,), _ = reports(kernel, demand)
        assert resumed["product_id"] == product["product_id"]
        with (
            kernel.purpose("read").begin() as connection,
            pytest.raises(DBAPIError, match="read acquisition pins differ") as invalid_read,
            connection.begin_nested(),
        ):
            read_data_demand(
                connection,
                demand,
                continuation=dict(
                    demand_id=demand,
                    read_id=selected.cut.record["read_id"],
                    read_snapshot="0:0:",
                    view="products",
                ),
            )
        assert isinstance(invalid_read.value.orig, RaiseException)
        assert invalid_read.value.orig.sqlstate == "P0001"


def test_original_spelling_remains_inspectable_without_current_native_occurrence(
    current_pdf_source_factory, tmp_path
):
    with current_pdf_source_factory((("text", "x+y", "x + y", None),)) as source:
        kernel = admit_current_target(source, projection_recipe(tmp_path), tmp_path / "consumer")
        ((row, original),) = selected_current_sources(source)
        assert original["text"] == "x + y"
        demand = register(kernel, projection_request(kernel, row, mode="literal"))
        execute(kernel, demand)
        (product,), _ = reports(kernel, demand)
        rows = candidate_member_values(product["body"], candidate_type="contribution")
        assert not any(item["kind"] == "occurrence" or item.get("occurrence_id") for item in rows)
        assert (
            json.loads(product["body"]["diagnostics_json"])["native_reply"]["native"]["answers"][
                "value"
            ]["text"]
            == "x + y"
        )


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_seventeen_question_refusal_stays_at_provider_boundary():
    from corpus_structure.settings import Settings
    from semantic.native_provider_support import actual_provider

    request = dict(
        state=dict(source="12"),
        questions={
            f"read_{index}": dict(type="text", instructions="Copy the numeral exactly.")
            for index in range(17)
        },
    )
    with actual_provider(
        "d1",
        Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"]),
        endpoint=Settings().nemotron.endpoint,
    ) as provider:
        reply = provider.infer(request, check_active=lambda: None)
    assert {name: reply[name] for name in ("outcome", "reason", "limit")} == dict(
        outcome="limited", reason="question_count", limit=16
    )
    assert "native" not in reply


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_literal_provider_answer_survives_current_selected_read(scenario_seeds, tmp_path):
    from corpus_structure.methods.native_profiles import pm2_selection, preflight_native_runtime
    from semantic.current_pm2_provider_fixture import OPERATION as ACTUAL

    assets = Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])
    checked = preflight_native_runtime("d1", assets)
    selected = pm2_selection("d1", assets, checked["runtime_identity"], checked["assets"])
    with table_source(scenario_seeds) as source:
        kernel = admit_current_target(
            source, provider_recipe(tmp_path, selected), tmp_path / "consumer"
        )
        ((row, original),) = selected_current_sources(source)
        cell = next(piece for piece in original["pieces"] if piece.get("cell_index") == 0)
        request = projection_request(kernel, row, mode="literal", operation=ACTUAL).model_copy(
            update={"inference": "actual-fixed-literal-panel"}
        )
        demand = register(kernel, request)
        assert execute(kernel, demand).receipt_count == 1
        (product,), snapshot = reports(kernel, demand, operation=ACTUAL)
        diagnostics = json.loads(product["body"]["diagnostics_json"])
        assert diagnostics["controlled_transport"] is False
        answer = diagnostics["native_reply"]["native"]["answers"]["value"]
        a, b = answer["span"]
        rendered = diagnostics["native_reply"]["rendered_state"]
        assert json.loads(rendered) == {"source": "12"}
        assert b - a == 2 and rendered[a:b] == "12"
        assert answer["text"] == "12" and answer["path"] == "/source"
        occurrences = [
            item
            for item in candidate_member_values(product["body"], candidate_type="contribution")
            if item["kind"] == "occurrence"
        ]
        assert len(occurrences) == 1
        (anchor,) = occurrences[0]["anchors"]
        assert (anchor["pointer"], anchor["start"], anchor["end"], anchor["source_piece"]) == (
            cell["item_ref"] + "/data/table_cells/0",
            0,
            2,
            "12",
        )
        use = next(item for item in snapshot.record["uses"] if item["use_id"] == product["use_id"])
        with source.kernel.clone.admin.connect() as connection:
            from sqlalchemy import text

            evidence = connection.scalar(
                text(
                    "SELECT intent.payload->'execution_evidence' FROM ops.data_derivation episode JOIN ops.data_completion_intent intent ON intent.id=episode.intent_id WHERE episode.id=:episode"
                ),
                {"episode": product["derivation_id"]},
            )
        assert evidence["request_id"] == use["request_id"]
        assert len(evidence["cpu_receipts"]) == 1
        assert evidence["provider_receipts"]
        assert all(
            item["provider"] == "d1"
            for receipt in evidence["provider_receipts"]
            for item in receipt["physical"]
        )
        assert execute(kernel, demand).receipt_count == 0


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_current_d1_limitation_is_inspectable_beside_successful_products(
    current_pdf_source_factory, tmp_path
):
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError

    long_text = " ".join(["12"] * 6000)
    oversized = " ".join(["unexamined"] * 7000)
    with current_pdf_source_factory(
        (
            ("text", "12", "12", None),
            ("text", long_text, long_text, None),
            ("text", oversized, oversized, None),
        )
    ) as source:
        kernel = admit_current_target(
            source,
            parser_recipe(Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])),
            tmp_path / "consumer",
        )
        demand = register(
            kernel,
            current_consumer_request(
                source, kernel, ("text.d1_source/source-native",), discover=True
            ),
        )
        with pytest.raises(NativeDemandExecutionError):
            execute(kernel, demand)
        from semantic.current_pm2_native_support import page

        selected = page(kernel, demand)
        (failed,) = [
            item
            for item in selected.record["attempt_failures"]
            if "d1_limitation" in item["failure"]
        ]
        diagnostic = failed["failure"]["d1_limitation"]
        assert diagnostic["native_reply"]["outcome"] == "limited"
        assert diagnostic["native_reply"]["reason"] == "packed_row_tokens"
        assert max(diagnostic["native_reply"]["row_tokens"]) > 4096
        assert json.loads(diagnostic["request_json"])["state"]["source"] == long_text
        assert diagnostic["inspected_count"] == diagnostic["emitted_count"] == 0
        assert diagnostic["standing"] == "unperformed-question-inspection"
        assert not {"members", "inspection_outcome"} & diagnostic.keys()
        assert diagnostic["execution_evidence"]["provider_receipts"][0]["physical"]
        assert all(
            not item["products"]
            for item in selected.record["uses"]
            if item.get("request_id") == failed["request_id"]
        )
        values, _ = reports(kernel, demand, operation="text.d1_source/source-native")
        assert {item["role"] for item in values} == {"result", "candidates"}
        assert all(
            item["body"].get("source_pin", {}).get("subject") != diagnostic["source_pin"]["subject"]
            for item in values
        )
        ineligible_subject = next(
            row["subject"]
            for row, body in selected_current_sources(source)
            if len(body["text"]) > 65536
        )
        ineligible = {
            item["role"]: item["body"]
            for item in values
            if item["body"]["source_pin"]["subject"] == ineligible_subject
        }
        assert set(ineligible) == {"result", "candidates"}
        assert ineligible["result"]["outcome"] == "partial"
        assert ineligible["result"]["observations"] == []
        assert all(
            not item["examined"] and item["unexamined"] and item["outcome"] == "partial"
            for item in ineligible["result"]["coverage"]
        )
        assert ineligible["candidates"]["members"] == ineligible["candidates"]["operations"] == []
        assert ineligible["candidates"]["coverage"][0]["outcome"] == "unsupported"
