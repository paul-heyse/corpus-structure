"""Installed test operations using the repository receipt supervisor."""

from __future__ import annotations

import json as jsonlib
import os
from contextlib import ExitStack
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from pydantic import BaseModel

from corpus_structure.cli.managed import (
    Invocation,
    ResultError,
    ResultStore,
    result_boundary,
    result_store,
)
from corpus_structure.cli.output import JsonOpt, diagnostic, emit, safe_text, state
from corpus_structure.cli.recipes import RecipeError, checkout, run_owned, run_recipe

Lane = Literal["ordinary", "fault"]
app = typer.Typer(invoke_without_command=True, help="Run, retry and reconcile test campaigns.")


class Campaign(BaseModel):
    id: str
    outcome: str
    lanes: dict[str, str]
    next_action: str | None = None


class Coverage(BaseModel):
    results: list[str]
    status: str
    node_coverage: dict[str, Any]
    sources_differ: bool


def _supervisor(*args: str) -> dict[str, Any]:
    root = checkout()
    process = run_owned(
        ["uv", "run", "python", "scripts/test_receipts.py", *args],
        cwd=root,
    )
    if not process.stdout.strip():
        raise ResultError(
            safe_text(process.stderr.strip()[-2000:]) or "test supervisor did not report"
        )
    try:
        return jsonlib.loads(process.stdout)
    except ValueError as error:
        raise ResultError("test supervisor did not return valid JSON") from error


def _validate(args: tuple[str, ...]) -> bool:
    if not args:
        return False
    check = run_owned(
        [
            "uv",
            "run",
            "python",
            "scripts/test_receipts.py",
            "validate-pytest",
            "--report-selection",
            "--",
            *args,
        ],
        cwd=checkout(),
    )
    if check.returncode:
        raise ResultError(safe_text(check.stderr.strip()[-2000:]) or "unsupported pytest options")
    return check.stdout.strip() == "true"


def _lane(
    result: Invocation,
    lane: Lane,
    args: tuple[str, ...] = (),
    *,
    selection: Path | None = None,
    narrowed: bool = False,
) -> str:
    name = "test-all" if lane == "ordinary" else "test-native-faults"
    directory = result.directory / lane
    result.stage(lane)
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"CORPUS_CI_RECEIPT_DIR", "CORPUS_CI_SELECTION_FILE", "CORPUS_CI_PYTHON_ONLY"}
    }
    env["CORPUS_CI_RECEIPT_DIR"] = str(directory)
    if selection is not None:
        env["CORPUS_CI_SELECTION_FILE"] = str(selection)
    if lane == "ordinary" and (narrowed or selection is not None):
        env["CORPUS_CI_PYTHON_ONLY"] = "1"
    try:
        process = run_recipe(name, *args, env=env)
    except RecipeError:
        result.manifest.details["custody_unsettled"] = True
        raise
    report = directory / "classification.json"
    if not report.is_file():
        result.manifest.details["custody_unsettled"] = True
        diagnostic(safe_text(process.stderr.strip()[-2000:]) or "test lane did not settle")
        return "interrupted" if process.returncode in (130, 143) else "failed"
    result.publish(lane, directory)
    classified = jsonlib.loads(report.read_text())
    if classified.get("custody_unsettled"):
        result.manifest.details["custody_unsettled"] = True
        diagnostic("test process ownership is unsettled; inspect the retained supervisor receipt")
    status = classified["status"]
    if process.returncode in (130, 143):
        return "interrupted"
    if status == "not_run" and all(
        not item["selected"] and item["reporting_complete"] for item in classified["receipts"]
    ):
        return "empty"
    if status == "passed" and process.returncode == 0:
        return "passed"
    return "blocked" if status == "blocked" else "failed"


def _finish(result: Invocation, outcomes: dict[str, str], json: bool) -> None:
    outcome = next(
        (
            state
            for state in ("interrupted", "failed", "blocked", "empty")
            if state in outcomes.values()
        ),
        "passed",
    )
    next_action = (
        f"ci test retry {result.id}"
        if outcome == "failed" and result.manifest.artifacts
        else f"ci results show {result.id}"
        if outcome != "passed"
        else None
    )
    result.settle(outcome, **result.manifest.details, lanes=outcomes, next_action=next_action)
    emit(
        Campaign(id=result.id, outcome=outcome, lanes=outcomes, next_action=next_action), json=json
    )
    if outcome != "passed":
        raise typer.Exit(130 if outcome == "interrupted" else 1)


