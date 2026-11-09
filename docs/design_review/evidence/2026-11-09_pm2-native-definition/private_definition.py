"""Stage and run one explicitly authorized private definition-chain comparison."""

import argparse
import json
import os
from copy import deepcopy
from pathlib import Path
from shutil import copytree

from pydantic import TypeAdapter
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.exc import DBAPIError

from corpus_structure.cli.managed import OperationAccount
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.definition_declaration import (
    DeclarationChainSelection,
    DeclarationComponentsConfig,
    DeclarationComponentsMethod,
)
from corpus_structure.methods.model_observation import (
    PRIVATE_DECLARATION_POLICY,
    private_declaration_enabled,
)
from corpus_structure.methods.pm2_products import PARSER_QUESTIONS
from corpus_structure.methods.pm2_source import HANLP_SEAM_LAYOUT
from corpus_structure.orchestrate.pm2_stage import ParserRunReport, ParserRunRequest
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import BoundRunReport, run_source_methods
from corpus_structure.semantic.authored_sql import (
    admit_archived_sql,
    analyze_archived_sql,
    has_authored_sql,
)
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.domain_operations import DomainResult
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import current_revision, migration_fence
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import open_release, persist_release
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import (
    StorageTarget,
    verify_declared_route,
    verify_target,
)
from corpus_structure.semantic.structural_products import (
    StructuralInput,
    StructuralProductReport,
    definition_component,
)
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    StructuralRequest,
    serve_structural_products,
)
from corpus_structure.settings import Settings


def stage(pack, directory):
    destination = directory / pack.name
    copytree(pack, destination)
    if (core := pack.parent / "core").is_dir() and not (directory / "core").exists():
        copytree(core, directory / "core")
    (destination / "pm2-definition-policy.json").write_bytes(
        canonical_bytes(PRIVATE_DECLARATION_POLICY)
    )
    *_, prepared = prepare_pack(destination)
    if not private_declaration_enabled(prepared.manifest):
        raise ValueError("staged release did not bind the private policy")
    return {"pack": str(destination), "release": prepared.release_id}


def deployment_binding(path, revision):
    deployment = json.loads(path.read_bytes())
    account = OperationAccount.model_validate(deployment["operation_account"])
    target = StorageTarget.model_validate(deployment["acquired_target"])
    if (
        deployment["stage"] != "deployed"
        or account.outcome != "passed"
        or account.cleanup != "established"
        or account.acquired_target != target
        or account.reached_revision != revision
        or not {"migration", "archive", "admission", "verified"} <= set(account.known_effects or ())
    ):
        raise ValueError("the approved native deployment did not settle on the selected target")
    return target


