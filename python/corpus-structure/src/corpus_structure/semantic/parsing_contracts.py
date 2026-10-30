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
    for name in (
        "prepare_parsing_product",
        "publish_parsing_product",
        "read_parsing_product",
        "decompose_source",
        "recognize_html",
        "project_canonical",
    ):
        model.require_operation(name)
    supported_capabilities = {
        "source/raw-partition",
        "source/canonical-partition",
        "source/html-structure",
        "source/partial-origin",
        "mapping/decode",
        "mapping/normalize",
        "mapping/copy",
        "mapping/synthetic",
        "mapping/exclude",
    }
    if len(model.parsing_adapters) != 1:
        _fail(
            "unsupported_parsing_adapter",
            "parsing_adapters",
            "declare the qualified html5lib-source-1 adapter profile",
        )
    adapter = model.parsing_adapters[0]
    if (
        adapter.adapter_id != "html5lib-source-1"
        or adapter.implementation_revision != "source-capture-1"
        or adapter.frontend_revision != "html5lib-1.1/lxml-6.1.3"
        or adapter.grammar_revision is not None
        or adapter.coordinate_fidelity != "exact"
        or adapter.repair_policy != "html5lib-html5"
        or adapter.ambiguity_policy != "explicit-partial"
        or adapter.lifetime != "operation"
        or adapter.provenance_universe != "canonical_output"
        or set(adapter.capabilities) != supported_capabilities
    ):
        _fail(
            "unsupported_parsing_adapter",
            "parsing_adapters/" + adapter.adapter_id,
            "qualify adapter revision/capabilities and its native admission "
            "before changing this profile",
        )
