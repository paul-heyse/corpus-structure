"""Resolve the configured target once for a CLI read or effect."""

from typing import Literal

import typer
from pydantic import BaseModel

from corpus_structure.cli.managed import ResultError
from corpus_structure.cli.output import state
from corpus_structure.settings import DeploymentProfile, Settings


def select_target(
    ctx: typer.Context, target: DeploymentProfile | None = None, *, effect: bool = False
) -> tuple[DeploymentProfile, Settings]:
    from corpus_structure.schema.model_deployment import deployment_settings

    settings = state(ctx).settings()
    if effect and target is None and settings.deployment is not None:
        raise ResultError("select --target development or --target deployment for this effect")
    selected = target or "development"
    if selected == "deployment" and settings.deployment is None:
        raise ResultError("configure CORPUS_DEPLOYMENT__URL for the deployment target")
    selected, configured = deployment_settings(settings, selected)
    if selected == "deployment":
        from corpus_structure.semantic.storage_target import assert_explicit_route

        assert_explicit_route(configured)
    return selected, configured


class ConfiguredSelection(BaseModel):
    """Configuration evidence only; resource identity belongs to acquired StorageTarget."""

    profile: DeploymentProfile
    target_parameter_source: str
    standing: Literal["configured_unobserved", "configuration_unavailable"] = (
        "configured_unobserved"
    )
    reason: str | None = None
    settings_section: Literal["database", "deployment"]
    resources: dict[str, str]
    origins: dict[str, str]
    observed_binding: None = None


def configured_selection(
    ctx: typer.Context,
    settings: Settings,
    profile: DeploymentProfile,
    *,
    report=None,
    allow_unavailable: bool = False,
) -> ConfiguredSelection:
    """Project the original snapshot's canonical fields and contribution origins."""
    from corpus_structure.cli.output import cli_settings_report

    if profile == "deployment" and settings.deployment is None:
        if not allow_unavailable:
            raise ResultError("configure CORPUS_DEPLOYMENT__URL for the deployment target")
        source = ctx.get_parameter_source("target")
        return ConfiguredSelection(
            profile=profile,
            target_parameter_source=source.name.lower() if source else "unknown",
            standing="configuration_unavailable",
            reason="current deployment profile is not configured",
            settings_section="deployment",
            resources={},
            origins={},
        )
    explanation = report if report is not None else cli_settings_report(settings)
    section = "deployment" if profile == "deployment" else "database"
    resources = {
        name: value
        for name, value in explanation.resolved.items()
        if name.startswith(section + ".")
    }
    source = ctx.get_parameter_source("target")
    return ConfiguredSelection(
        profile=profile,
        target_parameter_source=source.name.lower() if source is not None else "unknown",
        settings_section=section,
        resources=resources,
        origins={name: explanation.origins.get(name, "unknown") for name in resources},
    )


def current_selection(
    ctx: typer.Context, profile: DeploymentProfile | None
) -> ConfiguredSelection | None:
    """Explain present configuration beside archived identity without acquiring the target."""
    return (
        configured_selection(ctx, state(ctx).settings(), profile, allow_unavailable=True)
        if profile is not None
        else None
    )


def selection_summary(selection: ConfiguredSelection | None) -> str:
    if selection is None:
        return "unbound; no profile selected"
    if selection.standing == "configuration_unavailable":
        return selection.reason or "current configuration unavailable"
    endpoint = selection.resources.get(selection.settings_section + ".url", "endpoint unavailable")
    return f"{selection.profile} · configured, unobserved · {endpoint}"
