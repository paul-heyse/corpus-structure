"""Qualify one independently addressable role from the current real provider arm."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import anyio

from corpus_structure.methods.definition_terms import DefinitionTermsConfig, DefinitionTermsMethod
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import (
    RetainedDefinitionRoleRef,
    RetainedStructuralRef,
)
from corpus_structure.serve.contributions import (
    ContributionPage,
    ContributionRequest,
    serve_contributions,
)
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    read_structural_export_page,
)
from corpus_structure.settings import Settings

COMPARISON_EVIDENCE = Path(__file__).resolve().parents[1] / "2026-11-07_nce-comparison-model-links"
sys.path.insert(0, str(COMPARISON_EVIDENCE))
from check_delivery import read_mcp  # noqa: E402
from replay_selected import prepared_release, retain, run_method, task_custody  # noqa: E402


def cli(*args, body=None):
    result = subprocess.run(("ci", *args, "--json"), input=body, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def comparable_page(page):
    value = page.model_dump(mode="json")
    del value["binding"]["capture_id"]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--definitions", type=Path, required=True)
    parser.add_argument("--repeat-text")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, args.output, args.release)
    run = json.loads((args.definitions / "native/completed.json").read_bytes())
    config = json.loads((args.definitions / "native/configuration.json").read_bytes())
    with (
        open_runtime_engine(settings, "nce-audit-role-selection", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        page = read_structural_export_page(
            conn,
            StructuralExportRequest(
                run_id=run["run_id"],
                cut_id=run["cut_id"],
                kind="definition_components",
            ),
        )
        (report,) = page.reports
        (task,) = page.task_ids
        custody = task_custody(conn, run)[task]
    product = report.definition_components
    if product is None or (config["method"], config["version"]) != (
        "structure.definition_components",
        "9",
    ):
        raise ValueError("role source requires a completed version 9 definition arm")
    attached = {
        (role, span)
        for component in product.components
        if component.basis == "model_reading"
        for role, span in (("term", component.term), ("content", component.content))
    }
    unattached = tuple(
        row
        for row in product.role_candidates or ()
        if (row.role, row.span) not in attached
        and (args.repeat_text is None or row.span.text == args.repeat_text)
    )
    candidates = unattached if args.repeat_text is not None else unattached[:1]
    if not candidates or (
        args.repeat_text is not None
        and (
            len({row.span for row in candidates}) < 2
            or len({(row.role, row.span.passage_id) for row in candidates}) != 1
        )
    ):
        raise ValueError("expected distinct unattached role occurrences in one source passage")
    candidate = candidates[0]
    passage = next(p for p in report.inputs.passages if p.passage_id == candidate.span.passage_id)
    source = next(r for r in report.inputs.sources if r.identity == passage.source_ref)
    origin = RetainedStructuralRef(
        product_id=report.product_id,
        project_id=run["project_id"],
        run_id=run["run_id"],
        cut_id=run["cut_id"],
        release_id=run["release_id"],
        result_revision=run["result_revision"],
        **custody,
    )
    role_refs = tuple(
        RetainedDefinitionRoleRef(
            report=origin,
            role=row.role,
            envelope=row.envelope,
            index=row.index,
        )
        for row in candidates
    )
    selected = report.inputs.model_copy(update={"sources": (source,), "passages": (passage,)})
    cfg = DefinitionTermsConfig(
        role_refs=role_refs,
        source_product_digest=source.native_content_digest,
        source_projection_digest=source.projection_digest,
    )
    output_run = run_method(
        settings,
        prepared,
        DefinitionTermsMethod(),
        cfg.model_dump(mode="json"),
        selected,
        args.output / "native",
        "standalone-definition-role",
        args.output.name,
    )
    request = ContributionRequest(
        run_id=output_run["run_id"],
        source_view_id=source.source_view_id,
        method="locate.definition_terms",
        include_details=True,
    )
    with (
        open_runtime_engine(settings, "nce-audit-role-reader", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        reader = serve_contributions(conn, request)
    rows = tuple(item["row"] for item in reader.items if item["population"] == "contribution")
    expected = [
        (
            "proposal",
            "definition.term" if ref.role == "term" else "definition.defining_text",
            {"role": ref.role, "role_reference": ref.model_dump(mode="json")},
        )
        for ref in role_refs
    ]
    actual = [(r["kind"], r["semantic_type"], source_python(r["value"])) for r in rows]
    if (
        len(actual) != len(expected)
        or any(value not in actual for value in expected)
        or len({row["occurrence_id"] for row in rows}) != len(expected)
    ):
        raise ValueError("ordinary Reader did not return the exact private role")
    installed = ContributionPage.model_validate(
        cli(
            "contributions",
            "list",
            "--run",
            str(output_run["run_id"]),
            "--source-view",
            str(source.source_view_id),
            "--method",
            request.method,
            "--include-details",
        )
    )
    mcp = ContributionPage.model_validate(
        anyio.run(
            read_mcp,
            output_run["run_id"],
            "contributions",
            request.model_dump(mode="json"),
        )
    )
    for transport, delivered in (("reader", reader), ("cli", installed), ("mcp", mcp)):
        retain(args.output / f"{transport}-semantic-page.json", comparable_page(delivered))
    expected_page = comparable_page(reader)
    if comparable_page(installed) != expected_page or comparable_page(mcp) != expected_page:
        raise ValueError("standalone role delivery differs across ordinary readers")
    selection = ReviewSelection(
        selections=(
            request.model_copy(
                update={
                    "include_details": False,
                    "contribution_ids": tuple(row["contribution_id"] for row in rows),
                },
            ),
        )
    )
    export = cli("review", "export", "--exact-closure", "-", body=selection.model_dump_json())
    cli("review", "inspect", "--result", export["invocation_id"])
    result = {
        "run": output_run,
        "references": [row.model_dump(mode="json") for row in role_refs],
        "roles": [row.model_dump(mode="json") for row in candidates],
        "reader_cli_mcp_equal": True,
        "detached_result_id": export["invocation_id"],
        "detached_selection_digest": export["selection_digest"],
        "outcome": "passed",
    }
    retain(args.output / "result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
