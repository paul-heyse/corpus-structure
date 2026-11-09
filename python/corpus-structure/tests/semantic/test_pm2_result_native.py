"""Native completion and retained read over the private PM2 source boundary."""

import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import select, text

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods import pm2_native
from corpus_structure.methods.pm2_result import pm2_input_digest, pm2_unit_result
from corpus_structure.methods.pm2_source import D1SourceField, PM2SourceMap, SourceMapSegment
from corpus_structure.methods.pm2_worker import open_pm2_worker
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.pm2 import settle_pm2_claim
from corpus_structure.semantic._operation_calls import select_source_view
from corpus_structure.semantic.claim_lifetime import maintained_claims
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.operations import (
    BoundReader,
    OperationConflict,
    binding_of,
    claim_tasks,
    complete_unit_result,
    create_run,
    create_task,
)
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings
from semantic.native_record_fixtures import private_source as private_source
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import complete_contributions

SOURCE_PATH = "/source"


def _claim(case, digest, *, view_id=None, unit_key="private-unit"):
    with case.writer.begin() as conn:
        config = case.task_row["method_config_id"]
        task = create_task(
            conn,
            run_id=case.run,
            config_id=config,
            stage="record",
            unit_type="source_view",
            unit_id=case.view if view_id is None else view_id,
            unit_key=unit_key,
            input_hash=digest,
        )
        (held,) = claim_tasks(conn, run_id=case.run, config_id=config, holder="records")
    assert held.task_id == task
    return held


