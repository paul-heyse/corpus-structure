"""Installed test operations using the repository receipt supervisor."""

from __future__ import annotations

import json as jsonlib
import os
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from pydantic import BaseModel, ConfigDict, Field
from rich.console import Group
from rich.table import Table
from rich.text import Text

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
Phase = Literal["collection", "setup", "call", "teardown", "unknown"]
ReportLimit = Annotated[int, typer.Option(min=1, max=100)]
Workers = Annotated[
    int | None, typer.Option(min=1, help="Ordinary pytest workers (default: sized to explicit IDs; paths use auto).")
]
_DEFAULT_LIMIT = 20
_LANES: tuple[Lane, ...] = ("ordinary", "fault")
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


class CoverageCounts(BaseModel):
    status: str
    required: int
    covered: int
    unresolved: int
    applicability_note: str


class CoverageSummary(BaseModel):
    results: list[str]
    status: str
    node_coverage: CoverageCounts
    sources_differ: bool
    context_differences: list[str]
    context_unknowns: list[str]
    missing_lanes: list[str]
    selected_lanes: list[str]
    attempt_outcomes: dict[str, str]
    active_attempts: list[str]
    unsettled_attempts: list[str]
    next_actions: dict[str, str]
    native_observations: dict[str, int]


class UnresolvedNode(BaseModel):
    nodeid: str
    observations: list[str]


class UnresolvedCoverage(CoverageSummary):
    limit: int
    selected: int
    available: int
    omitted: int
    ordering: Literal["node_id"] = "node_id"
    sanitized_identities: int
    items: list[UnresolvedNode]


class NativePytestLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    native_path: str
    role: Literal["reprcrash", "reprfileloc"]
    path: str | None
    lineno: int | None
    message: str | None


class NativePytestChain(BaseModel):
    model_config = ConfigDict(extra="forbid")
    native_path: str
    description: str | None


class NativePytestOmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    native_path: str
    reason: str


class NativePytestTraceback(BaseModel):
    """Recorded pytest file locations, distinct from live exception observations."""

    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    format: Literal["pytest_report_longrepr"]
    scope: Literal["structured_file_locations_and_chain_descriptions"]
    availability: Literal["available", "partial", "unavailable"]
    locations: list[NativePytestLocation]
    chains: list[NativePytestChain]
    omissions: list[NativePytestOmission]
    omissions_omitted: int
    location_limit: int
    traversal_limit: int
    string_char_limit: int
    transport_bytes_limit: int
    display_string_chars: int | None = None


def _present_native_traceback(trace: NativePytestTraceback, chars: int) -> NativePytestTraceback:
    """Normalize complete allowed strings before applying one display-string budget."""
    selected = trace.model_copy(deep=True)
    for location in selected.locations:
        location.native_path = _display_text(location.native_path)
        location.path = _display_text(location.path) if location.path is not None else None
        location.message = _display_text(location.message) if location.message is not None else None
    for chain in selected.chains:
        chain.native_path = _display_text(chain.native_path)
        chain.description = (
            _display_text(chain.description) if chain.description is not None else None
        )
    for omission in selected.omissions:
        omission.native_path = _display_text(omission.native_path)
        omission.reason = _display_text(omission.reason)
    remaining = chars

    def bounded(value: str | None, path: str) -> str | None:
        nonlocal remaining
        if value is None:
            return None
        if len(value) <= remaining:
            remaining -= len(value)
            return value
        if len(selected.omissions) < 16:
            selected.omissions.append(
                NativePytestOmission(
                    native_path=path,
                    reason="complete redacted string exceeds native display budget",
                )
            )
        else:
            selected.omissions_omitted += 1
        if selected.availability == "available":
            selected.availability = "partial"
        return None

    for location in selected.locations:
        location.path = bounded(location.path, location.native_path + ".path")
        location.message = bounded(location.message, location.native_path + ".message")
    for chain in selected.chains:
        chain.description = bounded(chain.description, chain.native_path + "[2]")
    selected.display_string_chars = chars
    return selected