def archive_private(args):
    """Archive/admit the exact staged release; never activate or run it here."""
    from corpus_structure.semantic.execution_admission import verify_deployment_catalog

    target = deployment_binding(args.deployment, args.native_revision)
    stage_receipt = json.loads(args.stage_receipt.read_bytes())
    bundle, deps, profile, prepared = prepare_pack(Path(stage_receipt["pack"]))
    if prepared.release_id != stage_receipt["release"] or not private_declaration_enabled(
        prepared.manifest
    ):
        raise ValueError("the prepared private release differs from the exact staged receipt")
    settings = Settings()
    identity = f"source:pm2-private-definition:{prepared.release_id}"
    authored = has_authored_sql(prepared)

    def verified(conn, purpose):
        verify_declared_route(conn, settings)
        return verify_target(conn, target, purpose=purpose)

    with (
        open_runtime_engine(
            settings, "pm2-definition-native-fence", purpose="maintenance"
        ) as maintenance,
        maintenance.begin() as conn,
    ):
        verified(conn, "maintenance")
        migration_fence(conn)
        if current_revision(conn) != args.native_revision:
            raise ValueError("current native revision differs from the exact deployment receipt")
        verify_deployment_catalog(conn, revision=args.native_revision)
        required = (
            "ops.validate_hanlp_v2_report(bigint,jsonb)",
            "ops.validate_declaration_chain_component(jsonb,jsonb,jsonb,jsonb,text)",
        )
        if any(
            value is None
            for value in conn.execute(
                select(*(func.to_regprocedure(signature) for signature in required))
            ).one()
        ):
            raise ValueError("deployed catalog lacks the private parser and declaration guards")
        with (
            open_runtime_engine(settings, "pm2-definition-archive", purpose="admit") as engine,
            engine.begin() as writer,
        ):
            verified(writer, "admit")
            persist_release(writer, bundle, deps, profile, prepared)
            if not authored:
                admit_release(prepared, connection=writer)
        with open_runtime_engine(settings, "pm2-definition-release-read", purpose="read") as engine:
            if authored:
                with engine.connect() as reader:
                    verified(reader, "read")
                    analyzed = analyze_archived_sql(reader, prepared.release_id)
                with (
                    open_runtime_engine(settings, "pm2-definition-admit", purpose="admit") as admit,
                    admit.begin() as writer,
                ):
                    verified(writer, "admit")
                    admit_archived_sql(writer, prepared.release_id, analyzed=analyzed)
                    admit_release(prepared, connection=writer)
            with read_snapshot(engine) as reader:
                verified(reader, "read")
                archived = open_release(reader, prepared.release_id)
                if (
                    archived.manifest != prepared.manifest
                    or archived.artifacts_sha256 != prepared.artifacts_sha256
                ):
                    raise ValueError("archived private release differs from staged release")
        relation = table("data.realization")
        conn.execute(
            insert(relation)
            .values(
                realization_id=identity, release_id=prepared.release_id, project_id=args.project
            )
            .on_conflict_do_nothing(index_elements=[relation.c.realization_id])
        )
        revision = conn.execute(
            select(relation.c.data_revision).where(
                relation.c.realization_id == identity,
                relation.c.release_id == prepared.release_id,
                relation.c.project_id == args.project,
                relation.c.state == "active",
            )
        ).scalar_one()
    return {
        "release": prepared.release_id,
        "project": args.project,
        "realization": identity,
        "data_revision": revision,
        "native_revision": args.native_revision,
        "acquired_target": target.model_dump(mode="json"),
        "archived_and_admitted": True,
    }


def selected_source(args):
    inputs = StructuralInput.model_validate_json(args.inputs.read_bytes())
    (passage,) = (p for p in inputs.passages if p.passage_id == args.passage)
    (source,) = (s for s in inputs.sources if s.identity == passage.source_ref)
    return inputs, passage, source


def parser_request(args):
    _, passage, source = selected_source(args)
    start, end = args.extent
    if not start <= passage.start < passage.end <= end:
        raise ValueError("parser scope does not cover the selected passage")
    startup = json.loads(args.startup.read_bytes())
    return ParserRunRequest.model_validate(
        dict(
            project=source.project_id,
            release=args.release,
            realization=args.realization,
            assets=args.assets,
            scopes=[
                dict(
                    source=source.model_dump(mode="json"),
                    extent=args.extent,
                    profile={"provider": "hanlp", "device": "cpu", "startup": startup},
                    layout_policy=HANLP_SEAM_LAYOUT,
                )
            ],
        )
    ).model_dump(mode="json")