@pytest.mark.parametrize(
    "private_source",
    [{"sibling_references": ("The sensor records each request. It writes a receipt.",)}],
    indirect=True,
)
def test_native_mapped_answer_and_limited_operation_survive_a_retained_read(
    private_source, tmp_path, semantic_db_engine
):
    case = private_source
    with case.writer.connect() as conn:
        view = BoundReader(conn, case.run, case.prepared, analysis=False).source_view(case.view)
    source = replace(native_source_frame(view, ()), unit_ref="private-unit")
    cell = next(piece for piece in view.pieces if piece.get("cell_index") == 0)
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(case.view, cell["start"], cell["end"]),),
        "exact read",
        "native-test",
        "independently specified first cell",
    )
    assert context.text == "12"
    mapping = PM2SourceMap(context, context.text, (SourceMapSegment(0, 2, 0),), ())
    request = {
        "state": {"source": "12"},
        "questions": {"value": {"type": "text", "instructions": "Copy the numeral as written."}},
    }
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit")
    with case.writer.begin() as conn:
        complete_contributions(case, conn, UnitResult(ref=ref, outcome=ObservationOutcome.EMPTY))
    options = {
        "question": "locate_literal",
        "operation_version": "1",
        "source_path": SOURCE_PATH,
    }
    oversized = {
        "state": request["state"],
        "questions": {f"read_{index}": request["questions"]["value"] for index in range(17)},
    }
    assets = os.environ.get("CORPUS_PM2_NATIVE_TEST_ASSETS")
    if assets:
        # Opt-in native pass uses the same PostgreSQL fixture and public read as the
        # deterministic case. CUDA takes the configured shared device handoff.
        profile_file = tmp_path / "d1.json"
        profile_file.write_text(json.dumps({"provider": "d1", "device": "cuda", "assets": assets}))
        with open_pm2_worker(
            python=Path(sys.executable),
            script=Path(pm2_native.__file__),
            profile=profile_file,
            device="cuda",
            nemotron_endpoint=Settings().nemotron.endpoint,
        ) as worker:
            profile = worker.startup
            digest = pm2_input_digest(mapping, profile, request, **options)
            held = _claim(case, digest)
            limited_held = _claim(case, pm2_input_digest(mapping, profile, oversized, **options))
            with maintained_claims(
                case.writer, (held, limited_held), "records", interval=0.1
            ) as owner:
                for claim, selected in ((held, request), (limited_held, oversized)):
                    settle_pm2_claim(
                        owner,
                        claim,
                        worker,
                        mapping,
                        selected,
                        expected_profile=profile,
                        prepared=case.prepared,
                        method=case.method,
                        configuration_hash="private-config",
                        **options,
                    )
        _settle_reassigned_dipo(case, tmp_path, semantic_db_engine, assets)
    else:
        profile = {"provider": "d1", "checkpoint": "controlled-test", "dtype": "bfloat16"}
        rendered = '{"source":"12"}'
        reply = {
            "outcome": "succeeded",
            "rendered_state": rendered,
            "native": {"answers": {"value": {"span": [11, 13], "text": "12", "path": SOURCE_PATH}}},
        }
        field = D1SourceField(rendered, SOURCE_PATH, 11, 13)
        digest = pm2_input_digest(mapping, profile, request, **options)
        with pytest.raises(ValueError, match="admitted task input"):
            pm2_unit_result(
                ref,
                mapping,
                profile=profile,
                request=request,
                reply=reply,
                field=field,
                input_digest="wrong-input",
                **options,
            )
        result = pm2_unit_result(
            ref,
            mapping,
            profile=profile,
            request=request,
            reply=reply,
            field=field,
            input_digest=digest,
            **options,
        )
        held = _claim(case, digest)
        with case.writer.begin() as conn:
            _complete(case, conn, held, result)

    assert digest != pm2_input_digest(mapping, {**profile, "dtype": "float32"}, request, **options)
    assert digest != pm2_input_digest(
        mapping, profile, request, **(options | {"source_path": "/candidate"})
    )
    original = {"state": request["state"], "questions": {"first": 1, "second": 2}}
    changed = {"state": request["state"], "questions": {"second": 2, "first": 1}}
    assert pm2_input_digest(mapping, profile, original, **options) != pm2_input_digest(
        mapping, profile, changed, **options
    )
    if not assets:
        limited_digest = pm2_input_digest(mapping, profile, oversized, **options)
        limited_held = _claim(case, limited_digest)
        with case.writer.begin() as conn:
            limited = pm2_unit_result(
                ref,
                mapping,
                profile=profile,
                request=oversized,
                reply={"outcome": "limited", "reason": "question_count"},
                input_digest=limited_digest,
                **options,
            )
            _complete(case, conn, limited_held, limited)
    finalize_bound_run(case.writer, case.run, "pm2-private-read")
    with read_snapshot(case.writer) as conn:
        page = serve_contributions(
            conn,
            ContributionRequest(run_id=case.run, source_view_id=case.view, include_details=True),
        )
        if assets:
            second_page = serve_contributions(
                conn,
                ContributionRequest(
                    run_id=case.run,
                    source_view_id=case.other_view,
                    include_details=True,
                ),
            )
            assert second_page.inventory_counts["contributions"] > 0
        retained = table("ops.task_result")
        detail = conn.scalar(select(retained.c.body).where(retained.c.task_id == held.task_id))
    assert page.inventory_counts["contributions"] == 1
    anchor = next(
        cast(dict[str, Any], item["row"])["anchors"][0]
        for item in page.items
        if item["population"] == "contribution"
    )
    assert {
        cast(dict[str, Any], item["row"])["outcome"]
        for item in page.items
        if item["population"] == "operation"
    } == {
        "succeeded",
        "limited",
    }
    assert (anchor["space"], anchor["pointer"], anchor["start"], anchor["end"]) == (
        "native",
        case.table + "/data/table_cells/0",
        0,
        2,
    )
    report = source_python(detail["parse_detail"])["pm2_native"]
    assert report["locations"]["value"]["selected_projection"][0]["source_piece"] == "12"
    assert report["input_digest"] == digest
    with case.writer.begin() as conn:
        binding = binding_of(conn, case.run)
        comparison = create_run(
            conn,
            project_id=case.project_id,
            binding=replace(
                binding,
                dependencies=canonical_bytes(
                    {
                        **json.loads(binding.dependencies),
                        "local_semantic_admission": {"policy": "changed"},
                    }
                ),
            ),
            kind="slice",
            options={},
            code_commit="pm2-input-check",
            prepared=case.prepared,
        )
        select_source_view(
            conn,
            run_id=comparison,
            source_run_id=case.run,
            source_view_id=case.view,
            projection_context=case.prepared,
        )
        for input_hash in (
            digest,
            pm2_input_digest(
                mapping, profile, request, **(options | {"source_path": "/candidate"})
            ),
        ):
            create_task(
                conn,
                run_id=comparison,
                config_id=case.task_row["method_config_id"],
                stage="record",
                unit_type="source_view",
                unit_id=case.view,
                unit_key="private-unit",
                input_hash=input_hash,
            )
        tasks = table("ops.task")
        rows = conn.execute(select(tasks).where(tasks.c.run_id == comparison)).mappings()
        reuse = {row["input_hash"]: row["reused_task_id"] for row in rows}
        origin = conn.execute(
            select(
                tasks.c.id,
                tasks.c.input_hash,
                tasks.c.status,
                tasks.c.method_config_id,
                tasks.c.unit_id,
                tasks.c.unit_key,
            ).where(tasks.c.id == held.task_id)
        ).one()
        source_binding = binding_of(conn, case.run)
        comparison_binding = binding_of(conn, comparison)
    assert reuse[digest] == held.task_id, (origin, source_binding, comparison_binding, reuse)
    assert (
        reuse[
            pm2_input_digest(mapping, profile, request, **(options | {"source_path": "/candidate"}))
        ]
        is None
    )


