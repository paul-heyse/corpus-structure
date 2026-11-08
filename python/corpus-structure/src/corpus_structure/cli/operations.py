"""Environment, maintenance and host actions through their owned recipes."""

from __future__ import annotations

import json as jsonlib
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import BaseModel
from rich.console import Group
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.managed import result_boundary, result_store
from corpus_structure.cli.output import (
    JsonOpt,
    cli_settings_report,
    diagnostic,
    emit,
    safe_text,
    state,
    write_report_text,
)
from corpus_structure.cli.recipes import (
    RecipeCancellation,
    RecipeStep,
    StepExcerpt,
    checkout,
    run_recipe,
    run_recipe_steps,
)
from corpus_structure.settings import DeploymentProfile, SettingsReport

context_app = typer.Typer(help="Inspect invocation context.")
docs_app = typer.Typer(help="Check published documentation.")
evidence_app = typer.Typer(help="Check and retain evidence.")
adr_app = typer.Typer(help="Maintain architecture decisions.")
release_app = typer.Typer(help="Check the bound semantic release.")
host_app = typer.Typer(help="Operate the checkout's dedicated development cluster.")

_CHECK_RECIPES = {
    "types": "types",
    "lint": "ruff-check",
    "docs": "docs-check",
    "deps": "deps",
    "rules": "rules-scan",
    "adr": "adr-lint",
}
_CHECK_OPTIONS = {recipe: option for option, recipe in _CHECK_RECIPES.items()}


class ContextReport(BaseModel):
    checkout: Path | None
    results: Path
    settings: SettingsReport
    environment_fields: list[str]
    interpreter: str
    python_version: str
    target: DeploymentProfile
    observed_binding: None = None


class RecipeReport(BaseModel):
    recipe: str
    exit_code: int
    output: str
    diagnostic: str


class RecipeStepsReport(BaseModel):
    recipe: str
    exit_code: int
    steps: tuple[RecipeStep, ...]
    excerpts: tuple[StepExcerpt, ...]


def _render_steps(report: RecipeStepsReport) -> Group:
    table = Table.grid(padding=(0, 2))
    table.add_column()
    table.add_column()
    table.add_column()
    parts: list[Text | Table] = [Text(f"{report.recipe} exited {report.exit_code}")]
    for step in report.steps:
        outcome = step.outcome.replace("_", " ")
        if step.exit_code:
            outcome += f" (exit {step.exit_code})"
        if step.reason:
            outcome += f" ({step.reason})"
        retry = ""
        if step.outcome == "failed":
            option = _CHECK_OPTIONS.get(step.name)
            retry = f"ci check --only {option}" if option else f"just {step.name}"
        table.add_row(Text(step.name), Text(outcome), Text(retry))
    if report.steps:
        parts.append(table)
    else:
        parts.append(Text("Step outcomes unavailable"))
    for excerpt in report.excerpts:
        suffix = " (truncated)" if excerpt.truncated else ""
        parts.extend((Text(f"{excerpt.step} {excerpt.stream}{suffix}"), Text(excerpt.text)))
    return Group(*parts)


def recipe_action(name: str, json: bool, *args: str, no_sync: bool = False) -> None:
    with result_boundary(json):
        env = {**os.environ, "UV_NO_SYNC": "1"} if no_sync else None
        process = run_recipe(name, *args, env=env)
        emit(
            RecipeReport(
                recipe=name,
                exit_code=process.returncode,
                output=safe_text(process.stdout)[-12000:],
                diagnostic=safe_text(process.stderr)[-6000:],
            ),
            json=json,
            exit_code=process.returncode,
        )
        if process.returncode:
            raise typer.Exit(process.returncode)


