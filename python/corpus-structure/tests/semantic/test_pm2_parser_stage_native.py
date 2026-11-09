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