class FailureEvent(BaseModel):
    lane: Lane
    nodeid: str
    phase: Phase
    outcome: Literal["failed", "blocked"]
    reason: Literal["collection_failure", "prerequisite", "pytest_failure"]
    diagnostic: str | None = None
    diagnostic_truncated: bool = False
    native_traceback: NativePytestTraceback | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class RustEvidence(BaseModel):
    status: str
    applicability: str
    functional_coverage: bool
    listed_test_count: int | None = None
    reported_test_count: int | None = None
    reason: str | None = None
    reason_truncated: bool = False


class FailureLane(BaseModel):
    status: str
    reporting_complete: bool
    native_observation: str | None = None
    reporting_errors: list[str] = []
    reporting_errors_omitted: int = 0
    reporting_errors_truncated: bool = False
    rust: RustEvidence | None = None


class Failures(BaseModel):
    result_id: str
    outcome: str
    availability: Literal["available", "partial", "unavailable"]
    lane: Lane | None
    phase: Phase | None
    lanes: dict[Lane, FailureLane]
    limit: int
    after: int
    next_after: int | None
    selected: int
    available: int
    omitted: int
    ordering: Literal["lane_collection_node_phase"] = "lane_collection_node_phase"
    sanitized_identities: int
    items: list[FailureEvent]
    next_action: str | None = None


def _literal(value: str) -> Text:
    return Text(_display_text(value))


def _display_text(value: str) -> str:
    return safe_text(value).replace("\n", r"\n").replace("\t", r"\t")


def _sanitize_nodes(items: list[FailureEvent] | list[UnresolvedNode]) -> int:
    sanitized = 0
    for item in items:
        display = _display_text(item.nodeid)
        sanitized += display != item.nodeid
        item.nodeid = display
    return sanitized


def _render_coverage(report: CoverageSummary) -> Group:
    rows = Table.grid(padding=(0, 1))
    rows.add_column()
    rows.add_column(overflow="fold")
    counts = report.node_coverage
    original = report.results[0]
    rows.add_row("Original", _literal(f"{original} ({report.attempt_outcomes[original]})"))
    outcomes = Counter(report.attempt_outcomes.values())
    rows.add_row(
        "Attempts", _literal(", ".join(f"{key}: {value}" for key, value in outcomes.items()))
    )
    rows.add_row("Status", _literal(report.status))
    rows.add_row("Coverage", _literal(counts.status))
    if counts.required or report.selected_lanes:
        rows.add_row(
            "Nodes",
            Text(f"{counts.covered}/{counts.required} covered, {counts.unresolved} unresolved"),
        )
    rows.add_row("Missing lanes", _literal(", ".join(report.missing_lanes) or "none"))
    rows.add_row(
        "Sources differ", Text("yes" if report.sources_differ else "no observed difference")
    )
    rows.add_row(
        "Context changes", _literal(", ".join(report.context_differences) or "none observed")
    )
    if report.context_unknowns:
        rows.add_row("Unknown context", _literal(", ".join(report.context_unknowns)))
    if report.active_attempts or report.unsettled_attempts:
        rows.add_row(
            "Custody",
            Text(
                f"{len(report.active_attempts)} active, {len(report.unsettled_attempts)} unsettled"
            ),
        )
    for result, action in report.next_actions.items():
        rows.add_row("Next action", _literal(f"{result}: {action}"))
    if report.native_observations:
        rows.add_row(
            "Native receipts",
            _literal(
                ", ".join(f"{key}: {value}" for key, value in report.native_observations.items())
            ),
        )
    if not isinstance(report, UnresolvedCoverage):
        if counts.unresolved:
            rows.add_row("Detail", Text("Use --view unresolved for exact node identities."))
        return Group(rows, _literal(counts.applicability_note))
    rows.add_row(
        "Showing",
        Text(f"{report.selected}/{report.available} unresolved nodes ({report.omitted} omitted)"),
    )
    rows.add_row("Order", Text("node ID"))
    if report.sanitized_identities:
        rows.add_row("Identities sanitized", Text(str(report.sanitized_identities)))
    if not report.items:
        return Group(rows, _literal(counts.applicability_note))
    items = Table()
    items.add_column("Node", overflow="fold")
    items.add_column("Observed status")
    for item in report.items:
        items.add_row(Text(item.nodeid), _literal(", ".join(item.observations) or "unobserved"))
    return Group(rows, items, _literal(counts.applicability_note))


