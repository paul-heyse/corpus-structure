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
    private_source, parser_samples, tmp_path, monkeypatch
):
    from corpus_structure.methods import native_profiles

    from .native_provider_support import actual_provider_population

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
    settings = Settings()
    with actual_provider_population(
        ("hanlp", "maverick", "dipo"),
        os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"],
        endpoint=settings.nemotron.endpoint,
    ) as population:
        for provider, literal in zip(("hanlp", "maverick", "dipo"), parser_samples, strict=True):
            profile = dict(population[provider].startup)
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
    startup_differences = []
    original_match = native_profiles.admitted_startup_matches

    def compare_startup(observed, admitted):
        matched = original_match(observed, admitted)
        if not matched:
            startup_differences.append(
                dict(
                    provider=admitted.get("provider"),
                    fields=sorted(
                        key
                        for key in set(observed) | set(admitted)
                        if key != "host_stream" and observed.get(key) != admitted.get(key)
                    ),
                )
            )
        return matched

    monkeypatch.setattr(native_profiles, "admitted_startup_matches", compare_startup)
    result = run_parsers(case.writer, settings, request)
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
    assert {"linguistic.constituent", "maverick.cluster", "dipo.tree"} <= semantic_types, dict(
        operations=[
            {key: row.get(key) for key in ("question", "outcome", "reason")} for row in operations
        ],
        startup_differences=startup_differences,
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
    private_source, parser_samples, tmp_path, semantic_reader_engine
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
        selection = ContributionRequest(
            run_id=report.run_id, source_view_id=case.other_view, include_scope_coverage=True
        )
        inspection = serve_contributions(conn, selection)
    review = ReviewSelection(selections=(selection,))
    with read_snapshot(semantic_reader_engine) as conn:
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


def test_pm2_cli_refuses_invalid_extent_before_run_admission(
    private_source, parser_samples, semantic_application_settings, tmp_path, monkeypatch
):
    from sqlalchemy import func, select
    from typer.testing import CliRunner

    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState
    from corpus_structure.methods import native_host, native_profiles
    from corpus_structure.orchestrate import pm2_stage
    from corpus_structure.semantic.metadata import table

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
    finalize_bound_run(case.writer, case.run, "pm2-scope-refusal-origin")
    (source,) = prepare_structural_sources(
        case.writer,
        (
            StructuralPassageSelection(
                run_id=case.run,
                source_view_id=case.other_view,
                passage_id="invalid-extent-control",
                start=0,
                end=len(parser_samples[0]),
                scope="coverage",
            ),
        ),
    ).sources

    # Control asset/runtime admission at its actual owner. Original source loading
    # and canonical-token validation remain real; learned sentence inference is isolated.
    checked_providers = []

    def preflight(provider, assets):
        assert provider in {"hanlp", "d1"}
        assert assets == tmp_path
        checked_providers.append(provider)
        return {"assets": {}, "runtime_identity": {"fixture": "extent-control"}}

    monkeypatch.setattr(native_profiles, "preflight_native_runtime", preflight)

    def canonical_sentences(view, *, endpoint=None):
        # Independently supplied whole-source sentence control: [0,2) cuts it,
        # while [1,2) must first fail the actual canonical-token boundary check.
        assert view.text.startswith(parser_samples[0])
        return [(0, len(parser_samples[0]))]

    monkeypatch.setattr(pm2_stage, "_sentences", canonical_sentences)

    # With sentence bounds supplied above, this guards the later PM2 execution
    # host. It does not establish behavior of the unmocked spaCy inference path.
    def refuse_provider_start(self):
        pytest.fail("invalid source extent reached the PM2 execution host")

    monkeypatch.setattr(native_host.NativeHostGroup, "__enter__", refuse_provider_start)
    run, task = table("ops.run"), table("ops.task")

    def inventory():
        with case.writer.connect() as conn:
            return (
                conn.scalar(
                    select(func.count()).select_from(run).where(run.c.project_id == case.project_id)
                ),
                conn.scalar(
                    select(func.count())
                    .select_from(task.join(run, task.c.run_id == run.c.id))
                    .where(run.c.project_id == case.project_id)
                ),
            )

    before = inventory()
    request_path = tmp_path / "scope-request.json"
    runner = CliRunner()
    for command, extent, reason in (
        ("parsers", [0, 50_000], "invalid_source_extent"),
        ("interpret", [0, 50_000], "invalid_source_extent"),
        ("parsers", [1, 2], "partial_canonical_token"),
        ("parsers", [0, 2], "partial_canonical_sentence"),
    ):
        provider = "hanlp" if command == "parsers" else "d1"
        scope: dict[str, Any] = {
            "source": source.model_dump(mode="json"),
            "extent": extent,
            "profile": {
                "provider": provider,
                "device": "cuda",
                "startup": {
                    "provider": provider,
                    "device": "cuda",
                    "dtype": "torch.float32" if command == "parsers" else "torch.bfloat16",
                    "assets": {},
                },
            },
        }
        if command == "interpret":
            scope["family"] = "passage_function_v1"
        request_path.write_text(
            json.dumps(
                {
                    "project": case.project_id,
                    "release": case.prepared.release_id,
                    "realization": "private-input",
                    "assets": str(tmp_path),
                    "scopes": [scope],
                }
            )
        )
        result = runner.invoke(
            app,
            ["run", command, "--request", str(request_path), "--json"],
            obj=CliState(lambda: semantic_application_settings),
        )
        assert result.exit_code == 1, (result.output, result.exception)
        error = json.loads(result.stdout)["error"]
        assert (error["code"], error["reason"]) == ("Pm2ScopeRefused", reason), error
        assert inventory() == before

    assert checked_providers == ["hanlp", "d1", "hanlp", "hanlp"]


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
