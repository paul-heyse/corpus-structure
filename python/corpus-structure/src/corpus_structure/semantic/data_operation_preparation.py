"""Acquire explicitly named target inputs without importing their Python modules.

The manifest is an acquisition recipe. Only captured semantic/source bytes enter
the effective model; checkout paths do not become operation identity.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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
    generated_interfaces: tuple[
        Literal[
            "dataclasses", "unpack-typeddict", "dataclasses-runtime", "unpack-typeddict-runtime"
        ],
        ...,
    ] = ()


class PrimaryRecognitionInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    recipe: str = Field(min_length=1)
    options: str = Field(min_length=1)
    resources: str = Field(min_length=1)


class PrimaryCaptureInputs(BaseModel):
    """References to the existing frozen PDF recipe and prepared asset manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    recipe: str = Field(min_length=1)
    assets_manifest: str = Field(min_length=1)
    assets_root: str = Field(min_length=1)
    directory: str = Field(min_length=1)
    nemotron_endpoint: str | None = None
    require_nemotron_handoff: bool = False
    enrichment_options: str | None = None
    recognition: PrimaryRecognitionInputs | None = None


class LiteralM1Inputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    configuration: str = Field(min_length=1)
    schema_root: str = Field(min_length=1)
    schemas: tuple[NamedInput, ...] = Field(min_length=1)


class ContextualEncoderInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    profile: str = Field(min_length=1)
    model_path: str = Field(min_length=1)


