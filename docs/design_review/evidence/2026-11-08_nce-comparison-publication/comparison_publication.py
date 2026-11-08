"""Run one source-first, independently adjudicated comparison publication journey."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.evaluate.record_references import assign_origin
from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference,
    StructuralEvaluationFrame,
    create_structural_reference_set,
    record_structural_reference_pass,
)
from corpus_structure.methods.scoped_relations import ScopedRelationsConfig, ScopedRelationsMethod
from corpus_structure.methods.structural_products import (
    StructuralComparisonConfig,
    StructuralComparisonMethod,
    StructuralDossierConfig,
    StructuralDossierMethod,
)
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_admission import read_structural_assertions
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.protocol import QueryContext
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.source_decision_journey import (
    SourceDecisionJourneyParams,
    SourceDecisionJourneyQuery,
)
from corpus_structure.serve.structural_gaps import GapRequest, serve_structural_gap
from corpus_structure.serve.structural_products import StructuralExportRequest
from corpus_structure.settings import Settings

POLICY = "independent-structural-comparison-1"
CLI = Path(sys.executable).with_name("ci")


def data(path):
    return json.loads(path.read_bytes())


def retain(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def cli(*args, stdin=None):
    result = subprocess.run(
        [str(CLI), *map(str, args)], input=stdin, capture_output=True, check=False
    )
    if result.returncode:
        # CI emits its own scoped diagnostic. The driver never passes protected bytes to CI.
        raise RuntimeError(result.stderr.decode() or result.stdout.decode())
    return json.loads(result.stdout), result.stderr.decode()


def locate(args):
    """Return exact projected pieces matching one source-only physical page lead."""
    with (
        open_runtime_engine(Settings(), "nce-compare-locate", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        session = bind_completed_result(conn, args.run_id)
        rows = conn.execute(text("""
            SELECT DISTINCT view.id AS source_view_id, view.section_pointer,
                (piece->>'start')::int AS start, (piece->>'end')::int AS end,
                piece->>'item_ref' AS native_pointer, located.literal
            FROM ops.run_source_view selected
            JOIN kb.source_view view ON view.id=selected.source_view_id
            CROSS JOIN LATERAL jsonb_array_elements(view.projection->'pieces') piece
            CROSS JOIN LATERAL (
                SELECT substring(view.projection->>'text' FROM (piece->>'start')::int+1
                    FOR (piece->>'end')::int-(piece->>'start')::int) AS literal
            ) located
            WHERE selected.run_id=:run AND view.analysis_eligible
              AND piece->>'kind'='native_text' AND NOT piece ? 'cell_index'
              AND strpos(lower(located.literal), lower(:needle))>0
              AND EXISTS(
                SELECT FROM ops.pdf_published_region region
                WHERE region.task_id=view.native_task_id
                  AND region.product_key=view.native_product_key
                  AND region.pointer=piece->>'item_ref' AND region.page_no=:page
              )
            ORDER BY view.id, start
            LIMIT 32
            """), {"run": args.run_id, "page": args.page, "needle": args.needle}
        ).mappings()
        print(json.dumps({
            "run_id": args.run_id, "cut_id": session.completed_cut_id,
            "physical_page": args.page, "matches": [dict(row) for row in rows],
        }, ensure_ascii=False))


def prepare_scope(args):
    spec = data(args.spec)
    selections = tuple(StructuralPassageSelection.model_validate(x) for x in spec["passages"])
    if len(selections) != 2:
        raise ValueError("comparison preparation requires two selected source passages")
    with open_runtime_engine(Settings(), "nce-compare-excerpts", purpose="read") as engine:
        selected = prepare_structural_sources(engine, selections)
    if any(source.project_id != spec["project_id"] for source in selected.sources):
        raise ValueError("selected excerpts belong to another project")
    from corpus_structure.semantic.structural_products import StructuralInput

    inputs = StructuralInput(
        question=spec["question"], scope=spec["scope"], inventory_id=spec["inventory_id"],
        policy_id=spec["policy_id"], sources=selected.sources, passages=selected.passages,
        dependencies=tuple(s.identity for s in selected.sources),
    )
    retain(args.destination, {
        "project_id": spec["project_id"], "release_id": spec["release_id"],
        "configuration": {
            "inputs": inputs.model_dump(mode="json"), "structural_input_digest": inputs.identity,
        },
    })


def readings(args):
    """List exact retained readings for a selected passage before assembling the run."""
    with (
        open_runtime_engine(Settings(), "nce-compare-readings", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        session = bind_completed_result(conn, args.run_id)
        rows = conn.execute(text("""
            SELECT member.task_id AS selected_task_id, member.origin_task_id,
                   producer.project_id, producer.runtime_id AS runtime_fingerprint,
                   item->>'contribution_id' AS contribution_id, item->'component' AS reading,
                   frame->'component' AS frame
            FROM ops.cut_task member
            JOIN ops.task origin ON origin.id=member.origin_task_id
            JOIN ops.run producer ON producer.id=origin.run_id
            JOIN ops.task_result result ON result.task_id=origin.id
            CROSS JOIN LATERAL jsonb_array_elements(result.body->'contributions') item
            JOIN LATERAL jsonb_array_elements(result.body->'contributions') frame
              ON frame->>'contribution_id'=item->'component'->>'frame'
            WHERE member.cut_id=:cut AND result.body->>'method'='structure.scoped_relations'
              AND item->'component'->>'kind'='predicate_reading'
              AND item->'component'->>'scope'=:passage
            ORDER BY member.task_id, item->>'contribution_id'
            LIMIT 32
            """), {"cut": session.completed_cut_id, "passage": args.passage}
        ).mappings()
        print(json.dumps({
            "passage": args.passage, "run_id": args.run_id, "cut_id": session.completed_cut_id,
            "release_id": session.binding.release_id,
            "result_revision": session.binding.data_revision,
            "matches": [dict(row) for row in rows],
        }, ensure_ascii=False))


def freeze(args):
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    spec = data(args.spec)
    frame = StructuralEvaluationFrame.model_validate(spec["frame"])
    if (
        frame.operation != "qualified_comparison"
        or frame.direction != "source_first"
        or frame.partition != "development"
        or frame.rubric_version != POLICY
        or len(frame.inputs.passages) != 2
        or len({source.project_id for source in frame.inputs.sources}) != 1
        or any(source.project_id != spec["project_id"] for source in frame.inputs.sources)
    ):
        raise ValueError("this driver requires a source-first two-passage development comparison")
    with (
        open_runtime_engine(Settings(), "nce-compare-freeze", purpose="evaluate") as engine,
        engine.begin() as conn,
    ):
        if origin := spec.get("assign_origin"):
            assign_origin(conn, project_id=spec["project_id"], partition=frame.partition, **origin)
        set_id = create_structural_reference_set(
            conn, project_id=spec["project_id"], release_id=spec["release_id"], frame=frame
        )
    retain(args.receipt, {
        "project_id": spec["project_id"], "release_id": spec["release_id"],
        "set_id": set_id, "frame_digest": frame.identity,
        "spec_sha256": sha256(args.spec.read_bytes()).hexdigest(),
    })


def packet(args):
    spec, freeze_receipt = data(args.spec), data(args.freeze_receipt)
    frame = StructuralEvaluationFrame.model_validate(spec["frame"])
    if (
        frame.identity != freeze_receipt["frame_digest"]
        or sha256(args.spec.read_bytes()).hexdigest() != freeze_receipt["spec_sha256"]
    ):
        raise ValueError("packet differs from the frozen source frame")
    sources = {source.identity: source for source in frame.inputs.sources}
    with (
        open_runtime_engine(Settings(), "nce-compare-author-shape", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = open_release(conn, spec["release_id"])
        schema, = (
            artifact.content for artifact in prepared.artifacts
            if artifact.kind == "json_schema/StructuralPublicStatement"
        )
    retain(args.destination, {
        "frame_digest": frame.identity, "question": frame.inputs.question,
        "scope": frame.inputs.scope, "inventory_id": frame.inputs.inventory_id,
        "input_policy_id": frame.inputs.policy_id, "coverage_limits": frame.inputs.coverage_limits,
        "exclusions": [x.model_dump(mode="json") for x in frame.inputs.exclusions],
        "rubric": frame.rubric_text, "inspected_scope": frame.inspected_scope,
        "passages": [
            {
                **p.model_dump(mode="json", exclude={"source_ref"}, exclude_none=True),
                "source": sources[p.source_ref].model_dump(
                    mode="json", exclude_none=True, exclude={
                        "run_id", "cut_id", "release_id", "result_revision",
                        "source_view_id", "native_task_id",
                    }
                ),
            }
            for p in frame.inputs.passages
        ],
        "opportunities": [o.model_dump(mode="json") for o in frame.opportunities],
        "authoring_schema": StructuralAuthoredReference.model_json_schema(),
        "public_statement_schema": json.loads(schema),
    })


def submit(args):
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    frozen = data(args.freeze_receipt)
    body = args.authored.read_bytes()
    authored = StructuralAuthoredReference.model_validate_json(body)
    if authored.frame_digest != frozen["frame_digest"]:
        raise ValueError("authored reference belongs to another source frame")
    parents = tuple(data(path) for path in args.parents)
    if args.kind == "C":
        if [item["kind"] for item in parents] != ["A", "B"] or any(
            item["set_id"] != frozen["set_id"] or item["frame_digest"] != frozen["frame_digest"]
            for item in parents
        ):
            raise ValueError("C requires exact A and B receipts from this frame")
    elif parents:
        raise ValueError("independent authoring has no parent receipts")
    with (
        open_runtime_engine(Settings(), "nce-compare-submit", purpose="evaluate") as engine,
        engine.begin() as conn,
    ):
        pass_id = record_structural_reference_pass(
            conn, set_id=frozen["set_id"], pass_kind=args.kind, actor=args.actor,
            authored=body, parents=tuple(item["pass_id"] for item in parents),
        )
    retain(args.receipt, {
        "set_id": frozen["set_id"], "frame_digest": frozen["frame_digest"],
        "kind": args.kind, "pass_id": pass_id, "content_digest": sha256(body).hexdigest(),
        "parents": [item["pass_id"] for item in parents],
    })


def run(args):
    spec = data(args.spec)
    project, release = spec["project_id"], spec["release_id"]
    output = args.destination
    output.mkdir(parents=True, exist_ok=False)
    admissions = ()
    if args.phase == "dossier":
        method = StructuralDossierMethod()
        config = StructuralDossierConfig.model_validate(spec["configuration"])
    elif args.phase == "scope":
        method = ScopedRelationsMethod()
        config = ScopedRelationsConfig.model_validate(spec["configuration"])
    else:
        method = StructuralComparisonMethod()
        config = StructuralComparisonConfig.model_validate(spec["configuration"])
        frozen = data(args.freeze_receipt)
        frame = StructuralEvaluationFrame.model_validate(spec["frame"])
        if (
            project != frozen["project_id"] or release != frozen["release_id"]
            or config.inputs != frame.inputs or frame.identity != frozen["frame_digest"]
        ):
            raise ValueError("comparison inputs differ from the exact protected source frame")
        if args.phase == "publish":
            c = data(args.c_receipt)
            if (
                c["kind"] != "C"
                or c["set_id"] != frozen["set_id"]
                or c["frame_digest"] != frame.identity
            ):
                raise ValueError("publication requires the exact C adjudication")
            admissions = ({
                "product_id": args.product_id, "set_id": c["set_id"], "c_pass_id": c["pass_id"],
                "c_content_digest": c["content_digest"], "frame_digest": c["frame_digest"],
                "policy_id": POLICY,
            },)
    if config.inputs is None:
        raise ValueError("missing source selection")
    stage = Stage.SCOPE if args.phase == "scope" else Stage.ASSEMBLE
    registry = MethodRegistry(
        (method,), MethodsFile(configs={method.name: {"evidence": config.model_dump(mode="json")}})
    )
    realization = RealizationId(f"nce-comparison:{project}:{output.name}:{args.phase}:{release}")
    with open_runtime_engine(Settings(), "nce-compare-run", purpose="write") as engine:
        with engine.begin() as conn:
            prepared = open_release(conn, release)
            initialize_source_project(
                conn, project_id=ProjectId(project), release_id=ReleaseId(release),
                realization_id=realization, projection_context=prepared,
            )
            realized = table("data.realization")
            revision = conn.execute(
                select(realized.c.data_revision).where(realized.c.realization_id == realization)
            ).scalar_one()
        result = run_source_methods(
            engine, project_id=project, prepared=prepared,
            binding=OperationBinding(release, realization, revision, canonical_bytes({
                "structural_input": config.inputs.identity, "phase": args.phase,
            })),
            registry=registry,
            graph=Graph(
                ((stage, (Step(method.name + "/evidence"),)),), policy_propose=False,
            ),
            method_settings=MethodSettings(
                data_dir=output / "data", model_cache=Path.home() / ".cache/docling/models",
            ),
            guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(),
            selected_sources=config.inputs.sources, structural_admission=admissions,
        )
    retain(output / "source-ready.json", result.model_dump(mode="json"))
    if result.status != "source_ready":
        raise ValueError("selected producer did not reach source readiness")
    finalized, _ = cli(
        "run", "finalize", result.run_id, "--output-realization", f"{realization}:result", "--json",
    )
    retain(output / "finalized.json", finalized)
    with (
        open_runtime_engine(Settings(), "nce-compare-result", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        session = bind_completed_result(conn, result.run_id)
        if args.phase == "scope":
            retain(output / "completed.json", {
                "project_id": project, "run_id": result.run_id,
                "cut_id": session.completed_cut_id, "release_id": session.binding.release_id,
                "result_revision": session.binding.data_revision,
            })
            return
        selected, origin, runtime, raw = conn.execute(
            text("""
            SELECT member.task_id, member.origin_task_id, producer.runtime_id,
                   result.body->'structural_product'
            FROM ops.cut_task member
            JOIN ops.task origin ON origin.id=member.origin_task_id
            JOIN ops.run producer ON producer.id=origin.run_id
            JOIN ops.task_result result ON result.task_id=origin.id
            WHERE member.cut_id=:cut AND result.body->'structural_product'->>'kind'=:kind
            """),
            {
                "cut": session.completed_cut_id,
                "kind": "dossier" if args.phase == "dossier" else "qualified_comparison",
            },
        ).one()
        report = StructuralProductReport.model_validate(raw)
        if report.inputs != config.inputs:
            raise ValueError("completed product differs from selected source inputs")
        receipt = {
            "project_id": project, "run_id": result.run_id,
            "cut_id": session.completed_cut_id, "release_id": session.binding.release_id,
            "result_revision": session.binding.data_revision,
            "selected_task_id": selected, "origin_task_id": origin,
            "runtime_fingerprint": runtime, "product_id": report.product_id,
        }
        if args.phase == "publish":
            if report.product_id != args.product_id:
                raise ValueError("public rerun differs from the exact independently judged product")
            assertion, = read_structural_assertions(
                conn, release_id=release, realization_id=session.binding.realization_id,
                product_ids=(report.product_id,),
            )
            if (
                assertion["cut_id"] != session.completed_cut_id
                or assertion["selected_task_id"] != selected
                or assertion["origin_task_id"] != origin
                or assertion["policy_id"] != POLICY
            ):
                raise ValueError("publication does not bind the exact comparison")
            receipt["assertion_id"] = assertion["assertion_id"]
    retain(output / "completed.json", receipt)


async def mcp_call(run_id, tool, request):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command=str(CLI), args=["mcp", "serve", "--semantic-run", str(run_id)],
    )
    async with Client(transport, timeout=120) as client:
        response = await client.call_tool(tool, {"request": request})
        return response.structured_content


def verify_journey(request, journey):
    binding = request.binding_task
    layers = {layer.layer: layer for layer in journey.layers}
    if layers.keys() != {"comparison", "dossier"} or any(
        (layer.run_id, layer.cut_id, layer.task_id) != (pin.run_id, pin.cut_id, pin.task_id)
        for layer, pin in ((layers["comparison"], request), (layers["dossier"], binding))
    ):
        raise ValueError("journey layers must identify the exact comparison and dossier gap")
    with (
        open_runtime_engine(Settings(), "nce-compare-journey", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        row, = SourceDecisionJourneyQuery().rows(QueryContext(request.run_id, conn), journey)
        expected = row.row.model_dump(mode="json")
    payload = journey.model_dump(mode="json", exclude_none=True)
    installed, _ = cli(
        "query", "source_decision_journey", "--run", request.run_id,
        "--project", journey.opportunity.source.project_id,
        "--param", "opportunity=" + json.dumps(payload["opportunity"]),
        "--param", "layers=" + json.dumps(payload["layers"]), "--json",
    )
    fresh = asyncio.run(mcp_call(
        request.run_id, "source_decision_journey",
        {**payload, "run_id": request.run_id, "cut_id": request.cut_id},
    ))
    if installed["rows"] != [expected] or fresh != expected:
        raise ValueError("joined journey differs between Reader, CLI and fresh MCP")
    return {
        "source_capture": expected["source_capture"],
        "layers": {row["layer"]: row["status"] for row in expected["layers"]},
    }


def verify(args):
    request = GapRequest.model_validate(data(args.request))
    if (
        request.report != "unconnected_supported_comparison"
        or request.cut_id is None
        or request.binding_task is None
        or request.binding_task.cut_id is None
    ):
        raise ValueError("verification requires exact comparison and dossier custody pins")
    binding = request.binding_task
    with (
        open_runtime_engine(Settings(), "nce-compare-reader", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        expected = serve_structural_gap(conn, request).model_dump(mode="json")
        session = bind_completed_result(conn, request.run_id)
        assertions = read_structural_assertions(
            conn, release_id=session.binding.release_id,
            realization_id=session.binding.realization_id, product_ids=(args.product_id,),
        )
        admitted = [
            row for row in assertions
            if (row["selected_task_id"], row["cut_id"]) == (request.task_id, request.cut_id)
        ]
        if len(admitted) != 1:
            raise ValueError("no uniquely admitted assertion for the exact selected comparison")
    rows = expected["rows"]
    if expected["status"] != args.expected_status:
        raise ValueError("gap standing differs from independent expectation")
    if args.expected_status == "actionable":
        if len(rows) != 1 or set(rows[0]["evidence"]["sides"]) != set(args.side) or not any(
            value["assertion_id"] == admitted[0]["assertion_id"]
            for value in rows[0]["evidence"]["support"]
        ):
            raise ValueError("actionable sides or assertion support differ")
    elif args.side:
        raise ValueError("expected sides apply only to actionable rows")
    options = {
        "run": request.run_id, "cut": request.cut_id, "task": request.task_id,
        "binding-run": binding.run_id, "binding-cut": binding.cut_id,
        "binding-task": binding.task_id, "source-view": request.source_view_id,
        "scope": request.scope, "occurrence": request.occurrence_id,
        "operation": request.operation_key, "limit": request.limit, "max-bytes": request.max_bytes,
        "cursor": request.cursor,
    }
    installed, _ = cli(
        "structure", "gap", request.report,
        *(
            part for key, value in options.items()
            if value is not None for part in (f"--{key}", value)
        ),
        "--json",
    )
    fresh = asyncio.run(mcp_call(
        request.run_id, "structural_gap", request.model_dump(mode="json", exclude_none=True),
    ))
    if installed != expected or fresh != expected:
        raise ValueError("Reader, installed CLI and fresh MCP returned different gap pages")
    journey = None
    backing_tasks = ()
    joined = None
    if args.journey:
        journey = SourceDecisionJourneyParams.model_validate(data(args.journey))
        joined = verify_journey(request, journey)
        if args.expected_status == "actionable" and (
            joined["source_capture"] != "represented"
            or joined["layers"]["comparison"] != "observed"
            or joined["layers"]["dossier"] != "inspected_empty"
        ):
            raise ValueError("source-to-decision journey did not reach the unbound comparison")
        backing_tasks = (
            StructuralExportRequest(
                run_id=request.run_id, cut_id=request.cut_id, selected_task_id=request.task_id,
                kind="qualified_comparison", include_publication=True,
            ),
            StructuralExportRequest(
                run_id=binding.run_id, cut_id=binding.cut_id, selected_task_id=binding.task_id,
                kind="dossier",
            ),
        )
    selection = ReviewSelection(
        structural_gap_selections=(request,), require_original_gap_reports=True,
        source_decision_journeys=(journey,) if journey else (), structural_selections=backing_tasks,
    )
    if args.selection:
        retain(args.selection, selection.model_dump(mode="json", exclude_none=True))
    print(json.dumps({
        "comparison": request.model_dump(mode="json"), "product_id": args.product_id,
        "assertion_id": admitted[0]["assertion_id"], "status": expected["status"],
        "unconnected_sides": args.side, "journey": joined, "outcome": "passed",
    }))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in (
        "locate", "prepare-scope", "readings", "freeze", "packet", "submit", "run", "verify",
    ):
        sub = commands.add_parser(name)
        sub.set_defaults(action=globals()[name.replace("-", "_")])
        if name == "locate":
            sub.add_argument("run_id", type=int)
            sub.add_argument("page", type=int)
            sub.add_argument("needle")
        if name == "readings":
            sub.add_argument("run_id", type=int)
            sub.add_argument("passage")
        if name in {"prepare-scope", "freeze", "packet", "run"}:
            sub.add_argument("spec", type=Path)
        if name in {"packet", "submit"}:
            sub.add_argument("freeze_receipt", type=Path)
        if name in {"freeze", "submit"}:
            sub.add_argument("receipt", type=Path)
        if name in {"prepare-scope", "packet", "run"}:
            sub.add_argument("destination", type=Path)
        if name == "submit":
            sub.add_argument("kind", choices=("A", "B", "C"))
            sub.add_argument("actor")
            sub.add_argument("authored", type=Path)
            sub.add_argument("--parents", type=Path, nargs=2, default=())
        if name == "run":
            sub.add_argument("phase", choices=("scope", "candidate", "publish", "dossier"))
            sub.add_argument("--freeze-receipt", type=Path)
            sub.add_argument("--c-receipt", type=Path)
            sub.add_argument("--product-id")
        if name == "verify":
            sub.add_argument("request", type=Path)
            sub.add_argument("product_id")
            sub.add_argument("expected_status", choices=("actionable", "empty", "unavailable"))
            sub.add_argument("--side", choices=("left", "right"), action="append", default=[])
            sub.add_argument("--selection", type=Path)
            sub.add_argument("--journey", type=Path)
    args = parser.parse_args()
    if args.command == "run":
        if args.phase in {"candidate", "publish"} and args.freeze_receipt is None:
            parser.error("comparison runs require --freeze-receipt")
        if args.phase == "publish" and (args.c_receipt is None or not args.product_id):
            parser.error("publication requires --c-receipt and --product-id")
    args.action(args)


if __name__ == "__main__":
    main()
