"""Read policy-file transport; shared application settings own its interpretation."""

import json
from pathlib import Path

import typer

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.source_request import method_settings as build_method_settings


def method_settings(settings, policy_file: Path | None = None) -> MethodSettings:
    try:
        overrides = json.loads(policy_file.read_bytes()) if policy_file is not None else None
        if policy_file is not None and not isinstance(overrides, dict):
            raise ValueError("execution policy must be an object")
        return build_method_settings(settings, overrides)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="--execution-policy") from error
