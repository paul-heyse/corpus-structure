"""Resolve characterization capacity and complete method settings at CLI boundaries."""

import json
from dataclasses import asdict
from pathlib import Path

import typer
from pydantic import TypeAdapter

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.method import MethodSettings


def method_settings(settings, policy_file: Path | None = None) -> MethodSettings:
    policy = settings.characterization_execution
    if policy_file is not None:
        try:
            overrides = json.loads(policy_file.read_bytes())
            if not isinstance(overrides, dict):
                raise ValueError("execution policy must be an object")
            policy = TypeAdapter(CharacterizationExecutionPolicy).validate_python(
                {**asdict(policy), **overrides}
            )
        except (OSError, ValueError) as error:
            raise typer.BadParameter(str(error), param_hint="--execution-policy") from error
    return MethodSettings(
        data_dir=settings.paths.data_dir,
        model_cache=settings.paths.model_cache,
        nemotron_endpoint=settings.nemotron.endpoint,
        nemotron_python=settings.nemotron.python,
        nemotron_worker=settings.nemotron.worker,
        nemotron_receipts=settings.nemotron.receipts,
        nemotron_timeout_seconds=settings.nemotron.timeout_seconds,
        execution_policy=policy,
    )
