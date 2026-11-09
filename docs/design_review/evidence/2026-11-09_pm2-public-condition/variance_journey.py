"""Bounded PM2-08 exercise: use only the original retained variance source and ordinary owners."""

import argparse
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from sqlalchemy import cast, func, literal, select
from sqlalchemy.dialects.postgresql import JSONPATH
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference,
    StructuralEvaluationFrame,
    StructuralReferenceCase,
    StructuralSourceGroup,
    StructuralSourceOpportunity,
    create_structural_reference_set,
    record_structural_reference_pass,
)
from corpus_structure.methods.scoped_relations import ScopedRelationsWithRoleClosure
from corpus_structure.methods.structural_products import ConditionQualificationMethod
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader, OperationBinding
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import StructuralInput, StructuralProductReport
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings

SOURCE_RUN, SOURCE_CUT, VIEW = 297, 413, 177
ARCHIVED_RUN, ARCHIVED_CUT, ARCHIVED_TASK = 320, 441, 1498
SCOPE = "gs518-view-177"
REFERENCE_DESIGNS = {
    "phrase": (
        "independent-condition-qualification-1",
        "Exact source qualifier and its uniquely supported predicate",
        "p289-variance-qualifier",
    ),
    "role-anchors": (
        "independent-condition-qualification-1",
        "Complete stated qualifier clause and exact lexical host predicate member; source-only",
        "p289-variance-role-anchors",
    ),
}
ARCHIVED_ATTACHMENT = (
    "source-contribution:b50cca3c8385e5f63a74a64a6ebcb5381049ad3c28642fb1f96b4b865040f972"
)
# Absolute offsets on the immutable projection of physical page 289. Include the
# beginning of the next sentence, not just the earlier cue or the host token.
START, END = 116783, 116907


def selected(engine, run, *, view_id=VIEW, start=START, end=END):
    result = prepare_structural_sources(
        engine,
        (
            StructuralPassageSelection(
                run_id=run,
                source_view_id=view_id,
                passage_id=SCOPE,
                start=start,
                end=end,
                scope=SCOPE,
            ),
        ),
    )
    return StructuralInput(
        question="Which exact stated assumption or condition qualifies the neighboring predicate?",
        scope=SCOPE,
        inventory_id="pm2-p289-original-source",
        policy_id="pm2-p289-exact-conditioned-predicate",
        sources=result.sources,
        passages=result.passages,
        dependencies=("retained-original-source",),
    )


def current_projection(engine, run, original, release, native_baseline):
    from corpus_structure.semantic.source_views import load_source_view

    (expected,) = original.passages
    views, membership = map(table, ("kb.source_view", "ops.run_source_view"))
    with read_snapshot(engine) as conn:
        baseline = conn.execute(select(views).where(views.c.id == native_baseline)).mappings().one()
        old = load_source_view(conn, VIEW, analysis=False)
        if baseline["document_id"] != old.ref.document_id:
            raise ValueError("native alternate baseline belongs to a different original document")
        view_id = conn.execute(
            select(views.c.id)
            .join(membership, membership.c.source_view_id == views.c.id)
            .where(
                membership.c.run_id == run,
                views.c.release_id == release,
                views.c.native_task_id == baseline["native_task_id"],
                views.c.native_product_key == baseline["native_product_key"],
                views.c.native_content_digest == baseline["native_content_digest"],
                views.c.section_pointer == baseline["section_pointer"],
                views.c.membership == baseline["membership"],
            )
        ).scalar_one()
        new = load_source_view(conn, view_id, analysis=False)

    def role_block(view, start):
        (piece,) = (
            piece
            for piece in view.pieces
            if piece.get("item_ref") is not None and piece["start"] <= start < piece["end"]
        )
        (item,) = (item for item in view.items if item["self_ref"] == piece["item_ref"])
        if not any(loc["page_no"] == 289 for loc in item.get("prov", ())):
            raise ValueError("role source is not grounded on physical p289")
        return piece, view.text[piece["start"] : piece["end"]], item

    if new.text.count(expected.text) != 1:
        raise ValueError(
            "reprojected source must contain the complete independent passage exactly once"
        )
    start = new.text.index(expected.text)
    old_piece, old_text, old_item = role_block(old, expected.start)
    new_piece, new_text, new_item = role_block(new, start)
    if (old_text, old_piece.get("source_field", "text"), old_item["prov"]) != (
        new_text,
        new_piece.get("source_field", "text"),
        new_item["prov"],
    ):
        raise ValueError("current projection changed the physical role-bearing source item")
    if start - new_piece["start"] != expected.start - old_piece["start"]:
        raise ValueError("current projection moved the roles inside the physical source item")
    rebound = selected(engine, run, view_id=view_id, start=start, end=start + len(expected.text))
    if rebound.passages[0].text != expected.text:
        raise ValueError("new coordinates do not reproduce the exact independent source passage")
    return rebound, new_piece["item_ref"]