class PrimaryProfileInputs(BaseModel):
    """File references, using each provider's existing configuration shape."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    sentence_configuration: str = Field(min_length=1)
    sentence_selection: str = Field(min_length=1)
    hanlp_selection: str = Field(min_length=1)
    learned_selections: dict[Literal["maverick", "dipo", "d1", "gliner"], str] | None = None
    construction: str | None = None
    math: str | None = None
    external_protocol: str | None = None
    downstream: bool = False
    m1: LiteralM1Inputs | None = None
    contextual_encoder: ContextualEncoderInputs | None = None
    capture: PrimaryCaptureInputs | None = None


class DataOperationInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["data-operation-inputs-v1"]
    root: str = Field(min_length=1)
    schemas: tuple[NamedInput, ...]
    declarations: tuple[NamedInput, ...] = ()
    dependencies: tuple[NamedInput, ...] = ()
    python: PythonInputs | None = None
    source_bindings: bool = False
    record_bindings: bool = False
    pdf_contracts: bool = False
    primary_profile: PrimaryProfileInputs | None = None


@dataclass(frozen=True)
class AcquiredDataOperationInputs:
    bundle: SourceBundle
    dependencies: ResolvedDependencies
    profile: PreparationProfile
    files: tuple[tuple[str, bytes], ...]


def acquire_data_operation_inputs(
    root: Path, manifest: str, *, proposed: dict[str, bytes] | None = None
) -> AcquiredDataOperationInputs:
    """Read one closed workspace-relative recipe, retaining its complete file closure."""
    root = root.resolve()
    captured: dict[str, bytes] = {}

    def read(name: str) -> bytes:
        path = root / name
        if not name or Path(name).is_absolute():
            raise ValueError("data-operation input paths must be workspace-relative")
        if not path.is_relative_to(root) or path.resolve() != path or not path.is_file():
            raise ValueError(f"unsafe or unavailable data-operation input: {name}")
        content = proposed[name] if proposed is not None and name in proposed else path.read_bytes()
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
    if declared.source_bindings:
        from .source_products import source_product_inputs

        bundle = source_product_inputs(bundle)
    if declared.record_bindings:
        if not declared.source_bindings:
            raise ValueError("declared record bindings require the selected native source contract")
        from .declared_record_sources import declared_record_inputs

        bundle = declared_record_inputs(bundle)
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

    if declared.primary_profile is not None:
        from .primary_operations import primary_operation_inputs

        primary = _acquire_primary_profile(declared.primary_profile, read, root)
        composed = primary_operation_inputs(
            bundle,
            **primary,
            dependencies=ResolvedDependencies(artifacts(declared.dependencies)),
            extra_sources=sources,
            declarations=artifacts(declared.declarations),
        )
        dependencies = composed.dependencies
        if declared.pdf_contracts and declared.primary_profile.capture is None:
            from .pdf_domain import pdf_domain_dependencies

            dependencies = pdf_domain_dependencies(dependencies)
        return AcquiredDataOperationInputs(
            composed.bundle, dependencies, composed.profile, tuple(sorted(captured.items()))
        )
    native = native_protocol_sources()
    generator = capture_port_generator_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*artifacts(declared.dependencies), *native, *generator)),
        (
            *artifacts(declared.declarations),
            native_operation_declarations(native),
        ),
        sources,
    )
    if declared.pdf_contracts:
        from .pdf_domain import pdf_domain_dependencies

        dependencies = pdf_domain_dependencies(dependencies)
    return AcquiredDataOperationInputs(
        bundle,
        dependencies,
        PreparationProfile(version="semantic-2"),
        tuple(sorted(captured.items())),
    )


def _acquire_primary_profile(
    profile: PrimaryProfileInputs, read: Callable[[str], bytes], root: Path
) -> dict[str, Any]:
    """Reconstitute explicit frozen selections; never acquire a default provider."""
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

    from .identity import canonical_bytes

    def location(name: str) -> Path:
        path = Path(name)
        return (path if path.is_absolute() else root / path).resolve()

    def selection(name: str, provider: str):
        value = json.loads(read(name))
        if not isinstance(value, dict) or set(value) != {"profile", "fingerprint", "assets"}:
            raise ValueError("native selection must use the complete NativeSelection declaration")
        native = NativeProfile.from_content(canonical_bytes(value["profile"]))
        if native.provider != provider or native.fingerprint != value["fingerprint"]:
            raise ValueError("native selection provider or captured fingerprint differs")
        assets = location(value["assets"])
        if not assets.is_dir():
            raise ValueError("explicit native selection assets are unavailable")
        return NativeSelection(native, assets)

    configuration = SentenceConfig.model_validate(
        yaml.safe_load(read(profile.sentence_configuration))
    )
    sentence = selection(profile.sentence_selection, "spacy")
    if sentence.native.parameters != configuration.model_dump(mode="json"):
        raise ValueError("sentence configuration differs from its frozen native selection")
    arguments: dict[str, Any] = dict(
        sentence_configuration=configuration,
        sentence_selection=sentence,
        hanlp_selection=selection(profile.hanlp_selection, "hanlp"),
        downstream=profile.downstream,
    )
    if profile.learned_selections is not None:
        if set(profile.learned_selections) != {"maverick", "dipo", "d1", "gliner"}:
            raise ValueError("learned primary profile requires all four explicit selections")
        arguments["learned_selections"] = {
            provider: selection(path, provider)
            for provider, path in profile.learned_selections.items()
        }
    if profile.construction is not None:
        from .construction_products import ConstructionOptions

        arguments["construction_options"] = ConstructionOptions.model_validate(
            yaml.safe_load(read(profile.construction))
        )
    if profile.math is not None:
        from .declared_math_products import DeclaredMathOptions

        arguments["math_options"] = DeclaredMathOptions.model_validate(
            yaml.safe_load(read(profile.math))
        )
    if profile.m1 is not None:
        from corpus_structure.methods.m1_source import M1Config

        selected_m1 = M1Config.model_validate(yaml.safe_load(read(profile.m1.configuration)))
        if selected_m1.native_execution_profile is None:
            raise ValueError(
                "literal M1 acquisition requires its captured native execution profile"
            )
        selected_m1 = selected_m1.model_copy(
            update={"snapshot": location(str(selected_m1.snapshot))}
        )
        if not selected_m1.snapshot.is_dir():
            raise ValueError("literal M1 model snapshot is unavailable")
        schemas = tuple(SourceArtifact(item.name, read(item.path)) for item in profile.m1.schemas)
        if len({item.name for item in schemas}) != len(schemas) or profile.m1.schema_root not in {
            item.name for item in schemas
        }:
            raise ValueError("literal M1 requires unique named schemas and its declared root")
        arguments.update(
            m1_configuration=selected_m1,
            record_schemas=SourceBundle(profile.m1.schema_root, schemas),
        )
    if profile.contextual_encoder is not None:
        from pydantic import TypeAdapter

        from corpus_structure.methods.contextual_embeddings import EncoderProfile

        from .contextual_encoder import ContextualEncoderSelection

        encoder_profile = TypeAdapter(EncoderProfile).validate_json(
            canonical_bytes(yaml.safe_load(read(profile.contextual_encoder.profile))), strict=True
        )
        arguments["contextual_encoder"] = ContextualEncoderSelection.acquire(
            encoder_profile, location(profile.contextual_encoder.model_path)
        )
    if profile.external_protocol is not None:
        from dataclasses import fields

        from pydantic import TypeAdapter

        from .data_operation_model import ExternalExecutorContract

        selected = yaml.safe_load(read(profile.external_protocol))
        if not isinstance(selected, dict) or set(selected) != {
            field.name for field in fields(ExternalExecutorContract)
        }:
            raise ValueError(
                "external protocol requires its exact declared actor, model, instructions and reference scope"
            )
        arguments["external_protocol"] = TypeAdapter(ExternalExecutorContract).validate_json(
            canonical_bytes(selected), strict=True
        )
    if profile.capture is not None:
        from corpus_structure.ingest.pdf import PdfRecipe
        from corpus_structure.ingest.pdf_assets import PreparedPdfAssets

        from .pdf_capture import pdf_capture_operation_sources

        capture = profile.capture
        recipe = PdfRecipe.from_bytes(read(capture.recipe))
        manifest = read(capture.assets_manifest)
        value = json.loads(manifest)
        if (
            not isinstance(value, dict)
            or set(value) != {"recipe", "repositories", "files"}
            or value["recipe"] != "pdf-model-assets-v1"
        ):
            raise ValueError("PDF assets require the existing prepared model manifest")
        assets = PreparedPdfAssets(
            location(capture.assets_root),
            manifest,
            tuple((name, digest) for name, digest in value["files"]),
            tuple((name, revision) for name, revision in value["repositories"]),
        )
        if any(
            not name or Path(name).is_absolute() or ".." in Path(name).parts
            for name, _digest in assets.files
        ) or len({name for name, _digest in assets.files}) != len(assets.files):
            raise ValueError("PDF asset manifest requires unique relative artifact names")
        assets.verify()
        arguments["capture_sources"] = pdf_capture_operation_sources(
            recipe,
            assets,
            directory=location(capture.directory),
            nemotron_endpoint=capture.nemotron_endpoint,
            require_nemotron_handoff=capture.require_nemotron_handoff,
        )
        if capture.enrichment_options is not None:
            from .pdf_transforms import PdfEnrichmentOptions, pdf_transform_operation_sources

            options = PdfEnrichmentOptions.model_validate(
                yaml.safe_load(read(capture.enrichment_options))
            )
            arguments["pdf_enrichment_sources"] = pdf_transform_operation_sources(
                "enriched",
                recipe=recipe,
                assets=assets,
                options=options,
                directory=location(capture.directory),
                nemotron_endpoint=capture.nemotron_endpoint,
            )
        if capture.recognition is not None:
            from corpus_structure.ingest.pdf_recognition import NemotronRecipe

            from .pdf_transforms import (
                PdfIntegrationOptions,
                PdfRecognitionResources,
                pdf_transform_operation_sources,
            )

            selected = capture.recognition
            recognition_recipe = NemotronRecipe(**yaml.safe_load(read(selected.recipe)))
            options = PdfIntegrationOptions.model_validate(yaml.safe_load(read(selected.options)))
            resources = PdfRecognitionResources.model_validate(
                yaml.safe_load(read(selected.resources))
            )
            # Resource paths are explicit acquisition locations; interpreter and worker bytes
            # are retained and authenticated by the effect profile before every invocation.
            resources = resources.model_copy(
                update={
                    "python": str(location(resources.python)),
                    "script": str(location(resources.script)),
                    "receipts": str(location(resources.receipts)),
                }
            )
            if Path(resources.script).is_relative_to(root):
                read(str(Path(resources.script).relative_to(root)))
            arguments["pdf_integration_sources"] = pdf_transform_operation_sources(
                "integrated",
                options=options,
                recognition_recipe=recognition_recipe,
                resources=resources,
                directory=location(capture.directory),
            )
    return arguments


def prepare_data_operation_inputs(
    root: Path, manifest: str, *, proposed: dict[str, bytes] | None = None
):
    from .prepare import prepare_release

    acquired = acquire_data_operation_inputs(root, manifest, proposed=proposed)
    return (
        acquired.bundle,
        acquired.dependencies,
        acquired.profile,
        prepare_release(acquired.bundle, acquired.dependencies, acquired.profile),
    )