@app.callback()
def run_tests(
    ctx: typer.Context,
    lane: Annotated[Lane | None, typer.Option()] = None,
    json: JsonOpt = False,
) -> None:
    """Run applicable test lanes, or select one with --lane."""
    if ctx.invoked_subcommand is not None:
        if state(ctx).test_args or lane is not None or json:
            raise typer.BadParameter("place command options on the selected test subcommand")
        return
    args = state(ctx).test_args
    with result_boundary(json):
        narrowed = _validate(args)
        if narrowed and lane == "fault":
            raise ResultError("the exclusive fault lane owns its selection")
        with result_store(ctx).operation(
            "test", scope={"lane": lane or ("ordinary" if narrowed else "all")}
        ) as result:
            outcomes: dict[str, str] = {}
            if lane != "fault":
                outcomes["ordinary"] = _lane(result, "ordinary", args, narrowed=narrowed)
            if (
                not narrowed
                and lane != "ordinary"
                and outcomes.get("ordinary") != "interrupted"
                and not result.manifest.details.get("custody_unsettled")
            ):
                outcomes["fault"] = _lane(result, "fault", args)
            _finish(result, outcomes, json)


def _receipts(store: ResultStore, result_id: str) -> dict[str, Path]:
    result = store.show(result_id)
    if result.action not in {"test", "test.retry"} or result.settled is None:
        raise ResultError("a settled test result is required")
    return {role: store.artifact(result_id, role) for role in result.artifacts}


def _manifest_paths(receipts: list[Path]) -> list[str]:
    return [
        token
        for lane in receipts
        for events in sorted(lane.glob("events-*.jsonl"))
        for token in ("--required-from", str(events))
    ]


@app.command("coverage")
def coverage(
    ctx: typer.Context,
    results: Annotated[list[str], typer.Argument(min=1)],
    json: JsonOpt = False,
) -> None:
    """Compare attempts against the first result's required selection."""
    with result_boundary(json), ExitStack() as leases:
        store = result_store(ctx)
        for result in dict.fromkeys(results):
            leases.enter_context(store.lease(result))
        scopes = [_receipts(store, result) for result in results]
        args = [
            token
            for scope in scopes
            for path in scope.values()
            for token in ("--receipt-dir", str(path))
        ]
        if not scopes[0]:
            raise ResultError("the required campaign has no settled receipt")
        summary = _supervisor("classify", *args, *_manifest_paths(list(scopes[0].values())))
        emit(
            Coverage(
                results=results,
                status=summary["status"],
                node_coverage=summary["required_node_coverage"],
                sources_differ=summary["source_contexts_differ"],
            ),
            json=json,
        )


@app.command("retry")
def retry(
    ctx: typer.Context,
    original: str,
    lane: Annotated[Lane | None, typer.Option()] = None,
    json: JsonOpt = False,
) -> None:
    """Recollect and retry the unresolved identities from a retained receipt."""
    with result_boundary(json):
        store = result_store(ctx)
        with store.lease(original):
            receipts = _receipts(store, original)
            with store.operation("test.retry", scope={"retry_of": original}) as result:
                outcomes: dict[str, str] = {}
                context = _supervisor("context")
                for current in ("ordinary", "fault"):
                    if current not in receipts or (lane is not None and lane != current):
                        continue
                    path = receipts[current]
                    selection = result.directory / f"{current}-selection.txt"
                    flags = ["--receipt-dir", str(path), *_manifest_paths([path])]
                    report = _supervisor("classify", *flags)
                    if report["required_unresolved"]:
                        prior = report["receipts"][0]["invocation"] or {}
                        changed = [
                            name for name, value in context.items() if prior.get(name) != value
                        ]
                        if changed:
                            result.manifest.scope.setdefault("changed_context", {})[current] = (
                                changed
                            )
                            diagnostic(
                                f"{current} context changed ({', '.join(changed)}); "
                                "review coverage applicability after retry"
                            )
                        _supervisor(
                            "classify",
                            *flags,
                            "--write-unresolved",
                            str(selection),
                            "--selection-lane",
                            current,
                            "--managed-selection",
                        )
                        outcomes[current] = _lane(result, current, selection=selection)
                        if outcomes[current] == "interrupted" or result.manifest.details.get(
                            "custody_unsettled"
                        ):
                            break
                    elif report["status"] != "passed":
                        raise ResultError(
                            "no unresolved pytest nodes; run the affected lane explicitly"
                        )
                if not outcomes:
                    raise ResultError("no unresolved test selection")
                _finish(result, outcomes, json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="test")