def _render_failures(report: Failures) -> Group:
    rows = Table.grid(padding=(0, 1))
    rows.add_column()
    rows.add_column(overflow="fold")
    rows.add_row("Result", _literal(report.result_id))
    rows.add_row("Outcome", _literal(report.outcome))
    rows.add_row("Evidence", _literal(report.availability))
    for lane, evidence in report.lanes.items():
        status = evidence.status
        if evidence.native_observation:
            status += f", native evidence: {evidence.native_observation}"
        if not evidence.reporting_complete:
            status += ", incomplete node reporting"
        rows.add_row(lane, _literal(status))
        if evidence.rust is not None:
            rows.add_row(
                "Rust", _literal(f"{evidence.rust.status} ({evidence.rust.applicability})")
            )
            if evidence.rust.reason:
                rows.add_row("Rust reason", _literal(evidence.rust.reason))
        for issue in evidence.reporting_errors:
            rows.add_row("Reporting", _literal(issue))
        if evidence.reporting_errors_omitted:
            rows.add_row("Reporting omitted", Text(str(evidence.reporting_errors_omitted)))
    rows.add_row(
        "Showing",
        Text(f"{report.selected}/{report.available} observed failures ({report.omitted} omitted)"),
    )
    rows.add_row("Order", Text("lane (ordinary, fault), then collection errors, node ID and phase"))
    if report.next_after is not None:
        rows.add_row("Continue", Text(f"--after {report.next_after}"))
    if report.sanitized_identities:
        rows.add_row("Identities sanitized", Text(str(report.sanitized_identities)))
    if report.next_action:
        rows.add_row("Next action", _literal(report.next_action))
    if not report.items:
        return Group(rows)
    items = Table()
    items.add_column("Lane / phase")
    items.add_column("Node", overflow="fold")
    items.add_column("Outcome")
    items.add_column("Diagnostic", overflow="fold")
    for item in report.items:
        excerpt = item.diagnostic or ""
        if item.diagnostic_truncated:
            excerpt += "…" if excerpt else "(diagnostic exceeds the bound)"
        items.add_row(
            Text(f"{item.lane} / {item.phase}"),
            Text(item.nodeid or "(session)"),
            Text(f"{item.outcome} ({item.reason.replace('_', ' ')})"),
            Text(excerpt),
        )
    details: list[Text | Table] = []
    for item in report.items:
        native = item.native_traceback
        if native is None:
            continue
        details.append(
            Text(
                f"Native pytest locations · {item.lane}/{item.phase} · "
                f"{item.nodeid} · {native.availability}"
            )
        )
        details.append(
            Text(
                "Recorded structural paths; chain descriptions are native text, "
                "not inferred relationships."
            )
        )
        locations = Table.grid(padding=(0, 1))
        locations.add_column(no_wrap=True)
        locations.add_column(overflow="fold")
        for location in native.locations:
            locations.add_row(Text("Native path"), Text(location.native_path))
            locations.add_row(
                Text("File / line"),
                Text(
                    f"{location.path or '(path unavailable)'}:"
                    f"{location.lineno if location.lineno is not None else '?'}"
                ),
            )
            locations.add_row(Text("Message"), Text(location.message or ""))
        details.append(locations)
        for chain in native.chains:
            if chain.description is not None:
                details.append(Text(f"{chain.native_path}[2]: {chain.description}"))
        for omission in native.omissions:
            details.append(Text(f"Omitted {omission.native_path}: {omission.reason}"))
        if native.omissions_omitted:
            details.append(Text(f"Additional omission records: {native.omissions_omitted}"))
    return Group(rows, items, *details)


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
    if "receipt_states" in report:
        report["receipt_states"] = {
            str(sources.get(directory, directory)): state
            for directory, state in report["receipt_states"].items()
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
    workers: int | None = None,
) -> str:
    name = "test-all" if lane == "ordinary" else "test-native-faults"
    directory = result.directory / lane
    result.stage(lane)
    diagnostic(f"Test lane {lane}: running")
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "CORPUS_CI_RECEIPT_DIR",
            "CORPUS_CI_SELECTION_FILE",
            "CORPUS_CI_PYTHON_ONLY",
            "CORPUS_CI_TEST_WORKERS",
        }
    }
    env["CORPUS_CI_RECEIPT_DIR"] = str(directory)
    if lane == "ordinary" and workers is not None:
        env["CORPUS_CI_TEST_WORKERS"] = str(workers)
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
    counts = classified["counts"]
    result.manifest.scope.setdefault("workers", {})[lane] = classified.get("workers")
    result.manifest.details.setdefault("lane_counts", {})[lane] = counts
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
        outcome = "interrupted"
    elif status == "not_run" and classified["empty"]:
        outcome = "empty"
    elif status == "passed" and process.returncode == 0:
        outcome = "passed"
    else:
        outcome = "blocked" if status == "blocked" else "failed"
    observed = ", ".join(
        f"{counts[key]} {key}" for key in ("selected", "passed", "failed") if key in counts
    )
    diagnostic(f"Test lane {lane}: {outcome}" + (f" ({observed})" if observed else ""))
    return outcome


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
    exit_code = 130 if outcome == "interrupted" else int(outcome != "passed")
    emit(
        Campaign(id=result.id, outcome=outcome, lanes=outcomes, next_action=next_action),
        json=json,
        exit_code=exit_code,
    )
    if exit_code:
        raise typer.Exit(exit_code)


