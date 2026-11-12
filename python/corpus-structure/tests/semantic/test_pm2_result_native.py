"""Native completion and retained read over the private PM2 source boundary."""

import json
import os
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods.native_host_clients import HostedPM2
from corpus_structure.methods.pm2_result import pm2_input_digest, pm2_unit_result
from corpus_structure.methods.pm2_source import D1SourceField, PM2SourceMap, SourceMapSegment
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.pm2 import settle_pm2_claim
from corpus_structure.orchestrate.pm2_stage import _interpretation_dependency_reader
from corpus_structure.semantic._operation_calls import select_source_view
from corpus_structure.semantic.claim_lifetime import maintained_claims
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import QUESTION_INPUT, declared_families
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
from corpus_structure.semantic.pm2_coverage import scope_coverage
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    SourceSlice,
    record_source_pin,
)
from corpus_structure.semantic.types import SourceArtifact
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings
from semantic.native_record_fixtures import private_source as private_source
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_provider_support import actual_provider
from .native_record_fixtures import (
    build_record_source,
    complete_contributions,
    prepare_record_source,
)

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


@pytest.fixture
def literal_question_source(semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch):
    declaration = {
        "family": "literal_completion_v1",
        "questions": [
            {"key": "missing", "kind": "text", "instructions": "Copy the document's color."},
            {"key": "value", "kind": "number", "instructions": "Copy the numeral."},
        ],
    }
    base = prepare_record_source()
    artifact = SourceArtifact(QUESTION_INPUT, canonical_bytes([declaration]))
    dependencies = replace(base.dependencies, artifacts=(*base.dependencies.artifacts, artifact))
    preparation = replace(
        base,
        dependencies=dependencies,
        prepared=prepare_release(base.bundle, dependencies, base.profile),
    )
    return build_record_source(
        semantic_db_engine, semantic_writer_engine, tmp_path, preparation, monkeypatch=monkeypatch
    )


