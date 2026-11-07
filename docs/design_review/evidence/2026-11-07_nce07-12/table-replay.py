"""Replay the two retained table controls through a registered correspondence release."""

import argparse
import asyncio
import json
import subprocess
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.methods.table_interpretation import (
    CORRESPONDENCE_POLICY_VERSION,
    table_policy_operations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import (
    ContributionPage,
    ContributionRequest,
    serve_contributions,
)
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CLI = Path(sys.executable).with_name("ci")
LEGACY = HERE.parent / "2026-11-06_wce-completion-repair/table"
sys.path.insert(0, str(LEGACY))
from run_table_policy import (  # noqa: E402
    MARGINAL,
    REFERENCE,
    case_summary,
    compare_dice,
    compare_marginals,
    frozen_inputs,
    relation_projection,
    retain,
    run_method,
)

PROJECT = "wce-gs120-method-development-20261106"
FRAMES = {"tables-5.2-5.3": MARGINAL, "table-6.1": REFERENCE.name}
HISTORICAL = {"feasibility": 194, "independent": 198, "coupled": 199}


def cli(args, receipt, *, stdin=None):
    result = subprocess.run(
        [str(CLI), *args, "--json"],
        cwd=ROOT,
        input=stdin,
        check=False,
        capture_output=True,
        timeout=300,
    )
    receipt.with_suffix(".stdout").write_bytes(result.stdout)
    receipt.with_suffix(".stderr").write_bytes(result.stderr)
    if result.returncode:
        raise ValueError(f"ci {' '.join(args)} failed with exit {result.returncode}: {receipt}")
    return json.loads(result.stdout)


def population(settings, run, source_id):
    request = ContributionRequest(
        run_id=run["run_id"],
        source_view_id=source_id,
        method=ScopedRelationsMethod.name,
        include_details=True,
        include_interpretation=True,
        limit=1000,
        page_bytes=16_000_000,
        max_bytes=128_000_000,
    )
    items = []
    with (
        open_runtime_engine(settings, "nce11-retained-table-read", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        seen = set()
        while True:
            page = serve_contributions(conn, request)
            if page.cut_id != run["cut_id"]:
                raise ValueError("ordinary table read returned a different completed cut")
            items.extend(page.items)
            if page.next_cursor is None:
                break
            if page.next_cursor in seen:
                raise ValueError("table continuation did not advance")
            seen.add(page.next_cursor)
            request = request.model_copy(update={"cursor": page.next_cursor})
    contributions = [item["row"] for item in items if item["population"] == "contribution"]
    operations = [item["row"] for item in items if item["population"] == "operation"]
    return contributions, operations


def reports(operations, *, expected_policy=None):
    result = {}
    for operation in operations:
        report = operation.get("local_interpretation")
        if report is None:
            continue
        if expected_policy and report["policy_version"] != expected_policy:
            raise ValueError("ordinary Reader returned a different policy")
        result[operation["operation_key"]] = {
            "status": report["outcome"],
            "executed_mode": report["policy_mode"],
            "contribution_ids": report["contribution_ids"],
            "request_digest": report.get("request_digest"),
            "result_digest": report.get("result_digest"),
            "request": source_python(report["request"]) if "request" in report else None,
            "result": source_python(report["result"]) if "result" in report else None,
        }
    return result


def role_support(readings):
    support = {}
    for row in readings.values():
        request = row["request"]
        if request is None:
            continue
        decisions = [d for d in request["decisions"] if d["key"] != "M"]
        axes = tuple(d["key"] for d in decisions)
        if axes in support:
            raise ValueError("one role band occurs twice")
        support[axes] = (
            decisions,
            [(m["scope"], m["allowed"]) for m in request["constraints"]],
            request["selection"]["exclusions"],
            request["events"],
        )
    return support


def reported_probabilities(identifiers, checks):
    return {
        value["candidate"]: value["probability"]
        for check in checks
        for value in check.get("relation_marginals", ())
        if value["candidate"] in identifiers
    }


def matched_assessment(frame, reference, source, contributions, operations):
    new = reports(operations, expected_policy=CORRESPONDENCE_POLICY_VERSION)
    if not new or any(r["status"] != "completed" for r in new.values()):
        raise ValueError("selected correspondence bands did not all complete")
    if any(
        r["result"]["omitted_candidate_mass"] != "unknown"
        or r["result"]["probability_standing"] != "provisional_candidate_relative"
        for r in new.values()
    ):
        raise ValueError("correspondence output overstates its candidate-relative support")
    identifiers = {row["contribution_id"] for row in contributions}
    if any(not set(r["contribution_ids"]) <= identifiers for r in new.values()):
        raise ValueError("ordinary Reader lost a retained table input")
    old = {
        mode: reports(table_policy_operations(
            contributions=contributions,
            dependency_ids=("nce11-matched-retained-population",),
            source_revision=source.native_content_digest,
            mode=mode,
        ))
        for mode in ("feasibility", "independent", "coupled")
    }
    support = role_support(new)
    if any(role_support(readings) != support for readings in old.values()):
        raise ValueError("one arm changed the ordered role support, masks, or events")
    compare = compare_marginals if frame == MARGINAL else compare_dice
    links = relation_projection(contributions)
    cases = {mode: compare(links, readings, reference) for mode, readings in old.items()}
    cases["correspondence"] = compare(links, new, reference)
    statuses = Counter(r["request"]["correspondence_status"] for r in new.values())
    if frame == MARGINAL:
        summaries = {
            mode: {
                name: {
                    **summary,
                    "supported_marginals": reported_probabilities(
                        result[name]["positive"], result[name]["positive_checks"]
                    ),
                }
                for name, summary in case_summary({"source_cases": result}, frame).items()
            }
            for mode, result in cases.items()
        }
        if len(summaries["correspondence"]) != 9 or any(
            case["positive_states"] != ["top_assignment_present"]
            for case in summaries["correspondence"].values()
        ):
            raise ValueError("known marginal-role control lost a supported choice")
        if statuses["fixed"] != 3 or statuses["ambiguous"]:
            raise ValueError("observed/schematic control differs from its fixed correspondence")
        for mode, archive in HISTORICAL.items():
            historical = json.loads(
                (LEGACY / "marginal-attempt003" / f"{mode}-1/assessment.json").read_bytes()
            )
            if historical["run"]["run_id"] != archive:
                raise ValueError("historical matched policy receipt differs")
            if role_support(historical["assessment"]["reports"]) != support:
                raise ValueError("current role space differs from historical native control")
        probe = next(
            key for key, row in new.items() if row["request"]["correspondence_status"] == "fixed"
        )
    else:
        summaries = {
            mode: {
                case: {
                    role: {
                        "nomination": check["nomination"],
                        "states": sorted({item["state"] for item in check["policy_checks"]}),
                        "marginals": reported_probabilities(
                            check["relations"], check["policy_checks"]
                        ),
                    }
                    for role, check in value["comparisons"].items()
                }
                for case, value in result.items()
            }
            for mode, result in cases.items()
        }
        if statuses["fixed"] or statuses["ambiguous"]:
            raise ValueError("exact-header control introduced a schematic correspondence")
        probe = None
        for case in cases["correspondence"].values():
            for role, comparison in case["comparisons"].items():
                checks = comparison["policy_checks"]
                if role in ("measure_header", "sample_size_header"):
                    if {check["state"] for check in checks} != {"top_assignment_present"}:
                        raise ValueError("exact-header control lost its qualified header")
                    probe = probe or checks[0]["operation"]
                elif role.startswith("excluded_") and comparison["nomination"] == "nominated":
                    if {check["state"] for check in checks} != {"hard_excluded"}:
                        raise ValueError("exact-header control retained a cross-band alternative")
        if probe is None:
            raise ValueError("exact-header control lacks a selected header")
    return {
        "role_bands": len(support),
        "contribution_count": len(identifiers),
        "correspondence_statuses": dict(statuses),
        "historical_native_runs": HISTORICAL if frame == MARGINAL else {"independent": 195},
        "comparison_arms": "three local legacy evaluations on the same retained population",
        "case_summaries": summaries,
        "reports": {
            operation: {k: report[k] for k in ("status", "request_digest", "result_digest")}
            for operation, report in new.items()
        },
        "transport_operation": probe,
    }


async def mcp_page(request, output):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command=str(CLI),
        args=["mcp", "serve", "--semantic-run", str(request.run_id)],
        cwd=str(ROOT),
        log_file=output / "mcp-server.log",
    )
    async with Client(transport, timeout=180) as client:
        reply = await client.call_tool(
            "contributions",
            {"request": request.model_dump(mode="json", exclude_none=True)},
            raise_on_error=False,
        )
    if reply.is_error or reply.structured_content is None:
        retain(output / "mcp-error.json", reply.model_dump(mode="json"))
        raise ValueError("fresh MCP did not deliver the pinned contribution page")
    return reply.structured_content


def transport_projection(page):
    """Compare the completed binding while recording each independent read capture."""
    value = ContributionPage.model_validate(page).model_dump(mode="json")
    capture = value["binding"].pop("capture_id")
    return value, capture


def transports(settings, run, source_id, operation, output):
    request = ContributionRequest(
        run_id=run["run_id"],
        source_view_id=source_id,
        method=ScopedRelationsMethod.name,
        operation_key=operation,
        operation_version="local-interpretation-2",
        include_details=True,
        include_interpretation=True,
        page_bytes=16_000_000,
    )
    with (
        open_runtime_engine(settings, "nce11-transport-control", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        reader = serve_contributions(conn, request)
    if reader.cut_id != run["cut_id"] or reader.next_cursor:
        raise ValueError("transport control must read one complete pinned page")
    operation_rows = [
        item["row"] for item in reader.items if item["population"] == "operation"
    ]
    (retained,) = [
        row["local_interpretation"] for row in operation_rows if row.get("local_interpretation")
    ]
    if retained["policy_version"] != CORRESPONDENCE_POLICY_VERSION:
        raise ValueError("selected interpretation operation uses a different policy")
    installed_cli = cli(
        [
            "contributions", "list", "--run", str(request.run_id), "--source-view", str(source_id),
            "--method", request.method, "--operation", operation, "--operation-version",
            request.operation_version, "--include-details", "--include-interpretation",
            "--page-bytes", str(request.page_bytes),
        ],
        output / "cli-page",
    )
    detached_mcp = asyncio.run(mcp_page(request, output))
    expected, reader_capture = transport_projection(reader)
    cli_page, cli_capture = transport_projection(installed_cli)
    mcp_page_, mcp_capture = transport_projection(detached_mcp)
    if cli_page != expected or mcp_page_ != expected:
        raise ValueError("ordinary Reader, installed CLI and fresh MCP returned different pages")
    retain(output / "transport.json", {
        "outcome": "passed",
        "cut_id": reader.cut_id,
        "operation_key": operation,
        "request_digest": retained["request_digest"],
        "result_digest": retained["result_digest"],
        "page_digest": sha256(canonical_bytes(expected)).hexdigest(),
        "transports": ["ordinary Reader", "installed CLI", "fresh stdio MCP"],
        "capture_ids": [reader_capture, cli_capture, mcp_capture],
    })


def export(run, source_id, output):
    request = ContributionRequest(
        run_id=run["run_id"],
        source_view_id=source_id,
        method=ScopedRelationsMethod.name,
        include_details=True,
        include_interpretation=True,
        limit=1000,
        page_bytes=16_000_000,
        max_bytes=128_000_000,
    )
    selection = ReviewSelection(selections=(request,))
    prior = output / "review-export.stdout"
    if prior.is_file() and "destination" in (receipt := json.loads(prior.read_bytes())):
        exported = receipt
    else:
        exported = cli(
            ["review", "export", "-", "--exact-closure"],
            output / "review-export",
            stdin=selection.model_dump_json().encode(),
        )
    verified = cli(["review", "verify", exported["destination"]], output / "review-verify")
    if any(
        verified[key] != exported[key] for key in ("selection_digest", "completeness", "relations")
    ):
        raise ValueError("detached verification differs from the exact exported selection")
    retain(output / "detached.json", {
        "outcome": "passed",
        "run_id": run["run_id"],
        "cut_id": run["cut_id"],
        "managed_result_id": exported["invocation_id"],
        "selection_digest": verified["selection_digest"],
        "relations": {key: value["rows"] for key, value in verified["relations"].items()},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--release", required=True)
    parser.add_argument("--frame", choices=FRAMES, required=True)
    parser.add_argument("--native-only", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT / "build" not in output.parents:
        parser.error("output must be in this checkout's ignored build directory")
    output.mkdir(parents=True, exist_ok=True)
    frame = FRAMES[args.frame]
    reference, reference_digest, original, _ = frozen_inputs(frame)
    inputs = original.model_copy(update={"policy_id": CORRESPONDENCE_POLICY_VERSION})
    (source,) = inputs.sources
    if source.project_id != PROJECT:
        raise ValueError("table replay is outside the authorized historical project")
    settings = Settings()
    with (
        open_runtime_engine(settings, "nce11-table-release", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = load_release(conn, args.release)
    run = run_method(
        settings,
        prepared,
        ScopedRelationsMethod(),
        dict(
            inputs=inputs.model_dump(mode="json"),
            structural_input_digest=inputs.identity,
            interpretation_mode="correspondence",
            interpretation_weight_scale=1.0,
        ),
        inputs,
        output,
        args.frame,
        "nce11-" + output.name,
    )
    if run["project_id"] != PROJECT or run["release_id"] != args.release:
        raise ValueError("completed table run differs from the authorized project and release")
    contributions, operations = population(settings, run, source.source_view_id)
    assessed = matched_assessment(frame, reference, source, contributions, operations)
    retain(output / "comparison.json", {
        "outcome": "passed",
        "run": run,
        "source_view_id": source.source_view_id,
        "frozen_reference_sha256": reference_digest,
        "limitations": (
            "Known source and exact-header controls. The retained cases establish no unresolved "
            "correspondence."
        ),
        **assessed,
    })
    if not args.native_only:
        if not (output / "transport.json").is_file():
            transports(
                settings, run, source.source_view_id, assessed["transport_operation"], output
            )
        if not (output / "detached.json").is_file():
            export(run, source.source_view_id, output)


if __name__ == "__main__":
    main()
