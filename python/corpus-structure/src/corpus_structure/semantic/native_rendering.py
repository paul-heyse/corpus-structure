"""Deterministic native composition from the complete captured material population."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .target_installation import NativeGeneratorInputs, TargetInstallation


def render_captured(inputs: NativeGeneratorInputs) -> TargetInstallation:
    """Interpret exact captured inputs privately, then render their native products."""
    from corpus_structure.model.compiled import CompiledModel, model_request_scope

    from .pdf_domain import prepare_native_pdf_sources
    from .target_installation import render_target_installation
    from .value_codec import VALUE_CODEC_SOURCE, decimal_digit_limit

    model = CompiledModel(inputs.model_sources)
    with model_request_scope(model):
        owned = model.exact_physical(
            dict(inputs.physical_sources), linkml_types=inputs.linkml_types
        )
        pdf_sources = prepare_native_pdf_sources(inputs)
        codec_model = CompiledModel(
            ((VALUE_CODEC_SOURCE, dict(inputs.logical_sources)[VALUE_CODEC_SOURCE]),)
        )
        return render_target_installation(
            inputs,
            target_metadata=owned,
            pdf_sources=pdf_sources,
            decimal_digits=decimal_digit_limit(codec_model),
        )