@app.callback()
def run_tests(
    ctx: typer.Context,
    lane: Annotated[Lane | None, typer.Option()] = None,
    workers: Workers = None,
    json: JsonOpt = False,
) -> None:
    """Run applicable test lanes, or select one with --lane."""
    if ctx.invoked_subcommand is not None:
        if state(ctx).test_args or lane is not None or workers is not None or json:
            raise typer.BadParameter("place command options on the selected test subcommand")
        return
    args = state(ctx).test_args
    with result_boundary(json):
        if lane == "fault" and workers is not None:
            raise ResultError("--workers applies only to the ordinary lane")
        narrowed = _validate(args)
        if narrowed and lane == "fault":
            raise ResultError("the exclusive fault lane owns its selection")
        declared = lane or ("ordinary" if narrowed else "all")
        required_lanes = ["ordinary", "fault"] if declared == "all" else [declared]
        with result_store(ctx).operation(
            "test",
            scope={
                "lane": declared,
                "required_lanes": required_lanes,
                "narrowed": narrowed,
                "workers": {
                    name: {
                        "requested": workers if name == "ordinary" else 0,
                        "actual": None,
                    }
                    for name in required_lanes
                },
            },
            observations=True,
        ) as result:
            outcomes: dict[str, str] = {}
            if lane != "fault":
                outcomes["ordinary"] = _lane(
                    result, "ordinary", args, narrowed=narrowed, workers=workers
                )
            if (
                not narrowed
                and lane != "ordinary"
                and outcomes.get("ordinary") != "interrupted"
                and not result.manifest.details.get("custody_unsettled")
            ):
                outcomes["fault"] = _lane(result, "fault", args)
            _finish(result, outcomes, json)


def _receipts(
    store: ResultStore,
    result: Manifest,
    stack: ExitStack,
    *,
    allow_active: bool = False,
    lane: Lane | None = None,
) -> dict[str, tuple[Path, int]]:
    if result.action not in {"test", "test.retry"} or (result.settled is None and not allow_active):
        raise ResultError("a settled test result is required")
    if result.settled is None or result.details.get("custody_unsettled"):
        return {}
    return {
        role: stack.enter_context(store.open_artifact(result.id, role))
        for role in result.artifacts
        if role in _LANES and (lane is None or role == lane)
    }


