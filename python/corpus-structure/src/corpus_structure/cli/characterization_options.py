"""Read policy-file transport; shared application settings own its interpretation."""

from pathlib import Path

import typer

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.source_request import method_settings as build_method_settings
from corpus_structure.semantic.data_operation_json import finite_json_loads


def read_execution_policy(path: Path) -> dict:
    """Read the flat, explicit override file before the shared policy validates it."""
    overrides = finite_json_loads(path.read_bytes())
    if not isinstance(overrides, dict):
        raise ValueError("execution policy must be an object")
    return overrides


def method_settings(settings, policy_file: Path | None = None) -> MethodSettings:
    try:
        overrides = read_execution_policy(policy_file) if policy_file is not None else None
        return build_method_settings(settings, overrides)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="--execution-policy") from error
