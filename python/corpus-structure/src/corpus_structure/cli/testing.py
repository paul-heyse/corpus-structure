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
    Manifest,
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
    missing_lanes: list[str]
    lane_selections: dict[str, str]
    attempt_outcomes: dict[str, str]
    contexts: list[dict[str, Any]]


def _supervisor(*args: str, opened: dict[Path, int] | None = None) -> dict[str, Any]:
    root = checkout()
    descriptors = {str(path): f"/proc/self/fd/{fd}" for path, fd in (opened or {}).items()}
    process = run_owned(
        [
            "uv",
            "run",
            "python",
            "scripts/test_receipts.py",
            *(descriptors.get(arg, arg) for arg in args),
        ],
        cwd=root,
        pass_fds=tuple((opened or {}).values()),
    )
    if not process.stdout.strip():
        raise ResultError(
            safe_text(process.stderr.strip())[-2000:] or "test supervisor did not report"
        )
    try:
        report = jsonlib.loads(process.stdout)
    except ValueError as error:
        raise ResultError("test supervisor did not return valid JSON") from error
    sources = {descriptor: path for path, descriptor in descriptors.items()}
    for context in report.get("contexts", ()):
        directory = context["directory"]
        context["directory"] = sources.get(directory, directory)
    if "lane_selections" in report:
        report["lane_selections"] = {
            lane: sources.get(path, path) for lane, path in report["lane_selections"].items()
        }
    return report


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
        raise ResultError(safe_text(check.stderr.strip())[-2000:] or "unsupported pytest options")
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
    result.defer_settlement()
    try:
        process = run_recipe(name, *args, env=env)
    except RecipeError:
        result.manifest.details["custody_unsettled"] = True
        raise
    report = directory / "classification.json"
    if not report.is_file():
        result.manifest.details["custody_unsettled"] = True
        diagnostic(safe_text(process.stderr.strip())[-2000:] or "test lane did not settle")
        return "interrupted" if process.returncode in (130, 143) else "failed"
    result.publish(lane, directory)
    try:
        classified = jsonlib.loads(process.stdout)
    except ValueError as error:
        raise ResultError("test supervisor did not report its settlement") from error
    result.manifest.details.setdefault("lane_counts", {})[lane] = classified["counts"]
    if classified.get("custody_unsettled"):
        result.manifest.details["custody_unsettled"] = True
        diagnostic("test process ownership is unsettled; inspect the retained supervisor receipt")
        return "interrupted" if process.returncode in (130, 143) else "failed"
    else:
        result.confirm_settlement()
    if classified["retryable"]:
        result.manifest.details.setdefault("retryable_lanes", []).append(lane)
    status = classified["status"]
    if process.returncode in (130, 143):
        return "interrupted"
    if status == "not_run" and classified["empty"]:
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
    retryable = result.manifest.details.get("retryable_lanes", [])
    if result.manifest.details.get("custody_unsettled"):
        next_action = f"ci results recover {result.id}"
    elif outcome in {"failed", "interrupted"} and retryable:
        next_action = f"ci test retry {result.id} --lane {retryable[0]}"
    else:
        failed = next((lane for lane, status in outcomes.items() if status != "passed"), None)
        next_action = f"ci test --lane {failed}" if failed else None
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
        declared = lane or ("ordinary" if narrowed else "all")
        required_lanes = ["ordinary", "fault"] if declared == "all" else [declared]
        with result_store(ctx).operation(
            "test", scope={"lane": declared, "required_lanes": required_lanes, "narrowed": narrowed}
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


def _receipts(
    store: ResultStore, result: Manifest, stack: ExitStack
) -> dict[str, tuple[Path, int]]:
    if result.action not in {"test", "test.retry"} or result.settled is None:
        raise ResultError("a settled test result is required")
    if result.details.get("custody_unsettled"):
        return {}
    return {
        role: stack.enter_context(store.open_artifact(result.id, role)) for role in result.artifacts
    }


def _manifest_paths(receipts: list[Path]) -> list[str]:
    return [token for lane in receipts for token in ("--required-from", str(lane))]


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
        manifests = [store.show(result) for result in results]
        scopes = [_receipts(store, manifest, leases) for manifest in manifests]
        opened = dict(item for scope in scopes for item in scope.values())
        args = [
            token
            for scope in scopes
            for path, _ in scope.values()
            for token in ("--receipt-dir", str(path))
        ]
        initial = manifests[0]
        declared = initial.scope.get("lane")
        required = set(
            initial.scope.get("required_lanes")
            or (
                ["ordinary", "fault"]
                if declared == "all"
                else [declared]
                if declared
                else scopes[0]
            )
        )
        selectors = [token for lane in sorted(required) for token in ("--required-lane", lane)]
        for name in sorted(required & scopes[0].keys()):
            selectors.extend(("--required-lane-from", name, str(scopes[0][name][0])))
        for manifest, receipts in zip(manifests[1:], scopes[1:], strict=True):
            # The supervisor tries the original first. Only a full replacement
            # can supply a lane whose original selection could not be collected.
            if manifest.action == "test" and manifest.scope.get("narrowed") is False:
                for name in sorted(required & receipts.keys()):
                    if manifest.details.get("lanes", {}).get(name) == "passed":
                        selectors.extend(("--required-lane-from", name, str(receipts[name][0])))
        summary = (
            _supervisor(
                "classify",
                "--summary",
                *args,
                *selectors,
                opened=opened,
            )
            if args
            else {
                "status": "incomplete",
                "required_node_coverage": {},
                "source_contexts_differ": False,
                "contexts": [],
                "missing_lanes": sorted(required),
                "lane_selections": {},
            }
        )
        missing = summary["missing_lanes"]
        node_coverage = summary["required_node_coverage"]
        if missing:
            node_coverage["status"] = "unresolved"
        emit(
            Coverage(
                results=results,
                status="incomplete" if missing else summary["status"],
                node_coverage=node_coverage,
                sources_differ=summary["source_contexts_differ"],
                missing_lanes=missing,
                lane_selections=summary["lane_selections"],
                attempt_outcomes={m.id: m.outcome for m in manifests},
                contexts=summary["contexts"],
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
        with store.lease(original), ExitStack() as receipts_open:
            manifest = store.show(original)
            if manifest.details.get("custody_unsettled"):
                raise ResultError(f"settle the predecessor with ci results recover {original}")
            receipts = _receipts(store, manifest, receipts_open)
            with store.operation(
                "test.retry",
                scope={
                    "retry_of": original,
                    "required_lanes": [],
                },
            ) as result:
                outcomes: dict[str, str] = {}
                context = _supervisor("context")
                for current in ("ordinary", "fault"):
                    if current not in receipts or (lane is not None and lane != current):
                        continue
                    path, fd = receipts[current]
                    selection = result.directory / f"{current}-selection.txt"
                    flags = ["--receipt-dir", str(path), *_manifest_paths([path])]
                    report = _supervisor("classify", "--summary", *flags, opened={path: fd})
                    if report["retryable"] and report["required_unresolved"]:
                        prior = report["contexts"][0]["invocation"] or {}
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
                            "--summary",
                            *flags,
                            "--write-unresolved",
                            str(selection),
                            "--selection-lane",
                            current,
                            "--managed-selection",
                            opened={path: fd},
                        )
                        result.manifest.scope["required_lanes"].append(current)
                        outcomes[current] = _lane(result, current, selection=selection)
                        if outcomes[current] == "interrupted" or result.manifest.details.get(
                            "custody_unsettled"
                        ):
                            break
                    elif report["status"] != "passed":
                        remedy = f"{current} has no exact node retry; run ci test --lane {current}"
                        if lane is not None:
                            raise ResultError(remedy)
                        diagnostic(remedy)
                if not outcomes:
                    raise ResultError("no unresolved test selection")
                _finish(result, outcomes, json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="test")
