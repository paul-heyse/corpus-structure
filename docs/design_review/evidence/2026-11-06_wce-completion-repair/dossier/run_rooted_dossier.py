"""Run the rooted dossier policies against one exact published GS120 predecessor."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.structural_products import StructuralDossierMethod
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import (
    RetainedComponentRef,
    RetainedStructuralRef,
    StructuralProductReport,
)
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    export_review_bundle,
    inspect_review_bundle,
)
from corpus_structure.serve.structural_products import (
    DossierRepresentationRequest,
    StructuralExportRequest,
    read_structural_export_page,
    serve_dossier_representation,
)
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
GS120 = HERE.parents[1] / "2026-11-06_wce-gs120"
PROTECTED = GS120 / "assessment/protected-current/native160"
sys.path.insert(0, str(GS120 / "current-structural-journey"))
from journey_support import retain, run_method  # noqa: E402

SOURCE_PINS = {
    "published-predecessor-references.json": (
        "5a6275f84d01c3fbe7b76e71136ba01bb6cc4c0aee168ba954e7989566a75bab"
    ),
    "ordinary-reader-inspection.json": (
        "bb210e98e092cba566f26b4d90bc1cd811577aedf054391ce87feabd45042ce7"
    ),
    "publication-receipt.json": "6597c98260d1bba2f1b236d96817b14c3f7062bcc638780f56eab67e9f72d442",
}
NORMAL = "dd40f6c3f4447b2a25797110af22a04d16d1b35b1ed08f88f9c1922332d515d5"
MARGINAL = "1260f6b3c5b66b10b7d058303de67975cf8e98c4fa748d69c8d788f258aa5989"
POLICIES = ("supported-facet-greedy-1", "source-order-control-1")
BUDGET = 12


def frozen():
    documents = {}
    for filename, expected in SOURCE_PINS.items():
        content = (PROTECTED / filename).read_bytes()
        if sha256(content).hexdigest() != expected:
            raise ValueError(f"frozen protected predecessor file changed: {filename}")
        documents[filename] = json.loads(content)
    recorded = documents["published-predecessor-references.json"]
    source_read = documents["ordinary-reader-inspection.json"]
    receipt = documents["publication-receipt.json"]
    report, = tuple(StructuralProductReport.model_validate(r) for r in source_read["reports"])
    reference = RetainedStructuralRef.model_validate(recorded["structural_reference"])
    roots = {
        item.component_id: item
        for item in map(RetainedComponentRef.model_validate, recorded["component_references"])
    }
    if (
        (reference.run_id, reference.cut_id, reference.selected_task_id, reference.origin_task_id)
        != (169, 225, 956, 800)
        or source_read["task_ids"] != [reference.selected_task_id]
        or report.product_id != reference.product_id
        or receipt["outcome"] != "passed"
        or receipt["public_assertions"] != 2
        or set(roots) != {NORMAL, MARGINAL}
        or report.definition_components is None
    ):
        raise ValueError("frozen predecessor identity differs from protected publication")
    by_id = {c.component_id: c for c in report.definition_components.components}
    normal, unrelated = by_id[NORMAL], by_id[MARGINAL]
    if (normal.term.text, unrelated.term.text) != (
        "The normal density function", "marginal totals",
    ):
        raise ValueError("normal and unrelated component labels differ from the frozen subjects")
    for component in (normal, unrelated):
        component_reference = roots[component.component_id]
        candidate = component_reference.model_dump(
            exclude={"component_id", "operation_id", "operation_version", "dependencies"},
        )
        if (
            RetainedStructuralRef.model_validate(candidate) != reference
            or component_reference.dependencies != report.inputs.dependencies
        ):
            raise ValueError("component source custody differs from exact selected report")
    protected_by_term = {
        item["statement"]["definition_component"]["term"]["text"]: item
        for item in recorded["published_support_assertions"]
    }
    normal_support = protected_by_term[normal.term.text]
    unrelated_support = protected_by_term[unrelated.term.text]
    if normal_support["assessment_id"] == unrelated_support["assessment_id"]:
        raise ValueError("normal and unrelated components must have distinct protected support")
    inputs = report.inputs.model_copy(
        update={
            "question": "Which retained members have evidence for the normal-density sense?",
            "inventory_id": "gs120-rooted-normal-density-dossier-1",
            "dependencies": (*report.inputs.dependencies, report.product_id, NORMAL),
        }
    )
    return (
        inputs, report, reference, roots[NORMAL], normal, unrelated,
        normal_support, unrelated_support,
    )


def preflight_receipt(report, reference, root, normal, unrelated, positive, negative):
    return {
        "outcome": "passed",
        "scope": "immutable source files and distinct supported components; detached read only",
        "frozen_sha256": SOURCE_PINS,
        "predecessor": reference.model_dump(mode="json"),
        "root_component": root.model_dump(mode="json"),
        "available_components": len(report.definition_components.components),
        "required_citations": [
            span.model_dump(mode="json") for span in (normal.term, normal.content)
        ],
        "unrelated_component": unrelated.model_dump(mode="json"),
        "required_assessment_id": positive["assessment_id"],
        "unrelated_assessment_id": negative["assessment_id"],
    }


def retained_predecessor(settings, reference, report, positive, negative):
    request = StructuralExportRequest(
        run_id=reference.run_id,
        cut_id=reference.cut_id,
        kind="definition_components",
        include_publication=True,
        include_support=True,
        max_bytes=8_000_000,
    )
    with (
        open_runtime_engine(settings, "wce-rooted-dossier-predecessor", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        page = read_structural_export_page(conn, request)
    if (
        page.reports != (report,)
        or page.task_ids != (reference.selected_task_id,)
        or page.release_id != reference.release_id
    ):
        raise ValueError("ordinary reader predecessor differs from frozen exact selected report")
    stored = {
        item["assertion_id"]: item.get("statement")
        for item in page.public_assertions
    }
    for assertion in (positive, negative):
        if stored.get(assertion["assessment_id"]) != assertion["statement"]:
            raise ValueError("ordinary reader lost or substituted a frozen protected assertion")
    return request, page


def inspect_policy(settings, run, root, normal, unrelated, positive, negative, directory):
    request = StructuralExportRequest(
        run_id=run["run_id"], cut_id=run["cut_id"], kind="dossier", max_bytes=8_000_000,
    )
    with (
        open_runtime_engine(settings, "wce-rooted-dossier-reader", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        complete = read_structural_export_page(conn, request)
        report, = complete.reports
        task, = complete.task_ids
        dossier = report.dossier
        if dossier is None or dossier.root_id != NORMAL or dossier.root_component != root:
            raise ValueError("native dossier lost its exact root binding")
        if len(dossier.members) != 2:
            raise ValueError("rooted membership must contain the exact term and content")
        expected = {
            ("terminology", normal.term),
            ("definition", normal.content),
        }
        if {(member.role, member.citation) for member in dossier.members} != expected:
            raise ValueError("rooted membership includes an unrelated or incorrect citation")
        if any(
            member.sense != NORMAL or member.qualification != "independently_supported"
            or member.assessment_id != positive["assessment_id"]
            or member.relation_product_id != root.product_id
            for member in dossier.members
        ):
            raise ValueError("rooted membership changed sense, predecessor or support")
        if len(dossier.supported_facets) != 2 or {
            facet.member_id for facet in dossier.supported_facets
        } != {member.member_id for member in dossier.members}:
            raise ValueError("supported facets differ from the qualified root members")
        if any(
            member.citation in (unrelated.term, unrelated.content)
            or member.assessment_id == negative["assessment_id"]
            for member in dossier.members
        ):
            raise ValueError("same-report unrelated supported component entered the dossier")
        representation = DossierRepresentationRequest(
            run_id=run["run_id"], cut_id=run["cut_id"], task_id=task, limit=1,
        )
        first = serve_dossier_representation(conn, representation)
        if first.continuation is None:
            raise ValueError("one-item page failed to emit the second member continuation")
        second = serve_dossier_representation(
            conn, representation.model_copy(update={"continuation": first.continuation}),
        )
        if second.continuation is not None:
            raise ValueError("exact two-member dossier must end on the second page")
        forged = first.continuation.model_copy(
            update={"product_id": "structural:" + MARGINAL},
        )
        wrong_members = first.continuation.model_copy(update={"membership_digest": "0" * 64})
        refusals = {}
        controls = (("substituted_product", forged), ("substituted_membership", wrong_members))
        for name, cursor in controls:
            try:
                serve_dossier_representation(
                    conn, representation.model_copy(update={"continuation": cursor}),
                )
            except SemanticRefusal as error:
                refusals[name] = {"type": type(error).__name__, "message": str(error)}
            else:
                raise ValueError(f"ordinary Reader accepted a forged continuation: {name}")
    pages = [page.model_dump(mode="json") for page in (first, second)]
    selected_ids = tuple(member["member_id"] for page in pages for member in page["members"])
    if selected_ids != dossier.representatives:
        raise ValueError("bounded pages differ from exact representative identity order")
    for page in pages:
        if (
            page["full_member_count"] != 2
            or page["membership_digest"] != dossier.representation.membership_digest
            or page["facet_digest"] != dossier.representation.facet_digest
        ):
            raise ValueError("bounded pages altered full member/facet context")
    retain(directory / "ordinary-full.json", complete.model_dump(mode="json"))
    retain(directory / "ordinary-pages.json", pages)
    retain(directory / "ordinary-refusals.json", refusals)
    return request, representation, pages, dossier


def check_cli_mcp(representation, expected, directory):
    """Compare each fresh stdio and CLI page with the ordinary completed-cut reader."""
    import anyio
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    cli = Path(sys.executable).with_name("ci")
    args = representation.model_dump(mode="json", exclude_none=True)
    all_cli = []
    for index, page in enumerate(expected):
        command = [
            str(cli), "structure", "dossier-page", "--run", str(args["run_id"]),
            "--cut", str(args["cut_id"]), "--task", str(args["task_id"]),
            "--limit", str(args["limit"]), "--max-bytes", str(args["max_bytes"]), "--json",
        ]
        if index:
            cursor_json = canonical_bytes(expected[index - 1]["continuation"]).decode()
            command.extend(("--continuation", cursor_json))
        result = subprocess.run(command, cwd=ROOT, capture_output=True, check=False, timeout=180)
        (directory / f"cli-{index + 1}.stdout").write_bytes(result.stdout)
        (directory / f"cli-{index + 1}.stderr").write_bytes(result.stderr)
        if result.returncode or canonical_bytes(json.loads(result.stdout)) != canonical_bytes(page):
            raise ValueError("fresh CLI page differs from ordinary Reader")
        all_cli.append(json.loads(result.stdout))

    async def transport_pages():
        transport = StdioTransport(
            command=str(cli), args=["mcp", "serve", "--semantic-run", str(args["run_id"])],
            cwd=str(ROOT), log_file=directory / "mcp-server.log",
        )
        async with Client(transport, timeout=180) as client:
            inventory = await client.list_tools()
            retain(
                directory / "mcp-tools.json", [tool.model_dump(mode="json") for tool in inventory],
            )
            if "dossier_representation" not in {tool.name for tool in inventory}:
                raise ValueError("fresh MCP inventory lacks dossier representation")
            cursor = None
            for index, page in enumerate(all_cli):
                request = {**args, **({"continuation": cursor} if cursor else {})}
                result = await client.call_tool(
                    "dossier_representation", {"request": request}, raise_on_error=False,
                )
                actual = result.structured_content
                if result.is_error or canonical_bytes(actual) != canonical_bytes(page):
                    raise ValueError("fresh MCP page differs from exact CLI and ordinary Reader")
                retain(directory / f"mcp-page-{index + 1}.json", actual)
                cursor = actual.get("continuation")
            original = all_cli[0]["continuation"]
            for name, forged in (
                ("substituted_product", {**original, "product_id": "structural:" + MARGINAL}),
                ("substituted_membership", {**original, "membership_digest": "0" * 64}),
            ):
                result = await client.call_tool(
                    "dossier_representation", {"request": {**args, "continuation": forged}},
                    raise_on_error=False,
                )
                retain(directory / f"mcp-refused-{name}.json", {
                    "is_error": result.is_error,
                    "content": [part.model_dump(mode="json") for part in result.content],
                })
                if not result.is_error:
                    raise ValueError(f"fresh MCP accepted a forged continuation: {name}")

    anyio.run(transport_pages)


def run(args, output, frozen_values):
    inputs, report, reference, root, normal, unrelated, positive, negative = frozen_values
    settings = Settings()
    retain(output / "frozen-preflight.json", preflight_receipt(*frozen_values[1:]))
    with (
        open_runtime_engine(settings, "wce-rooted-dossier-release", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = load_release(conn, args.release)
    source_request, source_page = retained_predecessor(
        settings, reference, report, positive, negative,
    )
    retain(output / "retained-predecessor-reader.json", source_page.model_dump(mode="json"))
    retain(output / "input-closure.json", inputs.model_dump(mode="json"))
    dossiers, requests, outcomes = [], [], {}
    for policy in POLICIES:
        directory = output / policy
        complete_run = run_method(
            settings, prepared, StructuralDossierMethod(),
            {
                "inputs": inputs.model_dump(mode="json"),
                "structural_input_digest": inputs.identity,
                "root_component": root.model_dump(mode="json"),
                "predecessors": [reference.model_dump(mode="json")],
                "contribution_predecessors": [],
                "member_budget": BUDGET,
                "policy": policy,
            },
            inputs, directory, f"rooted-dossier-{policy}", f"wce-r17-{output.name}",
        )
        if complete_run["release_id"] != args.release:
            raise ValueError("rooted dossier completed under the wrong release")
        request, representation, pages, dossier = inspect_policy(
            settings, complete_run, root, normal, unrelated, positive, negative, directory,
        )
        if (
            dossier.representation.policy != policy
            or dossier.representation.member_budget != BUDGET
        ):
            raise ValueError("native dossier substituted policy or member budget")
        check_cli_mcp(representation, pages, directory)
        dossiers.append(dossier)
        requests.append(request)
        outcomes[policy] = {
            "run": complete_run,
            "member_count": len(dossier.members),
            "member_budget": BUDGET,
            "selected": list(dossier.representatives),
            "represented_facets": list(dossier.representation.represented_facets),
            "omitted": list(dossier.representation.omitted),
            "membership_digest": dossier.representation.membership_digest,
            "facet_digest": dossier.representation.facet_digest,
            "ordinary_cli_mcp_pages": len(pages),
        }
    a, b = dossiers
    if a.members != b.members or a.supported_facets != b.supported_facets:
        raise ValueError("equal-budget policies altered full rooted members or supported facets")
    selection = ReviewSelection(
        structural_selections=(source_request, *requests), max_bytes=512_000_000,
    )
    destination = output / "review"
    manifest = export_review_bundle(selection, destination, settings)
    detached = inspect_review_bundle(destination)
    retain(output / "portable-receipt.json", {"manifest": manifest, "detached": detached})
    retain(output / "result.json", {
        "outcome": "passed",
        "scope": "exact normal-density provisional root over one unchanged published predecessor",
        "root_component": root.model_dump(mode="json"),
        "excluded_supported_component": unrelated.component_id,
        "equal_membership_and_supported_facets": True,
        "policies": outcomes,
        "portable_bundle": "review",
        "limits": (
            "Both policies can display all qualified members within budget. "
            "Scope is limited to the provisional root and its retained members."
        ),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--release", help="exact admitted release for the new dossier operations")
    parser.add_argument("--preflight", action="store_true", help="verify immutable inputs offline")
    args = parser.parse_args()
    values = frozen()
    if args.preflight:
        print(json.dumps(preflight_receipt(*values[1:]), ensure_ascii=False, indent=2))
        return
    if args.output is None or args.release is None:
        parser.error("native execution requires output and --release")
    output = args.output.resolve()
    if HERE not in output.parents:
        parser.error("output must be inside the dossier evidence folder")
    output.mkdir()
    try:
        run(args, output, values)
    except BaseException as error:
        retain(output / "failure.json", {
            "outcome": "failed", "type": type(error).__name__, "message": str(error),
        })
        raise


if __name__ == "__main__":
    main()
