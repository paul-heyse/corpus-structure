"""Acquire explicitly named target inputs without importing their Python modules.

The manifest is an acquisition recipe. Only captured semantic/source bytes enter
the effective model; checkout paths do not become operation identity.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

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
    organization_policy: str | None = None
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
    sentence_configuration: str | None = Field(default=None, min_length=1)
    sentence_selection: str | None = Field(default=None, min_length=1)
    hanlp_selection: str | None = Field(default=None, min_length=1)
    learned_selections: dict[Literal["maverick", "dipo", "d1", "gliner"], str] | None = None
    construction: str | None = None
    math: str | None = None
    external_protocol: str | None = None
    visual: bool = False
    downstream: bool = False
    m1: LiteralM1Inputs | None = None
    contextual_encoder: ContextualEncoderInputs | None = None
    contextual_retrieval_options: str | None = None
    capture: PrimaryCaptureInputs | None = None


class DataOperationInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["data-operation-inputs-v1"]
    root: str = Field(min_length=1)
    schemas: tuple[NamedInput, ...]
    declarations: tuple[NamedInput, ...] = ()
    dependencies: tuple[NamedInput, ...] = ()
    ontology_sources: tuple[str, ...] = ()
    python: PythonInputs | None = None
    source_bindings: bool = False
    pdf_contracts: bool = False
    protected_references: bool = False
    protected_record_policy: bool = False
    primary_profile: PrimaryProfileInputs | None = None
    requested_operations: tuple[str, ...] = ()
    workflow: Literal["capture", "characterize", "phase0"] | None = None

    @model_validator(mode="after")
    def selected_ontology_dependencies(self):
        if self.workflow is not None and self.primary_profile is None:
            raise ValueError("workflow operation selection requires a primary profile")
        if len(set(self.requested_operations)) != len(self.requested_operations) or any(
            not identifier.strip() for identifier in self.requested_operations
        ):
            raise ValueError("requested operations require distinct nonempty identifiers")
        if len(set(self.ontology_sources)) != len(self.ontology_sources) or not set(
            self.ontology_sources
        ) <= {item.name for item in self.dependencies}:
            raise ValueError("ontology sources must select unique declared dependency names")
        return self


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
    if declared.protected_references:
        from .primary_operations import combine_primary_sources
        from .selected_reference_sources import (
            selected_reference_inputs,
            selected_reference_operation_sources,
        )

        bundle = selected_reference_inputs(bundle)
        reference_sources = selected_reference_operation_sources()
        sources = (
            reference_sources
            if sources is None
            else combine_primary_sources(sources, reference_sources)
        )
    declarations = artifacts(declared.declarations)
    if declared.protected_record_policy:
        from corpus_structure.evaluate.declared_record_policy import (
            protected_record_policy_kind_declarations,
            record_policy_inputs,
            record_policy_operation_sources,
        )

        from .primary_operations import combine_primary_sources
        from .reading_resolution_products import (
            reading_resolution_declarations,
            reading_resolution_operation_sources,
        )
        from .record_policy_authority import (
            record_policy_authorization_sources,
            record_policy_kind_declarations,
        )

        bundle = record_policy_inputs(bundle)
        policy_sources = combine_primary_sources(
            reading_resolution_operation_sources(),
            record_policy_operation_sources(),
            record_policy_authorization_sources(),
        )
        sources = (
            policy_sources if sources is None else combine_primary_sources(sources, policy_sources)
        )
        declarations = (
            *declarations,
            record_policy_kind_declarations(),
            protected_record_policy_kind_declarations(),
        )
        if declared.primary_profile is None or not declared.primary_profile.downstream:
            declarations = (*declarations, reading_resolution_declarations())
    from .data_operation_artifacts import capture_port_generator_sources
    from .data_operation_storage import native_operation_declarations, native_protocol_sources

    if declared.primary_profile is not None:
        from .primary_acquisition import requested_source_modules
        from .primary_operations import primary_operation_inputs, primary_operation_targets

        capture = declared.primary_profile.capture
        selected_operations = declared.requested_operations
        if not selected_operations and declared.workflow is not None:
            selected_operations = primary_operation_targets(
                declared.workflow,
                captured=capture is not None,
                organized=capture is not None and capture.organization_policy is not None,
                pdf_mode=(
                    "integrated"
                    if capture is not None and capture.recognition is not None
                    else "enriched"
                    if capture is not None and capture.enrichment_options is not None
                    else "standard"
                ),
            )

        def additional_declarations():
            if declared.primary_profile.external_protocol is None:
                return ()
            from .external_extraction import rich_external_declarations

            return (
                rich_external_declarations(
                    _external_protocol(read(declared.primary_profile.external_protocol))
                ),
            )

        selected_modules = (
            requested_source_modules(
                selected_operations,
                organized=capture is not None and capture.organization_policy is not None,
                extra_sources=sources,
                declarations=declarations,
                resolve_declarations=additional_declarations,
            )
            if selected_operations
            else None
        )
        primary = _acquire_primary_profile(
            declared.primary_profile, read, root, selected_modules=selected_modules
        )
        composed = primary_operation_inputs(
            bundle,
            **primary,
            dependencies=ResolvedDependencies(
                artifacts(declared.dependencies), ontology_sources=declared.ontology_sources
            ),
            extra_sources=sources,
            declarations=declarations,
            requested_operations=selected_operations,
            selected_modules=selected_modules,
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
        ResolvedDependencies(
            (*artifacts(declared.dependencies), *native, *generator),
            ontology_sources=declared.ontology_sources,
        ),
        (
            *declarations,
            native_operation_declarations(native),
        ),
        sources,
    )
    if declared.pdf_contracts:
        from .pdf_domain import pdf_domain_dependencies

        dependencies = pdf_domain_dependencies(dependencies)
    if declared.requested_operations:
        from .identity import canonical_bytes

        dependencies = replace(
            dependencies,
            artifacts=(
                *dependencies.artifacts,
                SourceArtifact(
                    "operation-selection.json", canonical_bytes(declared.requested_operations)
                ),
            ),
        )
    return AcquiredDataOperationInputs(
        bundle,
        dependencies,
        PreparationProfile(version="semantic-2"),
        tuple(sorted(captured.items())),
    )


def _acquire_primary_profile(
    profile: PrimaryProfileInputs,
    read: Callable[[str], bytes],
    root: Path,
    *,
    selected_modules: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Reconstitute explicit frozen selections; never acquire a default provider."""
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import (
        NativeProfile,
        NativeSelection,
        native_asset_files,
    )

    from .file_custody import verified_file
    from .identity import canonical_bytes

    def location(name: str) -> Path:
        path = Path(name)
        return (path if path.is_absolute() else root / path).resolve()

    receipts_type = TypeAdapter(tuple[tuple[str, str, tuple[int, int, int, int, int], bool], ...])

    def selection(name: str, provider: str):
        value = json.loads(read(name))
        if not isinstance(value, dict) or set(value) != {
            "profile",
            "fingerprint",
            "assets",
            "asset_custody",
        }:
            raise ValueError("native selection must use the complete NativeSelection declaration")
        native = NativeProfile.from_content(canonical_bytes(value["profile"]))
        if native.provider != provider or native.fingerprint != value["fingerprint"]:
            raise ValueError("native selection provider or captured fingerprint differs")
        assets = location(value["assets"])
        if not assets.is_dir():
            raise ValueError("explicit native selection assets are unavailable")
        receipts = receipts_type.validate_json(canonical_bytes(value["asset_custody"]), strict=True)
        expected_files = native_asset_files(native.wire, assets)
        if {(receipt[0], receipt[1]) for receipt in receipts} != {
            (str(path), digest) for path, digest in expected_files
        } or len(receipts) != len(expected_files):
            raise ValueError("native selection custody differs from declared file population")
        # Configuration files are not the private parent/child handoff. Establish
        # local content custody instead of trusting persisted metadata as proof.
        for path, digest in expected_files:
            verified_file(path, digest)
        return NativeSelection(native, assets)

    from .primary_acquisition import needs

    arguments: dict[str, Any] = dict(sentence_configuration=None, hanlp_selection=None)
    needs_sentences = needs(
        selected_modules,
        "methods.sentence_evidence",
        "methods.canonical_sentences",
        "methods.hanlp_evidence",
        "methods.m1_declared",
    )
    if needs_sentences:
        if profile.sentence_configuration is None or profile.sentence_selection is None:
            raise ValueError(
                "selected sentence operation requires its sentence configuration and provider selection"
            )
        configuration = SentenceConfig.model_validate(
            yaml.safe_load(read(profile.sentence_configuration))
        )
        sentence = selection(profile.sentence_selection, "spacy")
        if sentence.native.parameters != configuration.model_dump(mode="json"):
            raise ValueError("sentence configuration differs from its frozen native selection")
        arguments: dict[str, Any] = dict(
            sentence_configuration=configuration,
            sentence_selection=sentence,
        )
    if needs(selected_modules, "methods.hanlp_evidence"):
        if profile.hanlp_selection is None:
            raise ValueError("selected HanLP operation requires its explicit provider profile")
        arguments["hanlp_selection"] = selection(profile.hanlp_selection, "hanlp")
    arguments.update(downstream=profile.downstream, visual=profile.visual)
    if profile.learned_selections is not None and needs(
        selected_modules,
        "methods.learned_primary",
        "methods.clause_classification_declared",
        "methods.definition_components_declared",
    ):
        if set(profile.learned_selections) != {"maverick", "dipo", "d1", "gliner"}:
            raise ValueError("learned primary profile requires all four explicit selections")
        arguments["learned_selections"] = {
            provider: selection(path, provider)
            for provider, path in profile.learned_selections.items()
        }
    if profile.construction is not None and needs(
        selected_modules, "methods.construction_characterization"
    ):
        from .construction_products import ConstructionOptions

        arguments["construction_options"] = ConstructionOptions.model_validate(
            yaml.safe_load(read(profile.construction))
        )
    if profile.math is not None and needs(
        selected_modules, "methods.math.declared", "methods.math.analysis"
    ):
        from .declared_math_products import DeclaredMathOptions

        arguments["math_options"] = DeclaredMathOptions.model_validate(
            yaml.safe_load(read(profile.math))
        )
    if profile.m1 is not None and needs(selected_modules, "methods.m1_declared"):
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
    if profile.contextual_retrieval_options is not None and needs(
        selected_modules,
        "methods.contextual_declared",
        "methods.contextual_encoding",
        "methods.contextual_scoring",
        "methods.contextual_targets",
        "methods.contextual_witnesses",
    ):
        from .contextual_numerics import RetrievalNumericalPolicy

        if not profile.downstream and profile.contextual_encoder is None:
            raise ValueError(
                "contextual retrieval options require downstream or encoder dependencies"
            )
        arguments["contextual_retrieval_options"] = RetrievalNumericalPolicy.model_validate(
            yaml.safe_load(read(profile.contextual_retrieval_options))
        )
    if profile.contextual_encoder is not None and needs(
        selected_modules, "methods.contextual_encoding"
    ):
        from corpus_structure.methods.contextual_embeddings import EncoderProfile

        from .contextual_encoder import ContextualEncoderSelection

        encoder_profile = TypeAdapter(EncoderProfile).validate_json(
            canonical_bytes(yaml.safe_load(read(profile.contextual_encoder.profile))),
            strict=True,
        )
        arguments["contextual_encoder"] = ContextualEncoderSelection.acquire(
            encoder_profile, location(profile.contextual_encoder.model_path)
        )
    if profile.external_protocol is not None and needs(
        selected_modules, "methods.external_extraction"
    ):
        arguments["external_protocol"] = _external_protocol(read(profile.external_protocol))
    if profile.capture is not None and (
        selected_modules is None
        or any(module.startswith("corpus_structure.ingest.pdf_") for module in selected_modules)
    ):
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
        if capture.organization_policy is not None and needs(
            selected_modules, "ingest.pdf_organization_operation"
        ):
            from corpus_structure.ingest.pdf_hierarchy import SectionPolicy

            from .pdf_transforms import pdf_transform_operation_sources

            policy = TypeAdapter(SectionPolicy).validate_python(
                yaml.safe_load(read(capture.organization_policy))
            )
            arguments["pdf_organization_sources"] = pdf_transform_operation_sources(
                "organized", options=policy, directory=location(capture.directory)
            )
        input_operation = (
            "source.pdf_sections/organize"
            if capture.organization_policy is not None
            else "source.pdf/capture"
        )
        if capture.enrichment_options is not None and needs(
            selected_modules,
            "ingest.pdf_enrichment_operation",
            "ingest.pdf_organized_enriched_operation",
            "ingest.pdf_raw_enriched_operation",
        ):
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
                input_operation=input_operation,
            )
        if capture.recognition is not None and needs(
            selected_modules,
            "ingest.pdf_observation_operation",
            "ingest.pdf_integration_operation",
            "ingest.pdf_organized_integrated_operation",
            "ingest.pdf_raw_integrated_operation",
        ):
            from corpus_structure.ingest.pdf_recognition import NemotronRecipe

            from .pdf_transforms import (
                PdfIntegrationProfile,
                PdfRecognitionResources,
                pdf_transform_operation_sources,
            )

            selected = capture.recognition
            recognition_recipe = NemotronRecipe(**yaml.safe_load(read(selected.recipe)))
            options = PdfIntegrationProfile.model_validate(yaml.safe_load(read(selected.options)))
            resources = PdfRecognitionResources.model_validate(
                yaml.safe_load(read(selected.resources))
            )
            # Resource paths are explicit acquisition locations; interpreter and worker bytes
            # are retained and authenticated by the effect profile before every invocation.
            resources = resources.model_copy(
                update={
                    # Invocation through a venv symlink selects its pyvenv.cfg and packages.
                    # Resolving the executable itself would instead launch the base interpreter.
                    "python": os.path.abspath(root / resources.python),
                    "script": str(location(resources.script)),
                    "receipts": str(location(resources.receipts)),
                }
            )
            if Path(resources.script).is_relative_to(root):
                read(str(Path(resources.script).relative_to(root)))
            arguments["pdf_integration_sources"] = pdf_transform_operation_sources(
                "integrated",
                options=options.integration,
                recognition_options=options.recognition,
                recognition_recipe=recognition_recipe,
                resources=resources,
                directory=location(capture.directory),
                input_operation=input_operation,
            )
    return arguments


def _external_protocol(content: bytes):
    from dataclasses import fields

    from .data_operation_model import ExternalExecutorContract
    from .identity import canonical_bytes

    selected = yaml.safe_load(content)
    if not isinstance(selected, dict) or set(selected) != {
        field.name for field in fields(ExternalExecutorContract)
    }:
        raise ValueError(
            "external protocol requires its exact declared actor, model, instructions and reference scope"
        )
    return TypeAdapter(ExternalExecutorContract).validate_json(
        canonical_bytes(selected), strict=True
    )


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
