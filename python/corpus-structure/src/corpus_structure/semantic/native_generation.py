"""Input acquisition and cache selection outside deterministic native generation."""

from dataclasses import dataclass

from sqlalchemy import MetaData

from corpus_structure.caches import declare

from .target_installation import (
    NativeGeneratorInputs,
    TargetInstallation,
    render_target_installation,
)
from .types import SourceArtifact


def _installation_key(inputs: NativeGeneratorInputs) -> bytes:
    from .native_program_store import input_key

    if not inputs.complete:
        raise ValueError("native generator identity is incomplete")
    key = input_key(inputs, include_format=False)
    if key is None:
        raise ValueError("native generator identity did not produce an input key")
    return key


@dataclass(frozen=True)
class _GenerationFailure:
    error: Exception


@declare("native-installation", "program_sets", key=_installation_key)
def _held_target_installation(inputs: NativeGeneratorInputs):
    from corpus_structure.schema.physical import compile_physical

    owned = compile_physical(dict(inputs.physical_sources), linkml_types=inputs.linkml_types)
    try:
        from .native_program_store import (
            capture_generator_custody,
            input_key,
            load_installation,
            save_installation,
        )

        key = input_key(inputs, include_format=True)
        retained = None if key is None else load_installation(key, owned)
        if retained is not None:
            return retained
        with capture_generator_custody(inputs.code_identity, closed=True):
            result = render_target_installation(inputs)
        if key is not None:
            save_installation(key, result)
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

    from .data_operation_storage import capture_native_package_resource, native_logical_sources
    from .determinants import analysis_runtime, determinant_version
    from .native_program_store import (
        capture_generator_code,
        capture_generator_sources,
    )

    if not selected.info.get("physical_sources") or not isinstance(
        selected.info.get("physical_linkml_types"), bytes
    ):
        raise ValueError("native installation requires captured physical inputs and LinkML types")
    if pdf_sources is not None and pdf_actions is not None:
        raise ValueError("select PDF action input or an already captured PDF source cohort")
    model = running_model()
    model_inputs = tuple(sorted(model.sources.items()))
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
    )


def capture_target_installation(
    selected: MetaData,
    *,
    logical_sources: dict[str, bytes] | None = None,
    pdf_actions: SourceArtifact | None = None,
    pdf_sources: tuple[SourceArtifact, ...] | None = None,
    extra_sources: tuple[SourceArtifact, ...] = (),
) -> TargetInstallation:
    from .native_program_store import capture_generator_custody

    inputs = capture_generator_inputs(
        selected,
        logical_sources=logical_sources,
        pdf_actions=pdf_actions,
        pdf_sources=pdf_sources,
        extra_sources=extra_sources,
    )
    if not inputs.complete:
        return render_target_installation(inputs)
    with capture_generator_custody(inputs.code_identity):
        result = _held_target_installation(inputs)
    if isinstance(result, _GenerationFailure):
        raise result.error
    return result
