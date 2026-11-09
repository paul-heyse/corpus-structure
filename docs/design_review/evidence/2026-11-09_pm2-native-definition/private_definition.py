"""Stage and run one explicitly authorized private definition-chain comparison."""

import argparse
import json
from pathlib import Path
from shutil import copytree

from sqlalchemy import select

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
from corpus_structure.methods.pm2_source import HANLP_SEAM_LAYOUT
from corpus_structure.orchestrate.pm2_stage import ParserRunReport, ParserRunRequest
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
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
        or parsed.operation_version != "2"
        or parsed.outcome != "succeeded"
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
            if completed.binding.release_id != receipt.release:
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    staged = commands.add_parser("stage-pack")
    staged.add_argument("pack", type=Path)
    staged.add_argument("directory", type=Path)
    request = commands.add_parser("parser-request")
    request.add_argument("--release", required=True)
    request.add_argument("--startup", type=Path, required=True)
    request.add_argument("--assets", type=Path, required=True)
    request.add_argument("--extent", type=int, nargs=2, required=True)
    execute = commands.add_parser("run-chain")
    execute.add_argument("--parser-receipt", type=Path, required=True)
    execute.add_argument("--naming-frame", required=True)
    execute.add_argument("--output-directory", type=Path, required=True)
    for child in (request, execute):
        child.add_argument("--inputs", type=Path, required=True)
        child.add_argument("--passage", required=True)
        child.add_argument("--realization", required=True)
    args = parser.parse_args()
    if args.command == "stage-pack":
        output = stage(args.pack, args.directory)
    elif args.command == "parser-request":
        output = parser_request(args)
    else:
        output = run_chain(args)
    print(canonical_bytes(output).decode())


if __name__ == "__main__":
    main()
