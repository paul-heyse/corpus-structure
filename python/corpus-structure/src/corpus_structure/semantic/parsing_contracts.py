"""Finite implementation admission for the existing parsing operation/relationship model.

The catalog owns role semantics. This module states the independently implemented profile;
runtime and native consumers read the admitted catalog instead of restating its roles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .contracts import ExecutionModelProducts, RelationshipDefinition

PARSING_RELATION_KINDS = (
    "contains",
    "structural_parent",
    "reference",
    "binds",
    "derived_from",
    "sequence",
    "attribute_of",
    "text_of",
)
FUTURE_PARSING_OPERATIONS = (
    "prepare_parsing_text",
    "interpret_parsing_math",
    "assess_parsing_math",
)


def parsing_relationships(model: ExecutionModelProducts) -> dict[str, RelationshipDefinition]:
    return {
        kind: next(r for r in model.relationships if r.id == "parsing_" + kind)
        for kind in PARSING_RELATION_KINDS
    }


def validate_parsing_contracts(model: ExecutionModelProducts) -> None:
    """Refuse a declaration outside the actual bounded endpoint implementation."""
    from .contracts import _fail

    support = {
        "contains": ("parent", "child"),
        "structural_parent": ("parent", "child"),
        "reference": ("source", "target"),
        "binds": ("invocation", "definition"),
        "derived_from": ("target", "source"),
        "sequence": ("source", "target"),
        "attribute_of": ("attribute", "owner"),
        "text_of": ("text", "owner"),
    }
    for kind, relation in parsing_relationships(model).items():
        expected_concept = (
            "ParsingNode"
            if kind in {"contains", "structural_parent", "attribute_of", "text_of"}
            else "ParsingOccurrence"
        )
        if (
            tuple(e.role for e in relation.endpoints) != support[kind]
            or any(
                e.minimum != 1 or e.maximum != 1 or e.unresolved or e.concept != expected_concept
                for e in relation.endpoints
            )
            or relation.multiplicity != "sequence"
            or relation.reference_scope != "execution"
            or relation.identity_kind != "occurrence"
            or relation.identity_context != ("release", "build", "relationship_id")
        ):
            _fail(
                "unsupported_parsing_relationship",
                "relationships/" + relation.id,
                "qualify endpoint support and native enforcement before changing "
                "this relationship profile",
            )
    # Future declarations express required distinctions without advertising a producer.
    for name in FUTURE_PARSING_OPERATIONS:
        model.operation(name)
    for name in ("convert_pdf", "organize_pdf", "project_pdf_source", "publish_source_view", "read_source_view"):
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
            "docling-2.145.0/core-2.105.0",
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
