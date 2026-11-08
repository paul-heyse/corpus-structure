"""Shared exact completed-cut bindings for phased GS120 evidence journeys."""

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
    StructuralExportRequest,
    StructuralRequest,
    read_structural_export_page,
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


def run_method(
    settings, prepared, method, config, inputs, output, label, attempt, *, benchmark="gs120"
):
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
    if (output / "completed.json").exists():
        completed = json.loads((output / "completed.json").read_bytes())
        if completed["release_id"] != prepared.release_id:
            raise ValueError("completed stage belongs to a different exact release")
        return completed
    if (output / "source-ready.json").exists():
        ready = json.loads((output / "source-ready.json").read_bytes())
        return finish_source_stage(settings, ready["run_id"], output)
    realization = (
        benchmark + "-current-structural:" + attempt + ":" + label + ":" + prepared.release_id
    )
    with open_runtime_engine(
        settings, benchmark + "-structural-" + label, purpose="write"
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
                        scope=f"same {benchmark.upper()} development and assessment corpus",
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
    return finish_source_stage(settings, result.run_id, output)


def finish_source_stage(settings, run_id, output):
    with open_runtime_engine(settings, "gs120-structural-finish", purpose="write") as engine:
        with read_snapshot(engine) as conn:
            prior = completed_metadata(conn, run_id, optional=True)
        if prior is not None:
            retain(output / "completed.json", prior)
            return prior
        if (output / "sealed-cut.json").exists():
            sealed = json.loads((output / "sealed-cut.json").read_bytes())
            cut, realization = sealed["cut_id"], sealed["output_realization_id"]
        else:
            with engine.begin() as conn:
                cut = seal_cut(conn, run_id, "gs120-current-structural-final", final=True)
            realization = "gs120-current-structural-result:" + str(run_id)
            retain(output / "sealed-cut.json", dict(run_id=run_id, cut_id=cut,
                output_realization_id=realization))
        consolidate_cut(engine, cut, realization)
        with read_snapshot(engine) as conn:
            completed = completed_metadata(conn, run_id)
    retain(output / "completed.json", completed)
    print(json.dumps(completed), flush=True)
    return completed


def completed_metadata(conn, run_id, optional=False):
    row = conn.execute(text(
        "SELECT job.id run_id,job.project_id,job.release_id,job.runtime_id,"
        "completed.cut_id,batch.data_revision result_revision "
        "FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id "
        "JOIN data.batch batch ON batch.release_id=completed.release_id "
        "AND batch.realization_id=completed.output_realization_id "
        "AND batch.batch_id=completed.batch_id WHERE job.id=:run"
    ), dict(run=run_id)).mappings().one_or_none()
    if row is None and not optional:
        raise ValueError("run lacks exact completed custody: " + str(run_id))
    return dict(row) if row is not None else None


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
                root.mkdir(exist_ok=True)
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
                if (root / "pages.json").exists():
                    pages = json.loads((root / "pages.json").read_bytes())
                    if (pages[-1]["next_cursor"] is not None
                        or any(p["run_id"] != run["run_id"] or p["cut_id"] != run["cut_id"] for p in pages)):
                        raise ValueError("retained source pages differ from exact completed stage")
                else:
                    pages = []
                    while True:
                        page = serve_contributions(conn, request)
                        pages.append(page.model_dump(mode="json"))
                        if page.next_cursor is None:
                            break
                        request = request.model_copy(update=dict(cursor=page.next_cursor))
                    retain(root / "pages.json", pages)
                rows = [item["row"] for page in pages for item in page["items"]
                        if item["population"] == "contribution"]
                destination = root / "export"
                if destination.exists():
                    manifest = json.loads((destination / "manifest.json").read_bytes())
                    content = (destination / manifest["file"]).read_bytes()
                    if (manifest["run_id"] != run["run_id"] or manifest["cut_id"] != run["cut_id"]
                        or manifest["selection"] != requests[-1].selection()
                        or sha256(content).hexdigest() != manifest["sha256"]):
                        raise ValueError("retained selected source export differs")
                else:
                    manifest = export_contribution_selection(conn, requests[-1], destination)
                retain(root / "export.json", manifest)
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
    if (output / "structural-predecessor-selection.json").exists():
        saved = json.loads((output / "structural-predecessor-selection.json").read_bytes())
        if saved["run_ids"] != list(run_ids):
            raise ValueError("retained structural predecessor run selection differs")
        references = tuple(RetainedStructuralRef.model_validate(r) for r in saved["references"])
        requests = tuple(StructuralExportRequest(run_id=r, max_bytes=128_000_000,
            include_publication=True) for r in run_ids)
        return references, requests
    references, requests, omitted, public_counts = [], [], [], []
    allowed_passages = {p.passage_id: p for p in inputs.passages}
    with open_runtime_engine(
        settings, "gs120-dossier-predecessors", purpose="read"
    ) as engine:
        with read_snapshot(engine) as conn:
            for run_id in run_ids:
                after = 0
                while True:
                    page = read_structural_export_page(
                        conn,
                        StructuralExportRequest(
                            run_id=run_id, after_task_id=after, max_bytes=128_000_000, include_publication=True
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
                    public_counts.append(dict(run_id=run_id, after_task_id=after,
                        published_structural_assertions=len(page.public_assertions)))
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
                requests.append(StructuralExportRequest(run_id=run_id, max_bytes=128_000_000, include_publication=True))
    retain(
        output / "structural-predecessor-selection.json",
        dict(
            run_ids=list(run_ids), public_assertions=public_counts,
            references=[r.model_dump(mode="json") for r in references],
            omitted=omitted,
            note="Only explicitly named completed runs, exact original passages and supported current predecessor kinds.",
        ),
    )
    return tuple(references), tuple(requests)

