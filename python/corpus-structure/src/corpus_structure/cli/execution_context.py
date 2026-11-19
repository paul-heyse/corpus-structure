"""Captured execution selections and physical policy for exact managed recovery."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import typer
from pydantic import BaseModel, ConfigDict, Field, model_validator
from rich.table import Table

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.orchestrate.source_request import SourceRunRequest
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_service import NativeDemandRequest
from corpus_structure.semantic.storage_target import StorageTarget
from corpus_structure.settings import AnalyticsSettings

from .target import ConfiguredSelection, configured_selection


class ExecutionRecoveryAccount(BaseModel):
    """One immutable pre-execution account; acquired facts stay with native custody."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    observed_at: str
    action: str
    demand_id: str | None = None
    native_request: NativeDemandRequest | None = None
    source_request: SourceRunRequest | None = None
    project: str | None = None
    source_root: Path | None = None
    execution_policy: CharacterizationExecutionPolicy
    policy_origins: dict[str, str]
    analytics_settings: AnalyticsSettings
    configured_target: ConfiguredSelection
    required_targets: tuple[str, ...] | None = None
    predecessor_result: str | None = None
    overrides: tuple[str, ...] = ()
    limit: int = Field(default=100, ge=1, le=1000)
    max_rounds: int = Field(default=100, ge=1)

    def payload(self):
        # Semantic selections retain exact JSON numbers. Physical paths have their
        # ordinary JSON representation, independent of those semantic values.
        value = self.model_dump(mode="python")
        value["source_root"] = str(self.source_root) if self.source_root is not None else None
        value["analytics_settings"] = self.analytics_settings.model_dump(mode="json")
        return value

    @model_validator(mode="after")
    def one_selection(self):
        if (
            sum(
                value is not None
                for value in (self.demand_id, self.native_request, self.source_request)
            )
            != 1
        ):
            raise ValueError("execution context requires one exact demand or typed request")
        return self


class ExecutionPreview(BaseModel):
    version: Literal[1] = 1
    context: ExecutionRecoveryAccount
    standing: Literal["passive"] = "passive"
    native_availability: Literal["unobserved"] = "unobserved"
    prerequisites: tuple[str, ...] = (
        "Acquire the configured target and verify its purpose and identity.",
        "Verify the admitted release, runtime and captured executable sources.",
        "Native registration and binding determine remaining work and reuse.",
    )
    effects: tuple[str, ...] = ()


def execution_methods(settings, policy_file: Path | None = None, *, inherited=None):
    """Resolve once so captured values and executed bounds are the same object."""
    import json

    from corpus_structure.orchestrate.source_request import method_settings

    try:
        explicit = {} if policy_file is None else json.loads(policy_file.read_bytes())
        if not isinstance(explicit, dict):
            raise ValueError("execution policy must be an object")
        overrides = {} if inherited is None else asdict(inherited.execution_policy)
        overrides.update(explicit)
        return method_settings(settings, overrides), tuple(sorted(explicit))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="--execution-policy") from error


def capture_execution_context(
    ctx: typer.Context,
    *,
    settings,
    methods,
    action: str,
    source_root: Path | None,
    demand=None,
    request=None,
    source_request=None,
    project=None,
    policy_overrides: tuple[str, ...] = (),
    required_targets=None,
    predecessor=None,
    inherited: ExecutionRecoveryAccount | None = None,
    limit=100,
    max_rounds=100,
):
    from corpus_structure.cli.output import cli_settings_report

    explained = cli_settings_report(settings)
    policy = asdict(methods.execution_policy)
    origins = {
        name: explained.origins.get("characterization_execution." + name, "settings")
        for name in policy
    }
    if inherited is not None:
        origins = {name: "managed result " + str(predecessor) for name in policy}
    origins.update({name: "explicit execution policy" for name in policy_overrides})
    return ExecutionRecoveryAccount(
        observed_at=datetime.now(UTC).isoformat(),
        action=action,
        demand_id=demand,
        native_request=request,
        source_request=source_request,
        project=project,
        source_root=source_root.resolve() if source_root is not None else None,
        execution_policy=methods.execution_policy,
        policy_origins=origins,
        analytics_settings=inherited.analytics_settings
        if inherited is not None
        else settings.analytics,
        configured_target=configured_selection(ctx, settings, "development"),
        required_targets=required_targets,
        predecessor_result=predecessor,
        overrides=policy_overrides,
        limit=limit,
        max_rounds=max_rounds,
    )


def retain_execution_context(invocation, account: ExecutionRecoveryAccount):
    path = invocation.directory / "execution-context.json"
    path.write_bytes(json_bytes(account.payload()) + b"\n")
    invocation.publish("execution_context", path)
    invocation.stage("execution_context_captured", predecessor_result=account.predecessor_result)


def read_execution_context(store, result: str) -> ExecutionRecoveryAccount:
    from .managed import ResultError

    with store.lease(result):
        manifest = store.show(result, role="execution_context")
        if "execution_context" not in manifest.artifacts:
            raise ResultError(
                "managed result has no captured execution context; supply an exact native demand "
                "and its explicit source root and execution policy"
            )
        return ExecutionRecoveryAccount.model_validate(
            json_loads(store.read_artifact(result, "execution_context"))
        )


def configured_route(selection: ConfiguredSelection):
    """Endpoint components, independent of credentials and current connection pools."""
    from sqlalchemy.engine import make_url

    name = selection.settings_section + ".url"
    raw = selection.resources.get(name)
    if raw is None:
        return None
    value = make_url(raw)
    return (
        value.database,
        value.host,
        value.port,
        tuple((name, value.query.get(name)) for name in ("host", "hostaddr", "port")),
    )


def recovery_target(manifest) -> StorageTarget | None:
    target = manifest.details.get("observation_target")
    if target is None and manifest.operation_account is not None:
        return manifest.operation_account.acquired_target
    return StorageTarget.model_validate(target) if target is not None else None


def render_preview(report: ExecutionPreview):
    table = Table("Execution selection", "Captured value")
    account = report.context
    table.add_row("standing", report.standing)
    table.add_row("demand", account.demand_id or "registration pending")
    table.add_row(
        "project",
        account.project
        or getattr(account.source_request or account.native_request, "project_id", None)
        or "native selection",
    )
    table.add_row("source root", str(account.source_root))
    table.add_row("target", account.configured_target.profile + " · configured, unobserved")
    for name, value in asdict(account.execution_policy).items():
        table.add_row(name, str(value) + " · " + account.policy_origins[name])
    for prerequisite in report.prerequisites:
        table.add_row("prerequisite", prerequisite)
    return table


def emit_preview(report: ExecutionPreview, *, json: bool):
    from .output import emit, write_report_text

    if json:
        value = report.model_dump(mode="python")
        value["context"] = report.context.payload()
        write_report_text(json_bytes(value).decode() + "\n")
    else:
        emit(report, json=False, render=render_preview)
