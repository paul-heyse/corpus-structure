"""Resolve the configured target once for a CLI read or effect."""

import typer

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
