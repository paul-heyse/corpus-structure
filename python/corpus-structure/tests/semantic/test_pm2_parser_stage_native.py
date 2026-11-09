"""Exercise the private parser runner and contribution Reader with an alternate vocabulary."""

import json
import os
from pathlib import Path
from typing import Any, cast

import pytest

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.pm2_stage import ParserRunRequest, run_parsers
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings
from semantic.native_record_fixtures import private_source as private_source

from .native_record_fixtures import complete_contributions

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "docs/design_review/evidence"


@pytest.fixture
def parser_samples():
    panel = json.loads(
        (EVIDENCE / "2026-11-08_pm2-parsers/raw/reference-operations.json").read_bytes()
    )["cases"]
    return panel[0]["text"], panel[2]["text"], panel[4]["text"]


@pytest.fixture
def private_source_options(parser_samples):
    return {"sibling_references": parser_samples}


@pytest.mark.skipif(
    not os.environ.get("CORPUS_PM2_NATIVE_TEST_ASSETS"), reason="locked native assets are opt-in"
)
def test_alternate_domain_parser_run_retains_siblings_after_profile_refusal(
    private_source, parser_samples
):
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
    finalize_bound_run(case.writer, case.run, "pm2-transfer-origin")
    (source,) = prepare_structural_sources(
        case.writer,
        (
            StructuralPassageSelection(
                run_id=case.run,
                source_view_id=case.other_view,
                passage_id="operations",
                start=0,
                end=len("\n".join(parser_samples)),
                scope="transfer",
            ),
        ),
    ).sources
    scopes: list[dict[str, Any]] = []
    start = 0
    for provider, literal in zip(("hanlp", "maverick", "dipo"), parser_samples, strict=True):
        output = EVIDENCE / f"2026-11-08_pm2-foundation/raw/{provider}-cuda.jsonl"
        profile = json.loads(output.read_text().splitlines()[0])["startup"]
        scopes.append(
            dict(
                source=source.model_dump(mode="json"),
                extent=[start, start + len(literal)],
                profile=dict(provider=provider, device="cuda", startup=profile),
            )
        )
        start += len(literal) + 1
    refused = dict(scopes[-1])
    refused["profile"] = {
        **refused["profile"],
        "startup": {**refused["profile"]["startup"], "head": "deliberately-wrong"},
    }
    request = ParserRunRequest.model_validate(
        dict(
            project=case.project_id,
            release=case.prepared.release_id,
            realization="private-input",
            assets=os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"],
            scopes=[*scopes, refused],
        )
    )
    result = run_parsers(case.writer, Settings(), request)
    with read_snapshot(case.writer) as conn:
        page = serve_contributions(
            conn,
            ContributionRequest(
                run_id=result.run_id,
                include_details=True,
                limit=1000,
            ),
        )
    rows = [(item["population"], cast(dict[str, Any], item["row"])) for item in page.items]
    semantic_types = {
        row["semantic_type"] for population, row in rows if population == "contribution"
    }
    operations = [row for population, row in rows if population == "operation"]
    assert {"linguistic.predicate_frame", "maverick.cluster", "dipo.tree"} <= semantic_types, (
        operations
    )
    assert any(
        row["outcome"] == "failed" and "differs from the admitted profile" in row["reason"]
        for row in operations
    )
    coverage = {row.task_id: row for row in result.scope_coverage}
    assert set(coverage) == set(result.tasks)
    for operation in operations:
        entry = coverage[operation["selected_task_id"]]
        assert entry.outcome == operation["outcome"]
        assert entry.inspected_count == operation["inspected_count"]
        assert entry.emitted_count == operation["emitted_count"]


def test_pm2_unattempted_scope_remains_visible_without_provider_or_contributions(
    private_source, parser_samples, tmp_path
):
    from corpus_structure.orchestrate.commands import bound_status
    from corpus_structure.semantic.operations import BoundReader

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
    finalize_bound_run(case.writer, case.run, "pm2-coverage-origin")
    (source,) = prepare_structural_sources(
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
    base = dict(
        source=source.model_dump(mode="json"),
        extent=[0, len(parser_samples[0])],
        profile=dict(
            provider="hanlp", device="cpu", startup={"provider": "hanlp", "device": "cpu"}
        ),
    )
    request = ParserRunRequest.model_validate(
        dict(
            project=case.project_id,
            release=case.prepared.release_id,
            realization="private-input",
            assets=tmp_path / "intentionally-unstaged",
            scopes=[dict(base, language="fr"), dict(base, schedule=False)],
        )
    )
    report = run_parsers(case.writer, Settings(), request)
    assert not report.tasks
    with read_snapshot(case.writer) as conn:
        progress = bound_status(conn, report.run_id).run
        reader_coverage = BoundReader(
            conn, report.run_id, case.prepared, report.cut_id
        ).pm2_scope_coverage()
        inspection = serve_contributions(
            conn,
            ContributionRequest(run_id=report.run_id, include_scope_coverage=True),
        )
    assert progress is not None
    assert progress.pm2_scope_coverage == reader_coverage == report.scope_coverage
    assert [entry.outcome for entry in report.scope_coverage] == ["ineligible", "unscheduled"]
    assert all(entry.emitted_count == entry.inspected_count == 0 for entry in report.scope_coverage)
    assert inspection.inventory_counts["contributions"] == 0
    assert [item["row"] for item in inspection.items if item["population"] == "scope_coverage"] == [
        entry.model_dump(mode="json") for entry in report.scope_coverage
    ]


def test_cancelled_pm2_scope_does_not_gain_an_operation_result(private_source):
    from hashlib import sha256

    from corpus_structure.orchestrate.commands import bound_status, cancel_bound_run
    from corpus_structure.semantic._operation_calls import select_source_view
    from corpus_structure.semantic._operation_ids import SourceViewId
    from corpus_structure.semantic.operations import binding_of, create_run, create_task, start_run
    from corpus_structure.semantic.pm2_coverage import scope_coverage

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