def _required_lanes(manifest: Manifest) -> set[str]:
    declared = manifest.scope.get("lane")
    return set(
        manifest.scope.get("required_lanes")
        or (
            ["ordinary", "fault"]
            if declared == "all"
            else [declared]
            if declared
            else [role for role in manifest.artifacts if role in _LANES]
        )
    )


def _next_test_action(
    manifest: Manifest,
    lane_states: dict[Lane, str],
    retry_lanes: set[Lane],
    *,
    receipt_unsettled: bool,
) -> str | None:
    result_id = manifest.id
    if manifest.settled is None:
        return f"ci results watch {result_id}"
    if manifest.details.get("custody_unsettled") and manifest.stage in _LANES:
        return f"ci results recover {result_id}"
    if receipt_unsettled or manifest.details.get("custody_unsettled"):
        return f"Inspect supervisor settlement with ci results show {result_id} before retrying."
    for lane in _LANES:
        if lane in retry_lanes:
            return f"ci test retry {result_id} --lane {lane}"
    for lane in _LANES:
        if lane_states.get(lane) in {"failed", "blocked", "incomplete", "interrupted"}:
            return f"ci test --lane {lane}"
    return None


def _manifest_paths(receipts: list[Path]) -> list[str]:
    return [token for lane in receipts for token in ("--required-from", str(lane))]


@app.command("coverage")
def coverage(
    ctx: typer.Context,
    results: Annotated[list[str], typer.Argument(min=1)],
    json: JsonOpt = False,
    view: Annotated[Literal["unresolved"] | None, typer.Option()] = None,
    limit: Annotated[int | None, typer.Option(min=1, max=100)] = None,
) -> None:
    """Compare attempts against the first result's required selection."""
    if limit is not None and view is None:
        raise typer.BadParameter("--limit requires --view unresolved", param_hint="--limit")
    full = json and view is None
    with result_boundary(json), ExitStack() as leases:
        store = result_store(ctx)
        for result in dict.fromkeys(results):
            leases.enter_context(store.lease(result))
        manifests = [store.show(result) for result in results]
        scopes = [
            _receipts(store, manifest, leases, allow_active=not full) for manifest in manifests
        ]
        opened = dict(item for scope in scopes for item in scope.values())
        args = [
            token
            for scope in scopes
            for path, _ in scope.values()
            for token in ("--receipt-dir", str(path))
        ]
        initial = manifests[0]
        required = _required_lanes(initial)
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
        outcomes = {manifest.id: manifest.outcome for manifest in manifests}
        if not full:
            size = limit or _DEFAULT_LIMIT
            summary = (
                _supervisor(
                    "classify",
                    "--projection",
                    view or "coverage",
                    "--limit",
                    str(size),
                    *args,
                    *selectors,
                    opened=opened,
                )
                if args
                else {
                    "status": "incomplete",
                    "node_coverage": {
                        "status": "unavailable",
                        "required": 0,
                        "covered": 0,
                        "unresolved": 0,
                        "applicability_note": "No authenticated receipts are available.",
                    },
                    "source_contexts_differ": False,
                    "context_differences": [],
                    "context_unknowns": ["source", "python"],
                    "missing_lanes": sorted(required),
                    "selected_lanes": [],
                    "receipt_states": {},
                    "native_observations": {},
                }
            )
            missing = summary["missing_lanes"]
            counts = CoverageCounts.model_validate(summary["node_coverage"])
            if missing and args:
                counts.status = "unresolved"
            active = [item.id for item in manifests if item.settled is None]
            unsettled = []
            actions = {}
            for manifest, receipts in zip(manifests, scopes, strict=True):
                states = {
                    lane: summary["receipt_states"][str(receipts[lane][0])]
                    for lane in _LANES
                    if lane in receipts
                }
                receipt_unsettled = any(item["custody_unsettled"] for item in states.values())
                if receipt_unsettled or manifest.details.get("custody_unsettled"):
                    unsettled.append(manifest.id)
                action = _next_test_action(
                    manifest,
                    {
                        lane: manifest.details.get("lanes", {}).get(lane, "incomplete")
                        for lane in _LANES
                        if manifest.id == initial.id and lane in missing
                    },
                    {lane for lane, item in states.items() if item["retryable"]},
                    receipt_unsettled=receipt_unsettled,
                )
                if action:
                    actions[manifest.id] = action
            report = CoverageSummary(
                results=results,
                status=("incomplete" if missing or active or unsettled else summary["status"]),
                node_coverage=counts,
                sources_differ=summary["source_contexts_differ"],
                context_differences=summary["context_differences"],
                context_unknowns=summary["context_unknowns"],
                missing_lanes=missing,
                selected_lanes=summary["selected_lanes"],
                attempt_outcomes=outcomes,
                active_attempts=active,
                unsettled_attempts=unsettled,
                next_actions=actions,
                native_observations=summary["native_observations"],
            )
            if view == "unresolved":
                items = [UnresolvedNode.model_validate(item) for item in summary.get("items", [])]
                report = UnresolvedCoverage(
                    **report.model_dump(),
                    limit=size,
                    selected=len(items),
                    available=counts.unresolved,
                    omitted=counts.unresolved - len(items),
                    sanitized_identities=_sanitize_nodes(items),
                    items=items,
                )
            emit(report, json=json, render=lambda _: _render_coverage(report))
            return
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
                attempt_outcomes=outcomes,
                contexts=summary["contexts"],
            ),
            json=json,
        )


