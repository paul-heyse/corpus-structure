"""Finite supported native PDF, text and mathematical adapter bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .contracts import ExecutionModelProducts


def validate_native_adapters(model: ExecutionModelProducts) -> None:
    """Refuse a declaration outside the actual bounded endpoint implementation."""
    from .contracts import _fail

    # Future declarations express required distinctions without advertising a producer.
    for name in ("prepare_parsing_text", "interpret_parsing_math", "assess_parsing_math"):
        model.operation(name)
    for name in (
        "convert_pdf",
        "organize_pdf",
        "project_pdf_source",
        "publish_source_view",
        "publish_characterization",
        "read_characterization",
        "read_characterization_inventory",
        "read_source_view",
    ):
        model.require_operation(name)
    supported_ids = {
        "docling-pdf-source-1",
        "lark-structure-1",
        "lark-math-3",
    }
    if (
        not model.parsing_adapters
        or len({a.adapter_id for a in model.parsing_adapters}) != len(model.parsing_adapters)
        or not {a.adapter_id for a in model.parsing_adapters} <= supported_ids
    ):
        _fail(
            "unsupported_parsing_adapter",
            "parsing_adapters",
            "declare a qualified native PDF or positioned text/math adapter",
        )
    profiles = {
        "docling-pdf-source-1": (
            "docling-standard-pdf-v1",
            "docling-2.148.0/core-2.106.0",
            None,
            "native-normalize-before-identity",
            "explicit-partial",
            {
                "source/native-document",
                "source/native-items",
                "source/pdf-regions",
                "source/section-projection",
            },
        ),
        "lark-structure-1": (
            "text-structure-2",
            "sympy-1.14.0-lark-1.3.1",
            None,
            "strict-malformed",
            "explicit-partial",
            {"text/lexical-partition", "text/parse-view", "tex/structure"},
        ),
        "lark-math-3": (
            "prepared-math-3",
            "lark-1.3.1/sympy-1.14.0",
            "extended-lark-3",
            "refuse-invalid",
            "explicit-alternatives",
            {
                "math/lexical",
                "math/structure",
                "math/syntax",
                "math/interpretation",
                "math/assessment",
            },
        ),
    }
    for adapter in model.parsing_adapters:
        if adapter.adapter_id not in profiles:
            continue
        revision, frontend, grammar, repair, ambiguity, capabilities = profiles[adapter.adapter_id]
        if (
            adapter.implementation_revision != revision
            or adapter.frontend_revision != frontend
            or adapter.grammar_revision != grammar
            or adapter.repair_policy != repair
            or adapter.ambiguity_policy != ambiguity
            or set(adapter.capabilities) != capabilities
            or adapter.lifetime != "operation"
            or adapter.coordinate_fidelity != "exact"
            or adapter.provenance_universe != "canonical_output"
        ):
            _fail(
                "unsupported_parsing_adapter",
                "parsing_adapters/" + adapter.adapter_id,
                "qualify the actual finite producer profile before changing it",
            )
