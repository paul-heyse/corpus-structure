"""Bounded actual PCE07 retained-source parser journey; run only on the final runtime.

Reuses registered retained ingest, annotation and M1 candidate methods. Primary
regions are bounded; annotations cover the one selected retained chapter and may
reuse an exactly compatible retained task through the ordinary scheduler. No PDF
conversion, OCR, recognition, resolver, default selection or reference import.
Full raw reports remain in native task custody. Common inspection exports use a
bounded service read, independently of whole-record completion or assessment.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import Text, func, select

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate import commands, m1
from corpus_structure.orchestrate.phase0 import bind_pdf_source
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_bindings import installed_runtime_id
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings


def retained_producer_summaries(conn, origin_ids):
    """Preflight64MiB, then decode SourceValue once per selected origin in Python."""
    from corpus_structure.semantic.observations import source_python

    if len(origin_ids)>100:
        raise RuntimeError("bounded producer summary exceeds100 selected origins")
    results=table("ops.task_result")
    selected=results.c.task_id.in_(origin_ids)
    size=conn.scalar(select(func.coalesce(func.sum(func.octet_length(
        results.c.body["parse_detail"].cast(Text))),0)).where(selected))
    if size>64*1024*1024:
        raise RuntimeError("bounded producer summary exceeds64MiB before hydration")
    keys=("source_pin","source_region_selection","annotation_product","annotation_errors",
          "execution","local_execution","regions","exclusions","runtime","producer_failure")
    output=[]
    for row in conn.execute(select(results.c.task_id,results.c.body["outcome"].label("outcome"),
        results.c.body["error"].label("error"),func.octet_length(results.c.body.cast(Text)).label("retained_body_bytes"),
        results.c.body["parse_detail"].label("encoded_detail")).where(selected).order_by(results.c.task_id)).mappings():
        value=dict(row)
        encoded=value.pop("encoded_detail")
        decoded=source_python(encoded) if encoded is not None else {}
        output.append(dict(value,**{key:decoded.get(key) for key in keys}))
    return output


def retained_producer_gaps(summaries):
    return [
        dict(task_id=summary["task_id"], stage=field, **row)
        for summary in summaries
        for field in ("execution", "local_execution")
        for row in summary[field] or ()
        if row.get("outcome") not in {"succeeded", "completed", "complete", "empty"}
    ]


HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
INPUT = HERE / "parser-source-input-002.json"
ALLOWED = {"ingest.pdf_integrated", "extract.m1_annotations", "extract.m1_candidates"}


def write(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def run(args, state):
    source = json.loads(INPUT.read_bytes())
    pin = source["physical_pin"]
    project_id = source["project_id"]
    regions = tuple(pointer for group in source["region_groups"].values() for pointer in group)
    if len(regions) != 15 or len(set(regions)) != 15:
        raise ValueError("source-only input must retain precisely the 15 distinct primary regions")
    product = ProductReference(
        pin["native_product_task_id"], pin["product_key"], pin["product_digest"]
    )
    settings = Settings()
    pack = DOMAINS / "statistics"
    method_settings = MethodSettings(
        data_dir=settings.paths.data_dir,
        model_cache=settings.paths.model_cache,
        nemotron_endpoint=settings.nemotron.endpoint,
        nemotron_python=settings.nemotron.python,
        nemotron_worker=settings.nemotron.worker,
        nemotron_receipts=settings.nemotron.receipts,
        nemotron_timeout_seconds=settings.nemotron.timeout_seconds,
    )
    with open_runtime_engine(settings, "pce07-bounded-corpus-parser", purpose="write") as engine:
        with engine.connect() as conn:
            prepared = open_release(conn, args.release)
            if installed_runtime_id(prepared) != args.runtime:
                raise RuntimeError("installed runtime differs from the coordinator's final pin")
            projects, realizations, documents = map(
                table, ("data.project", "data.realization", "kb.document")
            )
            before = dict(
                conn.execute(select(projects).where(projects.c.project_id == project_id))
                .mappings()
                .one()
            )
            realization = (
                conn.execute(
                    select(realizations).where(
                        realizations.c.realization_id == args.realization,
                        realizations.c.project_id == project_id,
                        realizations.c.release_id == args.release,
                    )
                )
                .mappings()
                .one()
            )
            docs = [
                dict(row)
                for row in conn.execute(
                    select(documents).where(documents.c.project_id == project_id)
                ).mappings()
            ]
            document = m1.retained_document(
                conn, product, prepared=prepared, project_id=project_id, documents=docs
            )
            corpus, _ = records(
                [row for row in docs if row["id"] == document.id],
                {},
                slice=None,
                scope=None,
                corpus=None,
            )
            binding = OperationBinding(
                args.release,
                args.realization,
                realization["data_revision"],
                canonical_bytes(
                    dict(
                        domain="statistics",
                        release=args.release,
                        source_input_sha256=sha256(INPUT.read_bytes()).hexdigest(),
                    )
                ),
            )
        registry = bind_pdf_source(
            m1.registry(pack),
            product,
            configuration="default",
            method_name="ingest.pdf_integrated",
            input_role="integrated",
        )
        registry = m1.bind_retained_document(registry, document)
        configs = {
            key: dict(value) for key, value in registry.file.configs.items() if key in ALLOWED
        }
        candidate = dict(
            configs["extract.m1_candidates"][source["candidate_base_configuration"]],
            **source["candidate_overrides"],
            region_pointers=regions,
            source_projection_digest=pin["projection_digest"],
        )
        configs["extract.m1_candidates"] = {"default": candidate}
        configs["extract.m1_annotations"] = {
            "default": dict(
                configs["extract.m1_annotations"]["default"],
                source_projection_digest=pin["projection_digest"],
            )
        }
        registry = MethodRegistry(
            [method for method in registry.methods() if method.name in ALLOWED],
            replace(registry.file, configs=configs),
            registry.sources,
            prepared=registry.prepared,
        )
        if any(
            method.version != "7"
            for method in registry.methods()
            if method.name == "extract.m1_candidates"
        ):
            raise RuntimeError("bounded parser journey requires the declared M1 candidate version7")
        graph = m1.source_graph()
        if {
            step.config.partition("/")[0] for _, steps in graph.stages for step in steps
        } != ALLOWED or graph.policy_propose:
            raise RuntimeError("bounded parser graph contains an unauthorized producer or proposal")
        # Validate configurations before creating a run; no model call occurs here.
        effective = {
            name: registry.resolve(name, "default").config.model_dump(mode="json")
            for name in sorted(ALLOWED)
        }
        state["phase"] = "source_methods"
        write(
            RAW / f"{args.receipt}-configuration.json",
            dict(
                configs=effective,
                method_declaration_sha256=sha256(
                    (pack / "m1-methods.yaml").read_bytes()
                ).hexdigest(),
                annotation_scope=(
                    "entire selected retained Chapter5; not just the 15 primary regions"
                ),
                region_groups=source["region_groups"],
                reference_answers_consumed=False,
            ),
        )
        report = run_source_methods(
            engine,
            project_id=project_id,
            prepared=prepared,
            binding=binding,
            registry=registry,
            graph=graph,
            method_settings=method_settings,
            domain="statistics",
            guideline=(pack / "m1-guideline.md").read_text(),
            corpus_record=corpus,
            extraction_policy="m1-candidate",
            extraction_policy_config=canonical_bytes(
                dict(
                    route=source["protocol"],
                    primary_regions=regions,
                    source_projection_digest=pin["projection_digest"],
                    reference_answers_consumed=False,
                    recognition=False,
                    conversion=False,
                )
            ).decode(),
        )
        state.update(run_id=int(report.run_id), phase="finalization")
        write(RAW / f"{args.receipt}-prepared.json", report.model_dump(mode="json"))
        tasks, configurations, methods, runs = map(
            table, ("ops.task", "ops.method_config", "ops.method", "ops.run")
        )
        with engine.connect() as conn:
            inventory = [
                dict(row)
                for row in conn.execute(
                    select(
                        tasks.c.id,
                        tasks.c.status,
                        tasks.c.unit_type,
                        tasks.c.unit_id,
                        tasks.c.reused_task_id,
                        methods.c.name,
                        methods.c.version,
                        configurations.c.config_hash,
                        configurations.c.params,
                    )
                    .join(configurations, configurations.c.id == tasks.c.method_config_id)
                    .join(methods, methods.c.id == configurations.c.method_id)
                    .where(tasks.c.run_id == report.run_id)
                    .order_by(tasks.c.id)
                ).mappings()
            ]
            runtime = conn.scalar(select(runs.c.runtime_id).where(runs.c.id == report.run_id))
        write(RAW / f"{args.receipt}-tasks.json", inventory)
        if {row["name"] for row in inventory} != ALLOWED or runtime != args.runtime:
            raise RuntimeError("actual method inventory/runtime differs from declared journey")
        candidate_tasks = [row for row in inventory if row["name"] == "extract.m1_candidates"]
        annotation_tasks = [row for row in inventory if row["name"] == "extract.m1_annotations"]
        if (
            len(candidate_tasks) != 1
            or len(annotation_tasks) != 1
            or candidate_tasks[0]["unit_id"] != annotation_tasks[0]["unit_id"]
        ):
            raise RuntimeError(
                "journey did not select exactly one shared source view for annotation and parsing"
            )
        view_id = candidate_tasks[0]["unit_id"]
        with engine.connect() as conn:
            views, membership = map(table, ("kb.source_view", "ops.run_source_view"))
            view = dict(
                conn.execute(
                    select(*[column for column in views.c if column.name != "projection"])
                    .join(membership, membership.c.source_view_id == views.c.id)
                    .where(membership.c.run_id == report.run_id, views.c.id == view_id)
                )
                .mappings()
                .one()
            )
            expected = dict(
                native_task_id=product.task_id,
                native_product_key=product.product_key,
                native_content_digest=product.content_digest,
                projection_digest=pin["projection_digest"],
                recipe_digest=pin["recipe_digest"],
                section_pointer=pin["section_pointer"],
                membership=pin["membership"],
            )
            if any(view[key] != value for key, value in expected.items()):
                raise RuntimeError("selected view differs from the exact retained source-only pin")
        completed = commands.finalize_bound_run(
            engine,
            report.run_id,
            f"{args.receipt}:parser:{report.run_id}",
            analytics=settings.analytics,
        )
        state.update(phase="bounded_inspection", completed=asdict(completed))
        with read_snapshot(engine) as conn:
            inspected = read_source_contributions(
                conn,
                prepared=prepared,
                run_id=int(report.run_id),
                source_view_id=view_id,
                method="extract.m1_candidates",
                cut_id=completed.cut_id,
                limit=10_000,
                include_details=False,
            )
            if inspected.more:
                raise RuntimeError("bounded selected contribution inventory exceeds 10000 rows")
            origin_ids = {
                row["reused_task_id"] or row["id"]
                for row in inventory
                if row["unit_type"] == "source_view"
            }
            summaries = retained_producer_summaries(conn, origin_ids)
            pages, cursor = [], None
            while True:
                page = serve_contributions(
                    conn,
                    ContributionRequest(
                        run_id=int(report.run_id),
                        source_view_id=view_id,
                        method="extract.m1_candidates",
                        include_details=True,
                        cursor=cursor,
                        limit=100,
                        page_bytes=8_000_000,
                        max_bytes=32_000_000,
                    ),
                )
                pages.append(page.model_dump(mode="json"))
                cursor = page.next_cursor
                if cursor is None:
                    break
            after = dict(
                conn.execute(select(projects).where(projects.c.project_id == project_id))
                .mappings()
                .one()
            )
        write(RAW / f"{args.receipt}-producer-summary.json", summaries)
        write(RAW / f"{args.receipt}-common-pages.json", pages)
        if before != after:
            raise RuntimeError("bounded parser journey changed the project defaults")
        by_operation = defaultdict(Counter)
        for row in inspected.contributions:
            by_operation[row["operation_key"]][row["kind"]] += 1
        operations = [
            dict(row, contribution_counts=dict(by_operation[row["operation_key"]]))
            for row in inspected.operations
        ]
        gaps = [
            dict(task_id=row["id"], method=row["name"], status=row["status"])
            for row in inventory
            if row["status"] not in {"done", "empty", "reused"}
        ]
        gaps.extend(retained_producer_gaps(summaries))
        gaps.extend(
            dict(
                operation_key=row["operation_key"],
                question=row["question"],
                outcome=row["outcome"],
                reason=row.get("reason"),
            )
            for row in operations
            if row["outcome"] not in {"succeeded", "empty"}
        )
        return dict(
            outcome="passed" if not gaps else "partial",
            run_id=int(report.run_id),
            release_id=args.release,
            runtime_id=runtime,
            completed=asdict(completed),
            source_view=view,
            physical_pin=pin,
            primary_regions=regions,
            annotation_scope="entire selected retained Chapter5",
            annotation_tasks=annotation_tasks,
            annotation_reused=annotation_tasks[0]["reused_task_id"] is not None,
            method_inventory=inventory,
            contribution_counts=dict(Counter(row["kind"] for row in inspected.contributions)),
            semantic_type_counts=dict(
                Counter(row["semantic_type"] for row in inspected.contributions)
            ),
            operations=operations,
            failures_and_gaps=gaps,
            project_defaults_preserved=True,
            project_defaults_before=before,
            project_defaults_after=after,
            reference_answers_consumed=False,
            conversion=False,
            recognition=False,
            raw_report_custody=(
                "complete original task results retained in ops.task_result; "
                "exports are bounded projections"
            ),
            assessment=(
                "not_run; coordinator must register fresh applicable "
                "independent source/output assessments"
            ),
            scope=(
                "selected retained native parser capabilities; no completeness, "
                "quality benefit or PCE07 closure claim"
            ),
        )


def main():
    parser = argparse.ArgumentParser(__doc__)
    for required in ("release", "realization", "runtime", "receipt"):
        parser.add_argument("--" + required, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", args.receipt):
        raise ValueError("receipt must be a simple immutable file prefix")
    suffixes = (
        "-driver.py",
        "-input.json",
        "-configuration.json",
        "-prepared.json",
        "-tasks.json",
        "-producer-summary.json",
        "-common-pages.json",
        "-failure.json",
        "-result.json",
    )
    for suffix in suffixes:
        if (RAW / (args.receipt + suffix)).exists():
            raise FileExistsError(RAW / (args.receipt + suffix))
    for suffix, path in (("-driver.py", Path(__file__)), ("-input.json", INPUT)):
        with (RAW / (args.receipt + suffix)).open("xb") as stream:
            stream.write(path.read_bytes())
    state = dict(
        phase="preparation",
        arguments=vars(args),
        execution_driver_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        source_input_sha256=sha256(INPUT.read_bytes()).hexdigest(),
    )
    try:
        result = run(args, state)
    except BaseException as error:
        write(
            RAW / f"{args.receipt}-failure.json",
            dict(state, outcome="failed", error_type=type(error).__name__, error=str(error)),
        )
        raise
    write(RAW / f"{args.receipt}-result.json", dict(result, execution=state))
    print(
        json.dumps(
            dict(
                outcome=result["outcome"],
                run_id=result["run_id"],
                receipt=str(RAW / f"{args.receipt}-result.json"),
            )
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