@app.command("failures")
def failures(
    ctx: typer.Context,
    result_id: Annotated[str, typer.Argument(metavar="RESULT_ID")],
    lane: Annotated[Lane | None, typer.Option()] = None,
    phase: Annotated[Phase | None, typer.Option()] = None,
    limit: ReportLimit = _DEFAULT_LIMIT,
    after: Annotated[
        int, typer.Option(min=0, help="Continue after this many filtered observations.")
    ] = 0,
    diagnostic_chars: Annotated[
        int,
        typer.Option(
            min=1,
            max=32768,
            help=(
                "Maximum characters per redacted diagnostic and total native "
                "location/description string budget."
            ),
        ),
    ] = 600,
    native_traceback: Annotated[
        bool,
        typer.Option(
            "--native-traceback",
            help=(
                "Include retained pytest locations and native chain descriptions; "
                "no source listings, locals or captured streams."
            ),
        ),
    ] = False,
    json: JsonOpt = False,
) -> None:
    """Read exact failed pytest observations from a retained attempt."""
    with result_boundary(json), ExitStack() as leases:
        store = result_store(ctx)
        leases.enter_context(store.lease(result_id))
        manifest = store.show(result_id, role=lane)
        receipts = _receipts(store, manifest, leases, allow_active=True, lane=lane)
        selected_lanes = _required_lanes(manifest) | manifest.artifacts.keys()
        if manifest.stage in {"ordinary", "fault"}:
            selected_lanes.add(manifest.stage)
        lanes: dict[Lane, FailureLane] = {}
        items: list[FailureEvent] = []
        available = 0
        receipt_count = 0
        retry_lanes: set[Lane] = set()
        receipt_unsettled = False
        remaining_after = after
        for name in _LANES:
            if (lane is not None and name != lane) or (lane is None and name not in selected_lanes):
                continue
            if name not in receipts:
                outcomes = manifest.details.get("lanes", {})
                status = outcomes.get(name, "unavailable")
                if name not in selected_lanes:
                    status = "not_selected"
                elif manifest.settled is None and name == manifest.stage:
                    status = "running"
                lanes[name] = FailureLane(status=status, reporting_complete=False)
                continue
            path, fd = receipts[name]
            selection = ["--phase", phase] if phase is not None else []
            if native_traceback:
                selection.append("--native-traceback")
            report = _supervisor(
                "classify",
                "--projection",
                "failures",
                "--receipt-dir",
                str(path),
                "--limit",
                str(limit - len(items)),
                "--after",
                str(remaining_after),
                *selection,
                opened={path: fd},
            )
            receipt_count += 1
            receipt_unsettled |= report["custody_unsettled"]
            rust = RustEvidence.model_validate(report["rust"][0]) if report["rust"] else None
            if rust is not None and rust.reason is not None:
                reason = _display_text(rust.reason)
                rust.reason_truncated = len(reason) > diagnostic_chars
                rust.reason = reason[:diagnostic_chars]
            lanes[name] = FailureLane(
                status=report["status"],
                reporting_complete=report["reporting_complete"] and not report["custody_unsettled"],
                native_observation=report["native_observation"],
                rust=rust,
                reporting_errors=[
                    _display_text(message)[:diagnostic_chars]
                    for message in report["reporting_errors"]
                ],
                reporting_errors_omitted=report["reporting_errors_omitted"],
                reporting_errors_truncated=any(
                    len(_display_text(message)) > diagnostic_chars
                    for message in report["reporting_errors"]
                ),
            )
            if not report["custody_unsettled"]:
                available += report["available"]
                remaining_after = max(0, remaining_after - report["available"])
                for raw in report["items"]:
                    item = FailureEvent(lane=name, **raw)
                    if item.native_traceback is not None:
                        item.native_traceback = _present_native_traceback(
                            item.native_traceback, diagnostic_chars
                        )
                    if item.diagnostic is not None:
                        excerpt = _display_text(item.diagnostic)
                        item.diagnostic_truncated = len(excerpt) > diagnostic_chars
                        if (
                            item.diagnostic_truncated
                            and "\n" in item.diagnostic
                            and diagnostic_chars >= 5
                        ):
                            head = min(220, (diagnostic_chars - 3) // 2)
                            tail = diagnostic_chars - head - 3
                            item.diagnostic = excerpt[:head] + " … " + excerpt[-tail:]
                        else:
                            item.diagnostic = excerpt[:diagnostic_chars]
                    items.append(item)
                if report["retryable"]:
                    retry_lanes.add(name)
        next_action = _next_test_action(
            manifest,
            {name: evidence.status for name, evidence in lanes.items()},
            retry_lanes,
            receipt_unsettled=receipt_unsettled,
        )
        if lanes and all(item.reporting_complete for item in lanes.values()):
            availability = "available"
        elif receipt_count or manifest.settled is None:
            availability = "partial"
        else:
            availability = "unavailable"
        view = Failures(
            result_id=result_id,
            outcome=manifest.outcome,
            availability=availability,
            lane=lane,
            phase=phase,
            lanes=lanes,
            limit=limit,
            after=after,
            next_after=after + len(items) if after + len(items) < available else None,
            selected=len(items),
            available=available,
            omitted=available - len(items),
            sanitized_identities=_sanitize_nodes(items),
            items=items,
            next_action=next_action,
        )
        emit(view, json=json, render=lambda _: _render_failures(view))


@app.command("retry")
def retry(
    ctx: typer.Context,
    original: str,
    lane: Annotated[Lane | None, typer.Option()] = None,
    workers: Workers = None,
    json: JsonOpt = False,
) -> None:
    """Recollect and retry the unresolved identities from a retained receipt."""
    with result_boundary(json):
        if lane == "fault" and workers is not None:
            raise ResultError("--workers applies only to the ordinary lane")
        store = result_store(ctx)
        with store.lease(original), ExitStack() as receipts_open:
            manifest = store.show(original, role=lane)
            if manifest.details.get("custody_unsettled"):
                raise ResultError(f"settle the predecessor with ci results recover {original}")
            receipts = _receipts(store, manifest, receipts_open, lane=lane)
            if workers is not None and "ordinary" not in receipts:
                raise ResultError("--workers requires an ordinary retry lane")
            with store.operation(
                "test.retry",
                observations=True,
                scope={
                    "retry_of": original,
                    "required_lanes": [],
                    "workers": {},
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
                    if report["custody_unsettled"]:
                        raise ResultError(
                            "supervisor settlement unproven. "
                            f"Inspect with ci results show {original}"
                        )
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
                        result.manifest.scope["workers"][current] = {
                            "requested": workers if current == "ordinary" else 0,
                            "actual": None,
                        }
                        outcomes[current] = _lane(
                            result, current, selection=selection, workers=workers
                        )
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