def _settle_reassigned_dipo(case, tmp_path, admin, assets):
    key = "private-discourse-unit"
    with case.writer.connect() as conn:
        view = BoundReader(conn, case.run, case.prepared, analysis=False).source_view(
            case.other_view
        )
    source = replace(native_source_frame(view, ()), unit_ref=key)
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(case.other_view, 0, len(source.text)),),
        "local discourse",
        "native-test",
        "exact running-text scope",
    )
    mapping = PM2SourceMap(
        context,
        context.text,
        (SourceMapSegment(0, len(context.text), 0),),
        (),
    )
    request = {"text": context.text}
    profile_file = tmp_path / "dipo.json"
    profile_file.write_text(json.dumps({"provider": "dipo", "device": "cpu", "assets": assets}))
    child = Path(pm2_native.__file__)
    interpreter = child.parents[5] / "services/pm2-dipo/.venv/bin/python"
    dimensions = {"question": "locate_discourse_units", "operation_version": "1"}
    with open_pm2_worker(
        python=interpreter,
        script=child,
        profile=profile_file,
        device="cpu",
    ) as worker:
        profile = worker.startup
        digest = pm2_input_digest(mapping, profile, request, **dimensions)
        held = _claim(case, digest, view_id=case.other_view, unit_key=key)
        with admin.begin() as conn:
            conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
            conn.execute(
                text(
                    "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' "
                    "WHERE id=:id"
                ),
                {"id": held.task_id},
            )
        with case.writer.begin() as conn:
            (reassigned,) = claim_tasks(
                conn,
                run_id=case.run,
                config_id=held.method_config_id,
                holder="next-owner",
            )
        assert reassigned.task_id == held.task_id and reassigned.attempt > held.attempt
        completion = dict(
            expected_profile=profile,
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            **dimensions,
        )
        with (
            maintained_claims(case.writer, (held,), held.holder) as stale,
            pytest.raises(OperationConflict, match="attempt lost"),
        ):
            settle_pm2_claim(stale, held, worker, mapping, request, **completion)
        with maintained_claims(case.writer, (reassigned,), reassigned.holder) as current:
            settle_pm2_claim(current, reassigned, worker, mapping, request, **completion)


def _complete(case, conn, held, result):
    return complete_unit_result(
        conn,
        task_id=held.task_id,
        attempt=held.attempt,
        holder="records",
        prepared=case.prepared,
        method=case.method,
        configuration_hash="private-config",
        source="private-unit",
        result=result,
    )


@pytest.mark.parametrize(
    "private_source",
    [{"sibling_references": ("x+y",), "sibling_originals": ("x + y",)}],
    indirect=True,
)
def test_exact_original_projection_does_not_mint_a_physical_occurrence(private_source):
    case = private_source
    with case.writer.connect() as conn:
        view = BoundReader(conn, case.run, case.prepared, analysis=False).source_view(
            case.other_view
        )
    source = replace(native_source_frame(view, ()), unit_ref="private-unit")
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(case.other_view, 0, 5),),
        "literal",
        "native-test",
        "original spelling",
    )
    assert context.text == "x + y"
    mapping = PM2SourceMap(context, context.text, (SourceMapSegment(0, 5, 0),), ())
    profile = {"provider": "d1"}
    request = {
        "state": {"source": "x + y"},
        "questions": {"formula": {"type": "text", "instructions": "Read the formula."}},
    }
    rendered = '{"source":"x + y"}'
    options = dict(question="locate_literal", operation_version="1", source_path=SOURCE_PATH)
    digest = pm2_input_digest(mapping, profile, request, **options)
    with case.writer.begin() as conn:
        complete_contributions(
            case,
            conn,
            UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.EMPTY,
            ),
        )
    held = _claim(case, digest, view_id=case.other_view)
    result = pm2_unit_result(
        UnitRef(TaskUnitType.SOURCE_VIEW, case.other_view, "private-unit"),
        mapping,
        profile=profile,
        request=request,
        reply={
            "outcome": "succeeded",
            "rendered_state": rendered,
            "native": {
                "answers": {"formula": {"span": [11, 16], "text": "x + y", "path": SOURCE_PATH}}
            },
        },
        field=D1SourceField(rendered, SOURCE_PATH, 11, 16),
        input_digest=digest,
        **options,
    )
    with case.writer.begin() as conn:
        _complete(case, conn, held, result)
    finalize_bound_run(case.writer, case.run, "pm2-orig-projection")
    with read_snapshot(case.writer) as conn:
        page = serve_contributions(
            conn,
            ContributionRequest(
                run_id=case.run,
                selected_task_id=held.task_id,
                include_details=True,
            ),
        )
        locations = BoundReader(
            conn, case.run, case.prepared, page.cut_id
        ).pm2_projection_locations(held.task_id)
    assert page.inventory_counts["contributions"] == 0
    assert locations is not None
    location = locations["formula"]
    assert location["reason"] == "native_occurrence_unavailable"
    assert "occurrence_id" not in location
    assert location["selected_projection"][0]["source_piece"] == "x + y"