def run_chain(args):
    inputs, passage, source = selected_source(args)
    receipt = ParserRunReport.model_validate_json(args.parser_receipt.read_bytes())
    (parsed,) = receipt.scope_coverage
    if (
        parsed.source_view_id != source.source_view_id
        or parsed.question != PARSER_QUESTIONS["hanlp"]
        or parsed.operation_version != "2"
        or parsed.outcome != "succeeded"
        or parsed.task_id is None
        or parsed.origin_task_id is None
        or receipt.tasks != (parsed.task_id,)
        or not parsed.extent[0] <= passage.start < passage.end <= parsed.extent[1]
    ):
        raise ValueError("selected receipt lacks the exact completed parser v2 operation")
    settings = Settings()
    with open_runtime_engine(settings, "pm2-private-definition", purpose="write") as engine:
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, receipt.release)
            if not private_declaration_enabled(prepared.manifest):
                raise ValueError("parser release is missing the private declaration policy")
            completed = bind_completed_result(conn, receipt.run_id)
            if (
                completed.binding.release_id != receipt.release
                or completed.completed_cut_id != receipt.cut_id
            ):
                raise ValueError("parser completion differs from the exact released receipt")
            observed = read_source_contributions(
                conn,
                prepared=prepared,
                run_id=receipt.run_id,
                cut_id=receipt.cut_id,
                source_view_id=source.source_view_id,
                selected_task_id=parsed.task_id,
                method="extract.pm2_hanlp",
                method_version="2",
                include_details=True,
                limit=1024,
            )
            if observed.more:
                raise ValueError("selected parser output exceeds the bounded read")
            (naming,) = (
                row
                for row in observed.contributions
                if row["item_key"] == args.naming_frame and row["cut_member"] is True
            )
            if naming["origin_task_id"] != parsed.origin_task_id:
                raise ValueError("retained naming frame differs from the parser receipt origin")
            task, run, realization = map(table, ("ops.task", "ops.run", "data.realization"))
            runtime = conn.execute(
                select(run.c.runtime_id)
                .join(task, task.c.run_id == run.c.id)
                .where(task.c.id == naming["origin_task_id"])
            ).scalar_one()
            revision = conn.execute(
                select(realization.c.data_revision).where(
                    realization.c.realization_id == args.realization,
                    realization.c.release_id == receipt.release,
                    realization.c.project_id == source.project_id,
                    realization.c.state == "active",
                )
            ).scalar_one()
        reference = RetainedContributionRef(
            contribution_id=naming["contribution_id"],
            project_id=source.project_id,
            release_id=receipt.release,
            run_id=receipt.run_id,
            cut_id=receipt.cut_id,
            result_revision=completed.binding.data_revision,
            selected_task_id=naming["selected_task_id"],
            origin_task_id=naming["origin_task_id"],
            runtime_fingerprint=runtime,
        )
        selected = StructuralInput.model_validate(
            {
                **inputs.model_dump(mode="python"),
                "passages": (passage,),
                "sources": (source,),
                "dependencies": (source.identity, reference.contribution_id),
            }
        )
        config = DeclarationComponentsConfig(
            inputs=selected,
            structural_input_digest=selected.identity,
            selections=(
                DeclarationChainSelection(passage_id=passage.passage_id, parser=reference),
            ),
        )
        method = DeclarationComponentsMethod()
        result = run_source_methods(
            engine,
            project_id=source.project_id,
            prepared=prepared,
            binding=OperationBinding(
                receipt.release,
                args.realization,
                revision,
                canonical_bytes(
                    {"policy": PRIVATE_DECLARATION_POLICY["definition_declaration_chain"]}
                ),
            ),
            registry=MethodRegistry(
                (method,),
                MethodsFile(configs={method.name: {"private": config.model_dump(mode="json")}}),
            ),
            graph=Graph(((Stage.SCOPE, (Step(method.name + "/private"),)),), policy_propose=False),
            method_settings=MethodSettings(
                data_dir=args.output_directory, model_cache=settings.paths.model_cache
            ),
            selected_sources=(source,),
            kind="slice",
        )
    return result.model_dump(mode="json")