def report_meta(conn, run, method, *, view_id=VIEW, role_pointer="#/texts/5253"):
    session = bind_completed_result(conn, run)
    member, task, result, origin_run = map(
        table, ("ops.cut_task", "ops.task", "ops.task_result", "ops.run")
    )
    if method == "structure.scoped_relations":
        # Transport only the selected premise and attachment population, not the
        # potentially large immutable whole-view predicate report.
        selector = cast(
            literal(
                '$.contributions[*] ? (@.component.qualifier_kind == "assumption" || '
                '(@.component.cue_kind == "assumption" && @.anchors[*].pointer == '
                + json.dumps(role_pointer)
                + "))"
            ),
            JSONPATH,
        )
        payload = func.jsonb_build_object(
            "contributions", func.jsonb_path_query_array(result.c.body, selector)
        )
    else:
        payload = func.jsonb_build_object("structural_product", result.c.body["structural_product"])
    selected_id, origin, runtime, body = conn.execute(
        select(member.c.task_id, member.c.origin_task_id, origin_run.c.runtime_id, payload)
        .select_from(member)
        .join(result, result.c.task_id == member.c.origin_task_id)
        .join(task, task.c.id == member.c.origin_task_id)
        .join(origin_run, origin_run.c.id == task.c.run_id)
        .where(
            member.c.cut_id == session.completed_cut_id,
            result.c.body["method"].as_string() == method,
        )
        .where((task.c.unit_type == "run") | (task.c.unit_id == view_id))
    ).one()
    return session, selected_id, origin, runtime, body


def reference(source, run, session, selected_id, origin, runtime, contribution_id):
    return RetainedContributionRef(
        contribution_id=contribution_id,
        project_id=source.project_id,
        run_id=run,
        cut_id=session.completed_cut_id,
        release_id=session.binding.release_id,
        result_revision=session.binding.data_revision,
        selected_task_id=selected_id,
        origin_task_id=origin,
        runtime_fingerprint=runtime,
    )


def condition_edge(body, role_pointer):
    # Source-only packet and judgments have already frozen the named opportunity.
    cue = {
        row["contribution_id"]
        for row in body["contributions"]
        if row.get("component", {}).get("cue_kind") == "assumption"
        and any(
            a["pointer"] == role_pointer and "positive variance" in a["source_piece"]
            for a in row.get("anchors", ())
        )
    }
    (edge,) = (
        row["contribution_id"]
        for row in body["contributions"]
        if row.get("component", {}).get("qualifier_kind") == "assumption"
        and row["component"]["qualifier_contribution_id"] in cue
    )
    return edge


def authored_payload(frame, judgment, role_pointer):
    (source,) = frame.inputs.sources
    (passage,) = frame.inputs.passages
    physical = source.model_dump(
        mode="json",
        exclude={
            "run_id",
            "cut_id",
            "release_id",
            "result_revision",
            "source_view_id",
            "native_task_id",
        },
    )

    def citation(text):
        if not text or passage.text.count(text) != 1:
            raise ValueError("independently specified endpoint is not unique in the frozen source")
        start = passage.start + passage.text.index(text)
        return {
            "source_pointer": role_pointer,
            "passage": {
                "source": physical,
                "scope": SCOPE,
                "start": start,
                "end": start + len(text),
                "text": text,
            },
        }

    if set(judgment) != {"relation", "qualifier", "host_predicate", "explanation"}:
        raise ValueError("source judgment differs from the source-only supported statement shape")
    if judgment["relation"] not in {"condition", "assumption"}:
        raise ValueError("the adjudicator did not support a released condition-family relation")
    statement = {
        "version": "structural-public-statement-3",
        "kind": "condition_qualification",
        "scope": SCOPE,
        "coverage_limits": [],
        "exclusions": [],
        "condition_qualification": {
            "relation": judgment["relation"],
            "qualifier": [citation(judgment["qualifier"])],
            "host_predicate": [citation(judgment["host_predicate"])],
        },
    }
    return canonical_bytes(
        StructuralAuthoredReference(
            frame_digest=frame.identity,
            cases=(
                StructuralReferenceCase(
                    case_id=frame.opportunities[0].opportunity_id,
                    facet="public_statement",
                    path=("public_statement",),
                    expected=statement,
                    source_passages=(SCOPE,),
                    judgment="supported",
                    explanation=judgment["explanation"],
                ),
            ),
        ).model_dump(mode="json", exclude_none=True)
    )


