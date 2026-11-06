"""Actual current source→scoped contributions→dossier and artifact diagnostic journeys.

Run only after the coordinator confirms source recovery and native deployment.
All methods use ordinary immutable task completion and owned Reader/export routes.
No PDF conversion, GLiNER, recognition or linguistic model invocation is scheduled.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.artifact_identity import ArtifactIdentityMethod
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.methods.structural_products import StructuralDossierMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    RetainedStructuralRef,
    StructuralInput,
    StructuralPassage,
)
from corpus_structure.serve.contributions import (
    ContributionRequest,
    export_contribution_selection,
    serve_contributions,
)
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    export_review_bundle,
    inspect_review_bundle,
)
from corpus_structure.serve.structural_products import (
    DossierRepresentationRequest,
    StructuralRequest,
    serve_dossier_representation,
    serve_structural_products,
)
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
sys.path.insert(0, str(EVIDENCE / "source-recovery"))
from recover_sources import admit_current  # noqa: E402
from inventory_sources import PARENT, PROJECT  # noqa: E402

MODES = ("feasibility", "independent", "coupled")
STRUCTURAL_TYPES = {
    "structural.located_participant",
    "structural.scoped_attachment",
    "structural.artifact",
}


def retain(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(value) + b"\n"
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError("retained receipt differs: " + str(path))
        return
    with path.open("xb") as stream:
        stream.write(encoded)


def run_method(settings, prepared, method, config, inputs, output, label, attempt):
    if (output / "completed.json").exists():
        completed = json.loads((output / "completed.json").read_bytes())
        if completed["release_id"] != prepared.release_id:
            raise ValueError("completed stage belongs to a different exact release")
        return completed
    output.mkdir(exist_ok=True)
    registry = MethodRegistry(
        (method,), MethodsFile(configs={method.name: {"current": config}})
    )
    resolved = registry.resolve(method.name, "current")
    retain(
        output / "configuration.json",
        dict(
            method=method.name,
            version=method.version,
            config=resolved.config.model_dump(mode="json"),
            configuration_hash=resolved.config_hash,
        ),
    )
    realization = (
        "gs120-current-structural:" + attempt + ":" + label + ":" + prepared.release_id
    )
    with open_runtime_engine(
        settings, "gs120-structural-" + label, purpose="write"
    ) as engine:
        with engine.begin() as conn:
            initialize_source_project(
                conn,
                project_id=ProjectId(PROJECT),
                release_id=ReleaseId(prepared.release_id),
                realization_id=RealizationId(realization),
                projection_context=prepared,
            )
        with read_snapshot(engine) as conn:
            realized = table("data.realization")
            revision = conn.scalar(
                select(realized.c.data_revision).where(
                    realized.c.realization_id == realization
                )
            )
        result = run_source_methods(
            engine,
            project_id=PROJECT,
            prepared=prepared,
            binding=OperationBinding(
                prepared.release_id,
                realization,
                revision,
                canonical_bytes(
                    dict(
                        source_parent_sha256=PARENT,
                        structural_input=inputs.identity,
                        scope="same GS120 development and assessment corpus",
                        label=label,
                    )
                ),
            ),
            registry=registry,
            graph=Graph(
                (
                    (
                        Stage.SCOPE
                        if method.unit_type == "source_view"
                        else Stage.ASSEMBLE,
                        (Step(method.name + "/current"),),
                    ),
                ),
                policy_propose=False,
            ),
            method_settings=MethodSettings(
                data_dir=output / "data",
                model_cache=Path.home() / ".cache/docling/models",
            ),
            guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(),
            policy_source=None,
            kind="full",
            selected_sources=inputs.sources,
        )
        retain(output / "source-ready.json", result.model_dump(mode="json"))
        if result.status != "source_ready":
            raise ValueError("ordinary source stage did not reach source_ready")
        with engine.begin() as conn:
            cut = seal_cut(
                conn, result.run_id, "gs120-current-structural-final", final=True
            )
        output_realization = "gs120-current-structural-result:" + str(result.run_id)
        retain(
            output / "sealed-cut.json",
            dict(
                run_id=result.run_id,
                cut_id=cut,
                output_realization_id=output_realization,
            ),
        )
        consolidate_cut(engine, cut, output_realization)
        with read_snapshot(engine) as conn:
            completed = dict(
                conn.execute(
                    text(
                        "SELECT job.id run_id,job.project_id,job.release_id,job.runtime_id,"
                        "completed.cut_id,batch.data_revision result_revision "
                        "FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id "
                        "JOIN data.batch batch ON batch.release_id=completed.release_id "
                        "AND batch.realization_id=completed.output_realization_id "
                        "AND batch.batch_id=completed.batch_id WHERE job.id=:run"
                    ),
                    {"run": result.run_id},
                )
                .mappings()
                .one()
            )
    retain(output / "completed.json", completed)
    print(json.dumps(dict(label=label, **completed)), flush=True)
    return completed


def task_custody(conn, run):
    return {
        row["selected_task_id"]: dict(row)
        for row in conn.execute(
            text(
                "SELECT task.id selected_task_id,origin.id origin_task_id,origin_job.runtime_id runtime_fingerprint "
                "FROM ops.cut_task member JOIN ops.task task ON task.id=member.task_id "
                "JOIN ops.task origin ON origin.id=member.origin_task_id "
                "JOIN ops.run origin_job ON origin_job.id=origin.run_id WHERE member.cut_id=:cut"
            ),
            {"cut": run["cut_id"]},
        ).mappings()
    }


def inspect_scoped(settings, run, inputs, output):
    if (output / "inventory.json").exists():
        references = tuple(RetainedContributionRef.model_validate(r) for r in json.loads(
            (output / "contribution-predecessors.json").read_bytes()))
        requests = tuple(ContributionRequest(run_id=run["run_id"], source_view_id=source.source_view_id,
            method=ScopedRelationsMethod.name, include_interpretation=True,
            limit=1000, page_bytes=16_000_000, max_bytes=128_000_000) for source in inputs.sources)
        return references, requests
    references, requests, totals = [], [], Counter()
    with open_runtime_engine(
        settings, "gs120-structural-inspection", purpose="read"
    ) as engine:
        with read_snapshot(engine) as conn:
            custody = task_custody(conn, run)
            for source in inputs.sources:
                root = output / ("source-" + str(source.source_view_id))
                root.mkdir()
                request = ContributionRequest(
                    run_id=run["run_id"],
                    source_view_id=source.source_view_id,
                    method=ScopedRelationsMethod.name,
                    include_interpretation=True,
                    limit=1000,
                    page_bytes=16_000_000,
                    max_bytes=128_000_000,
                )
                requests.append(request)
                pages, rows = [], []
                while True:
                    page = serve_contributions(conn, request)
                    pages.append(page.model_dump(mode="json"))
                    rows.extend(
                        item["row"]
                        for item in page.items
                        if item["population"] == "contribution"
                    )
                    if page.next_cursor is None:
                        break
                    request = request.model_copy(update=dict(cursor=page.next_cursor))
                retain(root / "pages.json", pages)
                retain(
                    root / "export.json",
                    export_contribution_selection(conn, requests[-1], root / "export"),
                )
                totals.update(pages[0]["inventory_counts"])
                for row in rows:
                    if row["semantic_type"] not in STRUCTURAL_TYPES:
                        continue
                    references.append(
                        RetainedContributionRef(
                            contribution_id=row["contribution_id"],
                            project_id=run["project_id"],
                            run_id=run["run_id"],
                            cut_id=run["cut_id"],
                            release_id=run["release_id"],
                            result_revision=run["result_revision"],
                            **custody[row["selected_task_id"]],
                        )
                    )
    retain(
        output / "contribution-predecessors.json",
        [r.model_dump(mode="json") for r in references],
    )
    retain(
        output / "inventory.json",
        dict(
            sources=len(inputs.sources),
            counts=dict(totals),
            selected_contribution_predecessors=len(references),
            standing="retained_private",
            semantic_quality="unassessed",
            source_coverage="see recovered coverage, inventory does not establish capture recall",
        ),
    )
    return tuple(references), tuple(requests)


def structural_predecessors(settings, run_ids, inputs, output):
    references, requests, omitted = [], [], []
    allowed_passages = {p.passage_id: p for p in inputs.passages}
    with open_runtime_engine(
        settings, "gs120-dossier-predecessors", purpose="read"
    ) as engine:
        with read_snapshot(engine) as conn:
            for run_id in run_ids:
                after = 0
                while True:
                    page = serve_structural_products(
                        conn,
                        StructuralRequest(
                            run_id=run_id, after_task_id=after, max_bytes=8_000_000
                        ),
                    )
                    current = dict(
                        conn.execute(
                            text(
                                "SELECT job.project_id,completed.cut_id,batch.data_revision result_revision "
                                "FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id "
                                "JOIN data.batch batch ON batch.release_id=completed.release_id "
                                "AND batch.realization_id=completed.output_realization_id "
                                "AND batch.batch_id=completed.batch_id WHERE job.id=:run"
                            ),
                            {"run": run_id},
                        )
                        .mappings()
                        .one()
                    )
                    custody = task_custody(conn, current)
                    for task_id, report in zip(
                        page.task_ids, page.reports, strict=True
                    ):
                        if report.kind not in {
                            "definition_components",
                            "definition_applicability",
                            "qualified_comparison",
                        } or any(
                            allowed_passages.get(p.passage_id) != p
                            for p in report.inputs.passages
                        ):
                            omitted.append(
                                dict(
                                    run_id=run_id,
                                    task_id=task_id,
                                    product_id=report.product_id,
                                    reason="not a current supported predecessor kind or exact passage subset",
                                )
                            )
                            continue
                        references.append(
                            RetainedStructuralRef(
                                product_id=report.product_id,
                                project_id=current["project_id"],
                                run_id=run_id,
                                cut_id=page.cut_id,
                                release_id=page.release_id,
                                result_revision=current["result_revision"],
                                **custody[task_id],
                            )
                        )
                    if page.next_after_task_id is None:
                        break
                    after = page.next_after_task_id
                requests.append(StructuralRequest(run_id=run_id, max_bytes=8_000_000))
    retain(
        output / "structural-predecessor-selection.json",
        dict(
            references=[r.model_dump(mode="json") for r in references],
            omitted=omitted,
            note="Only explicitly named completed runs, exact original passages and supported current predecessor kinds.",
        ),
    )
    return tuple(references), tuple(requests)


def inspect_product(settings, run, kind, output):
    request = StructuralRequest(
        run_id=run["run_id"], cut_id=run["cut_id"], kind=kind, max_bytes=8_000_000
    )
    if (output / "inspection.json").exists():
        return request, json.loads((output / "inspection.json").read_bytes())
    with open_runtime_engine(
        settings, "gs120-current-product-reader", purpose="read"
    ) as engine:
        with read_snapshot(engine) as conn:
            page = serve_structural_products(conn, request)
            retain(output / "structural-page.json", page.model_dump(mode="json"))
            if len(page.reports) != 1:
                raise ValueError("expected exactly one retained current RUN product")
            report = page.reports[0]
            if kind == "dossier":
                selected = DossierRepresentationRequest(
                    run_id=run["run_id"],
                    cut_id=run["cut_id"],
                    task_id=page.task_ids[0],
                    limit=2,
                    max_bytes=8_000_000,
                )
                pages = []
                while True:
                    value = serve_dossier_representation(conn, selected)
                    pages.append(value.model_dump(mode="json"))
                    if value.continuation is None:
                        break
                    selected = selected.model_copy(
                        update=dict(continuation=value.continuation)
                    )
                retain(output / "representative-pages.json", pages)
                summary = dict(
                    members=len(report.dossier.members),
                    selected=len(report.dossier.representatives),
                    missing_sections=report.dossier.missing_sections,
                    supported_facets=len(report.dossier.supported_facets),
                    pages=len(pages),
                    mandatory_overflow=report.dossier.representation.mandatory_overflow,
                )
            else:
                product = report.artifact_identity
                summary = dict(
                    records=len(product.records),
                    pairs=len(product.pairs),
                    unbound_sources=product.unbound_source_ids,
                    identity_grain=product.identity_grain,
                    model_policy=product.policy.model_dump(mode="json"),
                    standing=product.standing,
                    probabilities="diagnostic assumptions, not calibrated truth",
                )
    retain(
        output / "inspection.json",
        dict(
            outcome="passed",
            **summary,
            scope="Ordinary current private Reader, not independent correctness assessment",
        ),
    )
    return request, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt")
    parser.add_argument("--release-id", help="Use this exact already admitted release without readmitting unrelated authored SQL")
    parser.add_argument("--resume", action="store_true", help="Reuse this attempt's completed native stages; never recompute them")
    parser.add_argument(
        "--source-packet",
        type=Path,
        default=EVIDENCE
        / "source-recovery/attempt001/source-packets/source-packet.json",
    )
    parser.add_argument("--structural-run", type=int, action="append", default=[])
    args = parser.parse_args()
    output = HERE / ("attempt" + args.attempt)
    output.mkdir(exist_ok=args.resume)
    try:
        packet = json.loads(args.source_packet.read_bytes())
        coverage = json.loads(
            (args.source_packet.parent.parent / "coverage.json").read_bytes()
        )
        if (
            coverage["outcome"] != "passed"
            or coverage["native_item_pages"] != list(range(191, 311))
            or coverage["projected_text_pages"] != list(range(191, 311))
        ):
            raise ValueError(
                "journey requires exact recovered same120-page source and text coverage"
            )
        if (
            packet["source_manifest"]["parent_sha256"] != PARENT
            or packet["predictions_included"]
        ):
            raise ValueError(
                "source packet differs from the neutral original GS120 custody"
            )
        inputs = StructuralInput(
            question="Progressively structure the same GS120 corpus",
            scope="grinstead-snell-physical191-310",
            inventory_id="gs120-current-source-structure-1",
            policy_id="source-grounded-private-proposals-1",
            sources=tuple(
                ExternalSourceRef.model_validate(s) for s in packet["sources"]
            ),
            passages=tuple(
                StructuralPassage.model_validate(p) for p in packet["passages"]
            ),
            dependencies=(
                "source-packet:" + sha256(args.source_packet.read_bytes()).hexdigest(),
            ),
            coverage_limits=(
                "Native geometry and model readings remain unassessed proposals.",
                "Missing dossier sections remain gaps; inventory counts do not establish capture recall.",
            ),
        )
        retain(output / "inputs.json", inputs.model_dump(mode="json"))
        retain(output / "source-coverage.json", coverage)
        settings = Settings()
        if args.release_id:
            from corpus_structure.semantic.releases import load_release
            with open_runtime_engine(settings, "gs120-current-existing-release", purpose="read") as engine:
                with read_snapshot(engine) as conn:
                    prepared = load_release(conn, args.release_id)
            retain(output / "release.json", dict(release_id=prepared.release_id,
                acquisition="exact already admitted current release",
                script_sha256=sha256(Path(__file__).read_bytes()).hexdigest()))
        else:
            prepared = admit_current(settings, output)
        bindings = [
            dict(
                native_content_digest=digest,
                source_work=PARENT,
                provenance="Authenticated recovered GS120 native-parent-map, same original source PDF SHA256",
            )
            for digest in sorted({s.native_content_digest for s in inputs.sources})
        ]
        predecessors, predecessor_requests = structural_predecessors(
            settings, args.structural_run, inputs, output
        )
        arms = []
        for mode in MODES:
            scoped = run_method(
                settings,
                prepared,
                ScopedRelationsMethod(),
                dict(
                    inputs=inputs.model_dump(mode="json"),
                    structural_input_digest=inputs.identity,
                    interpretation_mode=mode,
                    work_bindings=bindings,
                ),
                inputs,
                output / ("scoped-" + mode),
                "scoped-" + mode,
                args.attempt,
            )
            refs, requests = inspect_scoped(
                settings, scoped, inputs, output / ("scoped-" + mode)
            )
            if not refs:
                raise ValueError(
                    "current source run produced no eligible source structural contributions"
                )
            dossier_inputs = inputs.model_copy(
                update=dict(
                    dependencies=(
                        *inputs.dependencies,
                        *(r.contribution_id for r in refs),
                        *(r.product_id for r in predecessors),
                    )
                )
            )
            dossier = run_method(
                settings,
                prepared,
                StructuralDossierMethod(),
                dict(
                    inputs=dossier_inputs.model_dump(mode="json"),
                    structural_input_digest=dossier_inputs.identity,
                    root_id="gs120-corpus-structure",
                    predecessors=[r.model_dump(mode="json") for r in predecessors],
                    contribution_predecessors=[r.model_dump(mode="json") for r in refs],
                    member_budget=12,
                ),
                dossier_inputs,
                output / ("dossier-" + mode),
                "dossier-" + mode,
                args.attempt,
            )
            product_request, summary = inspect_product(
                settings, dossier, "dossier", output / ("dossier-" + mode)
            )
            annotation_requests = tuple(
                ContributionRequest(
                    run_id=source.run_id,
                    source_view_id=source.source_view_id,
                    method="extract.m1_annotations",
                    max_bytes=128_000_000,
                )
                for source in inputs.sources
            )
            export_selection = ReviewSelection(
                selections=(*requests, *annotation_requests),
                structural_selections=(*predecessor_requests, product_request),
                max_bytes=256_000_000,
            )
            destination = output / ("review-" + mode)
            if destination.exists():
                manifest = json.loads((destination / "manifest.json").read_bytes())
                inspect_review_bundle(destination)
            else:
                manifest = export_review_bundle(export_selection, destination, settings)
            retain(
                output / ("review-" + mode + ".json"),
                dict(
                    manifest=manifest,
                    detached=inspect_review_bundle(output / ("review-" + mode)),
                ),
            )
            arms.append(
                dict(
                    mode=mode,
                    source_run=scoped,
                    dossier_run=dossier,
                    inspection=summary,
                )
            )
        policy = json.loads((HERE / "artifact-policy.json").read_bytes())
        artifact = run_method(
            settings,
            prepared,
            ArtifactIdentityMethod(),
            dict(
                inputs=inputs.model_dump(mode="json"),
                structural_input_digest=inputs.identity,
                work_bindings=bindings,
                policy=policy,
            ),
            inputs,
            output / "artifact",
            "artifact",
            args.attempt,
        )
        artifact_request, artifact_summary = inspect_product(
            settings, artifact, "artifact_identity", output / "artifact"
        )
        if (output / "review-artifact").exists():
            manifest = json.loads((output / "review-artifact/manifest.json").read_bytes())
            inspect_review_bundle(output / "review-artifact")
        else:
            manifest = export_review_bundle(
                ReviewSelection(structural_selections=(artifact_request,), max_bytes=256_000_000),
                output / "review-artifact", settings)
        retain(
            output / "review-artifact.json",
            dict(
                manifest=manifest,
                detached=inspect_review_bundle(output / "review-artifact"),
            ),
        )
        retain(
            output / "result.json",
            dict(
                outcome="passed",
                arms=arms,
                artifact=artifact,
                artifact_inspection=artifact_summary,
                sources=len(inputs.sources),
                parent_physical_pages=list(range(191, 311)),
                semantic_quality="unassessed",
                source_semantic_support="not established by geometry, scores or source quote alone",
                scope="Actual registered native completion, bounded ordinary Reader/continuation and independently verified detached exports",
            ),
        )
    except BaseException as error:
        retain(
            output / ("failure-resume.json" if (output / "failure.json").exists() else "failure.json"),
            dict(
                outcome="interrupted"
                if isinstance(error, KeyboardInterrupt)
                else "failed",
                type=type(error).__name__,
                message=str(error),
            ),
        )
        raise


if __name__ == "__main__":
    main()