def review_selection(args):
    """Prepare a detached selection from the exact settled native definition and parser cut."""
    receipt = BoundRunReport.model_validate_json(args.chain_receipt.read_bytes())
    finished = TypeAdapter(DomainResult).validate_json(args.finalized_receipt.read_bytes())
    if receipt.status != "source_ready" or receipt.run_id != finished.run_id:
        raise ValueError("final definition cut differs from the settled source operation")
    settings = Settings()
    with (
        open_runtime_engine(settings, "pm2-definition-review-selection", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        page = serve_structural_products(
            conn,
            StructuralRequest(
                run_id=finished.run_id,
                cut_id=finished.cut_id,
                kind="definition_components",
                limit=1,
            ),
        )
    if (
        page.release_id != receipt.release_id
        or page.cut_id != finished.cut_id
        or page.next_after_task_id is not None
    ):
        raise ValueError("Reader returned a different completed declaration cut")
    (report,) = page.reports
    (selected_task,) = page.task_ids
    product = report.definition_components
    if product is None:
        raise ValueError("definition product was not retained")
    (component,) = product.components
    chain = component.declaration_chain
    if chain is None or chain.parser.release_id != receipt.release_id:
        raise ValueError("Reader did not return the exact private declaration witness")
    (source,) = report.inputs.sources
    if args.expected is not None:
        expected = json.loads(args.expected.read_bytes())
        if (
            component.term.model_dump(mode="json") != expected["term"]
            or component.content.model_dump(mode="json") != expected["content"]
            or chain.model_dump(mode="json", exclude={"parser"}) != expected["basis"]
        ):
            raise ValueError("retained declaration differs from the frozen source replay")
    return ReviewSelection(
        max_bytes=512 * 1024 * 1024,
        selections=(
            ContributionRequest(
                run_id=chain.parser.run_id,
                source_view_id=source.source_view_id,
                method="extract.pm2_hanlp",
                operation_version="2",
                selected_task_id=chain.parser.selected_task_id,
                include_details=True,
                limit=1000,
                page_bytes=16_000_000,
            ),
        ),
        structural_selections=(
            StructuralExportRequest(
                run_id=receipt.run_id,
                cut_id=finished.cut_id,
                kind="definition_components",
                selected_task_id=selected_task,
                limit=1,
            ),
        ),
    ).model_dump(mode="json")


def native_qualification(args):
    """Exercise the deployed role guard with a genuine result and one altered binding."""
    selection = ReviewSelection.model_validate_json(args.selection.read_bytes())
    (chosen,) = selection.structural_selections
    settings = Settings()
    target = deployment_binding(args.deployment, args.native_revision)
    with (
        open_runtime_engine(
            settings, "pm2-definition-native-refusal", purpose="maintenance"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        verify_declared_route(conn, settings)
        verify_target(conn, target, purpose="maintenance")
        if current_revision(conn) != args.native_revision:
            raise ValueError("native qualifier differs from the exact deployment receipt")
        session = bind_completed_result(conn, chosen.run_id)
        if session.completed_cut_id != chosen.cut_id or chosen.selected_task_id is None:
            raise ValueError("native qualifier does not address the exact completed declaration")
        member, result, task, cfg = map(
            table, ("ops.cut_task", "ops.task_result", "ops.task", "ops.method_config")
        )
        body, configuration = conn.execute(
            select(result.c.body, cfg.c.params)
            .select_from(member)
            .join(result, result.c.task_id == member.c.origin_task_id)
            .join(task, task.c.id == member.c.origin_task_id)
            .join(cfg, cfg.c.id == task.c.method_config_id)
            .where(member.c.cut_id == chosen.cut_id, member.c.task_id == chosen.selected_task_id)
        ).one()
        report = body["structural_product"]
        (component,) = report["definition_components"]["components"]
        (source,) = report["inputs"]["sources"]
        (passage,) = report["inputs"]["passages"]
        if body["release_id"] != session.binding.release_id:
            raise ValueError("native qualifier has a different producer release")

        def validate(candidate):
            conn.execute(
                select(
                    func.ops.validate_declaration_chain_component(
                        *(
                            literal(item, JSONB)
                            for item in (candidate, passage, source, configuration)
                        ),
                        body["release_id"],
                    )
                )
            ).scalar_one()

        validate(component)
        changed = deepcopy(component)
        binding = changed["declaration_chain"]["bindings"][0]
        binding["use_token"] += 1
        try:
            with conn.begin_nested():
                validate(changed)
        except DBAPIError as exc:
            refusal = exc.orig
            if (
                getattr(refusal, "sqlstate", None) != "23514"
                or getattr(getattr(refusal, "diag", None), "message_primary", None)
                != "declaration component differs from the exact native role chain"
            ):
                raise
        else:
            raise ValueError("deployed role guard accepted the altered declaration binding")
    return {
        "native_revision": args.native_revision,
        "run_id": chosen.run_id,
        "cut_id": chosen.cut_id,
        "task_id": chosen.selected_task_id,
        "exact_retained_component": "passed",
        "altered_role_binding": "refused",
    }


def detached_qualification(args):
    """Exercise detached semantic replay with the same single binding alteration."""
    from corpus_structure.serve.review_bundle import _member

    root = os.open(args.bundle, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with _member(root, "manifest.json", digest=args.manifest_sha256) as stream:
            manifest = json.load(stream)
        return detached_binding_refusal(root, manifest, args.manifest_sha256)
    finally:
        os.close(root)


def detached_binding_refusal(root, manifest, digest):
    from corpus_structure.methods.definition_declaration import CHAIN_METHOD
    from corpus_structure.serve.model_observation_replay import _verify_declaration_bases
    from corpus_structure.serve.review_bundle import _detached_relation

    origins = {row["origin_task_id"]: row for row in _detached_relation(root, manifest, "reports")}
    (declaration,) = (
        row for row in origins.values() if (row.get("body") or {}).get("method") == CHAIN_METHOD
    )
    body = declaration["body"]
    (contract,) = (
        row
        for row in _detached_relation(root, manifest, "contracts")
        if row["release_id"] == body["release_id"]
    )
    report = StructuralProductReport.model_validate(body["structural_product"])

    def validate(candidate):
        _verify_declaration_bases(
            root, manifest, candidate, body, declaration["configuration"], origins, contract
        )

    validate(report)
    candidate = report.model_dump(mode="json", exclude_none=True)
    (part,) = candidate["definition_components"]["components"]
    part.pop("component_id")
    part["declaration_chain"]["bindings"][0]["use_token"] += 1
    candidate["definition_components"]["components"][0] = definition_component(**part).model_dump(
        mode="json", exclude_none=True
    )
    try:
        validate(StructuralProductReport.model_validate(candidate))
    except ValueError as exc:
        if str(exc) != "definition declaration differs from retained role replay":
            raise
    else:
        raise ValueError("detached semantic replay accepted an altered declaration binding")
    return {
        "manifest_sha256": digest,
        "task_id": declaration["origin_task_id"],
        "exact_retained_component": "passed",
        "altered_role_binding": "refused",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    staged = commands.add_parser("stage-pack")
    staged.add_argument("pack", type=Path)
    staged.add_argument("directory", type=Path)
    archive = commands.add_parser("archive-private")
    archive.add_argument("--stage-receipt", type=Path, required=True)
    archive.add_argument("--deployment", type=Path, required=True)
    archive.add_argument("--native-revision", required=True)
    archive.add_argument("--project", required=True)
    request = commands.add_parser("parser-request")
    request.add_argument("--release", required=True)
    request.add_argument("--startup", type=Path, required=True)
    request.add_argument("--assets", type=Path, required=True)
    request.add_argument("--extent", type=int, nargs=2, required=True)
    execute = commands.add_parser("run-chain")
    execute.add_argument("--parser-receipt", type=Path, required=True)
    execute.add_argument("--naming-frame", required=True)
    execute.add_argument("--output-directory", type=Path, required=True)
    review = commands.add_parser("review-selection")
    review.add_argument("--chain-receipt", type=Path, required=True)
    review.add_argument("--finalized-receipt", type=Path, required=True)
    review.add_argument("--expected", type=Path)
    qualify = commands.add_parser("native-qualification")
    qualify.add_argument("--selection", type=Path, required=True)
    qualify.add_argument("--deployment", type=Path, required=True)
    qualify.add_argument("--native-revision", required=True)
    detached = commands.add_parser("detached-qualification")
    detached.add_argument("--bundle", type=Path, required=True)
    detached.add_argument("--manifest-sha256", required=True)
    for child in (request, execute):
        child.add_argument("--inputs", type=Path, required=True)
        child.add_argument("--passage", required=True)
        child.add_argument("--realization", required=True)
    args = parser.parse_args()
    if args.command == "stage-pack":
        output = stage(args.pack, args.directory)
    elif args.command == "archive-private":
        output = archive_private(args)
    elif args.command == "parser-request":
        output = parser_request(args)
    elif args.command == "run-chain":
        output = run_chain(args)
    elif args.command == "review-selection":
        output = review_selection(args)
    elif args.command == "native-qualification":
        output = native_qualification(args)
    else:
        output = detached_qualification(args)
    print(canonical_bytes(output).decode())


if __name__ == "__main__":
    main()