def verify_delivery(settings, publication, root):
    import anyio
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    from corpus_structure.serve.review_bundle import ReviewSelection
    from corpus_structure.serve.structural_products import (
        StructuralExportRequest,
        StructuralPage,
        StructuralRequest,
        serve_structural_products,
    )

    if publication["outcome"] != "published":
        raise ValueError("delivery requires a completed native public assertion")
    command = str(Path(sys.executable).with_name("ci"))
    env = os.environ | {"CORPUS_RUNTIME__DEFAULT_PROJECT": "nce-grinstead-snell-full-book"}
    run_id, cut_id = publication["run_id"], publication["cut_id"]
    request = StructuralRequest(
        run_id=run_id,
        cut_id=cut_id,
        kind="condition_qualification",
        include_publication=True,
        include_support=True,
    )

    def cli(*args, body=None, timeout=180):
        try:
            completed = subprocess.run(
                (command, *args),
                input=body,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                timeout=timeout,
            )
        except subprocess.CalledProcessError as error:
            print(error.stdout.decode(), file=sys.stderr)
            raise
        return completed.stdout

    with (
        open_runtime_engine(
            settings, application_name="pm2-variance-delivery", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        page = serve_structural_products(conn, request)
    (assertion,) = page.public_assertions
    (task_id,) = page.task_ids
    result = cli(
        "structure",
        "list",
        "--run",
        str(run_id),
        "--cut",
        str(cut_id),
        "--kind",
        request.kind,
        "--include-publication",
        "--include-support",
        "--json",
    )
    if StructuralPage.model_validate_json(result) != page:
        raise ValueError("ordinary CLI differs from the public Reader page")

    root.mkdir(parents=True, exist_ok=True)

    async def compare_mcp():
        transport = StdioTransport(
            command=command,
            args=["mcp", "serve", "--semantic-run", str(run_id)],
            env=env,
            keep_alive=False,
            log_file=root / "stdio.log",
        )
        async with Client(transport, timeout=120) as client:
            response = await client.call_tool(
                "structural_products", {"request": request.model_dump(mode="json")}
            )
        if response.is_error or StructuralPage.model_validate(response.structured_content) != page:
            raise ValueError("fresh MCP differs from the public Reader page")

    anyio.run(compare_mcp)
    print(
        canonical_bytes(
            dict(
                run_id=run_id,
                cut_id=cut_id,
                selected_task_id=task_id,
                release_id=page.release_id,
                transports=["ordinary Reader", "managed CLI", "fresh stdio MCP"],
                assertion=assertion,
            )
        ).decode(),
        flush=True,
    )
    bundle = root / "exact-closure"
    budget = 512 * 1024 * 1024
    selection = ReviewSelection(
        structural_selections=(
            StructuralExportRequest(
                **request.model_dump(exclude={"max_bytes", "selected_task_id"}),
                selected_task_id=task_id,
                max_bytes=budget,
            ),
        ),
        max_bytes=budget,
    )
    receipt = json.loads(
        cli(
            "review",
            "export",
            "-",
            str(bundle),
            "--exact-closure",
            "--json",
            body=selection.model_dump_json().encode(),
            timeout=360,
        )
    )
    managed = json.loads(cli("results", "show", receipt["invocation_id"], "--json"))
    manifest_sha = managed["details"]["bundle_manifest_sha256"]
    verified = json.loads(
        cli(
            "review",
            "verify",
            str(bundle),
            "--manifest-sha256",
            manifest_sha,
            "--json",
            timeout=360,
        )
    )
    with (bundle / "structural_public_assertions.jsonl").open() as rows:
        (detached,) = (json.loads(json.loads(row)["payload_json"]) for row in rows)
    if (
        detached["claim_id"] != assertion["claim_id"]
        or detached["statement"] != assertion["statement"]
    ):
        raise ValueError("exact detached assertion differs from the public Reader page")
    print(
        canonical_bytes(
            dict(
                export_receipt=receipt["invocation_id"],
                manifest_sha256=manifest_sha,
                completeness=verified["completeness"],
                verification_standing=verified["verification_standing"],
                assertion_id=detached["assertion_id"],
                claim_id=detached["claim_id"],
            )
        ).decode()
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "source",
            "archived",
            "initialize",
            "reproject",
            "freeze",
            "stage",
            "publish",
            "verify-delivery",
        ),
    )
    parser.add_argument("--release")
    parser.add_argument("--realization")
    parser.add_argument("--attempt", default="pm2-p289-qualification-1")
    parser.add_argument("--group")
    parser.add_argument("--partition", default="development")
    parser.add_argument("--a", type=Path)
    parser.add_argument("--b", type=Path)
    parser.add_argument("--c", type=Path)
    parser.add_argument("--reference-design", choices=tuple(REFERENCE_DESIGNS), default="phrase")
    parser.add_argument("--staged", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--scoped-run", type=int)
    parser.add_argument("--candidate-run", type=int)
    parser.add_argument("--projection-run", type=int)
    parser.add_argument("--native-baseline-view", type=int, choices=(177, 276), default=177)
    parser.add_argument("--publication", type=Path)
    parser.add_argument("--delivery-root", type=Path)
    args = parser.parse_args()
    settings = Settings()
    role_pointer = "#/texts/5253"
    if args.action == "verify-delivery":
        if args.publication is None or args.delivery_root is None:
            raise ValueError(
                "supply the exact publication receipt and an independent delivery directory"
            )
        verify_delivery(settings, json.loads(args.publication.read_bytes()), args.delivery_root)
        return
    with open_runtime_engine(
        settings, application_name="pm2-variance-source", purpose="read"
    ) as engine:
        inputs = selected(engine, SOURCE_RUN)
        (source,) = inputs.sources
        if source.cut_id != SOURCE_CUT:
            raise ValueError("the original variance source no longer has the expected cut")
        if args.projection_run is not None:
            if not args.release or args.action not in {"source", "freeze", "stage", "publish"}:
                raise ValueError("bind the release and a current projection explicitly")
            inputs, role_pointer = current_projection(
                engine,
                args.projection_run,
                inputs,
                args.release,
                args.native_baseline_view,
            )
            (source,) = inputs.sources
        if args.action == "source":
            print(inputs.model_dump_json(exclude_none=True))
            return
        if args.action == "archived":
            with read_snapshot(engine) as conn:
                session, selected_id, origin, runtime, _body = report_meta(
                    conn, ARCHIVED_RUN, "structure.scoped_relations"
                )
                if selected_id != ARCHIVED_TASK or session.completed_cut_id != ARCHIVED_CUT:
                    raise ValueError("unexpected archived source task")
                ref = reference(
                    source, ARCHIVED_RUN, session, selected_id, origin, runtime, ARCHIVED_ATTACHMENT
                )
                retained = BoundReader(
                    conn,
                    ARCHIVED_RUN,
                    session.prepared,
                    cut_id=ARCHIVED_CUT,
                    analysis=False,
                ).retained_source_contribution(ref)
            from corpus_structure.methods.structural_products import condition_qualification

            report = StructuralProductReport(
                kind="condition_qualification",
                inputs=inputs,
                condition_qualification=condition_qualification(inputs, ref, retained),
            )
            print(canonical_bytes(structural_statement(report)).decode())
            return

    if args.action == "initialize":
        if not args.release or not args.realization:
            raise ValueError(
                "bind the exact admitted release and intended private input realization"
            )
        with (
            open_runtime_engine(
                settings, application_name="pm2-variance-initialize", purpose="write"
            ) as engine,
            engine.begin() as conn,
        ):
            prepared = open_release(conn, args.release)
            identity = initialize_source_project(
                conn,
                project_id=ProjectId(source.project_id),
                release_id=ReleaseId(args.release),
                realization_id=RealizationId(args.realization),
                projection_context=prepared,
            )
        print(
            canonical_bytes(
                dict(release_id=args.release, project_id=source.project_id, realization=identity)
            ).decode()
        )
        return

    if args.action == "reproject":
        from corpus_structure.ingest.pdf_methods import IngestPdf
        from corpus_structure.methods.m1_annotations import M1Annotations

        if not args.release or not args.realization:
            raise ValueError("reprojection requires the exact private writer binding")
        ingest, annotations = IngestPdf(), M1Annotations()
        views, documents, realization = map(
            table, ("kb.source_view", "kb.document", "data.realization")
        )
        original_view = views.alias("original")
        with open_runtime_engine(
            settings, application_name="pm2-variance-reproject", purpose="write"
        ) as engine:
            with read_snapshot(engine) as conn:
                prepared = open_release(conn, args.release)
                baseline = (
                    conn.execute(
                        select(documents.c.source_uri, documents.c.key.label("document_key"), views)
                        .join(views, views.c.document_id == documents.c.id)
                        .where(
                            views.c.id == args.native_baseline_view,
                            documents.c.project_id == source.project_id,
                            views.c.document_id
                            == select(original_view.c.document_id)
                            .where(
                                original_view.c.id == VIEW,
                            )
                            .scalar_subquery(),
                        )
                    )
                    .mappings()
                    .one()
                )
                revision = conn.execute(
                    select(realization.c.data_revision).where(
                        realization.c.realization_id == args.realization,
                        realization.c.release_id == args.release,
                        realization.c.project_id == source.project_id,
                    )
                ).scalar_one()
            cfg = {
                "native_product": {
                    "task_id": baseline["native_task_id"],
                    "product_key": baseline["native_product_key"],
                    "content_digest": baseline["native_content_digest"],
                },
                "originals": (baseline["source_uri"],),
                "sections": (baseline["section_pointer"],),
                "membership": baseline["membership"],
            }
            result = run_source_methods(
                engine,
                project_id=source.project_id,
                prepared=prepared,
                binding=OperationBinding(prepared.release_id, args.realization, revision, b"{}"),
                registry=MethodRegistry(
                    (ingest, annotations),
                    MethodsFile(
                        configs={
                            ingest.name: {"p289": cfg},
                            annotations.name: {"p289": {}},
                        }
                    ),
                ),
                graph=Graph(
                    (
                        (Stage.INGEST, (Step(ingest.name + "/p289"),)),
                        (Stage.EXTRACT, (Step(annotations.name + "/p289"),)),
                    ),
                    policy_propose=False,
                ),
                method_settings=MethodSettings(
                    data_dir=Path("build"), model_cache=Path("build/models")
                ),
                corpus_record={"documents": [baseline["document_key"]]},
                kind="slice",
            )
            finalized = finalize_bound_run(engine, result.run_id, f"{args.attempt}-reprojected")
            rebound, role_pointer = current_projection(
                engine,
                result.run_id,
                inputs,
                args.release,
                args.native_baseline_view,
            )
        print(
            canonical_bytes(
                dict(
                    run_id=result.run_id,
                    cut_id=finalized.cut_id,
                    original_source=source.model_dump(mode="json"),
                    projected_source=rebound.sources[0].model_dump(mode="json"),
                    passage=rebound.passages[0].model_dump(mode="json"),
                    role_native_pointer=role_pointer,
                    exact_physical_role_source=True,
                    exact_passage=True,
                )
            ).decode()
        )
        return

    if args.action == "freeze":
        if (
            not args.release
            or args.group is None
            or any(p is None for p in (args.a, args.b, args.c))
        ):
            raise ValueError(
                "freeze requires a release, source origin and separate authored A/B/C files"
            )
        policy, rubric, opportunity = REFERENCE_DESIGNS[args.reference_design]
        exposure = ("Prior scoped qualification and source review at run 320/cut 441.",)
        if args.projection_run is not None:
            exposure += (
                "Original p289 source-only judgments were rebound unchanged after verifying the exact same physical role item and passage under the released projection.",
            )
        frame = StructuralEvaluationFrame(
            inputs=inputs,
            operation="condition_qualification",
            direction="source_first",
            rubric_version=policy,
            rubric_text=rubric,
            partition=args.partition,
            inspected_scope="Grinstead–Snell physical p289; original retained passage",
            source_groups=(
                StructuralSourceGroup(source_ref=source.identity, origin_group=args.group),
            ),
            opportunities=(
                StructuralSourceOpportunity(
                    opportunity_id=opportunity,
                    passage_id=SCOPE,
                    facet="attachment",
                    source_state="stated",
                ),
            ),
            exposure_history=exposure,
        )
        payloads = tuple(
            authored_payload(frame, json.loads(path.read_bytes()), role_pointer)
            for path in (args.a, args.b, args.c)
        )
        with open_runtime_engine(
            settings, application_name="pm2-variance-independent", purpose="evaluate"
        ) as evaluator:
            with evaluator.begin() as conn:
                set_id = create_structural_reference_set(
                    conn, project_id=source.project_id, release_id=args.release, frame=frame
                )
                actors = (
                    ("pm2-p289-reference-A", "pm2-p289-reference-B", "pm2-p289-adjudicator-C")
                    if args.reference_design == "phrase"
                    else (
                        "pm2-p289-role-anchors-A",
                        "pm2-p289-role-anchors-B",
                        "pm2-p289-role-anchors-C",
                    )
                )
                a = record_structural_reference_pass(
                    conn, set_id=set_id, pass_kind="A", actor=actors[0], authored=payloads[0]
                )
                b = record_structural_reference_pass(
                    conn, set_id=set_id, pass_kind="B", actor=actors[1], authored=payloads[1]
                )
                c = record_structural_reference_pass(
                    conn,
                    set_id=set_id,
                    pass_kind="C",
                    actor=actors[2],
                    authored=payloads[2],
                    parents=(a, b),
                )
        print(
            canonical_bytes(
                dict(
                    release_id=args.release,
                    structural_input_digest=inputs.identity,
                    a_pass_id=a,
                    b_pass_id=b,
                    set_id=set_id,
                    c_pass_id=c,
                    c_content_digest=sha256(payloads[2]).hexdigest(),
                    frame_digest=frame.identity,
                    policy_id=policy,
                )
            ).decode()
        )
        return

    if args.reference is None:
        raise ValueError("freeze the protected source-only reference before staging or publishing")
    frozen_reference = json.loads(args.reference.read_bytes())
    if (frozen_reference["release_id"], frozen_reference["structural_input_digest"]) != (
        args.release,
        inputs.identity,
    ):
        raise ValueError(
            "protected reference differs from selected release and original source input"
        )
    if not args.release or not args.realization:
        raise ValueError("bind an explicitly prepared development release and realization")
    with open_runtime_engine(
        settings, application_name="pm2-variance-stage", purpose="write"
    ) as engine:
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, args.release)
            rz = table("data.realization")
            revision = conn.execute(
                select(rz.c.data_revision).where(
                    rz.c.realization_id == args.realization,
                    rz.c.release_id == args.release,
                    rz.c.project_id == source.project_id,
                )
            ).scalar_one()

        def run(method, stage, inputs, cfg, label, admissions=(), *, finalize=True):
            result = run_source_methods(
                engine,
                project_id=source.project_id,
                prepared=prepared,
                binding=OperationBinding(prepared.release_id, args.realization, revision, b"{}"),
                registry=MethodRegistry(
                    (method,), MethodsFile(configs={method.name: {"p289": cfg}})
                ),
                graph=Graph(((stage, (Step(method.name + "/p289"),)),), policy_propose=False),
                method_settings=MethodSettings(
                    data_dir=Path("build"), model_cache=Path("build/models")
                ),
                selected_sources=inputs.sources,
                structural_admission=admissions,
            )
            if finalize:
                finalize_bound_run(engine, result.run_id, f"{args.attempt}-{label}")
            return result.run_id

        if args.action == "stage":
            # Original Standard cut 413 owns both the native projection and
            # the current-format M1 annotation result. A newer derivation may
            # select this view without becoming its original custody.
            scoped = args.scoped_run
            if scoped is None:
                scoped = run(
                    ScopedRelationsWithRoleClosure(),
                    Stage.SCOPE,
                    inputs,
                    {
                        "inputs": inputs.model_dump(mode="json", exclude_none=True),
                        "structural_input_digest": inputs.identity,
                    },
                    "scoped",
                )
            with read_snapshot(engine) as conn:
                session, selected_id, origin, runtime, body = report_meta(
                    conn,
                    scoped,
                    "structure.scoped_relations",
                    view_id=source.source_view_id,
                    role_pointer=role_pointer,
                )
                if session.binding.release_id != args.release:
                    raise ValueError("scoped producer differs from exact selected release")
                attachment = reference(
                    source,
                    scoped,
                    session,
                    selected_id,
                    origin,
                    runtime,
                    condition_edge(body, role_pointer),
                )
            cfg = dict(
                inputs=inputs.model_dump(mode="json", exclude_none=True),
                structural_input_digest=inputs.identity,
                attachment=attachment.model_dump(mode="json"),
            )
            candidate = run(ConditionQualificationMethod(), Stage.ASSEMBLE, inputs, cfg, "private")
            with read_snapshot(engine) as conn:
                session, _, _, _, body = report_meta(
                    conn, candidate, ConditionQualificationMethod.name
                )
            product = StructuralProductReport.model_validate(body["structural_product"])
            print(
                canonical_bytes(
                    dict(
                        run_id=candidate,
                        cut_id=session.completed_cut_id,
                        release_id=prepared.release_id,
                        product_id=product.product_id,
                        attachment=attachment.model_dump(mode="json"),
                        reference_set_id=frozen_reference["set_id"],
                        candidate_statement=structural_statement(product),
                    )
                ).decode()
            )
            return

        if args.staged is None:
            raise ValueError("publish requires the exact staged result")
        staged = json.loads(args.staged.read_bytes())
        if (
            staged["release_id"] != prepared.release_id
            or staged["reference_set_id"] != frozen_reference["set_id"]
        ):
            raise ValueError("staged condition differs from the protected source-only binding")
        cfg = dict(
            inputs=inputs.model_dump(mode="json", exclude_none=True),
            structural_input_digest=inputs.identity,
            attachment=staged["attachment"],
        )
        admission = {
            key: frozen_reference[key]
            for key in ("set_id", "c_pass_id", "c_content_digest", "frame_digest", "policy_id")
        }
        admission["product_id"] = staged["product_id"]
        run_id = args.candidate_run
        if run_id is None:
            run_id = run(
                ConditionQualificationMethod(),
                Stage.ASSEMBLE,
                inputs,
                cfg,
                "public",
                (admission,),
                finalize=False,
            )
        else:
            job = table("ops.run")
            with read_snapshot(engine) as conn:
                bound = conn.execute(
                    select(job.c.dependencies).where(
                        job.c.id == run_id,
                        job.c.project_id == source.project_id,
                        job.c.release_id == args.release,
                        job.c.input_realization_id == args.realization,
                    )
                ).scalar_one()
            if json.loads(bound).get("structural_admission") != [admission]:
                raise ValueError("existing candidate did not bind this exact protected reference")
        report = dict(run_id=run_id, staged_run_id=staged["run_id"], admission=admission)
        try:
            result = finalize_bound_run(engine, run_id, f"{args.attempt}-public")
        except DBAPIError as error:
            native = error.orig
            if getattr(native, "sqlstate", None) != "23514":
                raise
            job, completed, assertion, cut = map(
                table,
                (
                    "ops.run",
                    "ops.completed_result",
                    "data.structural_assertion",
                    "ops.input_cut",
                ),
            )
            with read_snapshot(engine) as conn:
                status, sealed, completed_cut = conn.execute(
                    select(job.c.status, job.c.sealed, completed.c.cut_id)
                    .select_from(job)
                    .outerjoin(completed, completed.c.run_id == job.c.id)
                    .where(job.c.id == run_id)
                ).one()
                candidate_cut = conn.execute(
                    select(cut.c.id).where(cut.c.run_id == run_id, cut.c.final)
                ).scalar_one_or_none()
                public_rows = conn.execute(
                    select(func.count())
                    .select_from(assertion)
                    .join(cut, cut.c.id == assertion.c.cut_id)
                    .where(cut.c.run_id == run_id)
                ).scalar_one()
            if completed_cut is not None or public_rows:
                raise ValueError(
                    "refused finalization unexpectedly completed or published"
                ) from error
            print(
                canonical_bytes(
                    dict(
                        report,
                        outcome="refused",
                        sqlstate=native.sqlstate,
                        reason=native.diag.message_primary,
                        status=status,
                        sealed=sealed,
                        candidate_cut=candidate_cut,
                        completed_cut=completed_cut,
                        public_rows=public_rows,
                    )
                ).decode()
            )
            raise SystemExit(1) from None
        print(
            canonical_bytes(
                dict(
                    report,
                    outcome="published",
                    cut_id=result.cut_id,
                    realization_id=result.realization_id,
                    result_revision=result.data_revision,
                )
            ).decode()
        )


if __name__ == "__main__":
    main()
