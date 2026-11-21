"""Input acquisition and cache selection outside deterministic native generation."""

from dataclasses import dataclass

from sqlalchemy import MetaData

from corpus_structure.caches import declare

from .target_installation import (
    NativeGeneratorInputs,
    TargetInstallation,
    capture_trigger_inputs,
)
from .types import SourceArtifact


def _installation_key(inputs: NativeGeneratorInputs) -> bytes:
    from .native_program_store import input_key

    if not inputs.complete:
        raise ValueError("native generator identity is incomplete")
    key = input_key(inputs)
    if key is None:
        raise ValueError("native generator identity did not produce an input key")
    return key


@dataclass(frozen=True)
class _GenerationFailure:
    error: Exception


def _render_captured(inputs: NativeGeneratorInputs) -> TargetInstallation:
    """Authenticate all preparation and rendering under the same captured custody."""
    from .native_program_store import capture_generator_custody
    from .native_rendering import render_captured

    with capture_generator_custody(inputs.code_identity, closed=True):
        return render_captured(inputs)


@declare("native-installation", "program_sets", key=_installation_key)
def _held_target_installation(inputs: NativeGeneratorInputs):
    from .code_reuse import record_code_reuse

    try:
        result = _render_captured(inputs)
        record_code_reuse(
            inputs.code_identity,
            entry_point="corpus_structure.semantic.target_installation.render_target_installation",
            tier="native-programs",
            outcome="derived",
        )
        return result
    except (ValueError, TypeError) as error:
        return _GenerationFailure(error)


def capture_generator_inputs(
    selected: MetaData,
    *,
    logical_sources: dict[str, bytes] | None = None,
    pdf_actions: SourceArtifact | None = None,
    pdf_sources: tuple[SourceArtifact, ...] | None = None,
    extra_sources: tuple[SourceArtifact, ...] = (),
) -> NativeGeneratorInputs:
    """Acquire every effective model, runtime, resource and provenance input once."""
    from corpus_structure.model.compiled import running_model

    from .determinants import analysis_runtime, determinant_version
    from .native_program_store import (
        capture_generator_code,
        capture_generator_sources,
    )
    from .native_protocol_authoring import capture_native_package_resource, native_logical_sources

    if not selected.info.get("physical_sources") or not isinstance(
        selected.info.get("physical_linkml_types"), bytes
    ):
        raise ValueError("native installation requires captured physical inputs and LinkML types")
    if pdf_sources is not None and pdf_actions is not None:
        raise ValueError("select PDF action input or an already captured PDF source cohort")
    model = running_model()
    # Explicit target and logical selections own their corresponding model bytes.
    # Ambient declarations only supply the unaffected remainder of the capture.
    effective = {
        **model.sources,
        **selected.info["physical_sources"],
        **(logical_sources or {}),
        "linkml:types": selected.info["physical_linkml_types"],
    }
    model_inputs = tuple(sorted(effective.items()))
    logical = (
        native_logical_sources(model_sources=dict(model_inputs))
        if logical_sources is None
        else logical_sources
    )
    code_identity = capture_generator_code()
    resource_sources = (capture_native_package_resource(),)
    return NativeGeneratorInputs(
        physical_sources=tuple(sorted(selected.info["physical_sources"].items())),
        linkml_types=selected.info["physical_linkml_types"],
        logical_sources=tuple(sorted(logical.items())),
        model_sources=model_inputs,
        pdf_actions=pdf_actions,
        pdf_sources=pdf_sources,
        extra_sources=tuple(extra_sources),
        resource_sources=resource_sources,
        module_sources=capture_generator_sources(code_identity),
        analysis_runtime=analysis_runtime(),
        native_library_runtime=tuple(
            (name, determinant_version(name))
            for name in ("pglast", "sqlalchemy", "linkml-runtime", "networkx")
        ),
        code_identity=code_identity,
        trigger_inputs=capture_trigger_inputs(selected),
    )


def capture_target_installation(
    selected: MetaData,
    *,
    logical_sources: dict[str, bytes] | None = None,
    pdf_actions: SourceArtifact | None = None,
    pdf_sources: tuple[SourceArtifact, ...] | None = None,
    extra_sources: tuple[SourceArtifact, ...] = (),
) -> TargetInstallation:
    from .code_reuse import record_code_reuse
    from .native_program_store import capture_generator_custody

    inputs = capture_generator_inputs(
        selected,
        logical_sources=logical_sources,
        pdf_actions=pdf_actions,
        pdf_sources=pdf_sources,
        extra_sources=extra_sources,
    )
    record_code_reuse(
        inputs.code_identity,
        entry_point="corpus_structure.semantic.target_installation.render_target_installation",
        tier="native-programs",
        outcome="unknown" if inputs.complete else "withheld",
    )
    if not inputs.complete:
        return _render_captured(inputs)
    with capture_generator_custody(inputs.code_identity):
        result = _held_target_installation(inputs)
    if isinstance(result, _GenerationFailure):
        raise result.error
    return result