@context_app.command("show")
def context_show(
    ctx: typer.Context, target: DeploymentProfile = "development", json: JsonOpt = False
) -> None:
    """Show effective redacted settings without opening a database."""
    with result_boundary(json):
        from corpus_structure.cli.recipes import RecipeError
        from corpus_structure.settings import known_env_names

        try:
            root = checkout(ctx)
        except RecipeError:
            root = None
        configured = state(ctx).settings()
        from corpus_structure.cli.managed import ResultError

        if target == "deployment" and configured.deployment is None:
            raise ResultError("configure CORPUS_DEPLOYMENT__URL for the deployment target")
        emit(
            ContextReport(
                checkout=root,
                results=result_store(ctx).root,
                settings=cli_settings_report(configured),
                environment_fields=sorted(known_env_names() & os.environ.keys()),
                interpreter=sys.executable,
                python_version=sys.version,
                target=target,
            ),
            json=json,
        )


def doctor(json: JsonOpt = False) -> None:
    """Check the prepared toolchain without synchronizing dependencies."""
    recipe_action("ready", json, no_sync=True)


def setup(json: JsonOpt = False) -> None:
    """Synchronize the checkout's locked environment."""
    recipe_action("ci-setup", json)


def check(
    only: Annotated[
        Literal["types", "lint", "docs", "deps", "rules", "adr"] | None,
        typer.Option(help="Run one repository check.", metavar="CHECK"),
    ] = None,
    json: JsonOpt = False,
    view: Annotated[
        Literal["steps"] | None,
        typer.Option(help="Report ordered step outcomes.", rich_help_panel="Reporting"),
    ] = None,
) -> None:
    """Run read-only repository checks and show which steps settled."""
    name = _CHECK_RECIPES[only] if only else "ci-check"
    if json and view is None:
        recipe_action(name, json)
        return
    with result_boundary(json):
        try:
            if only:
                process, steps, excerpts = run_recipe_steps("ci-check-only", name)
            else:
                process, steps, excerpts = run_recipe_steps(name)
        except RecipeCancellation as error:
            diagnostic(str(error))
            raise typer.Exit(128 + error.signum) from None
        emit(
            RecipeStepsReport(
                recipe=name, exit_code=process.returncode, steps=steps, excerpts=excerpts
            ),
            json=json,
            render=_render_steps,
            exit_code=process.returncode,
        )
        if process.returncode:
            raise typer.Exit(process.returncode)


def format_source(json: JsonOpt = False) -> None:
    """Apply the checkout's formatter."""
    recipe_action("fmt", json)


@docs_app.command("check")
def docs_check(json: JsonOpt = False) -> None:
    recipe_action("docs-check", json)


@docs_app.command("commands")
def command_reference(
    ctx: typer.Context,
    json: JsonOpt = False,
    stdout: Annotated[
        bool,
        typer.Option(
            "--stdout", help="Write Markdown directly to stdout.", rich_help_panel="Reporting"
        ),
    ] = False,
) -> None:
    """Generate the installed command reference for reading or managed retrieval."""
    from corpus_structure.cli.managed import Delivery, ResultError

    if stdout and json:
        raise typer.BadParameter("choose --stdout or --json", param_hint="--stdout")
    if stdout:
        with result_boundary(False):
            try:
                process = run_recipe("ci-reference", verify_cancelled_group=True)
            except RecipeCancellation as error:
                diagnostic(str(error))
                raise typer.Exit(128 + error.signum) from None
            if process.returncode:
                diagnostic(safe_text(process.stderr).strip()[-2000:])
                raise typer.Exit(process.returncode)
            write_report_text(process.stdout)
        return
    with result_boundary(json), result_store(ctx).operation("docs.commands") as result:
        signal = None
        process = None
        try:
            process = run_recipe("ci-reference", verify_cancelled_group=True)
        except RecipeCancellation as error:
            signal = error.signum
            result.defer_settlement()
        else:
            if process.returncode in (130, 143):
                signal = process.returncode - 128
        if signal is not None:
            next_action = (
                "Inspect recipe process custody before retry"
                if result.manifest.details.get("custody_unsettled")
                else "ci docs commands"
            )
            result.settle("interrupted", signal=signal, next_action=next_action)
            diagnostic(f"Reference generation interrupted · {next_action}")
            if json:
                write_report_text(
                    jsonlib.dumps(
                        {"error": {"code": "reference_interrupted", "invocation_id": result.id}}
                    )
                    + "\n",
                    exit_code=128 + signal,
                )
            raise typer.Exit(128 + signal)
        assert process is not None
        if process.returncode:
            raise ResultError(safe_text(process.stderr.strip())[-2000:])
        artifact = result.directory / "commands.md"
        artifact.write_text(process.stdout, encoding="utf-8")
        result.publish("commands", artifact)
        result.settle()
        emit(Delivery(id=result.id, path=artifact), json=json)


