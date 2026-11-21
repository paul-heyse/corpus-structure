"""Resolve explicit and retained execution policy at the CLI boundary."""

from dataclasses import asdict
from pathlib import Path

import typer
from pydantic import ValidationError

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.source_request import method_settings
from corpus_structure.semantic.data_operation_json import finite_json_loads
from corpus_structure.settings import Settings


def read_execution_policy(path: Path) -> dict:
    """Read the flat, explicit override file before the shared policy validates it."""
    overrides = finite_json_loads(path.read_bytes())
    if not isinstance(overrides, dict):
        raise ValueError("execution policy must be an object")
    return overrides


def execution_methods(
    settings: Settings,
    policy_file: Path | None = None,
    *,
    inherited: CharacterizationExecutionPolicy | None = None,
) -> tuple[MethodSettings, tuple[str, ...]]:
    """Validate the final policy once and identify the explicit override fields."""
    try:
        explicit = read_execution_policy(policy_file) if policy_file is not None else {}
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="--execution-policy") from error
    overrides = asdict(inherited) if inherited is not None else {}
    overrides.update(explicit)
    try:
        return method_settings(settings, overrides or None), tuple(sorted(explicit))
    except ValidationError as error:
        first = error.errors(include_url=False, include_context=False, include_input=False)[0]
        field = ".".join(map(str, first["loc"])) or "policy"
        raise typer.BadParameter(
            f"{field}: {first['type']}", param_hint="--execution-policy"
        ) from error