def test_completed_empty_d1_keeps_native_empty_and_publishes_unresolved_question(
    literal_question_source,
):
    case = literal_question_source
    family = declared_families(case.prepared.registry_rows)["literal_completion_v1"]
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
    mapping = PM2SourceMap(context, context.text, (SourceMapSegment(0, 2, 0),), ())
    assert context.text == "12"
    pin = record_source_pin(source)
    rendered = '{"source":"12"}'
    field = D1SourceField(rendered, SOURCE_PATH, 11, 13)
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit")
    profile = {"provider": "d1", "checkpoint": "controlled-test"}
    options = {
        "question": family.family,
        "operation_version": "3",
        "source_path": SOURCE_PATH,
    }
    with case.writer.begin() as conn:
        complete_contributions(case, conn, UnitResult(ref=ref, outcome=ObservationOutcome.EMPTY))

    def request_for(*keys):
        return {
            "state": {"source": "12"},
            "questions": {q.key: q.native([]) for q in family.questions if q.key in keys},
            "interpretation": {
                "version": "3",
                "declaration_digest": family.digest,
                "assessed_scope": {
                    "pin": pin,
                    "scope_digest": mapping.scope_digest,
                    "projection_extent": [cell["start"], cell["end"]],
                },
                "candidates": [],
            },
        }

    empty_request = request_for("missing")
    mixed_request = request_for("missing", "value")
    absent = {"type": "text", "found": 0.2, "span": None, "text": None}
    located = {
        "type": "number",
        "found": 0.98,
        "span": [11, 13],
        "text": "12",
        "number": 12,
        "path": SOURCE_PATH,
    }
    empty_reply = {
        "outcome": "empty",
        "rendered_state": rendered,
        "state_fields": [[11, 13, SOURCE_PATH]],
        "native": {"answers": {"missing": absent}},
    }
    mixed_reply = {
        "outcome": "succeeded",
        "rendered_state": rendered,
        "state_fields": [[11, 13, SOURCE_PATH]],
        "native": {"answers": {"missing": absent, "value": located}},
    }

    def project(request, reply, *, version="3"):
        selected = options | {"operation_version": version}
        digest = pm2_input_digest(mapping, profile, request, **selected)
        return digest, pm2_unit_result(
            ref,
            mapping,
            profile=profile,
            request=request,
            reply=reply,
            field=field,
            input_digest=digest,
            prepared=case.prepared,
            **selected,
        )

    for corrupted, expected in (
        (empty_reply | {"rendered_state": '{"source":"21"}'}, "admitted request"),
        (empty_reply | {"native": {"answers": {"wrong": absent}}}, "question population"),
        (empty_reply | {"native": {"answers": {"missing": located}}}, "absent span"),
    ):
        with pytest.raises(ValueError, match=expected):
            project(empty_request, corrupted)
    _, legacy = project(
        empty_request | {"interpretation": empty_request["interpretation"] | {"version": "2"}},
        empty_reply,
        version="2",
    )
    assert legacy.contribution_operations
    assert legacy.contribution_operations[0]["outcome"] == "empty"
    assert not legacy.contributions
    _, limited = project(empty_request, {"outcome": "limited", "reason": "question_count"})
    assert limited.contribution_operations
    assert limited.contribution_operations[0]["outcome"] == "limited"
    assert not limited.contributions

    intents = []
    for request, reply in ((empty_request, empty_reply), (mixed_request, mixed_reply)):
        digest = pm2_input_digest(mapping, profile, request, **options)
        held = _claim(case, digest)
        with maintained_claims(case.writer, (held,), held.holder) as owner:
            settle_pm2_claim(
                owner,
                held,
                cast(HostedPM2, SimpleNamespace(startup=profile)),
                mapping,
                request,
                expected_profile=profile,
                prepared=case.prepared,
                method=case.method,
                configuration_hash="private-config",
                prefetched_reply=reply,
                **options,
            )
        intents.append(
            dict(
                source_view_id=case.view,
                extent=(cell["start"], cell["end"]),
                question=family.family,
                operation_version="3",
                disposition="scheduled",
                input_digest=digest,
            )
        )
    finalize_bound_run(case.writer, case.run, "pm2-empty-question-read")
    with read_snapshot(case.writer) as conn:
        coverage = scope_coverage(conn, case.run, intents)
        page = serve_contributions(
            conn,
            ContributionRequest(
                run_id=case.run,
                source_view_id=case.view,
                include_details=True,
                include_interpretation=True,
            ),
        )
    assert [(row.outcome, row.provider_outcome, row.emitted_count) for row in coverage] == [
        ("succeeded", "empty", 1),
        ("succeeded", "succeeded", 3),
    ]
    rows = [
        cast(dict[str, Any], item["row"])
        for item in page.items
        if item["population"] == "contribution"
    ]
    unresolved = [row for row in rows if row["item_key"] == "interpretation:missing"]
    assert len(unresolved) == 2
    assert all(not row["anchors"] and not row.get("occurrence_id") for row in unresolved)
    values = [source_python(row["value"]) for row in unresolved]
    assert values[0] == values[1]
    assert values[0]["state"] == "unresolved"
    assert values[0]["native_answer"] == absent
    interpretations = [
        cast(dict[str, Any], item["row"])
        for item in page.items
        if item["population"] == "interpretation"
    ]
    facets = [
        row["composition"]
        for row in interpretations
        if row["semantic_type"] == f"interpretation.{family.family}"
    ]
    assert len(facets) == 3
    assert sum(facet["interpretation_state"] == "unresolved" for facet in facets) == 2


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
    source = native_source_frame(view, ())
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
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, case.view, source.unit_ref)
    with case.writer.begin() as conn:
        complete_contributions(
            case,
            conn,
            UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.EMPTY,
            ),
        )
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
        with actual_provider("d1", assets, endpoint=Settings().nemotron.endpoint) as worker:
            profile = worker.startup
            digest = pm2_input_digest(mapping, profile, request, **options)
            held = _claim(case, digest, unit_key=source.unit_ref)
            limited_held = _claim(
                case,
                pm2_input_digest(mapping, profile, oversized, **options),
                unit_key=source.unit_ref,
            )
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
        held = _claim(case, digest, unit_key=source.unit_ref)
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
        limited_held = _claim(case, limited_digest, unit_key=source.unit_ref)
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
    completed = finalize_bound_run(case.writer, case.run, "pm2-private-read")
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
        run = table("ops.run")
        runtime = conn.execute(select(run.c.runtime_id).where(run.c.id == case.run)).scalar_one()
        (contribution,) = detail["contributions"]
        ref = RetainedContributionRef(
            contribution_id=contribution["contribution_id"],
            project_id=case.project_id,
            run_id=case.run,
            cut_id=completed.cut_id,
            release_id=case.prepared.release_id,
            result_revision=completed.data_revision,
            selected_task_id=held.task_id,
            origin_task_id=held.task_id,
            runtime_fingerprint=runtime,
        )
        stale = ref.model_copy(update={"cut_id": completed.cut_id + 1})
        resolved = _interpretation_dependency_reader(conn, case.prepared, (ref, stale, ref))
        native_reads = []

        def observe_native_read(_conn, _cursor, statement, _parameters, _context, _executemany):
            if "ops.resolve_retained_source_contribution(" in statement:
                native_reads.append(statement)

        event.listen(conn, "before_cursor_execute", observe_native_read)
        try:
            assert resolved(ref) == [contribution]
            assert len(native_reads) == 1
            with (
                pytest.raises(DBAPIError, match="cannot resolve exact selected origin"),
                conn.begin_nested(),
            ):
                resolved(stale)
            assert resolved(ref) == [contribution]
            assert len(native_reads) == 2
        finally:
            event.remove(conn, "before_cursor_execute", observe_native_read)
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
                unit_key=source.unit_ref,
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
    dimensions = {"question": "locate_discourse_units", "operation_version": "1"}
    with actual_provider("dipo", assets, endpoint=Settings().nemotron.endpoint) as worker:
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
    assert held.unit_key is not None
    return complete_unit_result(
        conn,
        task_id=held.task_id,
        attempt=held.attempt,
        holder="records",
        prepared=case.prepared,
        method=case.method,
        configuration_hash="private-config",
        source=held.unit_key,
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