@evidence_app.command("check")
def evidence_check(json: JsonOpt = False) -> None:
    recipe_action("evidence", json, "check")


@evidence_app.command("index")
def evidence_index(json: JsonOpt = False) -> None:
    recipe_action("evidence", json, "index")


@evidence_app.command("finalize")
def evidence_finalize(folder: str, record: str, json: JsonOpt = False) -> None:
    """Finalize a specific prepared evidence record through the evidence owner."""
    recipe_action("evidence", json, "finalize", "--", folder, record)


@evidence_app.command("retain")
def evidence_retain(
    ctx: typer.Context,
    result: str,
    role: str | None = None,
    consumer: Annotated[
        str | None, typer.Option("--for", help="Plan, review, or decision consuming the result.")
    ] = None,
    json: JsonOpt = False,
) -> None:
    """Promote a named settled artifact into the evidence working set."""
    from corpus_evidence.model import FileRef, Record, Result
    from corpus_evidence.store import Folder, finalize, write
    from corpus_structure.cli.managed import Delivery, ResultError
    from corpus_structure.serve.companion_export import _publish_directory

    with result_boundary(json):
        store = result_store(ctx)
        with store.lease(result):
            manifest = store.show(result, role=role)
            if not manifest.custody_settled():
                raise ResultError(
                    "evidence promotion requires established custody; inspect the managed result"
                )
            consumer = consumer or manifest.scope.get("consumer")
            if not isinstance(consumer, str):
                raise ResultError("name the evidence consumer with --for")
            role = manifest.artifact_role(role)
            artifact = store.deliver(result, role, None)
            evidence = checkout(ctx) / "docs/design_review/evidence"
            day = datetime.now(UTC).date().isoformat()
            destination = evidence / f"{day}_cli-{result}"
            with tempfile.TemporaryDirectory(prefix=".retain-", dir=evidence) as scratch:
                bundle = Path(scratch) / "bundle"
                bundle.mkdir()
                raw = bundle / "raw"
                raw.mkdir()
                relative = f"raw/{artifact.name}"
                provenance = "invocation.json"
                (bundle / provenance).write_text(
                    jsonlib.dumps(
                        {
                            "id": manifest.id,
                            "action": manifest.action,
                            "stage": manifest.stage,
                            "started": manifest.started,
                            "settled": manifest.settled,
                            "outcome": manifest.outcome,
                            "artifact_role": role,
                            "custody": "settled",
                            "operation_account": manifest.operation_account.model_dump(mode="json")
                            if manifest.operation_account is not None
                            else None,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                outcome: Literal["passed", "failed", "blocked", "not_run"]
                if manifest.outcome == "empty":
                    outcome = "not_run"
                elif manifest.outcome in ("passed", "blocked"):
                    outcome = "passed" if manifest.outcome == "passed" else "blocked"
                else:
                    outcome = "failed"
                record = Record(
                    id=f"cli.{result}",
                    title=f"Retained CLI invocation {result}",
                    finalized=datetime.now(UTC).date(),
                    question=f"What evidence did {manifest.action} produce for {consumer}?",
                    method="Copy the selected published artifact under the invocation lease.",
                    inputs=[FileRef(path=provenance, role="invocation-provenance")],
                    outputs=[FileRef(path=relative, role="retained-artifact")],
                    results=[Result(name="invocation_outcome", value=manifest.outcome)],
                    outcome=outcome,
                    conclusion=f"The retained invocation settled as {manifest.outcome}.",
                    consumed_by=[consumer],
                )
                store.deliver(result, role, bundle / relative)
                folder = Folder(bundle)
                write(folder, record)
                finalize(folder, record.id)
                (bundle / "README.md").write_text(
                    "# Retained CLI evidence\n\n"
                    f"Invocation `{result}` ended with `{manifest.outcome}`. "
                    f"Retained `{artifact.name}` at `{relative}`.\n",
                    encoding="utf-8",
                )
                _publish_directory(bundle, destination)
            index = run_recipe("evidence", "index")
            if index.returncode:
                raise ResultError(f"evidence retained at {destination}; run ci evidence index")
            emit(Delivery(id=result, path=destination), json=json)


@release_app.command("check")
def release_check(
    ctx: typer.Context,
    project: str | None = None,
    release: str | None = None,
    target: DeploymentProfile = "development",
    json: JsonOpt = False,
) -> None:
    """Verify the selected release against its immutable archive."""
    from sqlalchemy import select

    from corpus_structure.cli.managed import ResultError
    from corpus_structure.cli.target import select_target
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.releases import ReleaseConflict, verify_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import (
        StorageTarget,
        acquired_target,
        verify_declared_route,
    )

    class ReleaseCheck(BaseModel):
        project: str
        release_id: str
        generation: int | None
        target: DeploymentProfile
        acquired: StorageTarget

    with result_boundary(json):
        selected, settings = select_target(ctx, target)
        project = project or settings.runtime.default_project
        projects = table("data.project")
        with (
            open_runtime_engine(settings, "ci-release-check", purpose="read", timeout=5) as engine,
            engine.connect() as conn,
        ):
            if selected == "deployment":
                verify_declared_route(conn, settings)
            acquired = acquired_target(conn, purpose="read")
            generation = None
            if release is None:
                row = conn.execute(
                    select(projects.c.active_release_id, projects.c.generation).where(
                        projects.c.project_id == project
                    )
                ).one_or_none()
                if row is None or row.active_release_id is None:
                    raise ResultError("project has no active release; supply an archived --release")
                release, generation = row.active_release_id, row.generation
            try:
                verify_release(conn, release)
            except KeyError as error:
                if error.args != (release,):
                    raise
                raise ResultError("release is unavailable in the configured archive") from error
            except ReleaseConflict as error:
                raise ResultError(str(error)) from error
            emit(
                ReleaseCheck(
                    project=project,
                    release_id=release,
                    generation=generation,
                    target=selected,
                    acquired=acquired,
                ),
                json=json,
            )


class SelectionReport(BaseModel):
    project: str
    release_id: str | None
    generation: int
    run_id: int | None = None
    target: DeploymentProfile
    acquired: dict[str, str | int]


@release_app.command("activate")
def release_activate(
    ctx: typer.Context,
    release: str,
    project: str | None = None,
    target: DeploymentProfile | None = None,
    expected_generation: int | None = None,
    json: JsonOpt = False,
) -> None:
    """Explicitly activate an archived release without selecting a run."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.managed import ResultError
    from corpus_structure.cli.target import select_target
    from corpus_structure.semantic.releases import (
        ActivationConflict,
        activate_release,
        activation_token,
    )
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import (
        acquired_target,
        verify_declared_route,
        verify_target,
    )

    with failure_boundary(
        json, expected=(ActivationConflict, ResultError), report_expected_validation=False
    ):
        selected, settings = select_target(ctx, target, effect=True)
        project = project or settings.runtime.default_project
        with (
            open_runtime_engine(settings, "ci-release-read", purpose="read") as reader,
            reader.connect() as read,
            open_runtime_engine(settings, "ci-release-activate", purpose="admit") as admit,
            admit.begin() as conn,
        ):
            if selected == "deployment":
                verify_declared_route(read, settings)
            acquired = verify_target(conn, acquired_target(read, purpose="read"), purpose="admit")
            try:
                before = activation_token(conn, project)
            except KeyError as error:
                if error.args != (project,):
                    raise
                raise ResultError("project is unavailable on the selected target") from error
            if expected_generation is not None and before.generation != expected_generation:
                raise ActivationConflict("project generation differs from the approved activation")
            token = activate_release(
                conn,
                project,
                release,
                expected_parent=before.release_id,
                expected_generation=before.generation,
                sql_reader=read,
            )
        emit(
            SelectionReport(
                project=project,
                release_id=token.release_id,
                generation=token.generation,
                target=selected,
                acquired=acquired.model_dump(mode="json"),
            ),
            json=json,
        )


def promote(
    ctx: typer.Context,
    run: int,
    project: str | None = None,
    target: DeploymentProfile | None = None,
    expected_generation: int | None = None,
    json: JsonOpt = False,
) -> None:
    """Explicitly select a completed run for the active release."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.managed import ResultError
    from corpus_structure.cli.target import select_target
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.releases import ActivationConflict, activation_token
    from corpus_structure.semantic.runtime import open_runtime_engine, select_completed_result
    from corpus_structure.semantic.storage_target import (
        acquired_target,
        verify_declared_route,
        verify_target,
    )

    with failure_boundary(
        json,
        expected=(ActivationConflict, OperationConflict, ResultError),
        report_expected_validation=False,
    ):
        selected, settings = select_target(ctx, target, effect=True)
        project = project or settings.runtime.default_project
        with (
            open_runtime_engine(settings, "ci-promote-read", purpose="read") as reader,
            reader.connect() as read,
            open_runtime_engine(settings, "ci-promote", purpose="admit") as engine,
            engine.begin() as conn,
        ):
            if selected == "deployment":
                verify_declared_route(read, settings)
            acquired = verify_target(conn, acquired_target(read, purpose="read"), purpose="admit")
            try:
                before = activation_token(conn, project)
            except KeyError as error:
                if error.args != (project,):
                    raise
                raise ResultError("project is unavailable on the selected target") from error
            if expected_generation is not None and before.generation != expected_generation:
                raise ActivationConflict("project generation differs from the approved selection")
            generation = select_completed_result(conn, project, run, before.generation)
        emit(
            SelectionReport(
                project=project,
                release_id=before.release_id,
                generation=generation,
                run_id=run,
                target=selected,
                acquired=acquired.model_dump(mode="json"),
            ),
            json=json,
        )


@adr_app.command("lint")
def adr_lint(json: JsonOpt = False) -> None:
    recipe_action("adr", json, "lint")


@adr_app.command("revisit")
def adr_revisit(json: JsonOpt = False) -> None:
    recipe_action("adr", json, "revisit")


@adr_app.command("new")
def adr_new(slug: str, title: str | None = None, json: JsonOpt = False) -> None:
    options = () if title is None else ("--title", title)
    recipe_action("adr", json, "new", slug, *options)


@host_app.command("status")
def host_status(json: JsonOpt = False) -> None:
    recipe_action("db-status", json)


@host_app.command("provision")
def host_provision(json: JsonOpt = False) -> None:
    recipe_action("db-provision", json)


@host_app.command("roles")
def host_roles(json: JsonOpt = False) -> None:
    recipe_action("db-semantic-roles", json)


@host_app.command("up")
def host_up(json: JsonOpt = False) -> None:
    recipe_action("db-up", json)


@host_app.command("down")
def host_down(json: JsonOpt = False) -> None:
    recipe_action("db-down", json)


def register(app: typer.Typer) -> None:
    app.command("doctor")(doctor)
    app.command("setup")(setup)
    app.command("check")(check)
    app.command("format")(format_source)
    app.command("promote")(promote)
    app.add_typer(context_app, name="context")
    app.add_typer(docs_app, name="docs")
    app.add_typer(evidence_app, name="evidence")
    app.add_typer(adr_app, name="adr")
    app.add_typer(host_app, name="host")
    app.add_typer(release_app, name="release")
