"""Acquire explicitly named target inputs without importing their Python modules.

The manifest is an acquisition recipe. Only captured semantic/source bytes enter
the effective model; checkout paths do not become operation identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .composed import data_operation_dependencies
from .python_operation_sources import PythonSource, PythonSourceCollection
from .types import PreparationProfile, ResolvedDependencies, SourceArtifact, SourceBundle


class NamedInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)


class PythonInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    module: str = Field(min_length=1)
    path: str = Field(min_length=1)
    stub: str | None = None


class PythonInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sources: tuple[PythonInput, ...]
    interpreter: str
    interpretation: str
    stub_policy: str
    boundary_contracts: tuple[NamedInput, ...] = ()
    generated_interfaces: tuple[Literal["dataclasses", "unpack-typeddict"], ...] = ()


class DataOperationInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["data-operation-inputs-v1"]
    root: str = Field(min_length=1)
    schemas: tuple[NamedInput, ...]
    declarations: tuple[NamedInput, ...] = ()
    dependencies: tuple[NamedInput, ...] = ()
    python: PythonInputs | None = None
    consumer_bindings: bool = False


@dataclass(frozen=True)
class AcquiredDataOperationInputs:
    bundle: SourceBundle
    dependencies: ResolvedDependencies
    profile: PreparationProfile
    files: tuple[tuple[str, bytes], ...]


def acquire_data_operation_inputs(root: Path, manifest: str) -> AcquiredDataOperationInputs:
    """Read one closed workspace-relative recipe, retaining its complete file closure."""
    root = root.resolve()
    captured: dict[str, bytes] = {}

    def read(name: str) -> bytes:
        path = root / name
        if not name or Path(name).is_absolute():
            raise ValueError("data-operation input paths must be workspace-relative")
        if not path.is_relative_to(root) or path.resolve() != path or not path.is_file():
            raise ValueError(f"unsafe or unavailable data-operation input: {name}")
        content = path.read_bytes()
        previous = captured.setdefault(name, content)
        if previous != content:
            raise ValueError(f"data-operation input changed during acquisition: {name}")
        return content

    declared = DataOperationInputs.model_validate(yaml.safe_load(read(manifest)))

    def artifacts(items: tuple[NamedInput, ...]) -> tuple[SourceArtifact, ...]:
        if len({item.name for item in items}) != len(items):
            raise ValueError("duplicate named data-operation input")
        return tuple(SourceArtifact(item.name, read(item.path)) for item in items)

    bundle = SourceBundle(declared.root, artifacts(declared.schemas))
    if declared.root not in {item.name for item in bundle.sources}:
        raise ValueError("data-operation root is absent from the supplied schemas")
    if declared.consumer_bindings:
        reserved = {"data_operation_consumers", "data_operation_consumer_target"}
        if reserved & {source.name for source in bundle.sources}:
            raise ValueError("consumer binding schemas use reserved trusted names")
        consumer_schema = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-consumers.yaml"
        wrapper = yaml.safe_dump({
            "id": "urn:corpus:data-operation-consumer-target",
            "name": "data_operation_consumer_target",
            "imports": [bundle.root, "data_operation_consumers"],
        }).encode()
        bundle = SourceBundle("data_operation_consumer_target", (
            *bundle.sources,
            SourceArtifact("data_operation_consumers", consumer_schema.read_bytes()),
            SourceArtifact("data_operation_consumer_target", wrapper),
        ))
    python = declared.python
    sources = (
        None
        if python is None
        else PythonSourceCollection(
            tuple(
                PythonSource(
                    item.module, read(item.path), item.path, read(item.stub) if item.stub else None
                )
                for item in python.sources
            ),
            python.interpreter,
            python.interpretation,
            python.stub_policy,
            artifacts(python.boundary_contracts),
            python.generated_interfaces,
        )
    )
    from .data_operation_artifacts import capture_port_generator_sources
    from .data_operation_storage import native_operation_declarations, native_protocol_sources

    from .data_operation_consumers import consumer_selection_declarations

    consumer_declarations = (
        consumer_selection_declarations(sources.sources)
        if declared.consumer_bindings and sources is not None
        else ()
    )
    native = native_protocol_sources()
    generator = capture_port_generator_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*artifacts(declared.dependencies), *native, *generator)),
        (*artifacts(declared.declarations), *consumer_declarations, native_operation_declarations(native)),
        sources,
    )
    return AcquiredDataOperationInputs(
        bundle,
        dependencies,
        PreparationProfile(version="semantic-2"),
        tuple(sorted(captured.items())),
    )


def prepare_data_operation_inputs(root: Path, manifest: str):
    from .prepare import prepare_release

    acquired = acquire_data_operation_inputs(root, manifest)
    return (
        acquired.bundle,
        acquired.dependencies,
        acquired.profile,
        prepare_release(acquired.bundle, acquired.dependencies, acquired.profile),
    )
